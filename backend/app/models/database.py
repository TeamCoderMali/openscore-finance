"""
OpenScore Finance — Database Models (SQLAlchemy 2.0 Async + MySQL)
Tables: users, credit_applications, extracted_data, scoring_results, audit_logs
"""

from datetime import datetime, timezone
from typing import List, Any
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


class ApplicationStatus(str, enum.Enum):
    DRAFT = "draft"
    DOCUMENTS_UPLOADED = "documents_uploaded"
    DATA_EXTRACTED = "data_extracted"
    PENDING_VERIFICATION = "pending_verification"
    DATA_VERIFIED = "data_verified"
    SCORED = "scored"
    APPROVED = "approved"
    ADJUSTED = "adjusted"
    REJECTED = "rejected"


class RiskLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


# ── Models ────────────────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False, default=UserRole.CLIENT)
    phone: Mapped[str] = mapped_column(String(20), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    applications: Mapped[List["CreditApplication"]] = relationship(
        "CreditApplication",
        back_populates="applicant",
        foreign_keys="[CreditApplication.applicant_id]"
    )


class CreditApplication(Base):
    __tablename__ = "credit_applications"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    reference: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)
    applicant_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    activity_sector: Mapped[ActivitySector] = mapped_column(Enum(ActivitySector), nullable=False)
    requested_amount: Mapped[float] = mapped_column(Float, nullable=False)
    requested_duration_months: Mapped[int] = mapped_column(default=12)
    business_description: Mapped[str] = mapped_column(Text, nullable=True)
    status: Mapped[ApplicationStatus] = mapped_column(Enum(ApplicationStatus), default=ApplicationStatus.DRAFT)
    agent_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    applicant: Mapped["User"] = relationship("User", foreign_keys=[applicant_id], back_populates="applications")
    agent: Mapped["User"] = relationship("User", foreign_keys=[agent_id])
    extracted_data: Mapped["ExtractedData"] = relationship("ExtractedData", back_populates="application", uselist=False)
    scoring_result: Mapped["ScoringResult"] = relationship("ScoringResult", back_populates="application", uselist=False)
    audit_logs: Mapped[List["AuditLog"]] = relationship("AuditLog", back_populates="application", order_by="desc(AuditLog.timestamp)")


class ExtractedData(Base):
    __tablename__ = "extracted_data"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("credit_applications.id"), unique=True, nullable=False)

    # Identity fields (from CNI / passport / NINA)
    full_name: Mapped[str] = mapped_column(String(255), nullable=True)
    date_of_birth: Mapped[str] = mapped_column(String(20), nullable=True)
    id_number: Mapped[str] = mapped_column(String(50), nullable=True)
    id_type: Mapped[str] = mapped_column(String(50), nullable=True)

    # Financial fields (from attestation / registre / carnet de reçus informels)
    monthly_revenue: Mapped[float] = mapped_column(Float, nullable=True)
    monthly_expenses: Mapped[float] = mapped_column(Float, nullable=True)
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

    # Score
    score: Mapped[int] = mapped_column(nullable=False)  # 0-1000
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

    scored_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    application: Mapped["CreditApplication"] = relationship("CreditApplication", back_populates="scoring_result")


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
