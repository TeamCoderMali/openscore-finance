"""
OpenScore Finance — Scoring & Voice Assist API
POST /api/v1/applications/{id}/evaluate
POST /api/v1/assist/voice-query
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.database import (
    User, CreditApplication, ExtractedData, ScoringResult,
    get_db, UserRole
)
from app.models.schemas import (
    ScoringResultOut, ExplainabilityItem,
    CounterProposalRequest, VoiceQueryRequest, VoiceQueryResponse
)
from app.api.v1.auth import get_current_user, require_role
from app.services.scoring_engine import run_scoring, recalculate_counter_proposal

router = APIRouter(tags=["Scoring & Assist"])


# ── EVALUATE ──────────────────────────────────────────────────────────
@router.post("/applications/{app_id}/evaluate", response_model=ScoringResultOut)
async def evaluate_application(
    app_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("agent")),
):
    """
    Run scoring engine on a verified application.
    Agent only — data must be verified first.
    """
    # Check application exists and data is verified
    stmt = select(CreditApplication).where(CreditApplication.id == app_id)
    result = await db.execute(stmt)
    app = result.scalar_one_or_none()

    if not app:
        raise HTTPException(status_code=404, detail="Dossier introuvable")

    stmt = select(ExtractedData).where(ExtractedData.application_id == app_id)
    result = await db.execute(stmt)
    extracted = result.scalar_one_or_none()

    if not extracted:
        raise HTTPException(status_code=400, detail="Aucune donnée extraite")

    if not extracted.is_verified:
        raise HTTPException(
            status_code=400,
            detail="Les données doivent être vérifiées avant l'évaluation"
        )

    # Run scoring
    scoring_result = await run_scoring(db, app_id)

    if not scoring_result:
        raise HTTPException(status_code=500, detail="Erreur lors du scoring")

    # Parse explainability from JSON
    explainability = scoring_result.explainability
    if isinstance(explainability, list):
        explainability_items = [ExplainabilityItem(**item) for item in explainability]
    else:
        explainability_items = []

    return ScoringResultOut(
        id=scoring_result.id,
        application_id=scoring_result.application_id,
        score=scoring_result.score,
        risk_level=scoring_result.risk_level.value if hasattr(scoring_result.risk_level, 'value') else scoring_result.risk_level,
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
        raise HTTPException(status_code=404, detail="Aucun scoring disponible")

    explainability = scoring.explainability
    if isinstance(explainability, list):
        explainability_items = [ExplainabilityItem(**item) for item in explainability]
    else:
        explainability_items = []

    return ScoringResultOut(
        id=scoring.id,
        application_id=scoring.application_id,
        score=scoring.score,
        risk_level=scoring.risk_level.value if hasattr(scoring.risk_level, 'value') else scoring.risk_level,
        decision=scoring.decision,
        approved_amount=scoring.approved_amount,
        proposed_amount=scoring.proposed_amount,
        proposed_duration_months=scoring.proposed_duration_months,
        explainability=explainability_items,
        debt_ratio=scoring.debt_ratio,
        disposable_income=scoring.disposable_income,
        scored_at=scoring.scored_at,
    )


# ── COUNTER-PROPOSAL recalculation ───────────────────────────────────
@router.post("/applications/{app_id}/recalculate", response_model=ScoringResultOut)
async def recalculate_score(
    app_id: int,
    proposal: CounterProposalRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("agent")),
):
    """Recalculate score with adjusted amount and duration (for counter-proposal panel)."""
    stmt = select(ExtractedData).where(ExtractedData.application_id == app_id)
    result = await db.execute(stmt)
    extracted = result.scalar_one_or_none()

    if not extracted:
        raise HTTPException(status_code=404, detail="Aucune donnée extraite")

    recalc = recalculate_counter_proposal(
        extracted=extracted,
        new_amount=proposal.proposed_amount,
        new_duration=proposal.proposed_duration_months,
    )

    explainability_items = [ExplainabilityItem(**item) for item in recalc["explainability"]]

    return ScoringResultOut(
        id=0,
        application_id=app_id,
        score=recalc["score"],
        risk_level=recalc["risk_level"].value if hasattr(recalc["risk_level"], 'value') else recalc["risk_level"],
        decision=recalc["decision"],
        approved_amount=recalc["approved_amount"],
        proposed_amount=proposal.proposed_amount,
        proposed_duration_months=proposal.proposed_duration_months,
        explainability=explainability_items,
        debt_ratio=recalc["debt_ratio"],
        disposable_income=recalc["disposable_income"],
        scored_at=None,
    )


# ── VOICE ASSIST ──────────────────────────────────────────────────────
@router.post("/assist/voice-query", response_model=VoiceQueryResponse)
async def voice_query(
    request: VoiceQueryRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Process a voice query (transcribed text) and return guidance.
    MVP: rule-based responses for common microfinance questions.
    """
    query = request.query_text.lower().strip()

    # Rule-based FAQ for microfinance in Mali
    responses = {
        "montant": VoiceQueryResponse(
            response_text="Le montant du microcrédit dépend de votre secteur d'activité et de vos revenus. "
                          "Pour le commerce, les montants vont généralement de 100 000 à 5 000 000 FCFA. "
                          "Pour l'agriculture, de 50 000 à 3 000 000 FCFA.",
            suggestions=["Quel est le taux d'intérêt ?", "Quels documents fournir ?", "Quelle est la durée de remboursement ?"],
        ),
        "document": VoiceQueryResponse(
            response_text="Pour constituer votre dossier, vous devez fournir : "
                          "1) Une pièce d'identité (NINA, CNI ou Passeport), "
                          "2) Une attestation de revenus ou un relevé de compte, "
                          "3) Le registre de commerce ou attestation d'activité si applicable.",
            suggestions=["Comment obtenir un NINA ?", "Quel montant puis-je demander ?", "Combien de temps pour une réponse ?"],
        ),
        "délai": VoiceQueryResponse(
            response_text="Le traitement de votre dossier prend généralement 24 à 72 heures ouvrables "
                          "après soumission complète des documents. L'extraction automatique des données "
                          "est instantanée, mais la vérification par l'agent de crédit peut prendre du temps.",
            suggestions=["Quels documents fournir ?", "Comment suivre mon dossier ?"],
        ),
        "taux": VoiceQueryResponse(
            response_text="Le taux d'intérêt varie selon le montant et la durée du prêt. "
                          "Les taux pratiqués par les IMF au Mali sont généralement entre 1% et 2,5% par mois, "
                          "soit 12% à 30% annuels selon le programme de financement.",
            suggestions=["Quel montant puis-je demander ?", "Quelle est la durée maximale ?"],
        ),
        "remboursement": VoiceQueryResponse(
            response_text="Le remboursement se fait par échéances mensuelles sur une durée de 1 à 60 mois. "
                          "Le montant de chaque échéance dépend du capital emprunté et du taux d'intérêt. "
                          "Un différé de 1 à 3 mois peut être accordé selon votre activité.",
            suggestions=["Quel est le taux d'intérêt ?", "Que se passe-t-il en cas de retard ?"],
        ),
    }

    # Match keywords
    for keyword, response in responses.items():
        if keyword in query:
            return response

    # Default response
    return VoiceQueryResponse(
        response_text="Je suis l'assistant OpenScore Finance. Je peux vous renseigner sur les montants, "
                      "les documents nécessaires, les délais de traitement, les taux d'intérêt et "
                      "les modalités de remboursement. Comment puis-je vous aider ?",
        suggestions=[
            "Quel montant puis-je demander ?",
            "Quels documents fournir ?",
            "Quel est le délai de traitement ?",
            "Quel est le taux d'intérêt ?",
        ],
    )
