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


# ── Guarantees & Debts ────────────────────────────────────────────────
class GuaranteeCreate(BaseModel):
    guarantee_type: str = Field(..., description="terrain, maison, vehicule, equipement, materiel_pro, stock, autre")
    description: str = Field(..., min_length=2)
    estimated_value: float = Field(..., gt=0)
    retained_value: Optional[float] = None  # if omitted, calculated by policy haircut
    proof_reference: Optional[str] = None


class GuaranteeOut(BaseModel):
    id: int
    application_id: int
    guarantee_type: str
    description: str
    estimated_value: float
    retained_value: float
    proof_reference: Optional[str] = None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class DebtCreate(BaseModel):
    creditor_name: str = Field(..., min_length=2)
    is_internal: bool = False
    initial_amount: Optional[float] = 0.0
    remaining_amount: float = Field(..., ge=0)
    monthly_payment: float = Field(..., ge=0)
    duration_months: Optional[int] = None
    remaining_installments: Optional[int] = None


class DebtOut(BaseModel):
    id: int
    application_id: int
    creditor_name: str
    is_internal: bool
    initial_amount: float
    remaining_amount: float
    monthly_payment: float
    duration_months: Optional[int] = None
    remaining_installments: Optional[int] = None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Account Linking & Lookup ──────────────────────────────────────────
class AccountLookupOut(BaseModel):
    account_number: str
    full_name: str
    phone: str
    email: Optional[str] = None
    id_number: Optional[str] = None
    id_type: Optional[str] = "NINA"
    activity_sector: str = "Commerce"
    monthly_revenue: float
    monthly_expenses: float
    years_in_business: float
    revenue_regularity_months: int
    existing_debts: List[Dict[str, Any]] = []
    known_guarantees: List[Dict[str, Any]] = []
    past_applications: List[Dict[str, Any]] = []


class AccountLinkRequest(BaseModel):
    account_number: str


class QuickApplicationInitRequest(BaseModel):
    account_number: str
    requested_amount: float = Field(..., gt=0)
    requested_duration_months: int = Field(default=12, ge=1, le=60)
    activity_sector: Optional[str] = None
    business_description: Optional[str] = None
    monthly_revenue: Optional[float] = None
    monthly_expenses: Optional[float] = None
    years_in_business: Optional[float] = None
    revenue_regularity_months: Optional[int] = None
    guarantees: Optional[List[GuaranteeCreate]] = []
    debts: Optional[List[DebtCreate]] = []


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
    account_number: Optional[str] = None
    monthly_revenue: Optional[float] = None
    secondary_revenue: Optional[float] = 0.0
    monthly_expenses: Optional[float] = None
    other_recurring_expenses: Optional[float] = 0.0
    existing_debt: Optional[float] = 0.0
    years_in_business: Optional[float] = 3.0
    revenue_regularity_months: Optional[int] = 12
    guarantees: Optional[List[GuaranteeCreate]] = []
    debts: Optional[List[DebtCreate]] = []


class ApplicationOut(BaseModel):
    id: int
    reference: str
    applicant_id: int
    account_number: Optional[str] = None
    applicant_name: Optional[str] = None
    applicant_phone: Optional[str] = None
    applicant_email: Optional[str] = None
    activity_sector: str
    requested_amount: float
    requested_duration_months: int
    business_description: Optional[str] = None
    status: str
    agent_id: Optional[int] = None
    agent_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    guarantees: Optional[List[GuaranteeOut]] = []
    debts: Optional[List[DebtOut]] = []
    scoring_result: Optional[Dict[str, Any]] = None

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


class CommitteeDecisionRequest(BaseModel):
    decision: str = Field(..., description="approved | rejected | adjusted")
    approved_amount: Optional[float] = None
    notes: Optional[str] = None


class RejectApplicationRequest(BaseModel):
    reason: str = Field(..., description="Motif officiel de rejet (ex: Ratio endettement > 40%, Insuffisance de garanties)")
    notes: Optional[str] = None


class FieldSurveyRequest(BaseModel):
    guarantee_type: Optional[str] = None
    guarantee_value: Optional[float] = None
    market_reputation: Optional[str] = None
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
    secondary_revenue: Optional[float] = 0.0
    monthly_expenses: Optional[float] = None
    other_recurring_expenses: Optional[float] = 0.0
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
    secondary_revenue: Optional[float] = None
    monthly_expenses: Optional[float] = None
    other_recurring_expenses: Optional[float] = None
    existing_debt: Optional[float] = None
    business_registration_number: Optional[str] = None
    business_start_date: Optional[str] = None
    years_in_business: Optional[float] = None
    revenue_regularity_months: Optional[int] = None
    verification_notes: Optional[str] = None


# ── Dynamic Scoring Policy & Variables ───────────────────────────────
class ScoringVariableOut(BaseModel):
    id: int
    policy_id: int
    code: str
    name: str
    description: Optional[str] = None
    weight: float  # e.g. 0.25 (25%)
    category: str
    impact_direction: str  # positive or negative
    is_active: bool
    min_val: Optional[float] = None
    max_val: Optional[float] = None
    calculation_rule: Optional[str] = None

    model_config = {"from_attributes": True}


class ScoringVariableCreate(BaseModel):
    code: str = Field(..., min_length=2)
    name: str = Field(..., min_length=2)
    description: Optional[str] = None
    weight: float = Field(..., ge=0.0, le=1.0)
    category: str = "financial"
    impact_direction: str = "positive"
    is_active: bool = True
    min_val: Optional[float] = None
    max_val: Optional[float] = None


class ScoringVariableUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    weight: Optional[float] = None
    impact_direction: Optional[str] = None
    is_active: Optional[bool] = None


class ScoringPolicyOut(BaseModel):
    id: int
    version: str
    is_active: bool
    approval_threshold: int
    counter_proposal_threshold: int
    rejection_threshold: int
    max_debt_ratio: float
    min_disposable_income: float
    created_at: datetime
    variables: List[ScoringVariableOut] = []

    model_config = {"from_attributes": True}


class ScoringPolicyCreate(BaseModel):
    version: str = Field(..., min_length=2)
    approval_threshold: int = Field(default=75, ge=1, le=100)
    counter_proposal_threshold: int = Field(default=60, ge=1, le=100)
    rejection_threshold: int = Field(default=40, ge=1, le=100)
    max_debt_ratio: float = Field(default=0.40, ge=0.05, le=0.90)
    min_disposable_income: float = Field(default=75000.0, ge=0.0)
    variables: List[ScoringVariableCreate]


# ── Granting Methods per Loan Amount Tiers ────────────────────────────
class GrantingMethodOut(BaseModel):
    id: int
    min_amount: float
    max_amount: float
    procedure_name: str
    approval_level: str
    required_documents: str
    min_guarantee_ratio: float
    is_active: bool

    model_config = {"from_attributes": True}


class GrantingMethodCreate(BaseModel):
    min_amount: float = Field(..., ge=0)
    max_amount: float = Field(..., gt=0)
    procedure_name: str = Field(..., min_length=2)
    approval_level: str = Field(..., min_length=2)
    required_documents: str = Field(..., min_length=2)
    min_guarantee_ratio: float = Field(default=0.0, ge=0.0)
    is_active: bool = True


class GrantingMethodUpdate(BaseModel):
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    procedure_name: Optional[str] = None
    approval_level: Optional[str] = None
    required_documents: Optional[str] = None
    min_guarantee_ratio: Optional[float] = None
    is_active: Optional[bool] = None


# ── Scoring Result & Simulation ───────────────────────────────────────
class ExplainabilityItem(BaseModel):
    variable: str
    label: str
    value: str
    impact: str  # positive, negative, neutral
    weight: float
    contribution: int  # Points (+/-) on base 100
    detail: str


class ScoringResultOut(BaseModel):
    id: int
    application_id: int
    score: int  # 0-100
    risk_level: str
    decision: str
    approved_amount: Optional[float] = None
    proposed_amount: Optional[float] = None
    proposed_duration_months: Optional[int] = None
    explainability: List[ExplainabilityItem]
    debt_ratio: Optional[float] = None
    disposable_income: Optional[float] = None
    guarantee_coverage_ratio: Optional[float] = None
    policy_version: Optional[str] = None
    granting_method: Optional[Dict[str, Any]] = None
    scored_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ScoringSimulationRequest(BaseModel):
    monthly_revenue: float = Field(..., gt=0)
    secondary_revenue: Optional[float] = 0.0
    monthly_expenses: float = Field(..., ge=0)
    other_recurring_expenses: Optional[float] = 0.0
    existing_debt: Optional[float] = 0.0
    years_in_business: Optional[float] = 3.0
    revenue_regularity_months: Optional[int] = 12
    requested_amount: float = Field(..., gt=0)
    requested_duration_months: int = Field(default=12, ge=1, le=60)
    activity_sector: str = "Commerce"
    guarantees: Optional[List[GuaranteeCreate]] = []
    debts: Optional[List[DebtCreate]] = []


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
    account_number: Optional[str] = None
    applicant_name: str
    applicant_email: str
    applicant_phone: Optional[str] = None
    activity_sector: str
    requested_amount: float
    decision: str
    approved_amount: Optional[float] = None
    proposed_amount: Optional[float] = None
    proposed_duration_months: Optional[int] = None
    score: int  # 0-100
    risk_level: str
    agent_name: Optional[str] = None
    procedure_name: Optional[str] = None
    scored_at: datetime
    created_at: datetime
    receipt_id: str


# ── Voice & Contextual Assist ────────────────────────────────────────
class VoiceQueryRequest(BaseModel):
    query_text: str
    language: Optional[str] = "fr"  # "fr" or "bm"
    application_id: Optional[int] = None
    context: Optional[Dict[str, Any]] = None


class VoiceQueryResponse(BaseModel):
    response_text: str
    suggestions: List[str] = []
    detected_intent: Optional[str] = None
    suggested_field: Optional[Dict[str, Any]] = None
    audio_base64: Optional[str] = None

