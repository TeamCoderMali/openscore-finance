"""
OpenScore Finance — Document Extraction Service
Orchestrates file upload, Gemini extraction, data persistence, and file purge.
"""

import logging
import os
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.gemini_client import extract_document_data
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
    1. Send document to Gemini for extraction
    2. Parse and store extracted data
    3. Purge temporary file from memory
    4. Update application status
    """
    try:
        # Step 1: Extract via Gemini
        extraction_result = await extract_document_data(file_content, filename, mime_type)

        if not extraction_result:
            logger.error(f"Extraction returned None for application {application_id}")
            return None

        # Step 2: Check if extracted data already exists for this application
        stmt = select(ExtractedData).where(ExtractedData.application_id == application_id)
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

        identity = extraction_result.get("identity", {})
        financial = extraction_result.get("financial", {})
        confidence = extraction_result.get("confidence", 0.0)

        if existing:
            # Merge new extraction with existing data (fill nulls)
            existing.full_name = identity.get("full_name") or existing.full_name
            existing.date_of_birth = identity.get("date_of_birth") or existing.date_of_birth
            existing.id_number = identity.get("id_number") or existing.id_number
            existing.id_type = identity.get("id_type") or existing.id_type
            existing.monthly_revenue = financial.get("monthly_revenue") or existing.monthly_revenue
            existing.monthly_expenses = financial.get("monthly_expenses") or existing.monthly_expenses
            existing.existing_debt = financial.get("existing_debt", 0) or existing.existing_debt
            existing.business_registration_number = financial.get("business_registration_number") or existing.business_registration_number
            existing.business_start_date = financial.get("business_start_date") or existing.business_start_date
            existing.years_in_business = financial.get("years_in_business") or existing.years_in_business
            existing.revenue_regularity_months = financial.get("revenue_regularity_months") or existing.revenue_regularity_months
            existing.extraction_confidence = max(confidence, existing.extraction_confidence or 0)
            existing.raw_extraction_json = extraction_result
            existing.extracted_at = datetime.now(timezone.utc)
            extracted = existing
        else:
            extracted = ExtractedData(
                application_id=application_id,
                full_name=identity.get("full_name"),
                date_of_birth=identity.get("date_of_birth"),
                id_number=identity.get("id_number"),
                id_type=identity.get("id_type"),
                monthly_revenue=financial.get("monthly_revenue"),
                monthly_expenses=financial.get("monthly_expenses"),
                existing_debt=financial.get("existing_debt", 0),
                business_registration_number=financial.get("business_registration_number"),
                business_start_date=financial.get("business_start_date"),
                years_in_business=financial.get("years_in_business"),
                revenue_regularity_months=financial.get("revenue_regularity_months"),
                extraction_confidence=confidence,
                raw_extraction_json=extraction_result,
                extracted_at=datetime.now(timezone.utc),
            )
            db.add(extracted)

        # Step 3: Update application status
        stmt = select(CreditApplication).where(CreditApplication.id == application_id)
        result = await db.execute(stmt)
        application = result.scalar_one_or_none()
        if application:
            application.status = ApplicationStatus.PENDING_VERIFICATION
            application.updated_at = datetime.now(timezone.utc)

        # Step 4: Audit log
        audit = AuditLog(
            application_id=application_id,
            action="document_extracted",
            details={
                "filename": filename,
                "document_type": extraction_result.get("document_type"),
                "confidence": confidence,
            },
        )
        db.add(audit)

        await db.commit()
        await db.refresh(extracted)

        # Step 5: File content is already in memory only — no disk cleanup needed
        logger.info(f"Extraction complete for application {application_id}, confidence: {confidence}")
        return extracted

    except Exception as e:
        await db.rollback()
        logger.error(f"Extraction service error: {e}")
        raise
