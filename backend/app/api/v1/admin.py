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
from sqlalchemy.orm.attributes import flag_modified

from app.models.database import (
    User, UserRole, CreditApplication, ExtractedData, ScoringResult,
    ApplicationStatus, AuditLog, get_db, ActivitySector, RiskLevel,
    ScoringPolicy, ScoringVariable, GrantingMethod,
    AgentEvaluation, CommitteeReport
)
from app.models.schemas import (
    UserOut, AuditLogOut, AuditLogListOut,
    ScoringPolicyCreate, ScoringVariableCreate, ScoringVariableUpdate,
    GrantingMethodCreate, GrantingMethodUpdate, GrantingMethodOut,
    CommitteeDecisionRequest, CommitteeDocumentRequest,
    AgentEvaluationCreate, AgentEvaluationOut, CommitteeReportCreate, CommitteeReportOut
)
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
    account_number: Optional[str] = None
    branch_code: Optional[str] = "701"
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
    account_number: Optional[str] = None
    branch_code: Optional[str] = "701"
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
    in_progress_count: int = 0
    in_progress_amount: float = 0.0
    incomplete_count: int = 0
    approved_count: int = 0
    approved_amount: float = 0.0
    rejected_count: int = 0
    total_applications: int = 0
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
        "Autre": sum(float(a.requested_amount) for a in apps if a.activity_sector == ActivitySector.AUTRE),
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


# ── DYNAMIC SCORING POLICY & VARIABLES (DB-Backed) ───────────────────
@router.get("/scoring/policy", response_model=Dict[str, Any])
async def get_admin_scoring_policy(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Get currently active scoring policy with all its dynamic variables."""
    stmt = (
        select(ScoringPolicy)
        .options(selectinload(ScoringPolicy.variables))
        .where(ScoringPolicy.is_active == True)
        .order_by(ScoringPolicy.id.desc())
    )
    res = await db.execute(stmt)
    policy = res.scalar_one_or_none()

    if not policy:
        # Create default initial policy in DB
        policy = ScoringPolicy(
            version="v1.0-UEMOA",
            is_active=True,
            approval_threshold=75,
            counter_proposal_threshold=60,
            rejection_threshold=40,
            max_debt_ratio=0.40,
            min_disposable_income=75000.0,
            created_by_user_id=current_user.id,
        )
        db.add(policy)
        await db.flush()

        from app.services.scoring_engine import DEFAULT_POLICY_VARIABLES
        for var_def in DEFAULT_POLICY_VARIABLES:
            db.add(
                ScoringVariable(
                    policy_id=policy.id,
                    code=var_def["code"],
                    name=var_def["name"],
                    weight=var_def["weight"],
                    impact_direction=var_def["impact_direction"],
                    category=var_def["category"],
                    description=var_def["description"],
                    is_active=True,
                )
            )
        await db.commit()
        await db.refresh(policy)

    vars_out = [
        {
            "id": v.id,
            "policy_id": v.policy_id,
            "code": v.code,
            "name": v.name,
            "description": v.description,
            "weight": v.weight,
            "category": v.category,
            "impact_direction": v.impact_direction,
            "is_active": v.is_active,
        }
        for v in policy.variables
    ]

    total_weight = sum(v["weight"] for v in vars_out if v["is_active"])

    return {
        "id": policy.id,
        "version": policy.version,
        "is_active": policy.is_active,
        "approval_threshold": policy.approval_threshold,
        "counter_proposal_threshold": policy.counter_proposal_threshold,
        "rejection_threshold": policy.rejection_threshold,
        "max_debt_ratio": policy.max_debt_ratio,
        "min_disposable_income": policy.min_disposable_income,
        "total_active_weight": round(total_weight, 4),
        "is_weight_valid": abs(total_weight - 1.0) < 0.005,
        "variables": vars_out,
        "created_at": policy.created_at.isoformat(),
    }


@router.post("/scoring/policy", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_new_scoring_policy(
    payload: ScoringPolicyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """
    Create a new versioned Scoring Policy.
    Validates strictly that the sum of active variable weights equals 100% (1.00).
    """
    active_vars = [v for v in payload.variables if v.is_active]
    total_weight = sum(v.weight for v in active_vars)

    if abs(total_weight - 1.0) > 0.005 and abs(total_weight - 100.0) > 0.5:
        raise HTTPException(
            status_code=400,
            detail=f"La somme des poids des variables actives doit être égale à 100% (1.00). Total actuel: {total_weight * 100 if total_weight <= 1.0 else total_weight:.1f}%"
        )

    # Normalize weights to 0.0-1.0 if entered as 0-100
    norm_factor = 0.01 if total_weight > 2.0 else 1.0

    # Deactivate previous active policies
    deact_stmt = select(ScoringPolicy).where(ScoringPolicy.is_active == True)
    deact_res = await db.execute(deact_stmt)
    for p in deact_res.scalars().all():
        p.is_active = False

    new_policy = ScoringPolicy(
        version=payload.version,
        is_active=True,
        approval_threshold=payload.approval_threshold,
        counter_proposal_threshold=payload.counter_proposal_threshold,
        rejection_threshold=payload.rejection_threshold,
        max_debt_ratio=payload.max_debt_ratio,
        min_disposable_income=payload.min_disposable_income,
        created_by_user_id=current_user.id,
    )
    db.add(new_policy)
    await db.flush()

    for v in payload.variables:
        db.add(
            ScoringVariable(
                policy_id=new_policy.id,
                code=v.code,
                name=v.name,
                description=v.description,
                weight=round(v.weight * norm_factor, 4),
                category=v.category,
                impact_direction=v.impact_direction,
                is_active=v.is_active,
                min_val=v.min_val,
                max_val=v.max_val,
            )
        )

    db.add(
        AuditLog(
            application_id=1,
            user_id=current_user.id,
            action="scoring_policy_version_created",
            details={"version": payload.version, "variables_count": len(payload.variables)},
        )
    )

    await db.commit()
    return await get_admin_scoring_policy(db=db, current_user=current_user)


@router.post("/scoring/variables", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def add_scoring_variable(
    payload: ScoringVariableCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Add a new variable to the currently active policy."""
    stmt = select(ScoringPolicy).where(ScoringPolicy.is_active == True).order_by(ScoringPolicy.id.desc())
    res = await db.execute(stmt)
    policy = res.scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail="Aucune politique de scoring active.")

    weight_norm = payload.weight if payload.weight <= 1.0 else payload.weight / 100.0
    var = ScoringVariable(
        policy_id=policy.id,
        code=payload.code,
        name=payload.name,
        description=payload.description,
        weight=round(weight_norm, 4),
        category=payload.category,
        impact_direction=payload.impact_direction,
        is_active=payload.is_active,
        min_val=payload.min_val,
        max_val=payload.max_val,
    )
    db.add(var)
    await db.commit()
    return await get_admin_scoring_policy(db=db, current_user=current_user)


@router.put("/scoring/variables/{var_id}", response_model=Dict[str, Any])
async def update_scoring_variable(
    var_id: int,
    payload: ScoringVariableUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Update variable properties or weight."""
    stmt = select(ScoringVariable).where(ScoringVariable.id == var_id)
    res = await db.execute(stmt)
    var = res.scalar_one_or_none()
    if not var:
        raise HTTPException(status_code=404, detail="Variable introuvable.")

    if payload.name is not None:
        var.name = payload.name
    if payload.description is not None:
        var.description = payload.description
    if payload.weight is not None:
        var.weight = payload.weight if payload.weight <= 1.0 else payload.weight / 100.0
    if payload.impact_direction is not None:
        var.impact_direction = payload.impact_direction
    if payload.is_active is not None:
        var.is_active = payload.is_active

    await db.commit()
    return await get_admin_scoring_policy(db=db, current_user=current_user)


@router.delete("/scoring/variables/{var_id}")
async def delete_or_deactivate_variable(
    var_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Deactivate or delete a scoring variable."""
    stmt = select(ScoringVariable).where(ScoringVariable.id == var_id)
    res = await db.execute(stmt)
    var = res.scalar_one_or_none()
    if not var:
        raise HTTPException(status_code=404, detail="Variable introuvable.")

    var.is_active = False
    await db.commit()
    return {"status": "deactivated", "var_id": var_id}


# ── GRANTING METHODS (By Loan Amount Tiers) ───────────────────────────
@router.get("/granting-methods", response_model=List[GrantingMethodOut])
async def list_granting_methods(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all configurable credit granting methods by loan tier."""
    stmt = select(GrantingMethod).order_by(GrantingMethod.min_amount.asc())
    res = await db.execute(stmt)
    items = res.scalars().all()

    if not items:
        # Seed defaults
        defaults = [
            GrantingMethod(
                min_amount=50000.0,
                max_amount=500000.0,
                procedure_name="Procédure Express Guichet",
                approval_level="Conseiller Clientèle / Chef de Guichet",
                required_documents="CNI ou NINA, Justificatif de domicile",
                min_guarantee_ratio=0.0,
                is_active=True,
            ),
            GrantingMethod(
                min_amount=500001.0,
                max_amount=2000000.0,
                procedure_name="Comité de Crédit Agence",
                approval_level="Comité de Crédit d'Agence (Chef d'Agence)",
                required_documents="CNI/NINA, Registre/Carnet de reçus, Caution solidaire ou gage",
                min_guarantee_ratio=0.30,
                is_active=True,
            ),
            GrantingMethod(
                min_amount=2000001.0,
                max_amount=10000000.0,
                procedure_name="Comité Supérieur / Direction des Crédits",
                approval_level="Direction des Crédits & Directeur Général",
                required_documents="Dossier financier complet, RCCM, Titre foncier ou carte grise",
                min_guarantee_ratio=0.70,
                is_active=True,
            ),
        ]
        db.add_all(defaults)
        await db.commit()
        stmt2 = select(GrantingMethod).order_by(GrantingMethod.min_amount.asc())
        res2 = await db.execute(stmt2)
        items = res2.scalars().all()

    return [GrantingMethodOut.model_validate(m) for m in items]


@router.post("/granting-methods", response_model=GrantingMethodOut, status_code=status.HTTP_201_CREATED)
async def create_granting_method(
    payload: GrantingMethodCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Create a new loan granting procedure tier."""
    method = GrantingMethod(
        min_amount=payload.min_amount,
        max_amount=payload.max_amount,
        procedure_name=payload.procedure_name,
        approval_level=payload.approval_level,
        required_documents=payload.required_documents,
        min_guarantee_ratio=payload.min_guarantee_ratio,
        is_active=payload.is_active,
    )
    db.add(method)
    await db.commit()
    await db.refresh(method)
    return GrantingMethodOut.model_validate(method)


@router.put("/granting-methods/{method_id}", response_model=GrantingMethodOut)
async def update_granting_method(
    method_id: int,
    payload: GrantingMethodUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    stmt = select(GrantingMethod).where(GrantingMethod.id == method_id)
    res = await db.execute(stmt)
    m = res.scalar_one_or_none()
    if not m:
        raise HTTPException(status_code=404, detail="Méthode d'octroi introuvable.")

    if payload.min_amount is not None:
        m.min_amount = payload.min_amount
    if payload.max_amount is not None:
        m.max_amount = payload.max_amount
    if payload.procedure_name is not None:
        m.procedure_name = payload.procedure_name
    if payload.approval_level is not None:
        m.approval_level = payload.approval_level
    if payload.required_documents is not None:
        m.required_documents = payload.required_documents
    if payload.min_guarantee_ratio is not None:
        m.min_guarantee_ratio = payload.min_guarantee_ratio
    if payload.is_active is not None:
        m.is_active = payload.is_active

    await db.commit()
    await db.refresh(m)
    return GrantingMethodOut.model_validate(m)


@router.delete("/granting-methods/{method_id}")
async def delete_granting_method(
    method_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    stmt = select(GrantingMethod).where(GrantingMethod.id == method_id)
    res = await db.execute(stmt)
    m = res.scalar_one_or_none()
    if not m:
        raise HTTPException(status_code=404, detail="Méthode introuvable.")

    await db.delete(m)
    await db.commit()
    return {"status": "deleted", "method_id": method_id}


# ── COMMITTEE / ADMIN APPROVAL QUEUE (Final Grant Authority) ──────────
@router.get("/pending-approvals")
async def get_pending_committee_approvals(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """
    List all applications awaiting final Committee / Admin validation.
    Displays agent who processed the dossier, score /100, and recommended decision.
    """
    stmt = (
        select(CreditApplication)
        .options(
            selectinload(CreditApplication.applicant),
            selectinload(CreditApplication.agent),
            selectinload(CreditApplication.scoring_result),
            selectinload(CreditApplication.guarantees),
            selectinload(CreditApplication.debts),
        )
        .where(
            CreditApplication.status.in_([
                ApplicationStatus.PENDING_COMMITTEE_APPROVAL,
                ApplicationStatus.SCORED,
                ApplicationStatus.APPROVED,
                ApplicationStatus.REJECTED,
                ApplicationStatus.ADJUSTED,
            ])
        )
        .order_by(desc(CreditApplication.updated_at))
    )
    res = await db.execute(stmt)
    apps = res.scalars().all()

    items = []
    for a in apps:
        scoring = a.scoring_result
        clean_status = a.status.value if hasattr(a.status, "value") else str(a.status).lower().replace("applicationstatus.", "")
        items.append({
            "id": a.id,
            "reference": a.reference,
            "account_number": a.account_number or (a.applicant.account_number if a.applicant else None),
            "applicant_name": a.applicant.full_name if a.applicant else "Demandeur",
            "applicant_phone": a.applicant.phone if a.applicant else None,
            "activity_sector": a.activity_sector.value if hasattr(a.activity_sector, "value") else str(a.activity_sector),
            "requested_amount": float(a.requested_amount),
            "requested_duration_months": a.requested_duration_months,
            "status": clean_status,
            "agent_id": a.agent_id,
            "agent_name": a.agent.full_name if a.agent else "Non assigné",
            "score": scoring.score if scoring else None,  # 0-100
            "risk_level": str(scoring.risk_level) if scoring else None,
            "algorithmic_decision": scoring.decision if scoring else None,
            "recommended_decision": scoring.decision if scoring else None,
            "proposed_amount": scoring.proposed_amount if scoring else None,
            "approved_amount": a.approved_amount or (scoring.approved_amount if scoring else None),
            "approved_duration_months": a.requested_duration_months,
            "branch_code": getattr(a, "branch_code", "701") or "701",
            "application_type": getattr(a, "application_type", "INDIVIDUAL") or "INDIVIDUAL",
            "committee_notes": a.committee_notes,
            "form_data": a.form_data or {},
            "guarantee_coverage_ratio": float(scoring.guarantee_coverage_ratio) if scoring and scoring.guarantee_coverage_ratio else 0.0,
            "total_guarantee_value": sum(float(g.retained_value or g.estimated_value) for g in a.guarantees),
            "guarantees_count": len(a.guarantees),
            "debts_count": len(a.debts),
            "updated_at": a.updated_at.isoformat(),
        })

    return {"total": len(items), "applications": items}


@router.post("/applications/{app_id}/committee-decision")
async def process_committee_decision(
    app_id: int,
    payload: CommitteeDecisionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """
    Super Admin / Credit Committee issues final approval or rejection.
    Sets approved_amount and seals the official decision.
    """
    stmt = (
        select(CreditApplication)
        .options(selectinload(CreditApplication.scoring_result))
        .where(CreditApplication.id == app_id)
    )
    res = await db.execute(stmt)
    app = res.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="Dossier introuvable.")

    decision = payload.decision.lower().strip()
    if decision in ["approved", "adjusted"]:
        app.status = ApplicationStatus.APPROVED if decision == "approved" else ApplicationStatus.ADJUSTED
        grant_amt = payload.approved_amount or float(app.requested_amount)
        app.approved_amount = grant_amt
        app.committee_notes = payload.notes
        if payload.approved_duration_months:
            app.requested_duration_months = payload.approved_duration_months
        if app.scoring_result:
            app.scoring_result.approved_amount = grant_amt
            app.scoring_result.decision = decision
            if payload.approved_duration_months:
                app.scoring_result.proposed_duration_months = payload.approved_duration_months
    elif decision == "rejected":
        app.status = ApplicationStatus.REJECTED
        app.committee_notes = payload.notes
        if app.scoring_result:
            app.scoring_result.decision = "rejected"
    else:
        raise HTTPException(status_code=400, detail="Décision invalide. Valeurs permises: approved, rejected, adjusted")

    app.updated_at = datetime.now(timezone.utc)

    db.add(
        AuditLog(
            application_id=app.id,
            user_id=current_user.id,
            action=f"committee_decision_{decision}",
            details={
                "admin": current_user.full_name,
                "approved_amount": app.approved_amount,
                "approved_duration_months": app.requested_duration_months,
                "notes": payload.notes,
            },
        )
    )
    await db.commit()

    clean_status = app.status.value if hasattr(app.status, "value") else str(app.status).lower().replace("applicationstatus.", "")

    return {
        "status": "success",
        "application_id": app.id,
        "new_status": clean_status,
        "approved_amount": app.approved_amount,
        "approved_duration_months": app.requested_duration_months,
    }


@router.post("/applications/{app_id}/request-document")
async def request_committee_document(
    app_id: int,
    payload: CommitteeDocumentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """
    Super Admin / Committee requests an additional document/piece from the agent.
    Directly attaches a notification to the dossier on the agent side.
    """
    stmt = select(CreditApplication).where(CreditApplication.id == app_id)
    res = await db.execute(stmt)
    app = res.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="Dossier introuvable.")

    form_data = dict(app.form_data or {})
    requests_list = list(form_data.get("document_requests", []))

    new_req = {
        "id": f"req_{int(datetime.now(timezone.utc).timestamp())}",
        "document_name": payload.document_name.strip(),
        "description": payload.description.strip() if payload.description else "",
        "status": "PENDING",  # PENDING or PROVIDED
        "requested_by": current_user.full_name,
        "requested_at": datetime.now(timezone.utc).isoformat(),
        "provided_file_name": None,
        "provided_at": None,
    }
    requests_list.append(new_req)
    form_data["document_requests"] = requests_list
    form_data["has_pending_document_request"] = True
    form_data["latest_document_request"] = new_req

    app.form_data = form_data
    flag_modified(app, "form_data")
    app.updated_at = datetime.now(timezone.utc)

    db.add(
        AuditLog(
            application_id=app.id,
            user_id=current_user.id,
            action="committee_document_requested",
            details={
                "admin": current_user.full_name,
                "document_name": payload.document_name,
                "description": payload.description,
            },
        )
    )
    await db.commit()

    return {
        "status": "success",
        "message": f"Demande de pièce '{payload.document_name}' transmise à l'agent.",
        "request": new_req,
        "document_request": new_req,
        "document_requests": requests_list,
        "form_data": form_data,
    }


# ── LEGACY PRUDENTIAL SETTINGS BRIDGE ─────────────────────────────────
@router.get("/settings", response_model=AdminPrudentialSettings)
async def get_prudential_settings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Bridge returning current settings from DB policy."""
    stmt = select(ScoringPolicy).where(ScoringPolicy.is_active == True).order_by(ScoringPolicy.id.desc())
    res = await db.execute(stmt)
    policy = res.scalar_one_or_none()
    if policy:
        return AdminPrudentialSettings(
            debt_ratio_ceiling=policy.max_debt_ratio,
            min_disposable_income=policy.min_disposable_income,
            approval_score_threshold=policy.approval_threshold * 10,  # for legacy clients
            counter_proposal_threshold=policy.counter_proposal_threshold * 10,
            rejection_threshold=policy.rejection_threshold * 10,
        )
    return _GLOBAL_PRUDENTIAL_SETTINGS


@router.put("/settings", response_model=AdminPrudentialSettings)
async def update_prudential_settings(
    payload: AdminPrudentialSettings,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Bridge updating settings."""
    global _GLOBAL_PRUDENTIAL_SETTINGS
    _GLOBAL_PRUDENTIAL_SETTINGS = payload
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

        c_branch = getattr(c, "branch_code", "701") or (latest_app.branch_code if latest_app else "701") or "701"

        out.append(
            AdminClientSummaryOut(
                id=c.id,
                full_name=c.full_name,
                email=c.email,
                phone=c.phone,
                account_number=c.account_number,
                branch_code=c_branch,
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
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Super Admin systemic risk matrix, PAR index, and stress test baseline."""
    stmt = select(CreditApplication).options(selectinload(CreditApplication.scoring_result))
    res = await db.execute(stmt)
    apps = res.scalars().all()

    total_applications = len(apps)
    in_prog_statuses = [
        ApplicationStatus.DOCUMENTS_UPLOADED,
        ApplicationStatus.DATA_EXTRACTED,
        ApplicationStatus.PENDING_VERIFICATION,
        ApplicationStatus.DATA_VERIFIED,
        ApplicationStatus.SCORED,
        ApplicationStatus.PENDING_COMMITTEE_APPROVAL,
    ]
    in_progress_count = sum(1 for a in apps if a.status in in_prog_statuses)
    in_progress_amount = sum(a.requested_amount for a in apps if a.status in in_prog_statuses)
    incomplete_count = sum(1 for a in apps if a.status == ApplicationStatus.DRAFT)
    approved_count = sum(1 for a in apps if a.status in [ApplicationStatus.APPROVED, ApplicationStatus.ADJUSTED])
    approved_amount = sum((a.approved_amount or a.requested_amount) for a in apps if a.status in [ApplicationStatus.APPROVED, ApplicationStatus.ADJUSTED])
    rejected_count = sum(1 for a in apps if a.status == ApplicationStatus.REJECTED)

    # Sector breakdown
    sector_counts: Dict[str, int] = {}
    for a in apps:
        raw_sec = getattr(a, "activity_sector", None) or getattr(a, "sector", None)
        sec = raw_sec.value if hasattr(raw_sec, "value") else (str(raw_sec) if raw_sec else "Commerce")
        sector_counts[sec] = sector_counts.get(sec, 0) + 1

    total_sec = max(1, sum(sector_counts.values()))
    sector_risk = {}
    for sec, count in sector_counts.items():
        exposure_pct = round((count / total_sec) * 100, 1)
        sector_risk[sec] = {
            "exposure_pct": exposure_pct,
            "par_30": 2.1 if sec == "Commerce" else (3.5 if sec == "Agriculture" else (2.6 if sec == "Autre" else 2.3)),
            "default_rate": 2.0 if sec == "Commerce" else (3.2 if sec == "Agriculture" else (2.8 if sec == "Autre" else 2.5)),
            "risk_grade": "Surveillance" if sec in ["TPE", "Autre"] else ("Modéré" if sec == "Agriculture" else "Faible"),
        }
    if not sector_risk:
        sector_risk = {
            "Commerce": {"exposure_pct": 58.0, "par_30": 1.9, "default_rate": 2.1, "risk_grade": "Faible"},
            "Agriculture": {"exposure_pct": 27.0, "par_30": 3.4, "default_rate": 3.8, "risk_grade": "Modéré"},
            "Artisanat": {"exposure_pct": 11.0, "par_30": 2.2, "default_rate": 2.5, "risk_grade": "Faible"},
            "TPE": {"exposure_pct": 4.0, "par_30": 4.1, "default_rate": 4.5, "risk_grade": "Surveillance"},
            "Autre": {"exposure_pct": 0.0, "par_30": 2.6, "default_rate": 2.8, "risk_grade": "Faible"},
        }

    branch_map = {
        "701": "Bamako-District",
        "801": "Sikasso",
        "901": "Ségou",
        "bko-central": "Bamako-District",
        "sik-maraichage": "Sikasso",
        "seg-region": "Ségou",
    }
    branch_stats = {
        "Bamako-District": {"active_loans": 0, "exposure": 0.0, "par_30": 1.8},
        "Ségou": {"active_loans": 0, "exposure": 0.0, "par_30": 2.6},
        "Sikasso": {"active_loans": 0, "exposure": 0.0, "par_30": 3.1},
    }
    for a in apps:
        b_name = branch_map.get(a.branch_code or "701", "Bamako-District")
        if b_name in branch_stats:
            branch_stats[b_name]["active_loans"] += 1
            branch_stats[b_name]["exposure"] += float(a.approved_amount or a.requested_amount)

    par_30 = 2.4
    par_60 = 1.1
    par_90 = 0.4
    if total_applications > 0:
        ratio_in_prog = in_progress_count / max(1, total_applications)
        par_30 = round(1.8 + ratio_in_prog * 1.2, 1)

    return RiskMatrixOut(
        par_30=par_30,
        par_60=par_60,
        par_90=par_90,
        npl_ratio=round(par_30 * 0.75, 1),
        guarantee_coverage_rate=86.5,
        in_progress_count=in_progress_count,
        in_progress_amount=in_progress_amount,
        incomplete_count=incomplete_count,
        approved_count=approved_count,
        approved_amount=approved_amount,
        rejected_count=rejected_count,
        total_applications=total_applications,
        sector_risk=sector_risk,
        branch_risk=branch_stats,
        stress_test_defaults={
            "income_shock_pct": 0.0,
            "inflation_shock_pct": 0.0,
            "baseline_par_30": par_30,
            "capital_adequacy_ratio": 16.2,
        },
    )


# ── AGENT EVALUATIONS ────────────────────────────────────────────────
@router.post("/agents/{agent_id}/evaluations", response_model=AgentEvaluationOut)
async def evaluate_agent(
    agent_id: int,
    payload: AgentEvaluationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Admin records a performance and compliance evaluation for a credit officer."""
    agent_stmt = select(User).where(User.id == agent_id, User.role == UserRole.AGENT)
    res = await db.execute(agent_stmt)
    agent = res.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent non trouvé.")

    eval_record = AgentEvaluation(
        agent_id=agent_id,
        admin_id=current_user.id,
        rating=payload.rating,
        criteria_scores=payload.criteria_scores or {},
        comments=payload.comments,
    )
    db.add(eval_record)
    await db.commit()
    await db.refresh(eval_record)

    return AgentEvaluationOut(
        id=eval_record.id,
        agent_id=eval_record.agent_id,
        admin_id=eval_record.admin_id,
        admin_name=current_user.full_name,
        rating=eval_record.rating,
        criteria_scores=eval_record.criteria_scores,
        comments=eval_record.comments,
        created_at=eval_record.created_at,
    )


@router.get("/agents/{agent_id}/evaluations", response_model=List[AgentEvaluationOut])
async def get_agent_evaluations(
    agent_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Fetch evaluations for a specific agent."""
    stmt = (
        select(AgentEvaluation)
        .where(AgentEvaluation.agent_id == agent_id)
        .options(selectinload(AgentEvaluation.admin))
        .order_by(AgentEvaluation.created_at.desc())
    )
    res = await db.execute(stmt)
    records = res.scalars().all()

    return [
        AgentEvaluationOut(
            id=r.id,
            agent_id=r.agent_id,
            admin_id=r.admin_id,
            admin_name=r.admin.full_name if r.admin else "Admin OpenScore",
            rating=r.rating,
            criteria_scores=r.criteria_scores,
            comments=r.comments,
            created_at=r.created_at,
        )
        for r in records
    ]


@router.get("/evaluations", response_model=List[AgentEvaluationOut])
async def list_all_evaluations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Fetch all agent evaluations across the institution."""
    stmt = (
        select(AgentEvaluation)
        .options(selectinload(AgentEvaluation.admin))
        .order_by(AgentEvaluation.created_at.desc())
    )
    res = await db.execute(stmt)
    records = res.scalars().all()

    return [
        AgentEvaluationOut(
            id=r.id,
            agent_id=r.agent_id,
            admin_id=r.admin_id,
            admin_name=r.admin.full_name if r.admin else "Admin OpenScore",
            rating=r.rating,
            criteria_scores=r.criteria_scores,
            comments=r.comments,
            created_at=r.created_at,
        )
        for r in records
    ]


# ── COMMITTEE REPORTS ────────────────────────────────────────────────
@router.post("/committee/reports", response_model=CommitteeReportOut)
async def create_committee_report(
    payload: CommitteeReportCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Upload or register a post-committee session report / minutes document."""
    report = CommitteeReport(
        title=payload.title,
        meeting_date=payload.meeting_date,
        file_name=payload.file_name,
        file_url=payload.file_url,
        file_size=payload.file_size or 0,
        notes=payload.notes,
        uploaded_by_user_id=current_user.id,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)

    return CommitteeReportOut(
        id=report.id,
        title=report.title,
        meeting_date=report.meeting_date,
        file_name=report.file_name,
        file_url=report.file_url,
        file_size=report.file_size,
        notes=report.notes,
        uploaded_by_user_id=report.uploaded_by_user_id,
        uploader_name=current_user.full_name,
        created_at=report.created_at,
    )


@router.get("/committee/reports", response_model=List[CommitteeReportOut])
async def list_committee_reports(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Retrieve all uploaded committee session reports."""
    stmt = (
        select(CommitteeReport)
        .options(selectinload(CommitteeReport.uploader))
        .order_by(CommitteeReport.created_at.desc())
    )
    res = await db.execute(stmt)
    reports = res.scalars().all()

    return [
        CommitteeReportOut(
            id=r.id,
            title=r.title,
            meeting_date=r.meeting_date,
            file_name=r.file_name,
            file_url=r.file_url,
            file_size=r.file_size,
            notes=r.notes,
            uploaded_by_user_id=r.uploaded_by_user_id,
            uploader_name=r.uploader.full_name if r.uploader else "Comité de Crédit",
            created_at=r.created_at,
        )
        for r in reports
    ]


