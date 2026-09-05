"""
OpenScore Finance — Pydantic Schemas
Request/Response validation for all API endpoints.
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ── Auth ──────────────────────────────────────────────────────────────
class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=4)


class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=4)
    full_name: str = Field(..., min_length=2)
    phone: Optional[str] = None
    role: str = "client"
    id_number: Optional[str] = None
    id_type: Optional[str] = "NINA"
    city: Optional[str] = None
    activity_sector: Optional[str] = "Commerce"
    monthly_revenue: Optional[float] = None
    monthly_expenses: Optional[float] = None
    existing_debt: Optional[float] = 0.0
    years_in_business: Optional[float] = 3.0
    revenue_regularity_months: Optional[int] = 12
    requested_amount: Optional[float] = None
    business_description: Optional[str] = None


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
    applicant_phone: Optional[str] = None
    applicant_email: Optional[str] = None
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


class ContactClientRequest(BaseModel):
    channel: str = Field(..., description="phone | whatsapp | email | in_app")
    subject: str = Field(..., min_length=2)
    message: str = Field(..., min_length=5)


class ApproveDecisionRequest(BaseModel):
    approved_amount: Optional[float] = None
    notes: Optional[str] = None


class RejectApplicationRequest(BaseModel):
    reason: str = Field(..., description="Motif officiel de rejet (ex: Ratio endettement > 40%, Insuffisance de garanties)")
    notes: Optional[str] = None


class FieldSurveyRequest(BaseModel):
    guarantee_type: Optional[str] = None  # Caution solidaire, Nantissement stock, etc.
    guarantee_value: Optional[float] = None
    market_reputation: Optional[str] = None  # Tres favorable, Favorable, etc.
    field_agent_notes: Optional[str] = None
    daily_cash_flow_observed: Optional[float] = None


class PortfolioStatsOut(BaseModel):
    total_applications: int
    pending_verification: int
    approved_count: int
    adjusted_count: int
    rejected_count: int
    draft_count: int
    total_volume_requested: float
    total_volume_approved: float
    approval_rate: float
    average_score: float
    sector_distribution: Dict[str, int]
    risk_distribution: Dict[str, int]


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
    existing_debt: Optional[float] = 0.0
    business_registration_number: Optional[str] = None
    business_start_date: Optional[str] = None
    years_in_business: Optional[float] = None
    revenue_regularity_months: Optional[int] = 12
    is_verified: bool
    verified_by_agent_id: Optional[int] = None
    verified_at: Optional[datetime] = None
    verification_notes: Optional[str] = None
    raw_extraction_json: Optional[Dict[str, Any]] = None
    extraction_confidence: Optional[float] = None
    extracted_at: datetime

    model_config = {"from_attributes": True}


class ExtractedDataSchema(BaseModel):
    """Pydantic schema used by Gemini 1.5 Flash structured output"""
    nom_complet: Optional[str] = Field(None, description="Nom et prénom identifiés sur le document")
    date_naissance: Optional[str] = Field(None, description="Date de naissance au format JJ/MM/AAAA")
    numero_identite: Optional[str] = Field(None, description="Numéro de carte NINA, CNI ou Passeport")
    type_piece: Optional[str] = Field(None, description="NINA, CNI, PASSPORT, CARNET_RECUS, RCCM, ATTESTATION")
    revenu_mensuel_estime: Optional[float] = Field(None, description="Montant moyen du revenu mensuel en FCFA")
    depenses_mensuelles_estimees: Optional[float] = Field(None, description="Charges et dépenses mensuelles en FCFA")
    dette_existante: Optional[float] = Field(0.0, description="Encours de crédit ou tontine en cours en FCFA")
    numero_registre_commerce: Optional[str] = Field(None, description="Numéro RCCM ou NIF si mentionné")
    date_debut_activite: Optional[str] = Field(None, description="Date ou année de création du commerce")
    anciennete_activite_annees: Optional[float] = Field(None, description="Nombre d'années d'exercice de l'activité")
    regularite_revenus_mois: Optional[int] = Field(12, description="Nombre de mois d'activité régulière sur 12")
    document_authenticity_score: Optional[float] = Field(0.9, description="Score de lisibilité et authenticité entre 0 et 1")
    commentaires_audit: Optional[str] = Field(None, description="Observations clés de l'auditeur IA")


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
    impact: str  # positive, negative, neutral
    weight: float
    contribution: int  # Points (+/-)
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
    scored_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class CounterProposalRequest(BaseModel):
    proposed_amount: float = Field(..., gt=0)
    proposed_duration_months: int = Field(..., ge=1, le=60)


class ApplyCounterProposalRequest(BaseModel):
    proposed_amount: float = Field(..., gt=0)
    proposed_duration_months: int = Field(..., ge=1, le=60)
    notes: Optional[str] = None


# ── Audit Log ────────────────────────────────────────────────────────
class AuditLogOut(BaseModel):
    id: int
    application_id: int
    user_id: Optional[int] = None
    user_name: Optional[str] = None
    action: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime

    model_config = {"from_attributes": True}


class AuditLogListOut(BaseModel):
    logs: List[AuditLogOut]
    total: int


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
    receipt_id: str


# ── Voice Assist ─────────────────────────────────────────────────────
class VoiceQueryRequest(BaseModel):
    query_text: str
    language: Optional[str] = "fr"  # "fr" or "bm"


class VoiceQueryResponse(BaseModel):
    response_text: str
    suggestions: List[str] = []
    detected_intent: Optional[str] = None
    suggested_field: Optional[Dict[str, Any]] = None
