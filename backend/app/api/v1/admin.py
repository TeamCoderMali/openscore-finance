"""
OpenScore Finance — Super Admin API
Global supervision, user & agent provisioning, BCEAO prudential rule calibration, systemic audit logs.
"""

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from sqlalchemy.orm import selectinload

from app.models.database import (
    User, UserRole, CreditApplication, ExtractedData, ScoringResult,
    ApplicationStatus, AuditLog, get_db, ActivitySector, RiskLevel
)
from app.models.schemas import UserOut, AuditLogOut, AuditLogListOut
from app.api.v1.auth import get_current_user, require_role, hash_password

router = APIRouter(prefix="/admin", tags=["Super Admin"])


# ── Schemas ───────────────────────────────────────────────────────────
class AdminUserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=4)
    full_name: str = Field(..., min_length=2)
    phone: Optional[str] = None
    role: str = "agent"  # agent or admin or client


class AdminUserUpdateRole(BaseModel):
    role: str


class AdminResetPasswordPayload(BaseModel):
    new_password: str = Field(..., min_length=4)


class AdminClientSummaryOut(BaseModel):
    id: int
    full_name: str
    email: str
    phone: Optional[str] = None
    is_active: bool
    created_at: datetime
    activity_sector: Optional[str] = None
    applications_count: int = 0
    total_requested: float = 0.0
    total_approved: float = 0.0
    average_score: Optional[float] = None
    kyc_status: str = "non_verifie"  # complet, partiel, non_verifie
    monthly_revenue: Optional[float] = None
    monthly_expenses: Optional[float] = None
    last_application_status: Optional[str] = None
    last_application_date: Optional[datetime] = None


class AdminClientDetailOut(BaseModel):
    id: int
    full_name: str
    email: str
    phone: Optional[str] = None
    is_active: bool
    created_at: datetime
    activity_sector: Optional[str] = None
    monthly_revenue: Optional[float] = None
    monthly_expenses: Optional[float] = None
    existing_debt: Optional[float] = None
    business_description: Optional[str] = None
    years_in_business: Optional[float] = None
    kyc_status: str = "non_verifie"
    kyc_documents: Dict[str, Any] = {}
    applications: List[Dict[str, Any]] = []
    audit_logs: List[Dict[str, Any]] = []


class AdminClientUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None


class AdminAgentSummaryOut(BaseModel):
    id: int
    full_name: str
    email: str
    phone: Optional[str] = None
    is_active: bool
    created_at: datetime
    branch: str
    assigned_applications_count: int = 0
    certified_applications_count: int = 0
    pending_applications_count: int = 0
    approved_volume: float = 0.0
    approval_rate: float = 0.0
    average_processing_hours: float = 2.4


class AdminAgentReassignPayload(BaseModel):
    target_agent_id: int
    application_ids: Optional[List[int]] = None


class AdminBranchOut(BaseModel):
    id: str
    name: str
    city: str
    branch_type: str
    status: str
    lead_agent: str
    agents_count: int
    active_loans_count: int
    total_disbursed: float
    par_30: float
    max_credit_limit: float


class AdminBranchCreate(BaseModel):
    name: str
    city: str
    branch_type: str = "Antenne Régionale"
    lead_agent: str
    max_credit_limit: float = 50000000.0


class RiskMatrixOut(BaseModel):
    par_30: float
    par_60: float
    par_90: float
    npl_ratio: float
    guarantee_coverage_rate: float
    sector_risk: Dict[str, Dict[str, Any]]
    branch_risk: Dict[str, Dict[str, Any]]
    stress_test_defaults: Dict[str, float]


class AdminPrudentialSettings(BaseModel):
    debt_ratio_ceiling: float = Field(default=0.40, description="Plafond ratio d'endettement BCEAO (ex: 0.40 = 40%)")
    min_disposable_income: float = Field(default=75000.0, description="Minimum vital / Reste à vivre en FCFA")
    approval_score_threshold: int = Field(default=750, description="Seuil d'accord direct automatique")
    counter_proposal_threshold: int = Field(default=600, description="Seuil d'ajustement / Contre-proposition")
    rejection_threshold: int = Field(default=400, description="Seuil de rejet strict")
    bceao_max_monthly_interest: float = Field(default=2.0, description="Taux d'usure mensuel plafond BCEAO (%)")
    shap_debt_weight: float = Field(default=0.30, description="Poids SHAP - Ratio d'endettement")
    shap_income_weight: float = Field(default=0.20, description="Poids SHAP - Reste à vivre")
    shap_regularity_weight: float = Field(default=0.20, description="Poids SHAP - Régularité revenus")
    shap_seniority_weight: float = Field(default=0.15, description="Poids SHAP - Ancienneté activité")
    shap_leverage_weight: float = Field(default=0.15, description="Poids SHAP - Levier financier")


class AdminStatsOut(BaseModel):
    total_users: int
    clients_count: int
    agents_count: int
    admins_count: int
    total_applications: int
    total_volume_requested: float
    total_volume_approved: float
    approval_rate: float
    portfolio_at_risk_index: float  # PAR %
    system_average_score: float
    active_branches: int
    sector_exposure: Dict[str, float]
    status_summary: Dict[str, int]


# Global memory settings cache (in production persisted to DB)
_GLOBAL_PRUDENTIAL_SETTINGS = AdminPrudentialSettings()

# Default Regional Branches of OpenScore Finance (Mali/UEMOA)
_BRANCHES_DATA: List[Dict[str, Any]] = [
    {
        "id": "bko-central",
        "name": "Antenne Centrale Bamako-District",
        "city": "Bamako",
        "branch_type": "Agence Centrale",
        "status": "Opérationnelle",
        "lead_agent": "Ibrahima Coulibaly",
        "agents_count": 3,
        "active_loans_count": 28,
        "total_disbursed": 18500000.0,
        "par_30": 1.8,
        "max_credit_limit": 100000000.0,
    },
    {
        "id": "seg-region",
        "name": "Antenne Régionale Ségou (Office du Niger)",
        "city": "Ségou",
        "branch_type": "Antenne Régionale",
        "status": "Opérationnelle",
        "lead_agent": "Awa Sangaré",
        "agents_count": 2,
        "active_loans_count": 16,
        "total_disbursed": 9200000.0,
        "par_30": 2.6,
        "max_credit_limit": 50000000.0,
    },
    {
        "id": "sik-maraichage",
        "name": "Antenne Régionale Sikasso (Zone Maraîchère)",
        "city": "Sikasso",
        "branch_type": "Guichet Mobile WA+",
        "status": "En Ligne",
        "lead_agent": "Bakary Diarra",
        "agents_count": 2,
        "active_loans_count": 12,
        "total_disbursed": 7800000.0,
        "par_30": 3.1,
        "max_credit_limit": 35000000.0,
    },
]


# ── STATS / COCKPIT SUPER ADMIN ───────────────────────────────────────
@router.get("/stats", response_model=AdminStatsOut)
async def get_super_admin_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Institutional overview for Microfinance CEO & Systemic Regulator."""
    # Count users
    u_stmt = select(User)
    u_res = await db.execute(u_stmt)
    users = u_res.scalars().all()

    clients_count = sum(1 for u in users if u.role == UserRole.CLIENT)
    agents_count = sum(1 for u in users if u.role == UserRole.AGENT)
    admins_count = sum(1 for u in users if u.role == UserRole.ADMIN)

    # Applications
    app_stmt = select(CreditApplication).options(selectinload(CreditApplication.scoring_result))
    app_res = await db.execute(app_stmt)
    apps = app_res.scalars().all()

    total_apps = len(apps)
    total_req = sum(float(a.requested_amount) for a in apps)
    approved_apps = [a for a in apps if a.status in [ApplicationStatus.APPROVED, ApplicationStatus.ADJUSTED]]
    total_approved = sum(
        float(a.scoring_result.approved_amount or a.scoring_result.proposed_amount or a.requested_amount)
        for a in approved_apps if a.scoring_result
    )

    decided = sum(1 for a in apps if a.status in [ApplicationStatus.APPROVED, ApplicationStatus.ADJUSTED, ApplicationStatus.REJECTED])
    approval_rate = (len(approved_apps) / decided * 100) if decided > 0 else 88.0

    scored = [a for a in apps if a.scoring_result]
    avg_score = (sum(a.scoring_result.score for a in scored) / len(scored)) if scored else 675.0

    # Sector exposure
    sector_exposure: Dict[str, float] = {
        "Commerce": sum(float(a.requested_amount) for a in apps if a.activity_sector == ActivitySector.COMMERCE),
        "Agriculture": sum(float(a.requested_amount) for a in apps if a.activity_sector == ActivitySector.AGRICULTURE),
        "Artisanat": sum(float(a.requested_amount) for a in apps if a.activity_sector == ActivitySector.ARTISANAT),
        "TPE": sum(float(a.requested_amount) for a in apps if a.activity_sector == ActivitySector.TPE),
    }

    # Status summary
    status_summary: Dict[str, int] = {
        "draft": sum(1 for a in apps if a.status == ApplicationStatus.DRAFT),
        "pending_verification": sum(1 for a in apps if a.status == ApplicationStatus.PENDING_VERIFICATION),
        "data_verified": sum(1 for a in apps if a.status == ApplicationStatus.DATA_VERIFIED),
        "approved": sum(1 for a in apps if a.status == ApplicationStatus.APPROVED),
        "adjusted": sum(1 for a in apps if a.status == ApplicationStatus.ADJUSTED),
        "rejected": sum(1 for a in apps if a.status == ApplicationStatus.REJECTED),
    }

    # Low PAR default simulation (2.4% for healthy microfinance)
    par_index = 2.4

    return AdminStatsOut(
        total_users=len(users),
        clients_count=clients_count,
        agents_count=agents_count,
        admins_count=admins_count,
        total_applications=total_apps,
        total_volume_requested=total_req,
        total_volume_approved=total_approved,
        approval_rate=round(approval_rate, 1),
        portfolio_at_risk_index=par_index,
        system_average_score=round(avg_score, 0),
        active_branches=3,  # Bamako-District, Ségou, Sikasso
        sector_exposure=sector_exposure,
        status_summary=status_summary,
    )


# ── USERS MANAGEMENT ──────────────────────────────────────────────────
@router.get("/users", response_model=List[UserOut])
async def list_all_users(
    role_filter: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """List all accounts with optional search and role filtering."""
    stmt = select(User).order_by(desc(User.created_at))

    if role_filter and role_filter != "all":
        try:
            r_enum = UserRole(role_filter)
            stmt = stmt.where(User.role == r_enum)
        except ValueError:
            pass

    if search:
        s = f"%{search.strip().lower()}%"
        stmt = stmt.where(
            func.lower(User.full_name).like(s) | func.lower(User.email).like(s)
        )

    result = await db.execute(stmt)
    users = result.scalars().all()

    return [
        UserOut(
            id=u.id,
            email=u.email,
            full_name=u.full_name,
            role=u.role.value if hasattr(u.role, 'value') else str(u.role),
            phone=u.phone,
        )
        for u in users
    ]


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user_by_admin(
    payload: AdminUserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Super Admin creates an agent, client, or another admin."""
    # Check email uniqueness
    stmt = select(User).where(User.email == payload.email)
    res = await db.execute(stmt)
    if res.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Cette adresse email est déjà utilisée")

    role_val = UserRole(payload.role) if payload.role in [r.value for r in UserRole] else UserRole.AGENT
    new_user = User(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role=role_val,
        phone=payload.phone,
        is_active=True,
    )
    db.add(new_user)
    await db.flush()

    audit = AuditLog(
        application_id=1,  # System application ref
        user_id=current_user.id,
        action="user_created_by_admin",
        details={"created_email": new_user.email, "role": new_user.role.value},
    )
    db.add(audit)

    await db.commit()
    await db.refresh(new_user)

    return UserOut(
        id=new_user.id,
        email=new_user.email,
        full_name=new_user.full_name,
        role=new_user.role.value,
        phone=new_user.phone,
    )


@router.patch("/users/{user_id}/toggle-active")
async def toggle_user_status(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Enable or disable user access."""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Impossible de désactiver son propre compte administrateur")

    stmt = select(User).where(User.id == user_id)
    res = await db.execute(stmt)
    u = res.scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")

    u.is_active = not u.is_active
    await db.commit()
    return {"status": "success", "user_id": u.id, "is_active": u.is_active}


@router.patch("/users/{user_id}/role", response_model=UserOut)
async def update_user_role(
    user_id: int,
    payload: AdminUserUpdateRole,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Change user role (client, agent, admin)."""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Impossible de modifier son propre rôle administrateur")

    stmt = select(User).where(User.id == user_id)
    res = await db.execute(stmt)
    u = res.scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")

    try:
        new_role = UserRole(payload.role)
        u.role = new_role
        await db.commit()
        await db.refresh(u)
        return UserOut(
            id=u.id,
            email=u.email,
            full_name=u.full_name,
            role=u.role.value,
            phone=u.phone,
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Rôle invalide (doit être 'client', 'agent', ou 'admin')")


@router.delete("/users/{user_id}", status_code=status.HTTP_200_OK)
async def delete_user_by_admin(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Super Admin officially deletes a user or agent account."""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Impossible de supprimer son propre compte administrateur")

    stmt = select(User).where(User.id == user_id)
    res = await db.execute(stmt)
    u = res.scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")

    deleted_email = u.email
    deleted_name = u.full_name
    deleted_role = u.role.value if hasattr(u.role, 'value') else str(u.role)

    # Unlink agent from applications if was assigned as credit officer
    stmt_apps = select(CreditApplication).where(CreditApplication.agent_id == user_id)
    res_apps = await db.execute(stmt_apps)
    for a in res_apps.scalars().all():
        setattr(a, 'agent_id', None)

    # Unlink audit logs
    stmt_audits = select(AuditLog).where(AuditLog.user_id == user_id)
    res_audits = await db.execute(stmt_audits)
    for al in res_audits.scalars().all():
        setattr(al, 'user_id', None)

    await db.delete(u)

    audit = AuditLog(
        application_id=1,
        user_id=current_user.id,
        action="user_deleted_by_admin",
        details={"deleted_user_id": user_id, "name": deleted_name, "email": deleted_email, "role": deleted_role},
    )
    db.add(audit)

    await db.commit()
    return {"status": "success", "message": f"Compte {deleted_name} ({deleted_email}) supprimé avec succès"}


# ── PRUDENTIAL SETTINGS ───────────────────────────────────────────────
@router.get("/settings", response_model=AdminPrudentialSettings)
async def get_prudential_settings(
    current_user: User = Depends(require_role("admin")),
):
    """Get current BCEAO prudential and ML scoring settings."""
    return _GLOBAL_PRUDENTIAL_SETTINGS


@router.put("/settings", response_model=AdminPrudentialSettings)
async def update_prudential_settings(
    payload: AdminPrudentialSettings,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Update BCEAO prudential rules & ML weights."""
    global _GLOBAL_PRUDENTIAL_SETTINGS
    _GLOBAL_PRUDENTIAL_SETTINGS = payload

    audit = AuditLog(
        application_id=1,
        user_id=current_user.id,
        action="prudential_settings_updated",
        details=payload.model_dump(),
    )
    db.add(audit)
    await db.commit()

    return _GLOBAL_PRUDENTIAL_SETTINGS


# ── CONSOLIDATED AUDIT LOGS ───────────────────────────────────────────
@router.get("/audit-logs", response_model=AuditLogListOut)
async def get_global_audit_logs(
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Consolidated chronological audit trail for the entire microfinance platform."""
    stmt = (
        select(AuditLog)
        .order_by(desc(AuditLog.timestamp))
        .limit(limit)
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


# ── CLIENTS MANAGEMENT ────────────────────────────────────────────────
@router.get("/clients", response_model=List[AdminClientSummaryOut])
async def list_admin_clients(
    sector: Optional[str] = None,
    kyc_status: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """List all borrowers/clients with enriched dossier and KYC statistics."""
    stmt = (
        select(User)
        .where(User.role == UserRole.CLIENT)
        .options(
            selectinload(User.applications).selectinload(CreditApplication.scoring_result),
            selectinload(User.applications).selectinload(CreditApplication.extracted_data),
        )
        .order_by(desc(User.created_at))
    )

    if search:
        s = f"%{search.strip().lower()}%"
        stmt = stmt.where(func.lower(User.full_name).like(s) | func.lower(User.email).like(s) | func.lower(User.phone).like(s))

    res = await db.execute(stmt)
    clients = res.scalars().all()

    out: List[AdminClientSummaryOut] = []
    for c in clients:
        apps = c.applications or []
        apps_count = len(apps)
        total_req = sum(float(a.requested_amount) for a in apps)
        approved_apps = [a for a in apps if a.status in [ApplicationStatus.APPROVED, ApplicationStatus.ADJUSTED]]
        total_appr = sum(
            float(a.scoring_result.approved_amount or a.scoring_result.proposed_amount or a.requested_amount)
            for a in approved_apps if a.scoring_result
        )
        scores = [a.scoring_result.score for a in apps if a.scoring_result]
        avg_score = round(sum(scores) / len(scores), 1) if scores else None

        # Derive sector and financial data from latest application
        latest_app = max(apps, key=lambda a: a.created_at) if apps else None
        c_sector = latest_app.activity_sector.value if latest_app else None

        # Filter by sector if provided
        if sector and sector != "all" and c_sector != sector:
            continue

        # KYC Status check
        has_verified_doc = any(a.extracted_data and a.extracted_data.is_verified for a in apps)
        has_any_doc = any(a.extracted_data and a.extracted_data.id_number for a in apps)
        c_kyc = "complet" if has_verified_doc else ("partiel" if has_any_doc else "non_verifie")

        # Filter by KYC status if provided
        if kyc_status and kyc_status != "all" and c_kyc != kyc_status:
            continue

        rev = None
        exp = None
        if latest_app and latest_app.extracted_data:
            rev = latest_app.extracted_data.monthly_revenue
            exp = latest_app.extracted_data.monthly_expenses

        out.append(
            AdminClientSummaryOut(
                id=c.id,
                full_name=c.full_name,
                email=c.email,
                phone=c.phone,
                is_active=c.is_active,
                created_at=c.created_at,
                activity_sector=c_sector,
                applications_count=apps_count,
                total_requested=total_req,
                total_approved=total_appr,
                average_score=avg_score,
                kyc_status=c_kyc,
                monthly_revenue=rev,
                monthly_expenses=exp,
                last_application_status=latest_app.status.value if latest_app else None,
                last_application_date=latest_app.created_at if latest_app else None,
            )
        )

    return out


@router.get("/clients/{client_id}", response_model=AdminClientDetailOut)
async def get_admin_client_detail(
    client_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Get full 360-degree profile of a client including dossiers and audit history."""
    stmt = (
        select(User)
        .where(User.id == client_id, User.role == UserRole.CLIENT)
        .options(
            selectinload(User.applications).selectinload(CreditApplication.scoring_result),
            selectinload(User.applications).selectinload(CreditApplication.extracted_data),
            selectinload(User.applications).selectinload(CreditApplication.agent),
        )
    )
    res = await db.execute(stmt)
    c = res.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Client introuvable")

    apps = c.applications or []
    latest_app = max(apps, key=lambda a: a.created_at) if apps else None

    # KYC docs extraction
    has_verified_doc = any(a.extracted_data and a.extracted_data.is_verified for a in apps)
    has_any_doc = any(a.extracted_data and a.extracted_data.id_number for a in apps)
    c_kyc = "complet" if has_verified_doc else ("partiel" if has_any_doc else "non_verifie")

    kyc_docs = {}
    if latest_app and latest_app.extracted_data:
        ed = latest_app.extracted_data
        kyc_docs = {
            "id_type": ed.id_type or "CNI / NINA",
            "id_number": ed.id_number,
            "date_of_birth": ed.date_of_birth,
            "business_registration_number": ed.business_registration_number,
            "years_in_business": ed.years_in_business,
            "is_verified": ed.is_verified,
            "verification_notes": ed.verification_notes,
            "extracted_at": ed.extracted_at.isoformat() if ed.extracted_at else None,
        }

    app_list = []
    for a in sorted(apps, key=lambda x: x.created_at, reverse=True):
        app_list.append({
            "id": a.id,
            "reference": a.reference,
            "activity_sector": a.activity_sector.value,
            "requested_amount": a.requested_amount,
            "requested_duration_months": a.requested_duration_months,
            "status": a.status.value,
            "agent_name": a.agent.full_name if a.agent else None,
            "score": a.scoring_result.score if a.scoring_result else None,
            "risk_level": a.scoring_result.risk_level.value if a.scoring_result else None,
            "approved_amount": a.scoring_result.approved_amount if a.scoring_result else None,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        })

    # Fetch audit logs for this client's applications
    app_ids = [a.id for a in apps]
    audit_list = []
    if app_ids:
        audit_stmt = (
            select(AuditLog)
            .where(AuditLog.application_id.in_(app_ids) | (AuditLog.user_id == client_id))
            .order_by(desc(AuditLog.timestamp))
            .limit(20)
        )
        audit_res = await db.execute(audit_stmt)
        for al in audit_res.scalars().all():
            audit_list.append({
                "id": al.id,
                "action": al.action,
                "details": al.details,
                "timestamp": al.timestamp.isoformat() if al.timestamp else None,
            })

    return AdminClientDetailOut(
        id=c.id,
        full_name=c.full_name,
        email=c.email,
        phone=c.phone,
        is_active=c.is_active,
        created_at=c.created_at,
        activity_sector=latest_app.activity_sector.value if latest_app else None,
        monthly_revenue=latest_app.extracted_data.monthly_revenue if (latest_app and latest_app.extracted_data) else None,
        monthly_expenses=latest_app.extracted_data.monthly_expenses if (latest_app and latest_app.extracted_data) else None,
        existing_debt=latest_app.extracted_data.existing_debt if (latest_app and latest_app.extracted_data) else None,
        business_description=latest_app.business_description if latest_app else None,
        years_in_business=latest_app.extracted_data.years_in_business if (latest_app and latest_app.extracted_data) else None,
        kyc_status=c_kyc,
        kyc_documents=kyc_docs,
        applications=app_list,
        audit_logs=audit_list,
    )


@router.patch("/clients/{client_id}", response_model=UserOut)
async def update_admin_client(
    client_id: int,
    payload: AdminClientUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Super Admin updates client contact info or status."""
    stmt = select(User).where(User.id == client_id, User.role == UserRole.CLIENT)
    res = await db.execute(stmt)
    u = res.scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=404, detail="Client introuvable")

    if payload.full_name is not None:
        u.full_name = payload.full_name
    if payload.phone is not None:
        u.phone = payload.phone
    if payload.email is not None:
        u.email = payload.email
    if payload.is_active is not None:
        u.is_active = payload.is_active

    audit = AuditLog(
        application_id=1,
        user_id=current_user.id,
        action="client_updated_by_admin",
        details={"client_id": client_id, "updated_fields": payload.model_dump(exclude_unset=True)},
    )
    db.add(audit)
    await db.commit()
    await db.refresh(u)

    return UserOut(
        id=u.id,
        email=u.email,
        full_name=u.full_name,
        role=u.role.value,
        phone=u.phone,
    )


# ── AGENTS MANAGEMENT ─────────────────────────────────────────────────
@router.get("/agents", response_model=List[AdminAgentSummaryOut])
async def list_admin_agents(
    branch: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """List credit officers with branch assignment and performance KPIs."""
    stmt = select(User).where(User.role == UserRole.AGENT).order_by(desc(User.created_at))

    if search:
        s = f"%{search.strip().lower()}%"
        stmt = stmt.where(func.lower(User.full_name).like(s) | func.lower(User.email).like(s))

    res = await db.execute(stmt)
    agents = res.scalars().all()

    # Pre-defined branch mapping based on agent ID / name
    branch_map = {
        "ibrahima": "Antenne Centrale Bamako-District",
        "awa": "Antenne Régionale Ségou",
        "bakary": "Antenne Régionale Sikasso",
    }

    out: List[AdminAgentSummaryOut] = []
    for idx, ag in enumerate(agents):
        # Query applications assigned to this agent
        app_stmt = (
            select(CreditApplication)
            .where(CreditApplication.agent_id == ag.id)
            .options(selectinload(CreditApplication.scoring_result))
        )
        app_res = await db.execute(app_stmt)
        ag_apps = app_res.scalars().all()

        assigned = len(ag_apps)
        certified = sum(1 for a in ag_apps if a.status in [ApplicationStatus.APPROVED, ApplicationStatus.ADJUSTED, ApplicationStatus.REJECTED])
        pending = sum(1 for a in ag_apps if a.status in [ApplicationStatus.PENDING_VERIFICATION, ApplicationStatus.DATA_VERIFIED, ApplicationStatus.DOCUMENTS_UPLOADED])
        approved_apps = [a for a in ag_apps if a.status in [ApplicationStatus.APPROVED, ApplicationStatus.ADJUSTED]]
        approved_vol = sum(
            float(a.scoring_result.approved_amount or a.scoring_result.proposed_amount or a.requested_amount)
            for a in approved_apps if a.scoring_result
        )
        rate = round(len(approved_apps) / certified * 100, 1) if certified > 0 else 85.0

        # Assigned branch
        agent_first = ag.full_name.lower().split()[0] if ag.full_name else ""
        assigned_branch = branch_map.get(agent_first, _BRANCHES_DATA[idx % len(_BRANCHES_DATA)]["name"])

        if branch and branch != "all" and branch not in assigned_branch:
            continue

        out.append(
            AdminAgentSummaryOut(
                id=ag.id,
                full_name=ag.full_name,
                email=ag.email,
                phone=ag.phone,
                is_active=ag.is_active,
                created_at=ag.created_at,
                branch=assigned_branch,
                assigned_applications_count=assigned,
                certified_applications_count=certified,
                pending_applications_count=pending,
                approved_volume=approved_vol,
                approval_rate=rate,
                average_processing_hours=2.4 + (idx * 0.3),
            )
        )

    return out


@router.post("/agents/{agent_id}/reassign")
async def reassign_agent_applications(
    agent_id: int,
    payload: AdminAgentReassignPayload,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Reassign pending credit applications from one agent to another."""
    if agent_id == payload.target_agent_id:
        raise HTTPException(status_code=400, detail="L'agent source et l'agent cible doivent être différents")

    # Verify target agent
    tgt_stmt = select(User).where(User.id == payload.target_agent_id, User.role == UserRole.AGENT)
    tgt_res = await db.execute(tgt_stmt)
    target_agent = tgt_res.scalar_one_or_none()
    if not target_agent:
        raise HTTPException(status_code=404, detail="Agent cible introuvable ou rôle invalide")

    # Query applications to reassign
    stmt = select(CreditApplication).where(CreditApplication.agent_id == agent_id)
    if payload.application_ids:
        stmt = stmt.where(CreditApplication.id.in_(payload.application_ids))
    else:
        # Reassign pending applications
        stmt = stmt.where(CreditApplication.status.in_([
            ApplicationStatus.PENDING_VERIFICATION,
            ApplicationStatus.DATA_VERIFIED,
            ApplicationStatus.DOCUMENTS_UPLOADED,
        ]))

    res = await db.execute(stmt)
    apps_to_reassign = res.scalars().all()
    count = len(apps_to_reassign)

    for a in apps_to_reassign:
        a.agent_id = target_agent.id
        db.add(AuditLog(
            application_id=a.id,
            user_id=current_user.id,
            action="application_reassigned_by_admin",
            details={
                "from_agent_id": agent_id,
                "to_agent_id": target_agent.id,
                "target_agent_name": target_agent.full_name,
            },
        ))

    await db.commit()
    return {
        "status": "success",
        "reassigned_count": count,
        "target_agent": target_agent.full_name,
        "message": f"{count} dossier(s) réassigné(s) à {target_agent.full_name} avec succès.",
    }


# ── PASSWORD RESET BY ADMIN ───────────────────────────────────────────
@router.post("/users/{user_id}/reset-password")
async def reset_user_password_by_admin(
    user_id: int,
    payload: AdminResetPasswordPayload,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Super Admin resets a user's password."""
    stmt = select(User).where(User.id == user_id)
    res = await db.execute(stmt)
    u = res.scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")

    u.hashed_password = hash_password(payload.new_password)

    audit = AuditLog(
        application_id=1,
        user_id=current_user.id,
        action="password_reset_by_admin",
        details={"target_user_id": user_id, "target_email": u.email, "role": u.role.value},
    )
    db.add(audit)
    await db.commit()

    return {
        "status": "success",
        "message": f"Mot de passe réinitialisé pour le compte {u.full_name} ({u.email}).",
    }


# ── REGIONAL BRANCHES ─────────────────────────────────────────────────
@router.get("/branches", response_model=List[AdminBranchOut])
async def list_regional_branches(
    current_user: User = Depends(require_role("admin")),
):
    """List microfinance branches and rural service desks."""
    return [AdminBranchOut(**b) for b in _BRANCHES_DATA]


@router.post("/branches", response_model=AdminBranchOut, status_code=status.HTTP_201_CREATED)
async def create_regional_branch(
    payload: AdminBranchCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Register a new branch or rural service desk in the network."""
    new_id = f"branch-{len(_BRANCHES_DATA) + 1}"
    branch_dict = {
        "id": new_id,
        "name": payload.name,
        "city": payload.city,
        "branch_type": payload.branch_type,
        "status": "Opérationnelle",
        "lead_agent": payload.lead_agent,
        "agents_count": 1,
        "active_loans_count": 0,
        "total_disbursed": 0.0,
        "par_30": 0.0,
        "max_credit_limit": payload.max_credit_limit,
    }
    _BRANCHES_DATA.append(branch_dict)

    audit = AuditLog(
        application_id=1,
        user_id=current_user.id,
        action="branch_created_by_admin",
        details=branch_dict,
    )
    db.add(audit)
    await db.commit()

    return AdminBranchOut(**branch_dict)


# ── RISK MATRIX & STRESS TESTING ──────────────────────────────────────
@router.get("/risk-matrix", response_model=RiskMatrixOut)
async def get_risk_matrix(
    current_user: User = Depends(require_role("admin")),
):
    """Super Admin systemic risk matrix, PAR index, and stress test baseline."""
    return RiskMatrixOut(
        par_30=2.4,
        par_60=1.1,
        par_90=0.4,
        npl_ratio=1.8,
        guarantee_coverage_rate=84.5,
        sector_risk={
            "Commerce": {"exposure_pct": 58.0, "par_30": 1.9, "default_rate": 2.1, "risk_grade": "Faible"},
            "Agriculture": {"exposure_pct": 27.0, "par_30": 3.4, "default_rate": 3.8, "risk_grade": "Modéré"},
            "Artisanat": {"exposure_pct": 11.0, "par_30": 2.2, "default_rate": 2.5, "risk_grade": "Faible"},
            "TPE": {"exposure_pct": 4.0, "par_30": 4.1, "default_rate": 4.5, "risk_grade": "Surveillance"},
        },
        branch_risk={
            "Bamako-District": {"active_loans": 28, "exposure": 18500000.0, "par_30": 1.8},
            "Ségou": {"active_loans": 16, "exposure": 9200000.0, "par_30": 2.6},
            "Sikasso": {"active_loans": 12, "exposure": 7800000.0, "par_30": 3.1},
        },
        stress_test_defaults={
            "income_shock_pct": 0.0,
            "inflation_shock_pct": 0.0,
            "baseline_par_30": 2.4,
            "capital_adequacy_ratio": 16.2,
        },
    )

