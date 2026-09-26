"""
OpenScore Finance — Document Extraction Service
Orchestrates secure file processing, Gemini 1.5 Flash structured OCR, and immediate in-memory purge.
"""

from __future__ import annotations

import logging
import gc
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.gemini_client import extract_financial_data_from_image
from app.models.database import ExtractedData, CreditApplication, ApplicationStatus, AuditLog

logger = logging.getLogger(__name__)


async def process_document_extraction(
    db: AsyncSession,
    application_id: int,
    file_content: bytes,
    filename: str,
    mime_type: str,
) -> Optional[ExtractedData]:
    """
    1. Send document to Gemini 1.5 Flash for structured data extraction.
    2. Map structured response into ExtractedData model.
    3. Purge raw file bytes from memory immediately.
    4. Transition application status and record audit log.
    """
    try:
        # Step 1: Send to Gemini AI OCR
        extraction_dict = await extract_financial_data_from_image(
            image_bytes=file_content,
            filename=filename,
            mime_type=mime_type
        )

        # Immediate memory purge of original payload
        del file_content
        gc.collect()

        if not extraction_dict:
            logger.error(f"Extraction returned empty result for application {application_id}")
            return None

        # Step 2: Query existing extraction record
        stmt = select(ExtractedData).where(ExtractedData.application_id == application_id)
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

        full_name = extraction_dict.get("nom_complet") or f"{extraction_dict.get('prenom', '')} {extraction_dict.get('nom', '')}".strip() or None
        date_of_birth = extraction_dict.get("date_naissance")
        id_number = extraction_dict.get("numero_piece")
        id_type = extraction_dict.get("type_piece")
        monthly_revenue = extraction_dict.get("revenus_estimes")
        monthly_expenses = extraction_dict.get("depenses_estimees")
        existing_debt = extraction_dict.get("dettes_existantes", 0.0)
        years_in_business = extraction_dict.get("anciennete_activite_annees")
        regularity_months = extraction_dict.get("regularite_revenus_mois", 12)
        reg_number = extraction_dict.get("numero_registre_commerce")
        start_date = extraction_dict.get("date_debut_activite")
        confidence = float(extraction_dict.get("niveau_confiance", 0.85))

        if existing:
            # Merge with existing values without overwriting non-nulls with nulls
            existing.full_name = full_name or existing.full_name
            existing.date_of_birth = date_of_birth or existing.date_of_birth
            existing.id_number = id_number or existing.id_number
            existing.id_type = id_type or existing.id_type
            existing.monthly_revenue = monthly_revenue if monthly_revenue is not None else existing.monthly_revenue
            existing.monthly_expenses = monthly_expenses if monthly_expenses is not None else existing.monthly_expenses
            existing.existing_debt = existing_debt if existing_debt is not None else existing.existing_debt
            existing.business_registration_number = reg_number or existing.business_registration_number
            existing.business_start_date = start_date or existing.business_start_date
            existing.years_in_business = years_in_business if years_in_business is not None else existing.years_in_business
            existing.revenue_regularity_months = regularity_months if regularity_months is not None else existing.revenue_regularity_months
            existing.extraction_confidence = max(confidence, existing.extraction_confidence or 0.0)
            existing.raw_extraction_json = extraction_dict
            existing.extracted_at = datetime.now(timezone.utc)
            extracted = existing
        else:
            extracted = ExtractedData(
                application_id=application_id,
                full_name=full_name,
                date_of_birth=date_of_birth,
                id_number=id_number,
                id_type=id_type,
                monthly_revenue=monthly_revenue,
                monthly_expenses=monthly_expenses,
                existing_debt=existing_debt or 0.0,
                business_registration_number=reg_number,
                business_start_date=start_date,
                years_in_business=years_in_business,
                revenue_regularity_months=regularity_months,
                extraction_confidence=confidence,
                raw_extraction_json=extraction_dict,
                extracted_at=datetime.now(timezone.utc),
            )
            db.add(extracted)

        # Step 3: Update application status
        stmt_app = select(CreditApplication).where(CreditApplication.id == application_id)
        res_app = await db.execute(stmt_app)
        application = res_app.scalar_one_or_none()
        if application:
            application.status = ApplicationStatus.PENDING_VERIFICATION
            application.updated_at = datetime.now(timezone.utc)

        # Step 4: Audit trail
        audit = AuditLog(
            application_id=application_id,
            action="document_extracted",
            details={
                "filename": filename,
                "document_type": extraction_dict.get("document_type", "autre"),
                "confidence": confidence,
                "notes_audit": extraction_dict.get("notes_audit"),
            },
        )
        db.add(audit)

        await db.commit()
        await db.refresh(extracted)
        logger.info(f"Extraction successfully saved for application {application_id}, confidence: {confidence:.2f}")
        return extracted

    except Exception as e:
        await db.rollback()
        logger.error(f"Error in extraction service for application {application_id}: {e}")
        raise
