"""
OpenScore Finance — Applications API
CRUD dossiers, extraction documents, vérification agent, récépissé.
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload

from app.models.database import (
    User, CreditApplication, ExtractedData, ScoringResult,
    ApplicationStatus, AuditLog, get_db, UserRole
)
from app.models.schemas import (
    ApplicationCreate, ApplicationOut, ApplicationListOut,
    ExtractedDataOut, VerifyDataRequest, ReceiptData
)
from app.api.v1.auth import get_current_user, require_role
from app.services.extraction_service import process_document_extraction

router = APIRouter(prefix="/applications", tags=["Applications"])


def _generate_reference() -> str:
    """Generate unique application reference: OSF-YYYYMMDD-XXXX"""
    now = datetime.now(timezone.utc)
    short_id = uuid.uuid4().hex[:4].upper()
    return f"OSF-{now.strftime('%Y%m%d')}-{short_id}"


def _application_to_out(app: CreditApplication, applicant_name: str = None) -> ApplicationOut:
    return ApplicationOut(
        id=app.id,
        reference=app.reference,
        applicant_id=app.applicant_id,
        applicant_name=applicant_name,
        activity_sector=app.activity_sector.value if hasattr(app.activity_sector, 'value') else app.activity_sector,
        requested_amount=app.requested_amount,
        requested_duration_months=app.requested_duration_months,
        business_description=app.business_description,
        status=app.status.value if hasattr(app.status, 'value') else app.status,
        agent_id=app.agent_id,
        created_at=app.created_at,
        updated_at=app.updated_at,
    )


# ── CREATE application ───────────────────────────────────────────────
@router.post("", response_model=ApplicationOut, status_code=status.HTTP_201_CREATED)
async def create_application(
    data: ApplicationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("client")),
):
    """Create a new credit application (client only)."""
    application = CreditApplication(
        reference=_generate_reference(),
        applicant_id=current_user.id,
        activity_sector=data.activity_sector.value,
        requested_amount=data.requested_amount,
        requested_duration_months=data.requested_duration_months,
        business_description=data.business_description,
        status=ApplicationStatus.DRAFT,
    )
    db.add(application)

    audit = AuditLog(
        application_id=0,  # will be set after flush
        user_id=current_user.id,
        action="application_created",
        details={"requested_amount": data.requested_amount, "sector": data.activity_sector.value},
    )

    await db.flush()
    audit.application_id = application.id
    db.add(audit)
    await db.commit()
    await db.refresh(application)

    return _application_to_out(application, current_user.full_name)


# ── LIST applications ────────────────────────────────────────────────
@router.get("", response_model=ApplicationListOut)
async def list_applications(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List applications:
    - Client sees own applications
    - Agent sees all pending verification + already assigned
    """
    if current_user.role == UserRole.AGENT:
        stmt = (
            select(CreditApplication)
            .options(selectinload(CreditApplication.applicant))
            .order_by(desc(CreditApplication.created_at))
        )
    else:
        stmt = (
            select(CreditApplication)
            .where(CreditApplication.applicant_id == current_user.id)
            .order_by(desc(CreditApplication.created_at))
        )

    result = await db.execute(stmt)
    apps = result.scalars().all()

    return ApplicationListOut(
        applications=[
            _application_to_out(
                a,
                a.applicant.full_name if hasattr(a, 'applicant') and a.applicant else None
            )
            for a in apps
        ],
        total=len(apps),
    )


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
        raise HTTPException(status_code=403, detail="Accès non autorisé")

    return _application_to_out(app, app.applicant.full_name if app.applicant else None)


# ── EXTRACT DOCS ─────────────────────────────────────────────────────
@router.post("/{app_id}/extract-docs", response_model=ExtractedDataOut)
async def extract_documents(
    app_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("client")),
):
    """
    Upload a document for AI extraction.
    File is processed in memory and never persisted to disk.
    """
    # Verify application belongs to user
    stmt = select(CreditApplication).where(CreditApplication.id == app_id)
    result = await db.execute(stmt)
    app = result.scalar_one_or_none()

    if not app:
        raise HTTPException(status_code=404, detail="Dossier introuvable")
    if app.applicant_id != current_user.id:
        raise HTTPException(status_code=403, detail="Accès non autorisé")

    # Read file content into memory
    file_content = await file.read()
    mime_type = file.content_type or "application/octet-stream"

    # Process extraction
    extracted = await process_document_extraction(
        db=db,
        application_id=app_id,
        file_content=file_content,
        filename=file.filename,
        mime_type=mime_type,
    )

    if not extracted:
        raise HTTPException(status_code=500, detail="Échec de l'extraction")

    # File content is discarded here (never saved to disk)
    del file_content

    return extracted


# ── GET extracted data ────────────────────────────────────────────────
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
        raise HTTPException(status_code=404, detail="Aucune donnée extraite")
    return data


# ── VERIFY DATA (Agent) ──────────────────────────────────────────────
@router.put("/{app_id}/verify-data", response_model=ExtractedDataOut)
async def verify_data(
    app_id: int,
    verified: VerifyDataRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("agent")),
):
    """Agent validates and corrects extracted data."""
    stmt = select(ExtractedData).where(ExtractedData.application_id == app_id)
    result = await db.execute(stmt)
    data = result.scalar_one_or_none()

    if not data:
        raise HTTPException(status_code=404, detail="Aucune donnée extraite à vérifier")

    # Update fields with verified values
    update_fields = verified.model_dump(exclude_unset=True, exclude_none=True)
    for field, value in update_fields.items():
        if hasattr(data, field):
            setattr(data, field, value)

    data.is_verified = True
    data.verified_by_agent_id = current_user.id
    data.verified_at = datetime.now(timezone.utc)

    # Update application status and assign agent
    stmt = select(CreditApplication).where(CreditApplication.id == app_id)
    result = await db.execute(stmt)
    app = result.scalar_one_or_none()
    if app:
        app.status = ApplicationStatus.DATA_VERIFIED
        app.agent_id = current_user.id
        app.updated_at = datetime.now(timezone.utc)

    # Audit log
    audit = AuditLog(
        application_id=app_id,
        user_id=current_user.id,
        action="data_verified",
        details={"updated_fields": list(update_fields.keys())},
    )
    db.add(audit)

    await db.commit()
    await db.refresh(data)
    return data


# ── RECEIPT ───────────────────────────────────────────────────────────
@router.get("/{app_id}/receipt", response_model=ReceiptData)
async def get_receipt(
    app_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate receipt data for printing."""
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

    return ReceiptData(
        reference=app.reference,
        applicant_name=app.applicant.full_name,
        applicant_email=app.applicant.email,
        applicant_phone=app.applicant.phone,
        activity_sector=app.activity_sector.value if hasattr(app.activity_sector, 'value') else app.activity_sector,
        requested_amount=app.requested_amount,
        decision=scoring.decision,
        approved_amount=scoring.approved_amount,
        proposed_amount=scoring.proposed_amount,
        proposed_duration_months=scoring.proposed_duration_months,
        score=scoring.score,
        risk_level=scoring.risk_level.value if hasattr(scoring.risk_level, 'value') else scoring.risk_level,
        agent_name=app.agent.full_name if app.agent else None,
        scored_at=scoring.scored_at,
        created_at=app.created_at,
        receipt_id=receipt_id,
    )
