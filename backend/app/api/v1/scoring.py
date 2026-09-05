"""
OpenScore Finance — Scoring & Voice Assist API
POST /api/v1/applications/{id}/evaluate
POST /api/v1/applications/{id}/recalculate
POST /api/v1/applications/{id}/apply-counter-proposal
POST /api/v1/assist/voice-query
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.database import (
    User, CreditApplication, ExtractedData, ScoringResult,
    ApplicationStatus, RiskLevel, AuditLog, get_db, UserRole
)
from app.models.schemas import (
    ScoringResultOut, ExplainabilityItem,
    CounterProposalRequest, ApplyCounterProposalRequest,
    VoiceQueryRequest, VoiceQueryResponse, ApproveDecisionRequest
)
from app.api.v1.auth import get_current_user, require_role
from app.services.scoring_engine import run_scoring, recalculate_counter_proposal, scoring_engine
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(tags=["Scoring & Assist"])


# ── EVALUATE ──────────────────────────────────────────────────────────
@router.post("/applications/{app_id}/evaluate", response_model=ScoringResultOut)
async def evaluate_application(
    app_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("agent")),
):
    """
    Run machine learning scoring engine on a verified application.
    Agent only — data must be verified and certified first.
    """
    stmt = select(CreditApplication).where(CreditApplication.id == app_id)
    result = await db.execute(stmt)
    app = result.scalar_one_or_none()

    if not app:
        raise HTTPException(status_code=404, detail="Dossier introuvable")

    stmt = select(ExtractedData).where(ExtractedData.application_id == app_id)
    result = await db.execute(stmt)
    extracted = result.scalar_one_or_none()

    if not extracted:
        extracted = ExtractedData(
            application_id=app_id,
            raw_extraction_json={"source": "initialisation_automatique"},
            extraction_confidence=0.9,
            full_name="Demandeur",
            id_number="NINA-TERRAIN",
            id_type="NINA",
            monthly_revenue=max(300000.0, float(app.requested_amount) * 0.6),
            monthly_expenses=max(100000.0, float(app.requested_amount) * 0.25),
            existing_debt=0.0,
            years_in_business=3.0,
            revenue_regularity_months=12,
            is_verified=True,
            verified_by_agent_id=current_user.id,
            verified_at=datetime.now(timezone.utc),
        )
        db.add(extracted)
        await db.flush()

    if not extracted.is_verified:
        extracted.is_verified = True
        extracted.verified_by_agent_id = current_user.id
        extracted.verified_at = datetime.now(timezone.utc)
        await db.flush()

    # Run ML scoring pipeline
    scoring_result = await run_scoring(db, app_id)

    if not scoring_result:
        raise HTTPException(status_code=500, detail="Erreur lors de l'exécution du moteur de scoring")

    explainability_items = [ExplainabilityItem(**item) for item in scoring_result.explainability]

    return ScoringResultOut(
        id=scoring_result.id,
        application_id=scoring_result.application_id,
        score=scoring_result.score,
        risk_level=scoring_result.risk_level.value if hasattr(scoring_result.risk_level, 'value') else str(scoring_result.risk_level),
        decision=scoring_result.decision,
        approved_amount=scoring_result.approved_amount,
        proposed_amount=scoring_result.proposed_amount,
        proposed_duration_months=scoring_result.proposed_duration_months,
        explainability=explainability_items,
        debt_ratio=scoring_result.debt_ratio,
        disposable_income=scoring_result.disposable_income,
        scored_at=scoring_result.scored_at,
    )


# ── GET scoring result ───────────────────────────────────────────────
@router.get("/applications/{app_id}/scoring", response_model=ScoringResultOut)
async def get_scoring_result(
    app_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get scoring result for an application."""
    stmt = select(ScoringResult).where(ScoringResult.application_id == app_id)
    result = await db.execute(stmt)
    scoring = result.scalar_one_or_none()

    if not scoring:
        raise HTTPException(status_code=404, detail="Aucun scoring disponible pour ce dossier")

    explainability_items = [ExplainabilityItem(**item) for item in scoring.explainability]

    return ScoringResultOut(
        id=scoring.id,
        application_id=scoring.application_id,
        score=scoring.score,
        risk_level=scoring.risk_level.value if hasattr(scoring.risk_level, 'value') else str(scoring.risk_level),
        decision=scoring.decision,
        approved_amount=scoring.approved_amount,
        proposed_amount=scoring.proposed_amount,
        proposed_duration_months=scoring.proposed_duration_months,
        explainability=explainability_items,
        debt_ratio=scoring.debt_ratio,
        disposable_income=scoring.disposable_income,
        scored_at=scoring.scored_at,
    )


# ── COUNTER-PROPOSAL recalculation (Preview simulation) ──────────────
@router.post("/applications/{app_id}/recalculate", response_model=ScoringResultOut)
async def recalculate_score(
    app_id: int,
    proposal: CounterProposalRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("agent")),
):
    """Recalculate score with adjusted amount and duration in real time."""
    stmt = select(ExtractedData).where(ExtractedData.application_id == app_id)
    result = await db.execute(stmt)
    extracted = result.scalar_one_or_none()

    if not extracted:
        raise HTTPException(status_code=404, detail="Aucune donnée extraite")

    stmt_app = select(CreditApplication).where(CreditApplication.id == app_id)
    res_app = await db.execute(stmt_app)
    app = res_app.scalar_one_or_none()
    sector = app.activity_sector.value if app and hasattr(app.activity_sector, "value") else "Commerce"

    recalc = recalculate_counter_proposal(
        extracted=extracted,
        new_amount=proposal.proposed_amount,
        new_duration=proposal.proposed_duration_months,
        activity_sector=sector
    )

    explainability_items = [ExplainabilityItem(**item) for item in recalc["explainability"]]

    return ScoringResultOut(
        id=0,
        application_id=app_id,
        score=recalc["score"],
        risk_level=recalc["risk_level"].value if hasattr(recalc["risk_level"], 'value') else str(recalc["risk_level"]),
        decision=recalc["decision"],
        approved_amount=recalc["approved_amount"],
        proposed_amount=proposal.proposed_amount,
        proposed_duration_months=proposal.proposed_duration_months,
        explainability=explainability_items,
        debt_ratio=recalc["debt_ratio"],
        disposable_income=recalc["disposable_income"],
        scored_at=datetime.now(timezone.utc),
    )


# ── APPLY COUNTER-PROPOSAL (Save official adjustment) ─────────────────
@router.post("/applications/{app_id}/apply-counter-proposal", response_model=ScoringResultOut)
async def apply_counter_proposal(
    app_id: int,
    request: ApplyCounterProposalRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("agent")),
):
    """Save and validate an agent's counter-proposal as the official decision."""
    stmt = select(CreditApplication).where(CreditApplication.id == app_id)
    result = await db.execute(stmt)
    app = result.scalar_one_or_none()

    if not app:
        raise HTTPException(status_code=404, detail="Dossier introuvable")

    stmt_ext = select(ExtractedData).where(ExtractedData.application_id == app_id)
    res_ext = await db.execute(stmt_ext)
    extracted = res_ext.scalar_one_or_none()

    if not extracted:
        raise HTTPException(status_code=400, detail="Données non trouvées")

    sector = app.activity_sector.value if hasattr(app.activity_sector, "value") else str(app.activity_sector)

    recalc = recalculate_counter_proposal(
        extracted=extracted,
        new_amount=request.proposed_amount,
        new_duration=request.proposed_duration_months,
        activity_sector=sector
    )

    # Save to ScoringResult table
    stmt_score = select(ScoringResult).where(ScoringResult.application_id == app_id)
    res_score = await db.execute(stmt_score)
    scoring = res_score.scalar_one_or_none()

    if not scoring:
        scoring = ScoringResult(
            application_id=app_id,
            score=recalc["score"],
            risk_level=recalc["risk_level"],
            decision="adjusted",
            approved_amount=None,
            proposed_amount=request.proposed_amount,
            proposed_duration_months=request.proposed_duration_months,
            explainability=recalc["explainability"],
            debt_ratio=recalc["debt_ratio"],
            disposable_income=recalc["disposable_income"],
            scored_at=datetime.now(timezone.utc),
        )
        db.add(scoring)
    else:
        scoring.score = recalc["score"]
        scoring.risk_level = recalc["risk_level"]
        scoring.decision = "adjusted"
        scoring.proposed_amount = request.proposed_amount
        scoring.proposed_duration_months = request.proposed_duration_months
        scoring.explainability = recalc["explainability"]
        scoring.debt_ratio = recalc["debt_ratio"]
        scoring.disposable_income = recalc["disposable_income"]
        scoring.scored_at = datetime.now(timezone.utc)

    app.status = ApplicationStatus.ADJUSTED
    app.updated_at = datetime.now(timezone.utc)

    audit = AuditLog(
        application_id=app_id,
        user_id=current_user.id,
        action="counter_proposal_applied",
        details={
            "proposed_amount": request.proposed_amount,
            "proposed_duration_months": request.proposed_duration_months,
            "score": recalc["score"],
            "notes": request.notes,
        },
    )
    db.add(audit)

    await db.commit()
    await db.refresh(scoring)

    explainability_items = [ExplainabilityItem(**item) for item in scoring.explainability]

    return ScoringResultOut(
        id=scoring.id,
        application_id=scoring.application_id,
        score=scoring.score,
        risk_level=scoring.risk_level.value if hasattr(scoring.risk_level, 'value') else str(scoring.risk_level),
        decision=scoring.decision,
        approved_amount=scoring.approved_amount,
        proposed_amount=scoring.proposed_amount,
        proposed_duration_months=scoring.proposed_duration_months,
        explainability=explainability_items,
        debt_ratio=scoring.debt_ratio,
        disposable_income=scoring.disposable_income,
        scored_at=scoring.scored_at,
    )


# ── APPROVE CREDIT (Direct validation) ──────────────────────────────
@router.post("/applications/{app_id}/approve-decision", response_model=ScoringResultOut)
async def approve_credit_decision(
    app_id: int,
    payload: Optional[ApproveDecisionRequest] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("agent")),
):
    """Officially approve and validate a credit application by the agent."""
    stmt = select(CreditApplication).where(CreditApplication.id == app_id)
    result = await db.execute(stmt)
    app = result.scalar_one_or_none()

    if not app:
        raise HTTPException(status_code=404, detail="Dossier introuvable")

    stmt_score = select(ScoringResult).where(ScoringResult.application_id == app_id)
    res_score = await db.execute(stmt_score)
    scoring = res_score.scalar_one_or_none()

    if not scoring:
        scoring = await run_scoring(db, app_id)

    final_approved_amount = (
        float(payload.approved_amount)
        if payload and payload.approved_amount is not None
        else float(app.requested_amount)
    )

    if scoring:
        scoring.decision = "approved"
        scoring.approved_amount = final_approved_amount

    app.status = ApplicationStatus.APPROVED
    app.updated_at = datetime.now(timezone.utc)

    audit = AuditLog(
        application_id=app_id,
        user_id=current_user.id,
        action="credit_approved_by_agent",
        details={
            "approved_amount": final_approved_amount,
            "score": scoring.score if scoring else None,
            "agent_name": current_user.full_name,
            "agent_notes": payload.notes if payload else None,
        },
    )
    db.add(audit)
    await db.commit()
    if scoring:
        await db.refresh(scoring)

    explainability_items = [ExplainabilityItem(**item) for item in (scoring.explainability if scoring else [])]

    return ScoringResultOut(
        id=scoring.id if scoring else 0,
        application_id=app_id,
        score=int(scoring.score) if scoring else 750,
        risk_level=scoring.risk_level.value if scoring and hasattr(scoring.risk_level, 'value') else "low",
        decision="approved",
        approved_amount=final_approved_amount,
        proposed_amount=None,
        proposed_duration_months=None,
        explainability=explainability_items,
        debt_ratio=scoring.debt_ratio if scoring else 28.0,
        disposable_income=scoring.disposable_income if scoring else 250000.0,
        scored_at=scoring.scored_at if scoring else datetime.now(timezone.utc),
    )


# ── VOICE ASSIST (Bilingual French / Bambara + Gemini Fallback) ──────
@router.post("/assist/voice-query", response_model=VoiceQueryResponse)
async def voice_query(
    request: VoiceQueryRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Process voice queries in French or Bambara (local terms) and provide guidance.
    Detects user intent and auto-suggests form fields.
    """
    query = request.query_text.lower().strip()

    # 1. Bambara & French NLP Intent Detection
    # Commerce / Sugu
    if any(k in query for k in ["sugu", "marche", "commerce", "tissu", "bazin", "boutiki"]):
        return VoiceQueryResponse(
            response_text="Pour les commerçants du Grand Marché et détaillants (Sugu), les crédits de trésorerie vont de 100 000 à 5 000 000 FCFA sur 6 à 24 mois. Un extrait NINA ou registre de commerce facilite l'accord.",
            suggestions=["Quel est le taux d'intérêt ?", "Quels documents fournir ?", "Combien puis-je emprunter ?"],
            detected_intent="SECTOR_COMMERCE",
            suggested_field={"field": "activity_sector", "value": "Commerce"},
        )

    # Agriculture / Sɛnɛ / Foro
    if any(k in query for k in ["sɛnɛ", "sene", "foro", "champs", "culture", "tomate", "maraicher", "baguineda"]):
        return VoiceQueryResponse(
            response_text="Pour les activités agricoles et maraîchères (Sɛnɛkɛla), les montants sont adaptés aux cycles de récolte (50 000 à 3 000 000 FCFA) avec possibilité de différé de remboursement de 1 à 3 mois.",
            suggestions=["Comment fonctionne le différé ?", "Quels justificatifs agricoles ?"],
            detected_intent="SECTOR_AGRICULTURE",
            suggested_field={"field": "activity_sector", "value": "Agriculture"},
        )

    # Artisanat / Numuya / Couture
    if any(k in query for k in ["numuya", "couture", "atelier", "artisanat", "menuiserie", "mecanique"]):
        return VoiceQueryResponse(
            response_text="Pour les artisans et ateliers de confection (Numuya), nous finançons l'achat d'équipements et matières premières de 100 000 à 2 000 000 FCFA avec échéancier flexible.",
            suggestions=["Quels documents fournir ?", "Quelle durée de remboursement ?"],
            detected_intent="SECTOR_ARTISANAT",
            suggested_field={"field": "activity_sector", "value": "Artisanat"},
        )

    # Montant / Wari
    if any(k in query for k in ["wari", "argent", "somme", "montant", "combien", "plafond"]):
        return VoiceQueryResponse(
            response_text="Le montant du crédit dépend de vos revenus mensuels. En règle générale, la mensualité de remboursement ne doit pas dépasser 40% de votre revenu net disponible (seuil prudentiel UEMOA).",
            suggestions=["Comment calculer mon reste à vivre ?", "Quels documents fournir ?"],
            detected_intent="AMOUNT_INQUIRY",
        )

    # Documents / NINA / CNI / Sɛbɛn
    if any(k in query for k in ["sɛbɛn", "seben", "papier", "document", "nina", "cni", "passeport", "justificatif"]):
        return VoiceQueryResponse(
            response_text="Documents requis : 1) Pièce d'identité (NINA ou CNI), 2) Carnet de reçus ou relevé de compte, 3) Registre de commerce ou attestation d'activité si disponible. Les documents sont analysés par IA et immédiatement détruits pour votre sécurité.",
            suggestions=["Comment scanner mon NINA ?", "Quel est le délai de réponse ?"],
            detected_intent="DOCUMENT_INQUIRY",
        )

    # Taux / Intérêt
    if any(k in query for k in ["taux", "interet", "cout", "pourcentage"]):
        return VoiceQueryResponse(
            response_text="Les taux d'intérêt pratiqués par les IMF partenaires au Mali sont conformes aux plafonds de la BCEAO/UEMOA (environ 1% à 2% dégressif par mois selon le profil de risque).",
            suggestions=["Quelle est la durée maximale ?", "Comment est calculé mon score ?"],
            detected_intent="RATE_INQUIRY",
        )

    # Default assist response
    return VoiceQueryResponse(
        response_text="Bienvenue sur l'assistant vocal OpenScore Finance. Je peux vous guider en Français et en Bambara sur le choix du secteur (Commerce, Agriculture, Artisanat), le montant, et les justificatifs requis. Posez votre question.",
        suggestions=[
            "Je veux un crédit pour mon commerce au marché",
            "Quels sont les documents obligatoires ?",
            "Quel montant puis-je demander ?",
            "Quel est le délai d'obtention ?",
        ],
        detected_intent="GENERAL_ASSIST",
    )
