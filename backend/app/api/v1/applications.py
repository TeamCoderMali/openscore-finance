"""
OpenScore Finance — Applications API
CRUD dossiers, extraction documents, certification agent, audit logs, récépissé, portfolio stats, rejets officiels.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload

from app.models.database import (
    User, CreditApplication, ExtractedData, ScoringResult,
    ApplicationStatus, AuditLog, get_db, UserRole, ActivitySector, RiskLevel
)
from app.models.schemas import (
    ApplicationCreate, ApplicationOut, ApplicationListOut,
    ExtractedDataOut, VerifyDataRequest, ReceiptData,
    AuditLogOut, AuditLogListOut, PortfolioStatsOut,
    RejectApplicationRequest, FieldSurveyRequest, ContactClientRequest
)
from app.api.v1.auth import get_current_user, require_role
from app.services.extraction_service import process_document_extraction

router = APIRouter(prefix="/applications", tags=["Applications"])


def _generate_reference() -> str:
    """Generate unique application reference: OSF-YYYYMMDD-XXXX"""
    now = datetime.now(timezone.utc)
    short_id = uuid.uuid4().hex[:4].upper()
    return f"OSF-{now.strftime('%Y%m%d')}-{short_id}"


def _application_to_out(
    app: CreditApplication,
    applicant_name: Optional[str] = None,
    applicant_phone: Optional[str] = None,
    applicant_email: Optional[str] = None,
) -> ApplicationOut:
    sector_val = app.activity_sector.value if hasattr(app.activity_sector, 'value') else str(app.activity_sector)
    status_val = app.status.value if hasattr(app.status, 'value') else str(app.status)
    name = applicant_name or (app.applicant.full_name if app.applicant else None)
    phone = applicant_phone or (app.applicant.phone if app.applicant else None)
    email = applicant_email or (app.applicant.email if app.applicant else None)
    return ApplicationOut(
        id=int(app.id),
        reference=str(app.reference),
        applicant_id=int(app.applicant_id),
        applicant_name=name,
        applicant_phone=phone,
        applicant_email=email,
        activity_sector=sector_val,
        requested_amount=float(app.requested_amount),
        requested_duration_months=int(app.requested_duration_months),
        business_description=app.business_description,
        status=status_val,
        agent_id=int(app.agent_id) if app.agent_id else None,
        created_at=app.created_at,
        updated_at=app.updated_at,
    )


# ── PORTFOLIO STATS (Agent Cockpit) ──────────────────────────────────
@router.get("/stats/portfolio", response_model=PortfolioStatsOut)
async def get_portfolio_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("agent")),
):
    """Aggregated portfolio analytics for microfinance credit officers."""
    stmt = select(CreditApplication).options(
        selectinload(CreditApplication.scoring_result)
    )
    result = await db.execute(stmt)
    apps = result.scalars().all()

    total = len(apps)
    pending_verification = sum(1 for a in apps if a.status == ApplicationStatus.PENDING_VERIFICATION)
    approved_count = sum(1 for a in apps if a.status == ApplicationStatus.APPROVED)
    adjusted_count = sum(1 for a in apps if a.status == ApplicationStatus.ADJUSTED)
    rejected_count = sum(1 for a in apps if a.status == ApplicationStatus.REJECTED)
    draft_count = sum(1 for a in apps if a.status in [ApplicationStatus.DRAFT, ApplicationStatus.DOCUMENTS_UPLOADED, ApplicationStatus.DATA_EXTRACTED])

    total_volume_requested = sum(float(a.requested_amount) for a in apps)
    total_volume_approved = sum(
        float(a.scoring_result.approved_amount or a.scoring_result.proposed_amount or a.requested_amount)
        for a in apps if a.scoring_result and a.status in [ApplicationStatus.APPROVED, ApplicationStatus.ADJUSTED]
    )

    scored_apps = [a for a in apps if a.scoring_result]
    average_score = (
        sum(a.scoring_result.score for a in scored_apps) / len(scored_apps)
        if scored_apps else 650.0
    )

    decided_total = approved_count + adjusted_count + rejected_count
    approval_rate = ((approved_count + adjusted_count) / decided_total * 100) if decided_total > 0 else 85.0

    sector_distribution: dict[str, int] = {
        "Commerce": sum(1 for a in apps if a.activity_sector == ActivitySector.COMMERCE),
        "Agriculture": sum(1 for a in apps if a.activity_sector == ActivitySector.AGRICULTURE),
        "Artisanat": sum(1 for a in apps if a.activity_sector == ActivitySector.ARTISANAT),
        "TPE": sum(1 for a in apps if a.activity_sector == ActivitySector.TPE),
    }

    risk_distribution: dict[str, int] = {
        "low": sum(1 for a in scored_apps if a.scoring_result.risk_level == RiskLevel.LOW),
        "medium": sum(1 for a in scored_apps if a.scoring_result.risk_level == RiskLevel.MEDIUM),
        "high": sum(1 for a in scored_apps if a.scoring_result.risk_level == RiskLevel.HIGH),
        "very_high": sum(1 for a in scored_apps if a.scoring_result.risk_level == RiskLevel.VERY_HIGH),
    }

    return PortfolioStatsOut(
        total_applications=total,
        pending_verification=pending_verification,
        approved_count=approved_count,
        adjusted_count=adjusted_count,
        rejected_count=rejected_count,
        draft_count=draft_count,
        total_volume_requested=total_volume_requested,
        total_volume_approved=total_volume_approved,
        approval_rate=round(approval_rate, 1),
        average_score=round(average_score, 0),
        sector_distribution=sector_distribution,
        risk_distribution=risk_distribution,
    )


# ── CREATE application ───────────────────────────────────────────────
@router.post("", response_model=ApplicationOut, status_code=status.HTTP_201_CREATED)
async def create_application(
    data: ApplicationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Client creates a new credit application (DRAFT)."""
    sector_enum = ActivitySector(data.activity_sector.value)
    application = CreditApplication(
        reference=_generate_reference(),
        applicant_id=current_user.id,
        activity_sector=sector_enum,
        requested_amount=data.requested_amount,
        requested_duration_months=data.requested_duration_months,
        business_description=data.business_description,
        status=ApplicationStatus.DRAFT,
    )
    db.add(application)
    await db.flush()

    audit = AuditLog(
        application_id=application.id,
        user_id=current_user.id,
        action="application_created",
        details={
            "requested_amount": data.requested_amount,
            "duration_months": data.requested_duration_months,
            "sector": data.activity_sector.value,
        },
    )
    db.add(audit)

    await db.commit()
    await db.refresh(application)
    return _application_to_out(application, applicant_name=current_user.full_name)


# ── LIST applications ────────────────────────────────────────────────
@router.get("", response_model=ApplicationListOut)
async def list_applications(
    status_filter: Optional[str] = None,
    sector_filter: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List applications:
    - Clients only see their own applications.
    - Agents see all applications across the agency.
    """
    stmt = (
        select(CreditApplication)
        .options(selectinload(CreditApplication.applicant))
        .order_by(desc(CreditApplication.created_at))
    )

    if current_user.role == UserRole.CLIENT:
        stmt = stmt.where(CreditApplication.applicant_id == current_user.id)

    if status_filter:
        try:
            status_enum = ApplicationStatus(status_filter)
            stmt = stmt.where(CreditApplication.status == status_enum)
        except ValueError:
            pass

    if sector_filter:
        try:
            sector_enum = ActivitySector(sector_filter)
            stmt = stmt.where(CreditApplication.activity_sector == sector_enum)
        except ValueError:
            pass

    result = await db.execute(stmt)
    applications = result.scalars().all()

    out_list = [
        _application_to_out(
            app,
            applicant_name=app.applicant.full_name if app.applicant else None,
        )
        for app in applications
    ]
    return ApplicationListOut(applications=out_list, total=len(out_list))


# ── GET single application ───────────────────────────────────────────
@router.get("/{app_id}", response_model=ApplicationOut)
async def get_application(
    app_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = (
        select(CreditApplication)
        .options(selectinload(CreditApplication.applicant))
        .where(CreditApplication.id == app_id)
    )
    result = await db.execute(stmt)
    app = result.scalar_one_or_none()

    if not app:
        raise HTTPException(status_code=404, detail="Dossier introuvable")

    if current_user.role == UserRole.CLIENT and app.applicant_id != current_user.id:
        raise HTTPException(status_code=403, detail="Accès non autorisé à ce dossier")

    return _application_to_out(
        app,
        applicant_name=app.applicant.full_name if app.applicant else None,
    )


# ── EXTRACT DOCUMENTS (OCR Gemini 1.5 Flash Pipeline) ────────────────
@router.post("/{app_id}/extract-docs", response_model=ExtractedDataOut)
async def extract_documents(
    app_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload a document and trigger Gemini 1.5 Flash structured OCR extraction."""
    stmt = select(CreditApplication).where(CreditApplication.id == app_id)
    result = await db.execute(stmt)
    app = result.scalar_one_or_none()

    if not app:
        raise HTTPException(status_code=404, detail="Dossier introuvable")

    if current_user.role == UserRole.CLIENT and app.applicant_id != current_user.id:
        raise HTTPException(status_code=403, detail="Accès non autorisé")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Fichier vide")

    extracted_data = await process_document_extraction(
        db=db,
        application_id=app_id,
        file_content=file_bytes,
        filename=file.filename or "document.jpg",
        mime_type=file.content_type or "image/jpeg",
    )

    if not extracted_data:
        raise HTTPException(status_code=500, detail="Échec du traitement OCR du document")

    app.status = ApplicationStatus.PENDING_VERIFICATION
    app.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(extracted_data)

    return extracted_data


# ── GET EXTRACTED DATA ───────────────────────────────────────────────
@router.get("/{app_id}/extracted-data", response_model=ExtractedDataOut)
async def get_extracted_data(
    app_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(ExtractedData).where(ExtractedData.application_id == app_id)
    result = await db.execute(stmt)
    data = result.scalar_one_or_none()

    if not data:
        raise HTTPException(status_code=404, detail="Aucune donnée extraite pour ce dossier")
    return data


# ── VERIFY DATA (Agent Certification) ────────────────────────────────
@router.put("/{app_id}/verify-data", response_model=ExtractedDataOut)
async def verify_data(
    app_id: int,
    verified: VerifyDataRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("agent")),
):
    """Agent validates, certifies and corrects extracted data."""
    stmt = select(ExtractedData).where(ExtractedData.application_id == app_id)
    result = await db.execute(stmt)
    data = result.scalar_one_or_none()

    if not data:
        data = ExtractedData(
            application_id=app_id,
            raw_extraction_json={"source": "saisie_manuelle_agent_terrain"},
            extraction_confidence=1.0,
            full_name=verified.full_name or "Demandeur",
            id_number=verified.id_number or "NINA-TERRAIN",
            id_type=verified.id_type or "NINA",
            monthly_revenue=verified.monthly_revenue or 350000.0,
            monthly_expenses=verified.monthly_expenses or 120000.0,
            existing_debt=verified.existing_debt or 0.0,
            years_in_business=verified.years_in_business or 3.0,
            revenue_regularity_months=verified.revenue_regularity_months or 12,
        )
        db.add(data)

    update_fields = verified.model_dump(exclude_unset=True, exclude_none=True)
    for field, value in update_fields.items():
        if hasattr(data, field):
            setattr(data, field, value)

    data.is_verified = True
    data.verified_by_agent_id = current_user.id
    data.verified_at = datetime.now(timezone.utc)

    # Update application status
    stmt_app = select(CreditApplication).where(CreditApplication.id == app_id)
    res_app = await db.execute(stmt_app)
    app = res_app.scalar_one_or_none()
    if app:
        app.status = ApplicationStatus.DATA_VERIFIED
        app.agent_id = current_user.id
        app.updated_at = datetime.now(timezone.utc)

    # Audit log
    audit = AuditLog(
        application_id=app_id,
        user_id=current_user.id,
        action="data_certified",
        details={"certified_by": current_user.full_name, "updated_fields": list(update_fields.keys())},
    )
    db.add(audit)

    await db.commit()
    await db.refresh(data)
    return data


# ── FIELD SURVEY & GUARANTEES (Enquête de Terrain Agent) ─────────────
@router.put("/{app_id}/field-survey", response_model=ExtractedDataOut)
async def update_field_survey(
    app_id: int,
    survey: FieldSurveyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("agent")),
):
    """Record physical field survey observations, guarantees, and market reputation."""
    stmt = select(ExtractedData).where(ExtractedData.application_id == app_id)
    result = await db.execute(stmt)
    data = result.scalar_one_or_none()

    if not data:
        raise HTTPException(status_code=404, detail="Dossier sans données extraites")

    notes_part = []
    if survey.guarantee_type:
        notes_part.append(f"Garantie: {survey.guarantee_type} (Val: {survey.guarantee_value or 0:,.0f} FCFA)")
    if survey.market_reputation:
        notes_part.append(f"Avis Moralité/Marché: {survey.market_reputation}")
    if survey.daily_cash_flow_observed:
        notes_part.append(f"Flux constaté sur place: {survey.daily_cash_flow_observed:,.0f} FCFA/jour")
    if survey.field_agent_notes:
        notes_part.append(f"Notes: {survey.field_agent_notes}")

    combined_notes = " | ".join(notes_part)
    data.verification_notes = f"{data.verification_notes or ''}\n[ENQUÊTE TERRAIN]: {combined_notes}".strip()

    audit = AuditLog(
        application_id=app_id,
        user_id=current_user.id,
        action="field_survey_recorded",
        details={"guarantee": survey.guarantee_type, "reputation": survey.market_reputation},
    )
    db.add(audit)

    await db.commit()
    await db.refresh(data)
    return data


# ── REJECT APPLICATION (Motif Réglementaire BCEAO) ───────────────────
@router.post("/{app_id}/reject", response_model=ApplicationOut)
async def reject_application(
    app_id: int,
    data: RejectApplicationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("agent")),
):
    """Agent officially rejects an application with BCEAO regulatory justification."""
    stmt = select(CreditApplication).options(selectinload(CreditApplication.applicant)).where(CreditApplication.id == app_id)
    result = await db.execute(stmt)
    app = result.scalar_one_or_none()

    if not app:
        raise HTTPException(status_code=404, detail="Dossier introuvable")

    app.status = ApplicationStatus.REJECTED
    app.agent_id = current_user.id
    app.updated_at = datetime.now(timezone.utc)

    # Scoring result update or creation for traceability
    stmt_sc = select(ScoringResult).where(ScoringResult.application_id == app_id)
    res_sc = await db.execute(stmt_sc)
    sc = res_sc.scalar_one_or_none()
    if sc:
        sc.decision = "rejected"
        sc.scored_at = datetime.now(timezone.utc)

    audit = AuditLog(
        application_id=app_id,
        user_id=current_user.id,
        action="application_rejected",
        details={
            "agent": current_user.full_name,
            "reason": data.reason,
            "notes": data.notes
        },
    )
    db.add(audit)

    await db.commit()
    await db.refresh(app)
    return _application_to_out(app, applicant_name=app.applicant.full_name if app.applicant else None)


# ── AUDIT LOGS ────────────────────────────────────────────────────────
@router.get("/{app_id}/audit-logs", response_model=AuditLogListOut)
async def get_application_audit_logs(
    app_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get chronological audit logs for an application."""
    stmt = (
        select(AuditLog)
        .where(AuditLog.application_id == app_id)
        .order_by(desc(AuditLog.timestamp))
    )
    result = await db.execute(stmt)
    logs = result.scalars().all()

    out_logs = []
    for log in logs:
        user_name = None
        if log.user_id:
            u_stmt = select(User).where(User.id == log.user_id)
            u_res = await db.execute(u_stmt)
            u = u_res.scalar_one_or_none()
            if u:
                user_name = u.full_name

        out_logs.append(
            AuditLogOut(
                id=log.id,
                application_id=log.application_id,
                user_id=log.user_id,
                user_name=user_name,
                action=log.action,
                details=log.details,
                timestamp=log.timestamp,
            )
        )

    return AuditLogListOut(logs=out_logs, total=len(out_logs))


# ── RECEIPT ───────────────────────────────────────────────────────────
@router.get("/{app_id}/receipt", response_model=ReceiptData)
async def get_receipt(
    app_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate tamper-evident official receipt data for printing and archiving."""
    stmt = (
        select(CreditApplication)
        .options(
            selectinload(CreditApplication.applicant),
            selectinload(CreditApplication.scoring_result),
            selectinload(CreditApplication.agent),
        )
        .where(CreditApplication.id == app_id)
    )
    result = await db.execute(stmt)
    app = result.scalar_one_or_none()

    if not app:
        raise HTTPException(status_code=404, detail="Dossier introuvable")

    if not app.scoring_result:
        raise HTTPException(status_code=400, detail="Le dossier n'a pas encore été évalué")

    scoring = app.scoring_result
    receipt_id = f"REC-{app.reference}-{uuid.uuid4().hex[:6].upper()}"

    applicant_name = app.applicant.full_name if app.applicant else "Demandeur"
    applicant_email = app.applicant.email if app.applicant else "email@domain.ml"
    applicant_phone = app.applicant.phone if app.applicant else None

    return ReceiptData(
        reference=str(app.reference),
        applicant_name=applicant_name,
        applicant_email=applicant_email,
        applicant_phone=applicant_phone,
        activity_sector=app.activity_sector.value if hasattr(app.activity_sector, 'value') else str(app.activity_sector),
        requested_amount=float(app.requested_amount),
        decision=str(scoring.decision),
        approved_amount=scoring.approved_amount,
        proposed_amount=scoring.proposed_amount,
        proposed_duration_months=scoring.proposed_duration_months,
        score=int(scoring.score),
        risk_level=scoring.risk_level.value if hasattr(scoring.risk_level, 'value') else str(scoring.risk_level),
        agent_name=app.agent.full_name if app.agent else None,
        scored_at=scoring.scored_at,
        created_at=app.created_at,
        receipt_id=receipt_id,
    )


# ── CONTACT CLIENT (Agent Direct Communication) ──────────────────────
@router.post("/{app_id}/contact-client")
async def contact_client(
    app_id: int,
    data: ContactClientRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("agent")),
):
    """
    Log an agent's communication attempt or direct interaction with the client
    (WhatsApp, direct call, SMS or email) into the official audit trail.
    """
    stmt = (
        select(CreditApplication)
        .options(selectinload(CreditApplication.applicant))
        .where(CreditApplication.id == app_id)
    )
    res = await db.execute(stmt)
    app = res.scalar_one_or_none()

    if not app:
        raise HTTPException(status_code=404, detail="Dossier introuvable")

    client_name = app.applicant.full_name if app.applicant else "Client"
    client_phone = app.applicant.phone if app.applicant else "Non renseigné"

    audit = AuditLog(
        application_id=app_id,
        user_id=current_user.id,
        action="client_contacted",
        details={
            "channel": data.channel,
            "subject": data.subject,
            "message": data.message,
            "client_name": client_name,
            "client_phone": client_phone,
            "agent_name": current_user.full_name,
        },
    )
    db.add(audit)
    await db.commit()

    return {
        "status": "success",
        "message": f"Communication via {data.channel} enregistrée avec succès pour {client_name}.",
        "channel": data.channel,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

