"""
OpenScore Finance — Database Models (SQLAlchemy Async + MySQL)
Tables: users, credit_applications, extracted_data, scoring_results, audit_logs
"""

from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Float, Text, Boolean, DateTime,
    ForeignKey, Enum, JSON, create_engine
)
from sqlalchemy.orm import relationship, DeclarativeBase
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
import enum

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

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.CLIENT)
    phone = Column(String(20), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    applications = relationship("CreditApplication", back_populates="applicant", foreign_keys="[CreditApplication.applicant_id]")


class CreditApplication(Base):
    __tablename__ = "credit_applications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    reference = Column(String(20), unique=True, nullable=False, index=True)
    applicant_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    activity_sector = Column(Enum(ActivitySector), nullable=False)
    requested_amount = Column(Float, nullable=False)
    requested_duration_months = Column(Integer, default=12)
    business_description = Column(Text, nullable=True)
    status = Column(Enum(ApplicationStatus), default=ApplicationStatus.DRAFT)
    agent_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    applicant = relationship("User", foreign_keys=[applicant_id], back_populates="applications")
    agent = relationship("User", foreign_keys=[agent_id])
    extracted_data = relationship("ExtractedData", back_populates="application", uselist=False)
    scoring_result = relationship("ScoringResult", back_populates="application", uselist=False)
    audit_logs = relationship("AuditLog", back_populates="application")


class ExtractedData(Base):
    __tablename__ = "extracted_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    application_id = Column(Integer, ForeignKey("credit_applications.id"), unique=True, nullable=False)

    # Identity fields (from CNI / passport)
    full_name = Column(String(255), nullable=True)
    date_of_birth = Column(String(20), nullable=True)
    id_number = Column(String(50), nullable=True)
    id_type = Column(String(50), nullable=True)

    # Financial fields (from attestation / registre)
    monthly_revenue = Column(Float, nullable=True)
    monthly_expenses = Column(Float, nullable=True)
    existing_debt = Column(Float, default=0.0)
    business_registration_number = Column(String(100), nullable=True)
    business_start_date = Column(String(20), nullable=True)
    years_in_business = Column(Float, nullable=True)

    # Revenue regularity (months with income out of last 12)
    revenue_regularity_months = Column(Integer, default=12)

    # Verification
    is_verified = Column(Boolean, default=False)
    verified_by_agent_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    verified_at = Column(DateTime, nullable=True)
    verification_notes = Column(Text, nullable=True)

    # Raw extraction
    raw_extraction_json = Column(JSON, nullable=True)
    extraction_confidence = Column(Float, nullable=True)
    extracted_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    application = relationship("CreditApplication", back_populates="extracted_data")


class ScoringResult(Base):
    __tablename__ = "scoring_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    application_id = Column(Integer, ForeignKey("credit_applications.id"), unique=True, nullable=False)

    # Score
    score = Column(Integer, nullable=False)  # 0-1000
    risk_level = Column(Enum(RiskLevel), nullable=False)
    decision = Column(String(20), nullable=False)  # approved, adjusted, rejected

    # Amounts
    approved_amount = Column(Float, nullable=True)
    proposed_amount = Column(Float, nullable=True)  # counter-proposal
    proposed_duration_months = Column(Integer, nullable=True)

    # Explainability
    explainability = Column(JSON, nullable=False)  # list of {variable, value, impact, weight, contribution}

    # Ratios
    debt_ratio = Column(Float, nullable=True)
    disposable_income = Column(Float, nullable=True)

    scored_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    application = relationship("CreditApplication", back_populates="scoring_result")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    application_id = Column(Integer, ForeignKey("credit_applications.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(100), nullable=False)
    details = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    application = relationship("CreditApplication", back_populates="audit_logs")


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
