"""
OpenScore Finance — Database Models (SQLAlchemy 2.0 Async + MySQL)
Tables: users, credit_applications, extracted_data, scoring_results, audit_logs
"""

from datetime import datetime, timezone
from typing import List, Any, Optional, Dict
import enum

from sqlalchemy import (
    String, Float, Text, Boolean, DateTime,
    ForeignKey, Enum, JSON
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.core.config import get_settings

settings = get_settings()

# ── Async engine & session ────────────────────────────────────────────
engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG, pool_recycle=3600)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


# ── Enums ─────────────────────────────────────────────────────────────
class UserRole(str, enum.Enum):
    CLIENT = "client"
    AGENT = "agent"
    ADMIN = "admin"


class ActivitySector(str, enum.Enum):
    COMMERCE = "Commerce"
    AGRICULTURE = "Agriculture"
    ARTISANAT = "Artisanat"
    TPE = "TPE"
    AUTRE = "Autre"


class ApplicationStatus(str, enum.Enum):
    DRAFT = "draft"
    DOCUMENTS_UPLOADED = "documents_uploaded"
    DATA_EXTRACTED = "data_extracted"
    PENDING_VERIFICATION = "pending_verification"
    DATA_VERIFIED = "data_verified"
    SCORED = "scored"
    PENDING_COMMITTEE_APPROVAL = "pending_committee_approval"
    APPROVED = "approved"
    ADJUSTED = "adjusted"
    REJECTED = "rejected"


class RiskLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class GuaranteeType(str, enum.Enum):
    TERRAIN = "terrain"
    MAISON = "maison"
    VEHICULE = "vehicule"
    EQUIPEMENT = "equipement"
    MATERIEL_PRO = "materiel_pro"
    STOCK = "stock"
    AUTRE = "autre"


# ── Models ────────────────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False, default=UserRole.CLIENT)
    phone: Mapped[str] = mapped_column(String(20), nullable=True)
    account_number: Mapped[str] = mapped_column(String(50), nullable=True, index=True)
    branch_code: Mapped[str] = mapped_column(String(50), nullable=True, default="701", index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    applications: Mapped[List["CreditApplication"]] = relationship(
        "CreditApplication",
        back_populates="applicant",
        foreign_keys="[CreditApplication.applicant_id]"
    )


class MicrofinanceAccount(Base):
    """Officially registered client accounts within the Microfinance Institution."""
    __tablename__ = "microfinance_accounts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    account_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(30), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=True)
    id_number: Mapped[str] = mapped_column(String(50), nullable=True)
    id_type: Mapped[str] = mapped_column(String(50), default="NINA")
    activity_sector: Mapped[str] = mapped_column(String(50), default="Commerce")
    monthly_revenue: Mapped[float] = mapped_column(Float, default=0.0)
    monthly_expenses: Mapped[float] = mapped_column(Float, default=0.0)
    years_in_business: Mapped[float] = mapped_column(Float, default=3.0)
    revenue_regularity_months: Mapped[int] = mapped_column(default=12)
    opened_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE")


class CreditApplication(Base):
    __tablename__ = "credit_applications"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    reference: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)
    applicant_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    account_number: Mapped[str] = mapped_column(String(50), nullable=True, index=True)
    branch_code: Mapped[str] = mapped_column(String(50), nullable=True, default="701", index=True)
    application_type: Mapped[str] = mapped_column(String(50), default="INDIVIDUAL")  # INDIVIDUAL (Salarié/Particulier) or PME
    activity_sector: Mapped[ActivitySector] = mapped_column(Enum(ActivitySector), nullable=False)
    requested_amount: Mapped[float] = mapped_column(Float, nullable=False)
    requested_duration_months: Mapped[int] = mapped_column(default=12)
    approved_amount: Mapped[float] = mapped_column(Float, nullable=True)
    business_description: Mapped[str] = mapped_column(Text, nullable=True)
    status: Mapped[ApplicationStatus] = mapped_column(Enum(ApplicationStatus), default=ApplicationStatus.DRAFT)
    agent_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=True)
    committee_notes: Mapped[str] = mapped_column(Text, nullable=True)
    form_data: Mapped[dict] = mapped_column(JSON, nullable=True)  # Complete Fiche data (Salarié or PME)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    applicant: Mapped["User"] = relationship("User", foreign_keys=[applicant_id], back_populates="applications")
    agent: Mapped["User"] = relationship("User", foreign_keys=[agent_id])
    extracted_data: Mapped["ExtractedData"] = relationship("ExtractedData", back_populates="application", uselist=False, cascade="all, delete-orphan")
    scoring_result: Mapped["ScoringResult"] = relationship("ScoringResult", back_populates="application", uselist=False, cascade="all, delete-orphan")
    audit_logs: Mapped[List["AuditLog"]] = relationship("AuditLog", back_populates="application", order_by="desc(AuditLog.timestamp)", cascade="all, delete-orphan")
    guarantees: Mapped[List["Guarantee"]] = relationship("Guarantee", back_populates="application", cascade="all, delete-orphan")
    debts: Mapped[List["Debt"]] = relationship("Debt", back_populates="application", cascade="all, delete-orphan")


class Guarantee(Base):
    """Pledged collateral assets supporting the loan application."""
    __tablename__ = "guarantees"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("credit_applications.id"), nullable=False)
    guarantee_type: Mapped[str] = mapped_column(String(50), nullable=False)  # terrain, maison, vehicule, equipement, stock, autre
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    estimated_value: Mapped[float] = mapped_column(Float, nullable=False)
    retained_value: Mapped[float] = mapped_column(Float, nullable=False)  # haircut / value retained for credit
    proof_reference: Mapped[str] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    application: Mapped["CreditApplication"] = relationship("CreditApplication", back_populates="guarantees")


class Debt(Base):
    """Existing debt commitments (internal microfinance or external)."""
    __tablename__ = "debts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("credit_applications.id"), nullable=False)
    creditor_name: Mapped[str] = mapped_column(String(150), nullable=False)
    is_internal: Mapped[bool] = mapped_column(Boolean, default=False)  # True = current MFI, False = external bank/tontine
    initial_amount: Mapped[float] = mapped_column(Float, default=0.0)
    remaining_amount: Mapped[float] = mapped_column(Float, nullable=False)
    monthly_payment: Mapped[float] = mapped_column(Float, nullable=False)
    duration_months: Mapped[int] = mapped_column(nullable=True)
    remaining_installments: Mapped[int] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    application: Mapped["CreditApplication"] = relationship("CreditApplication", back_populates="debts")


class ExtractedData(Base):
    __tablename__ = "extracted_data"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("credit_applications.id"), unique=True, nullable=False)

    # Identity fields (from CNI / passport / NINA)
    full_name: Mapped[str] = mapped_column(String(255), nullable=True)
    date_of_birth: Mapped[str] = mapped_column(String(20), nullable=True)
    id_number: Mapped[str] = mapped_column(String(50), nullable=True)
    id_type: Mapped[str] = mapped_column(String(50), nullable=True)

    # Financial fields
    monthly_revenue: Mapped[float] = mapped_column(Float, nullable=True)
    secondary_revenue: Mapped[float] = mapped_column(Float, default=0.0)
    monthly_expenses: Mapped[float] = mapped_column(Float, nullable=True)
    other_recurring_expenses: Mapped[float] = mapped_column(Float, default=0.0)
    existing_debt: Mapped[float] = mapped_column(Float, default=0.0)
    business_registration_number: Mapped[str] = mapped_column(String(100), nullable=True)
    business_start_date: Mapped[str] = mapped_column(String(20), nullable=True)
    years_in_business: Mapped[float] = mapped_column(Float, nullable=True)

    # Revenue regularity (months with income out of last 12)
    revenue_regularity_months: Mapped[int] = mapped_column(default=12)

    # Verification
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verified_by_agent_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=True)
    verified_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    verification_notes: Mapped[str] = mapped_column(Text, nullable=True)

    # Raw extraction & Gemini metadata
    raw_extraction_json: Mapped[dict] = mapped_column(JSON, nullable=True)
    extraction_confidence: Mapped[float] = mapped_column(Float, nullable=True)
    extracted_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    application: Mapped["CreditApplication"] = relationship("CreditApplication", back_populates="extracted_data")


class ScoringResult(Base):
    __tablename__ = "scoring_results"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("credit_applications.id"), unique=True, nullable=False)

    # Score: Normalized on a 0-100 base (standard across all interfaces)
    score: Mapped[int] = mapped_column(nullable=False)  # 0-100
    risk_level: Mapped[RiskLevel] = mapped_column(Enum(RiskLevel), nullable=False)
    decision: Mapped[str] = mapped_column(String(20), nullable=False)  # approved, adjusted, rejected

    # Amounts
    approved_amount: Mapped[float] = mapped_column(Float, nullable=True)
    proposed_amount: Mapped[float] = mapped_column(Float, nullable=True)  # counter-proposal
    proposed_duration_months: Mapped[int] = mapped_column(nullable=True)

    # Explainability (list of {variable, label, value, impact, weight, contribution, detail})
    explainability: Mapped[list] = mapped_column(JSON, nullable=False)

    # Ratios
    debt_ratio: Mapped[float] = mapped_column(Float, nullable=True)
    disposable_income: Mapped[float] = mapped_column(Float, nullable=True)
    guarantee_coverage_ratio: Mapped[float] = mapped_column(Float, nullable=True)
    policy_version: Mapped[str] = mapped_column(String(50), nullable=True)

    scored_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    application: Mapped["CreditApplication"] = relationship("CreditApplication", back_populates="scoring_result")


class ScoringPolicy(Base):
    """Dynamic, versioned Scoring Policies configured in Super Admin."""
    __tablename__ = "scoring_policies"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    version: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    approval_threshold: Mapped[int] = mapped_column(default=75)  # 0-100
    counter_proposal_threshold: Mapped[int] = mapped_column(default=60)  # 0-100
    rejection_threshold: Mapped[int] = mapped_column(default=40)  # 0-100
    max_debt_ratio: Mapped[float] = mapped_column(Float, default=0.40)
    min_disposable_income: Mapped[float] = mapped_column(Float, default=75000.0)
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    variables: Mapped[List["ScoringVariable"]] = relationship("ScoringVariable", back_populates="policy", cascade="all, delete-orphan")


class ScoringVariable(Base):
    """Dynamic variables belonging to a ScoringPolicy."""
    __tablename__ = "scoring_variables"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    policy_id: Mapped[int] = mapped_column(ForeignKey("scoring_policies.id"), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    weight: Mapped[float] = mapped_column(Float, nullable=False)  # 0.0 to 1.0 (or percentage)
    category: Mapped[str] = mapped_column(String(50), default="financial")
    impact_direction: Mapped[str] = mapped_column(String(20), default="positive")  # positive or negative
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    min_val: Mapped[float] = mapped_column(Float, nullable=True)
    max_val: Mapped[float] = mapped_column(Float, nullable=True)
    calculation_rule: Mapped[str] = mapped_column(String(255), nullable=True)

    policy: Mapped["ScoringPolicy"] = relationship("ScoringPolicy", back_populates="variables")


class GrantingMethod(Base):
    """Credit granting procedures based on requested loan amount thresholds."""
    __tablename__ = "granting_methods"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    min_amount: Mapped[float] = mapped_column(Float, nullable=False)
    max_amount: Mapped[float] = mapped_column(Float, nullable=False)
    procedure_name: Mapped[str] = mapped_column(String(150), nullable=False)
    approval_level: Mapped[str] = mapped_column(String(100), nullable=False)
    required_documents: Mapped[str] = mapped_column(Text, nullable=False)
    min_guarantee_ratio: Mapped[float] = mapped_column(Float, default=0.0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("credit_applications.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    details: Mapped[dict] = mapped_column(JSON, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    application: Mapped["CreditApplication"] = relationship("CreditApplication", back_populates="audit_logs")


class AgentEvaluation(Base):
    """Administrator evaluations of credit officers."""
    __tablename__ = "agent_evaluations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    agent_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    admin_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    rating: Mapped[float] = mapped_column(Float, default=5.0)  # Rating from 1.0 to 5.0
    criteria_scores: Mapped[dict] = mapped_column(JSON, nullable=True)  # diligence, speed, bceao_compliance, portfolio_quality
    comments: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    agent: Mapped["User"] = relationship("User", foreign_keys=[agent_id])
    admin: Mapped["User"] = relationship("User", foreign_keys=[admin_id])


class CommitteeReport(Base):
    """Post-committee arbitration minutes and reports uploaded by administrators."""
    __tablename__ = "committee_reports"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    meeting_date: Mapped[str] = mapped_column(String(50), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_url: Mapped[str] = mapped_column(Text, nullable=False)  # Download URL or base64 data
    file_size: Mapped[int] = mapped_column(default=0)  # bytes
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    uploaded_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    uploader: Mapped["User"] = relationship("User", foreign_keys=[uploaded_by_user_id])


class AccountCreationRequest(Base):
    """Kafo Jiginew membership & account creation requests from mobile."""
    __tablename__ = "account_creation_requests"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(30), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=True)
    id_type: Mapped[str] = mapped_column(String(50), default="NINA")
    id_number: Mapped[str] = mapped_column(String(50), nullable=False)
    birth_date: Mapped[str] = mapped_column(String(30), nullable=True)
    city: Mapped[str] = mapped_column(String(100), default="Bamako")
    address: Mapped[str] = mapped_column(String(255), nullable=True)
    profession: Mapped[str] = mapped_column(String(100), nullable=False)
    branch_code: Mapped[str] = mapped_column(String(50), default="701")  # 701 (Bamako), 801 (Sikasso), 901 (Ségou)
    account_type: Mapped[str] = mapped_column(String(50), default="INDIVIDUAL")  # INDIVIDUAL or PME
    status: Mapped[str] = mapped_column(String(30), default="PENDING")  # PENDING, APPROVED, REJECTED
    account_number_generated: Mapped[str] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


# ── Database initialization ───────────────────────────────────────────
async def get_db():
    """Dependency: yields an async database session."""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Create all tables if they don't exist."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
