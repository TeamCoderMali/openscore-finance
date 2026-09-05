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
