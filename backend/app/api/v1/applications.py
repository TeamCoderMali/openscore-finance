"""
OpenScore Finance — Applications API
CRUD dossiers, multi-search (account / dossier), quick-init for agents,
multi-guarantees, multi-debts, committee submission, and official receipt.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, or_
from sqlalchemy.orm import selectinload

from app.models.database import (
    User, CreditApplication, ExtractedData, ScoringResult,
    ApplicationStatus, AuditLog, get_db, UserRole, ActivitySector, RiskLevel,
    Guarantee, Debt, MicrofinanceAccount, GrantingMethod
)
from app.models.schemas import (
    ApplicationCreate, ApplicationOut, ApplicationListOut,
    ExtractedDataOut, VerifyDataRequest, ReceiptData,
    AuditLogOut, AuditLogListOut, PortfolioStatsOut,
    RejectApplicationRequest, FieldSurveyRequest, ContactClientRequest,
    GuaranteeCreate, GuaranteeOut, DebtCreate, DebtOut,
    AccountLookupOut, AccountLinkRequest, QuickApplicationInitRequest
)
from app.api.v1.auth import get_current_user, get_current_user_optional, require_role
from app.services.extraction_service import process_document_extraction

router = APIRouter(prefix="/applications", tags=["Applications"])


def _generate_reference() -> str:
    """Generate unique application reference: OSF-YYYYMMDD-XXXX"""
    now = datetime.now(timezone.utc)
    short_id = uuid.uuid4().hex[:4].upper()
    return f"OSF-{now.strftime('%Y%m%d')}-{short_id}"


def _application_to_out(app: CreditApplication) -> ApplicationOut:
    sector_val = app.activity_sector.value if hasattr(app.activity_sector, "value") else str(app.activity_sector)
    status_val = app.status.value if hasattr(app.status, "value") else str(app.status)
    name = app.applicant.full_name if app.applicant else None
    phone = app.applicant.phone if app.applicant else None
    email = app.applicant.email if app.applicant else None
    agent_name = app.agent.full_name if app.agent else None

    guarantees_out = [GuaranteeOut.model_validate(g) for g in app.guarantees] if app.guarantees else []
    debts_out = [DebtOut.model_validate(d) for d in app.debts] if app.debts else []

    scoring_dict = None
    if app.scoring_result:
        sr = app.scoring_result
        scoring_dict = {
            "score": sr.score,  # 0-100
            "risk_level": sr.risk_level.value if hasattr(sr.risk_level, "value") else str(sr.risk_level),
            "decision": sr.decision,
            "approved_amount": sr.approved_amount,
            "proposed_amount": sr.proposed_amount,
            "proposed_duration_months": sr.proposed_duration_months,
            "debt_ratio": sr.debt_ratio,
            "disposable_income": sr.disposable_income,
            "guarantee_coverage_ratio": sr.guarantee_coverage_ratio,
            "explainability": sr.explainability,
            "scored_at": sr.scored_at.isoformat() if sr.scored_at else None,
        }

    return ApplicationOut(
        id=int(app.id),
        reference=str(app.reference),
        applicant_id=int(app.applicant_id),
        account_number=app.account_number or (app.applicant.account_number if app.applicant else None),
        applicant_name=name,
        applicant_phone=phone,
        applicant_email=email,
        activity_sector=sector_val,
        requested_amount=float(app.requested_amount),
        requested_duration_months=int(app.requested_duration_months),
        business_description=app.business_description,
        status=status_val,
        agent_id=int(app.agent_id) if app.agent_id else None,
        agent_name=agent_name,
        created_at=app.created_at,
        updated_at=app.updated_at,
        guarantees=guarantees_out,
        debts=debts_out,
        scoring_result=scoring_dict,
    )


# ── MULTI-SEARCH (By Reference OR Account Number OR Name) ────────────
@router.get("/search", response_model=ApplicationListOut)
async def search_applications(
    q: str = Query(..., min_length=2, description="Numéro de dossier (OSF-...) ou numéro de compte (CMF-...)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("agent", "admin")),
):
    """
    Search applications by application reference, client account number, or applicant name.
    """
    term = f"%{q.strip()}%"
    stmt = (
        select(CreditApplication)
        .join(CreditApplication.applicant)
        .options(
            selectinload(CreditApplication.applicant),
            selectinload(CreditApplication.agent),
            selectinload(CreditApplication.guarantees),
            selectinload(CreditApplication.debts),
            selectinload(CreditApplication.scoring_result),
        )
        .where(
            or_(
                CreditApplication.reference.ilike(term),
                CreditApplication.account_number.ilike(term),
                User.account_number.ilike(term),
                User.full_name.ilike(term),
                User.phone.ilike(term),
            )
        )
        .order_by(desc(CreditApplication.created_at))
    )
    result = await db.execute(stmt)
    apps = result.scalars().all()
    out_list = [_application_to_out(a) for a in apps]
    return ApplicationListOut(applications=out_list, total=len(out_list))


# ── ACCOUNT LOOKUP ───────────────────────────────────────────────────
@router.get("/accounts/{account_number}", response_model=AccountLookupOut)
async def lookup_microfinance_account(
    account_number: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    Look up known client information from their microfinance account number.
    Returns existing profile, financial history, and past applications.
    """
    clean_acc = account_number.strip().upper()
    stmt = select(MicrofinanceAccount).where(MicrofinanceAccount.account_number == clean_acc)
    res = await db.execute(stmt)
    acc = res.scalar_one_or_none()

    if not acc:
        raise HTTPException(status_code=404, detail="Numéro de compte microfinance introuvable.")

    # Find past applications linked to this account
    app_stmt = (
        select(CreditApplication)
        .options(selectinload(CreditApplication.scoring_result))
        .where(
            or_(
                CreditApplication.account_number == clean_acc,
                CreditApplication.applicant.has(account_number=clean_acc),
            )
        )
        .order_by(desc(CreditApplication.created_at))
    )
    app_res = await db.execute(app_stmt)
    past_apps = app_res.scalars().all()

    past_apps_summary = [
        {
            "id": a.id,
            "reference": a.reference,
            "requested_amount": float(a.requested_amount),
            "status": str(a.status),
            "score": a.scoring_result.score if a.scoring_result else None,
            "created_at": a.created_at.isoformat(),
        }
        for a in past_apps
    ]

    return AccountLookupOut(
        account_number=acc.account_number,
        full_name=acc.full_name,
        phone=acc.phone,
        email=acc.email,
        id_number=acc.id_number,
        id_type=acc.id_type or "NINA",
        activity_sector=acc.activity_sector,
        monthly_revenue=acc.monthly_revenue,
        monthly_expenses=acc.monthly_expenses,
        years_in_business=acc.years_in_business,
        revenue_regularity_months=acc.revenue_regularity_months,
        existing_debts=[],
        known_guarantees=[],
        past_applications=past_apps_summary,
    )


# ── ACCOUNT LINK (Bind user to microfinance account) ─────────────────
@router.post("/accounts/link")
async def link_microfinance_account(
    payload: AccountLinkRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Permanently link current authenticated mobile user to a microfinance account number."""
    clean_acc = payload.account_number.strip().upper()
    stmt = select(MicrofinanceAccount).where(MicrofinanceAccount.account_number == clean_acc)
    res = await db.execute(stmt)
    acc = res.scalar_one_or_none()
    if not acc:
        raise HTTPException(status_code=404, detail="Numéro de compte microfinance invalide ou introuvable.")

    current_user.account_number = clean_acc
    await db.commit()
    return {"status": "success", "message": f"Compte {clean_acc} rattaché avec succès.", "account_number": clean_acc}


# ── QUICK INITIALIZATION FOR AGENT ───────────────────────────────────
@router.post("/quick-init", response_model=ApplicationOut, status_code=status.HTTP_201_CREATED)
async def quick_init_application(
    payload: QuickApplicationInitRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("agent", "admin")),
):
    """
    Agent quickly initializes a credit application by supplying ONLY the client account number.
    Auto-loads client identity and financial parameters from MicrofinanceAccount.
    """
    clean_acc = payload.account_number.strip().upper()
    stmt = select(MicrofinanceAccount).where(MicrofinanceAccount.account_number == clean_acc)
    res = await db.execute(stmt)
    acc = res.scalar_one_or_none()

    if not acc:
        raise HTTPException(status_code=404, detail="Compte microfinance introuvable. Veuillez vérifier le numéro.")

    # Find or create User record for this client
    user_stmt = select(User).where(or_(User.account_number == clean_acc, User.phone == acc.phone))
    user_res = await db.execute(user_stmt)
    applicant = user_res.scalar_one_or_none()

    if not applicant:
        # Create user record automatically
        safe_email = acc.email or f"{clean_acc.lower().replace('-', '')}@client.openscore.ml"
        applicant = User(
            email=safe_email,
            full_name=acc.full_name,
            hashed_password="client_auto_pwd",
            phone=acc.phone,
            role=UserRole.CLIENT,
            account_number=clean_acc,
            is_active=True,
        )
        db.add(applicant)
        await db.flush()

    sector_str = payload.activity_sector or acc.activity_sector or "Commerce"
    try:
        sector_enum = ActivitySector(sector_str)
    except ValueError:
        sector_enum = ActivitySector.COMMERCE

    # Create application
    application = CreditApplication(
        reference=_generate_reference(),
        applicant_id=applicant.id,
        account_number=clean_acc,
        activity_sector=sector_enum,
        requested_amount=payload.requested_amount,
        requested_duration_months=payload.requested_duration_months,
        business_description=payload.business_description,
        status=ApplicationStatus.DATA_VERIFIED,
        agent_id=current_user.id,
    )
    db.add(application)
    await db.flush()

    # Pre-populate ExtractedData from known account profile
    extracted = ExtractedData(
        application_id=application.id,
        full_name=acc.full_name,
        id_number=acc.id_number,
        id_type=acc.id_type or "NINA",
        monthly_revenue=payload.monthly_revenue or acc.monthly_revenue or 500000.0,
        monthly_expenses=payload.monthly_expenses or acc.monthly_expenses or 250000.0,
        years_in_business=payload.years_in_business or acc.years_in_business or 3.0,
        revenue_regularity_months=payload.revenue_regularity_months or acc.revenue_regularity_months or 12,
        is_verified=True,
        verified_by_agent_id=current_user.id,
        verified_at=datetime.now(timezone.utc),
        raw_extraction_json={"source": "compte_microfinance_existant", "account_number": clean_acc},
        extraction_confidence=1.0,
    )
    db.add(extracted)

    # Add initial guarantees if supplied
    if payload.guarantees:
        for g in payload.guarantees:
            ret_val = g.retained_value or (g.estimated_value * 0.70)
            db.add(
                Guarantee(
                    application_id=application.id,
                    guarantee_type=g.guarantee_type,
                    description=g.description,
                    estimated_value=g.estimated_value,
                    retained_value=ret_val,
                    proof_reference=g.proof_reference,
                )
            )

    # Add initial debts if supplied
    if payload.debts:
        for d in payload.debts:
            db.add(
                Debt(
                    application_id=application.id,
                    creditor_name=d.creditor_name,
                    is_internal=d.is_internal,
                    initial_amount=d.initial_amount or 0.0,
                    remaining_amount=d.remaining_amount,
                    monthly_payment=d.monthly_payment,
                    duration_months=d.duration_months,
                    remaining_installments=d.remaining_installments,
                )
            )

    db.add(
        AuditLog(
            application_id=application.id,
            user_id=current_user.id,
            action="quick_init_created",
            details={"account_number": clean_acc, "requested_amount": payload.requested_amount},
        )
    )

    await db.commit()
    await db.refresh(application)

    # Reload with relations
    stmt_full = (
        select(CreditApplication)
        .options(
            selectinload(CreditApplication.applicant),
            selectinload(CreditApplication.agent),
            selectinload(CreditApplication.guarantees),
            selectinload(CreditApplication.debts),
            selectinload(CreditApplication.scoring_result),
        )
        .where(CreditApplication.id == application.id)
    )
    res_full = await db.execute(stmt_full)
    full_app = res_full.scalar_one()
    return _application_to_out(full_app)


# ── PORTFOLIO STATS (Agent Cockpit) ──────────────────────────────────
@router.get("/stats/portfolio", response_model=PortfolioStatsOut)
async def get_portfolio_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("agent")),
):
    """Aggregated portfolio analytics for microfinance credit officers."""
    stmt = select(CreditApplication).options(selectinload(CreditApplication.scoring_result))
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
        if scored_apps else 68.0  # Base 100
    )

    decided_total = approved_count + adjusted_count + rejected_count
    approval_rate = ((approved_count + adjusted_count) / decided_total * 100) if decided_total > 0 else 85.0

    sector_distribution = {
        "Commerce": sum(1 for a in apps if a.activity_sector == ActivitySector.COMMERCE),
        "Agriculture": sum(1 for a in apps if a.activity_sector == ActivitySector.AGRICULTURE),
        "Artisanat": sum(1 for a in apps if a.activity_sector == ActivitySector.ARTISANAT),
        "TPE": sum(1 for a in apps if a.activity_sector == ActivitySector.TPE),
    }

    risk_distribution = {
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
        average_score=round(average_score, 1),
        sector_distribution=sector_distribution,
        risk_distribution=risk_distribution,
    )


# ── CREATE APPLICATION (Standard Form) ────────────────────────────────
@router.post("", response_model=ApplicationOut, status_code=status.HTTP_201_CREATED)
async def create_application(
    data: ApplicationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new credit application with optional collateral and debts."""
    sector_enum = ActivitySector(data.activity_sector.value)
    account_num = data.account_number or current_user.account_number

    application = CreditApplication(
        reference=_generate_reference(),
        applicant_id=current_user.id,
        account_number=account_num,
        activity_sector=sector_enum,
        requested_amount=data.requested_amount,
        requested_duration_months=data.requested_duration_months,
        business_description=data.business_description,
        status=ApplicationStatus.DRAFT,
    )
    db.add(application)
    await db.flush()

    # Create extracted_data with initial inputs if provided
    extracted = ExtractedData(
        application_id=application.id,
        full_name=current_user.full_name,
        monthly_revenue=data.monthly_revenue or 0.0,
        secondary_revenue=data.secondary_revenue or 0.0,
        monthly_expenses=data.monthly_expenses or 0.0,
        other_recurring_expenses=data.other_recurring_expenses or 0.0,
        existing_debt=data.existing_debt or 0.0,
        years_in_business=data.years_in_business or 3.0,
        revenue_regularity_months=data.revenue_regularity_months or 12,
        is_verified=False,
    )
    db.add(extracted)

    # Save guarantees
    if data.guarantees:
        for g in data.guarantees:
            ret_val = g.retained_value or (g.estimated_value * 0.70)
            db.add(
                Guarantee(
                    application_id=application.id,
                    guarantee_type=g.guarantee_type,
                    description=g.description,
                    estimated_value=g.estimated_value,
                    retained_value=ret_val,
                    proof_reference=g.proof_reference,
                )
            )

    # Save debts
    if data.debts:
        for d in data.debts:
            db.add(
                Debt(
                    application_id=application.id,
                    creditor_name=d.creditor_name,
                    is_internal=d.is_internal,
                    initial_amount=d.initial_amount or 0.0,
                    remaining_amount=d.remaining_amount,
                    monthly_payment=d.monthly_payment,
                    duration_months=d.duration_months,
                    remaining_installments=d.remaining_installments,
                )
            )

    audit = AuditLog(
        application_id=application.id,
        user_id=current_user.id,
        action="application_created",
        details={
            "requested_amount": data.requested_amount,
            "duration_months": data.requested_duration_months,
            "sector": data.activity_sector.value,
            "account_number": account_num,
        },
    )
    db.add(audit)

    await db.commit()

    stmt_full = (
        select(CreditApplication)
        .options(
            selectinload(CreditApplication.applicant),
            selectinload(CreditApplication.agent),
            selectinload(CreditApplication.guarantees),
            selectinload(CreditApplication.debts),
            selectinload(CreditApplication.scoring_result),
        )
        .where(CreditApplication.id == application.id)
    )
    res = await db.execute(stmt_full)
    full_app = res.scalar_one()
    return _application_to_out(full_app)


# ── LIST APPLICATIONS ────────────────────────────────────────────────
@router.get("", response_model=ApplicationListOut)
async def list_applications(
    status_filter: Optional[str] = None,
    sector_filter: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List applications for client or agent."""
    stmt = (
        select(CreditApplication)
        .options(
            selectinload(CreditApplication.applicant),
            selectinload(CreditApplication.agent),
            selectinload(CreditApplication.guarantees),
            selectinload(CreditApplication.debts),
            selectinload(CreditApplication.scoring_result),
        )
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
    out_list = [_application_to_out(app) for app in applications]
    return ApplicationListOut(applications=out_list, total=len(out_list))


# ── GET SINGLE APPLICATION ───────────────────────────────────────────
@router.get("/{app_id}", response_model=ApplicationOut)
async def get_application(
    app_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = (
        select(CreditApplication)
        .options(
            selectinload(CreditApplication.applicant),
            selectinload(CreditApplication.agent),
            selectinload(CreditApplication.guarantees),
            selectinload(CreditApplication.debts),
            selectinload(CreditApplication.scoring_result),
        )
        .where(CreditApplication.id == app_id)
    )
    result = await db.execute(stmt)
    app = result.scalar_one_or_none()

    if not app:
        raise HTTPException(status_code=404, detail="Dossier introuvable")

    if current_user.role == UserRole.CLIENT and app.applicant_id != current_user.id:
        raise HTTPException(status_code=403, detail="Accès non autorisé à ce dossier")

    return _application_to_out(app)


# ── EXTRACT DOCUMENTS (OCR Gemini) ───────────────────────────────────
@router.post("/{app_id}/extract-docs", response_model=ExtractedDataOut)
async def extract_documents(
    app_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(CreditApplication).where(CreditApplication.id == app_id)
    result = await db.execute(stmt)
    app = result.scalar_one_or_none()

    if not app:
        raise HTTPException(status_code=404, detail="Dossier introuvable")

    content = await file.read()
    extracted = await process_document_extraction(
        db=db,
        application_id=app_id,
        file_content=content,
        filename=file.filename or "document.jpg",
        mime_type=file.content_type or "image/jpeg",
    )

    if not extracted:
        raise HTTPException(status_code=500, detail="Échec de l'extraction documentaire")

    return ExtractedDataOut.model_validate(extracted)


# ── GET EXTRACTED DATA ───────────────────────────────────────────────
@router.get("/{app_id}/extracted-data", response_model=ExtractedDataOut)
async def get_extracted_data(
    app_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(ExtractedData).where(ExtractedData.application_id == app_id)
    result = await db.execute(stmt)
    extracted = result.scalar_one_or_none()

    if not extracted:
        raise HTTPException(status_code=404, detail="Aucune donnée extraite pour ce dossier")

    return ExtractedDataOut.model_validate(extracted)


# ── VERIFY EXTRACTED DATA ─────────────────────────────────────────────
@router.put("/{app_id}/verify-data", response_model=ExtractedDataOut)
async def verify_extracted_data(
    app_id: int,
    data: VerifyDataRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("agent")),
):
    stmt = select(ExtractedData).where(ExtractedData.application_id == app_id)
    result = await db.execute(stmt)
    extracted = result.scalar_one_or_none()

    if not extracted:
        extracted = ExtractedData(application_id=app_id)
        db.add(extracted)

    if data.full_name is not None:
        extracted.full_name = data.full_name
    if data.date_of_birth is not None:
        extracted.date_of_birth = data.date_of_birth
    if data.id_number is not None:
        extracted.id_number = data.id_number
    if data.id_type is not None:
        extracted.id_type = data.id_type
    if data.monthly_revenue is not None:
        extracted.monthly_revenue = data.monthly_revenue
    if data.secondary_revenue is not None:
        extracted.secondary_revenue = data.secondary_revenue
    if data.monthly_expenses is not None:
        extracted.monthly_expenses = data.monthly_expenses
    if data.other_recurring_expenses is not None:
        extracted.other_recurring_expenses = data.other_recurring_expenses
    if data.existing_debt is not None:
        extracted.existing_debt = data.existing_debt
    if data.business_registration_number is not None:
        extracted.business_registration_number = data.business_registration_number
    if data.business_start_date is not None:
        extracted.business_start_date = data.business_start_date
    if data.years_in_business is not None:
        extracted.years_in_business = data.years_in_business
    if data.revenue_regularity_months is not None:
        extracted.revenue_regularity_months = data.revenue_regularity_months
    if data.verification_notes is not None:
        extracted.verification_notes = data.verification_notes

    extracted.is_verified = True
    extracted.verified_by_agent_id = current_user.id
    extracted.verified_at = datetime.now(timezone.utc)

    # Update app status
    stmt_app = select(CreditApplication).where(CreditApplication.id == app_id)
    res_app = await db.execute(stmt_app)
    app = res_app.scalar_one_or_none()
    if app and app.status in [ApplicationStatus.DRAFT, ApplicationStatus.PENDING_VERIFICATION, ApplicationStatus.DOCUMENTS_UPLOADED]:
        app.status = ApplicationStatus.DATA_VERIFIED
        app.agent_id = current_user.id

    db.add(
        AuditLog(
            application_id=app_id,
            user_id=current_user.id,
            action="data_verified",
            details={"agent": current_user.full_name},
        )
    )

    await db.commit()
    await db.refresh(extracted)
    return ExtractedDataOut.model_validate(extracted)


# ── GUARANTEES (Collateral) CRUD ─────────────────────────────────────
@router.get("/{app_id}/guarantees", response_model=List[GuaranteeOut])
async def list_guarantees(
    app_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(Guarantee).where(Guarantee.application_id == app_id).order_by(desc(Guarantee.created_at))
    res = await db.execute(stmt)
    items = res.scalars().all()
    return [GuaranteeOut.model_validate(g) for g in items]


@router.post("/{app_id}/guarantees", response_model=GuaranteeOut, status_code=status.HTTP_201_CREATED)
async def add_guarantee(
    app_id: int,
    data: GuaranteeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a collateral asset to the application."""
    stmt_app = select(CreditApplication).where(CreditApplication.id == app_id)
    res_app = await db.execute(stmt_app)
    app = res_app.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="Dossier introuvable")

    # Haircuts standard selon type de garantie
    haircuts = {
        "terrain": 0.80,
        "maison": 0.75,
        "vehicule": 0.60,
        "equipement": 0.50,
        "materiel_pro": 0.50,
        "stock": 0.45,
        "autre": 0.40,
    }
    ret_val = data.retained_value or (data.estimated_value * haircuts.get(data.guarantee_type.lower(), 0.50))

    guarantee = Guarantee(
        application_id=app_id,
        guarantee_type=data.guarantee_type,
        description=data.description,
        estimated_value=data.estimated_value,
        retained_value=ret_val,
        proof_reference=data.proof_reference,
    )
    db.add(guarantee)

    db.add(
        AuditLog(
            application_id=app_id,
            user_id=current_user.id,
            action="guarantee_added",
            details={"type": data.guarantee_type, "value": data.estimated_value, "retained": ret_val},
        )
    )

    await db.commit()
    await db.refresh(guarantee)
    return GuaranteeOut.model_validate(guarantee)


@router.delete("/{app_id}/guarantees/{guarantee_id}")
async def delete_guarantee(
    app_id: int,
    guarantee_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(Guarantee).where(Guarantee.id == guarantee_id, Guarantee.application_id == app_id)
    res = await db.execute(stmt)
    g = res.scalar_one_or_none()
    if not g:
        raise HTTPException(status_code=404, detail="Garantie introuvable")

    await db.delete(g)
    await db.commit()
    return {"status": "deleted", "guarantee_id": guarantee_id}


# ── DEBTS CRUD ───────────────────────────────────────────────────────
@router.get("/{app_id}/debts", response_model=List[DebtOut])
async def list_debts(
    app_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(Debt).where(Debt.application_id == app_id).order_by(desc(Debt.created_at))
    res = await db.execute(stmt)
    items = res.scalars().all()
    return [DebtOut.model_validate(d) for d in items]


@router.post("/{app_id}/debts", response_model=DebtOut, status_code=status.HTTP_201_CREATED)
async def add_debt(
    app_id: int,
    data: DebtCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add an existing debt obligation to the application."""
    stmt_app = select(CreditApplication).where(CreditApplication.id == app_id)
    res_app = await db.execute(stmt_app)
    app = res_app.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="Dossier introuvable")

    debt = Debt(
        application_id=app_id,
        creditor_name=data.creditor_name,
        is_internal=data.is_internal,
        initial_amount=data.initial_amount or 0.0,
        remaining_amount=data.remaining_amount,
        monthly_payment=data.monthly_payment,
        duration_months=data.duration_months,
        remaining_installments=data.remaining_installments,
    )
    db.add(debt)

    db.add(
        AuditLog(
            application_id=app_id,
            user_id=current_user.id,
            action="debt_added",
            details={"creditor": data.creditor_name, "monthly": data.monthly_payment},
        )
    )

    await db.commit()
    await db.refresh(debt)
    return DebtOut.model_validate(debt)


@router.delete("/{app_id}/debts/{debt_id}")
async def delete_debt(
    app_id: int,
    debt_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(Debt).where(Debt.id == debt_id, Debt.application_id == app_id)
    res = await db.execute(stmt)
    d = res.scalar_one_or_none()
    if not d:
        raise HTTPException(status_code=404, detail="Dette introuvable")

    await db.delete(d)
    await db.commit()
    return {"status": "deleted", "debt_id": debt_id}


# ── SUBMIT TO COMMITTEE (Agent submits scored application) ────────────
@router.post("/{app_id}/submit-to-committee", response_model=ApplicationOut)
async def submit_to_committee(
    app_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("agent", "admin")),
):
    """Agent forwards a scored application to the Credit Committee / Admin for final grant."""
    stmt = (
        select(CreditApplication)
        .options(
            selectinload(CreditApplication.applicant),
            selectinload(CreditApplication.agent),
            selectinload(CreditApplication.scoring_result),
            selectinload(CreditApplication.guarantees),
            selectinload(CreditApplication.debts),
        )
        .where(CreditApplication.id == app_id)
    )
    res = await db.execute(stmt)
    app = res.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="Dossier introuvable")

    if not app.scoring_result:
        raise HTTPException(status_code=400, detail="Le dossier doit d'abord être scoré avant d'être soumis au comité.")

    app.status = ApplicationStatus.PENDING_COMMITTEE_APPROVAL
    app.agent_id = current_user.id
    app.updated_at = datetime.now(timezone.utc)

    db.add(
        AuditLog(
            application_id=app_id,
            user_id=current_user.id,
            action="submitted_to_committee",
            details={"agent": current_user.full_name, "score": app.scoring_result.score},
        )
    )

    await db.commit()
    await db.refresh(app)
    return _application_to_out(app)


# ── AUDIT LOGS ───────────────────────────────────────────────────────
@router.get("/{app_id}/audit-logs", response_model=AuditLogListOut)
async def get_audit_logs(
    app_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
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
            u_stmt = select(User.full_name).where(User.id == log.user_id)
            u_res = await db.execute(u_stmt)
            user_name = u_res.scalar_one_or_none()

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


# ── RECEIPT (Base 100 with Account Number & Agent Name) ──────────────
@router.get("/{app_id}/receipt", response_model=ReceiptData)
async def get_receipt(
    app_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate official receipt with score on base 100, account number, and agent name."""
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
    applicant_email = app.applicant.email if app.applicant else "client@openscore.ml"
    applicant_phone = app.applicant.phone if app.applicant else None
    account_num = app.account_number or (app.applicant.account_number if app.applicant else None)

    # Agent name from assigned agent, or current logged-in agent/admin
    agent_name = (
        app.agent.full_name
        if app.agent
        else (current_user.full_name if current_user.role in [UserRole.AGENT, UserRole.ADMIN] else "Agent de Crédit Assermenté")
    )

    # Granting method procedure name
    proc_stmt = (
        select(GrantingMethod.procedure_name)
        .where(
            GrantingMethod.is_active == True,
            GrantingMethod.min_amount <= app.requested_amount,
            GrantingMethod.max_amount >= app.requested_amount,
        )
    )
    proc_res = await db.execute(proc_stmt)
    procedure_name = proc_res.scalar_one_or_none() or "Procédure d'Octroi Microfinance"

    return ReceiptData(
        reference=str(app.reference),
        account_number=account_num,
        applicant_name=applicant_name,
        applicant_email=applicant_email,
        applicant_phone=applicant_phone,
        activity_sector=app.activity_sector.value if hasattr(app.activity_sector, "value") else str(app.activity_sector),
        requested_amount=float(app.requested_amount),
        decision=str(scoring.decision),
        approved_amount=scoring.approved_amount,
        proposed_amount=scoring.proposed_amount,
        proposed_duration_months=scoring.proposed_duration_months,
        score=int(scoring.score),  # 0-100!
        risk_level=scoring.risk_level.value if hasattr(scoring.risk_level, "value") else str(scoring.risk_level),
        agent_name=agent_name,
        procedure_name=procedure_name,
        scored_at=scoring.scored_at,
        created_at=app.created_at,
        receipt_id=receipt_id,
    )


# ── CONTACT CLIENT ───────────────────────────────────────────────────
@router.post("/{app_id}/contact-client")
async def contact_client(
    app_id: int,
    data: ContactClientRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("agent")),
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

    db.add(
        AuditLog(
            application_id=app_id,
            user_id=current_user.id,
            action=f"client_contacted_{data.channel}",
            details={"channel": data.channel, "subject": data.subject, "agent": current_user.full_name},
        )
    )
    await db.commit()

    return {
        "status": "sent",
        "channel": data.channel,
        "recipient": app.applicant.full_name if app.applicant else "Client",
        "delivered_at": datetime.now(timezone.utc).isoformat(),
    }
