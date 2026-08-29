"""
OpenScore Finance — Pydantic Schemas
Request/Response validation for all API endpoints.
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


# ── Auth ──────────────────────────────────────────────────────────────
class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=4)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    full_name: str
    user_id: int


class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    phone: Optional[str] = None

    model_config = {"from_attributes": True}


# ── Application ──────────────────────────────────────────────────────
class ActivitySectorEnum(str, Enum):
    COMMERCE = "Commerce"
    AGRICULTURE = "Agriculture"
    ARTISANAT = "Artisanat"
    TPE = "TPE"


class ApplicationCreate(BaseModel):
    activity_sector: ActivitySectorEnum
    requested_amount: float = Field(..., gt=0, description="Montant demandé en FCFA")
    requested_duration_months: int = Field(default=12, ge=1, le=60)
    business_description: Optional[str] = None


class ApplicationOut(BaseModel):
    id: int
    reference: str
    applicant_id: int
    applicant_name: Optional[str] = None
    activity_sector: str
    requested_amount: float
    requested_duration_months: int
    business_description: Optional[str] = None
    status: str
    agent_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ApplicationListOut(BaseModel):
    applications: List[ApplicationOut]
    total: int


# ── Extracted Data ───────────────────────────────────────────────────
class ExtractedDataOut(BaseModel):
    id: int
    application_id: int
    full_name: Optional[str] = None
    date_of_birth: Optional[str] = None
    id_number: Optional[str] = None
    id_type: Optional[str] = None
    monthly_revenue: Optional[float] = None
    monthly_expenses: Optional[float] = None
    existing_debt: Optional[float] = None
    business_registration_number: Optional[str] = None
    business_start_date: Optional[str] = None
    years_in_business: Optional[float] = None
    revenue_regularity_months: Optional[int] = None
    is_verified: bool = False
    extraction_confidence: Optional[float] = None
    raw_extraction_json: Optional[dict] = None

    model_config = {"from_attributes": True}


class VerifyDataRequest(BaseModel):
    full_name: Optional[str] = None
    date_of_birth: Optional[str] = None
    id_number: Optional[str] = None
    id_type: Optional[str] = None
    monthly_revenue: Optional[float] = None
    monthly_expenses: Optional[float] = None
    existing_debt: Optional[float] = None
    business_registration_number: Optional[str] = None
    business_start_date: Optional[str] = None
    years_in_business: Optional[float] = None
    revenue_regularity_months: Optional[int] = None
    verification_notes: Optional[str] = None


# ── Scoring ──────────────────────────────────────────────────────────
class ExplainabilityItem(BaseModel):
    variable: str
    label: str
    value: str
    impact: str  # "positive" | "negative" | "neutral"
    weight: float
    contribution: float  # points contributed to score
    detail: str


class ScoringResultOut(BaseModel):
    id: int
    application_id: int
    score: int
    risk_level: str
    decision: str
    approved_amount: Optional[float] = None
    proposed_amount: Optional[float] = None
    proposed_duration_months: Optional[int] = None
    explainability: List[ExplainabilityItem]
    debt_ratio: Optional[float] = None
    disposable_income: Optional[float] = None
    scored_at: datetime

    model_config = {"from_attributes": True}


class CounterProposalRequest(BaseModel):
    proposed_amount: float = Field(..., gt=0)
    proposed_duration_months: int = Field(..., ge=1, le=60)


# ── Receipt ──────────────────────────────────────────────────────────
class ReceiptData(BaseModel):
    reference: str
    applicant_name: str
    applicant_email: str
    applicant_phone: Optional[str] = None
    activity_sector: str
    requested_amount: float
    decision: str
    approved_amount: Optional[float] = None
    proposed_amount: Optional[float] = None
    proposed_duration_months: Optional[int] = None
    score: int
    risk_level: str
    agent_name: Optional[str] = None
    scored_at: datetime
    created_at: datetime
    receipt_id: str  # unique receipt identifier


# ── Voice Assist ─────────────────────────────────────────────────────
class VoiceQueryRequest(BaseModel):
    query_text: str = Field(..., min_length=1, description="Texte de la requête vocale transcrite")
    language: str = Field(default="fr", description="Langue de la requête")


class VoiceQueryResponse(BaseModel):
    response_text: str
    suggestions: List[str] = []
