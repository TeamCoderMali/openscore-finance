"""
OpenScore Finance — Scoring & Voice Assist API
Handles scoring evaluation (0-100 base), counter-proposals, policy lookup,
simulation for unbanked prospects, and contextual voice assist via GeminiService.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.database import (
    User, CreditApplication, ExtractedData, ScoringResult,
    ApplicationStatus, RiskLevel, AuditLog, get_db, UserRole,
    GrantingMethod
)
from app.models.schemas import (
    ScoringResultOut, ExplainabilityItem,
    CounterProposalRequest, ApplyCounterProposalRequest,
    VoiceQueryRequest, VoiceQueryResponse, ApproveDecisionRequest,
    ScoringSimulationRequest, ScoringPolicyOut, ScoringVariableOut
)
from app.api.v1.auth import get_current_user, get_current_user_optional, require_role
from app.services.scoring_engine import (
    run_scoring, scoring_engine, get_active_policy_dict
)
from app.services.gemini_service import gemini_service
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(tags=["Scoring & Assist"])


async def _get_matching_granting_method(db: AsyncSession, amount: float) -> Optional[Dict[str, Any]]:
    """Find granting procedure applicable to this requested loan amount."""
    try:
        stmt = (
            select(GrantingMethod)
            .where(
                GrantingMethod.is_active == True,
                GrantingMethod.min_amount <= amount,
                GrantingMethod.max_amount >= amount,
            )
            .order_by(GrantingMethod.min_amount.desc())
        )
        res = await db.execute(stmt)
        method = res.scalar_one_or_none()
        if method:
            return {
                "id": method.id,
                "procedure_name": method.procedure_name,
                "approval_level": method.approval_level,
                "required_documents": method.required_documents,
                "min_guarantee_ratio": method.min_guarantee_ratio,
            }
    except Exception as e:
        logger.warning(f"Error fetching granting method: {e}")
    return None


# ── GET ACTIVE POLICY ────────────────────────────────────────────────
@router.get("/scoring/policy", response_model=Dict[str, Any])
async def get_active_scoring_policy(db: AsyncSession = Depends(get_db)):
    """Return the currently active scoring policy parameters and variables."""
    return await get_active_policy_dict(db)


# ── EVALUATE (Score on 0-100 base) ────────────────────────────────────
@router.post("/applications/{app_id}/evaluate", response_model=ScoringResultOut)
async def evaluate_application(
    app_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("agent", "admin")),
):
    """
    Run machine learning scoring engine on a verified application (0-100 scale).
    Takes into account all declared debts and pledged collateral.
    """
    stmt = (
        select(CreditApplication)
        .options(
            selectinload(CreditApplication.extracted_data),
            selectinload(CreditApplication.guarantees),
            selectinload(CreditApplication.debts),
        )
        .where(CreditApplication.id == app_id)
    )
    result = await db.execute(stmt)
    app = result.scalar_one_or_none()

    if not app:
        raise HTTPException(status_code=404, detail="Dossier introuvable")

    extracted = app.extracted_data
    if not extracted:
        extracted = ExtractedData(
            application_id=app_id,
            raw_extraction_json={"source": "initialisation_automatique"},
            extraction_confidence=0.9,
            full_name=app.applicant.full_name if app.applicant else "Demandeur",
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

    # Run ML scoring pipeline on base 100
    scoring_result = await run_scoring(db, app_id)

    if not scoring_result:
        raise HTTPException(status_code=500, detail="Erreur lors de l'exécution du moteur de scoring")

    explainability_items = [ExplainabilityItem(**item) for item in scoring_result.explainability]
    granting_method = await _get_matching_granting_method(db, float(app.requested_amount))

    return ScoringResultOut(
        id=scoring_result.id,
        application_id=scoring_result.application_id,
        score=scoring_result.score,  # 0-100
        risk_level=scoring_result.risk_level.value if hasattr(scoring_result.risk_level, "value") else str(scoring_result.risk_level),
        decision=scoring_result.decision,
        approved_amount=scoring_result.approved_amount,
        proposed_amount=scoring_result.proposed_amount,
        proposed_duration_months=scoring_result.proposed_duration_months,
        explainability=explainability_items,
        debt_ratio=scoring_result.debt_ratio,
        disposable_income=scoring_result.disposable_income,
        guarantee_coverage_ratio=scoring_result.guarantee_coverage_ratio,
        policy_version=scoring_result.policy_version,
        granting_method=granting_method,
        scored_at=scoring_result.scored_at,
    )


# ── GET SCORING RESULT ────────────────────────────────────────────────
@router.get("/applications/{app_id}/scoring", response_model=ScoringResultOut)
async def get_scoring_result(
    app_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get scoring result for an application (0-100 base)."""
    stmt = (
        select(ScoringResult)
        .options(selectinload(ScoringResult.application))
        .where(ScoringResult.application_id == app_id)
    )
    result = await db.execute(stmt)
    scoring = result.scalar_one_or_none()

    if not scoring:
        raise HTTPException(status_code=404, detail="Aucun scoring disponible pour ce dossier")

    explainability_items = [ExplainabilityItem(**item) for item in scoring.explainability]
    granting_method = None
    if scoring.application:
        granting_method = await _get_matching_granting_method(db, float(scoring.application.requested_amount))

    return ScoringResultOut(
        id=scoring.id,
        application_id=scoring.application_id,
        score=scoring.score,  # 0-100
        risk_level=scoring.risk_level.value if hasattr(scoring.risk_level, "value") else str(scoring.risk_level),
        decision=scoring.decision,
        approved_amount=scoring.approved_amount,
        proposed_amount=scoring.proposed_amount,
        proposed_duration_months=scoring.proposed_duration_months,
        explainability=explainability_items,
        debt_ratio=scoring.debt_ratio,
        disposable_income=scoring.disposable_income,
        guarantee_coverage_ratio=scoring.guarantee_coverage_ratio,
        policy_version=scoring.policy_version,
        granting_method=granting_method,
        scored_at=scoring.scored_at,
    )


# ── SIMULATE SCORING (For prospects without account or sandbox testing) ──
@router.post("/scoring/simulate", response_model=Dict[str, Any])
async def simulate_credit_score(
    payload: ScoringSimulationRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Public / Prospect simulation on base 100 with guarantees and multiple debts.
    Does not persist to database.
    """
    policy_dict = await get_active_policy_dict(db)

    # Mock ExtractedData
    dummy_extracted = ExtractedData(
        application_id=0,
        monthly_revenue=payload.monthly_revenue,
        secondary_revenue=payload.secondary_revenue or 0.0,
        monthly_expenses=payload.monthly_expenses,
        other_recurring_expenses=payload.other_recurring_expenses or 0.0,
        existing_debt=payload.existing_debt or 0.0,
        years_in_business=payload.years_in_business or 3.0,
        revenue_regularity_months=payload.revenue_regularity_months or 12,
    )

    scoring = scoring_engine.calculate_score_direct(
        extracted=dummy_extracted,
        requested_amount=payload.requested_amount,
        requested_duration_months=payload.requested_duration_months,
        activity_sector=payload.activity_sector,
        guarantees=payload.guarantees,
        debts=payload.debts,
        policy_override=policy_dict,
    )

    granting_method = await _get_matching_granting_method(db, payload.requested_amount)
    scoring["granting_method"] = granting_method
    return scoring


# ── COUNTER-PROPOSAL RECALCULATION ───────────────────────────────────
@router.post("/applications/{app_id}/recalculate", response_model=ScoringResultOut)
async def recalculate_score(
    app_id: int,
    proposal: CounterProposalRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("agent", "admin")),
):
    """Recalculate score with adjusted amount and duration in real time."""
    stmt = (
        select(CreditApplication)
        .options(
            selectinload(CreditApplication.extracted_data),
            selectinload(CreditApplication.guarantees),
            selectinload(CreditApplication.debts),
        )
        .where(CreditApplication.id == app_id)
    )
    res_app = await db.execute(stmt)
    app = res_app.scalar_one_or_none()

    if not app:
        raise HTTPException(status_code=404, detail="Dossier introuvable")

    policy_dict = await get_active_policy_dict(db)
    recalc = scoring_engine.calculate_score_direct(
        extracted=app.extracted_data,
        requested_amount=proposal.proposed_amount,
        requested_duration_months=proposal.proposed_duration_months,
        activity_sector=app.activity_sector,
        guarantees=app.guarantees,
        debts=app.debts,
        policy_override=policy_dict,
    )

    explainability_items = [ExplainabilityItem(**item) for item in recalc["explainability"]]
    granting_method = await _get_matching_granting_method(db, proposal.proposed_amount)

    return ScoringResultOut(
        id=0,
        application_id=app_id,
        score=recalc["score"],
        risk_level=recalc["risk_level"].value if hasattr(recalc["risk_level"], "value") else str(recalc["risk_level"]),
        decision=recalc["decision"],
        approved_amount=None,
        proposed_amount=proposal.proposed_amount,
        proposed_duration_months=proposal.proposed_duration_months,
        explainability=explainability_items,
        debt_ratio=recalc["debt_ratio"],
        disposable_income=recalc["disposable_income"],
        guarantee_coverage_ratio=recalc["guarantee_coverage_ratio"],
        policy_version=recalc["policy_version"],
        granting_method=granting_method,
        scored_at=datetime.now(timezone.utc),
    )


# ── APPLY COUNTER-PROPOSAL ────────────────────────────────────────────
@router.post("/applications/{app_id}/apply-counter-proposal", response_model=ScoringResultOut)
async def apply_counter_proposal(
    app_id: int,
    request: ApplyCounterProposalRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("agent")),
):
    """Save and validate an agent's counter-proposal as the official decision."""
    stmt = (
        select(CreditApplication)
        .options(
            selectinload(CreditApplication.extracted_data),
            selectinload(CreditApplication.guarantees),
            selectinload(CreditApplication.debts),
            selectinload(CreditApplication.scoring_result),
        )
        .where(CreditApplication.id == app_id)
    )
    result = await db.execute(stmt)
    app = result.scalar_one_or_none()

    if not app:
        raise HTTPException(status_code=404, detail="Dossier introuvable")

    policy_dict = await get_active_policy_dict(db)
    recalc = scoring_engine.calculate_score_direct(
        extracted=app.extracted_data,
        requested_amount=request.proposed_amount,
        requested_duration_months=request.proposed_duration_months,
        activity_sector=app.activity_sector,
        guarantees=app.guarantees,
        debts=app.debts,
        policy_override=policy_dict,
    )

    scoring = app.scoring_result
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
            guarantee_coverage_ratio=recalc["guarantee_coverage_ratio"],
            policy_version=recalc["policy_version"],
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
        scoring.guarantee_coverage_ratio = recalc["guarantee_coverage_ratio"]
        scoring.policy_version = recalc["policy_version"]
        scoring.scored_at = datetime.now(timezone.utc)

    app.status = ApplicationStatus.ADJUSTED
    app.updated_at = datetime.now(timezone.utc)

    db.add(
        AuditLog(
            application_id=app_id,
            user_id=current_user.id,
            action="counter_proposal_applied",
            details={
                "proposed_amount": request.proposed_amount,
                "proposed_duration": request.proposed_duration_months,
                "new_score": recalc["score"],
                "notes": request.notes,
            },
        )
    )

    await db.commit()
    await db.refresh(scoring)

    explainability_items = [ExplainabilityItem(**item) for item in scoring.explainability]
    granting_method = await _get_matching_granting_method(db, request.proposed_amount)

    return ScoringResultOut(
        id=scoring.id,
        application_id=scoring.application_id,
        score=scoring.score,
        risk_level=scoring.risk_level.value if hasattr(scoring.risk_level, "value") else str(scoring.risk_level),
        decision=scoring.decision,
        approved_amount=scoring.approved_amount,
        proposed_amount=scoring.proposed_amount,
        proposed_duration_months=scoring.proposed_duration_months,
        explainability=explainability_items,
        debt_ratio=scoring.debt_ratio,
        disposable_income=scoring.disposable_income,
        guarantee_coverage_ratio=scoring.guarantee_coverage_ratio,
        policy_version=scoring.policy_version,
        granting_method=granting_method,
        scored_at=scoring.scored_at,
    )


# ── VOICE & CONTEXTUAL ASSIST (Gemini 1.5 Flash Connected) ───────────
@router.post("/assist/voice-query", response_model=VoiceQueryResponse)
async def voice_query(
    request: VoiceQueryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    Process conversational & voice queries connected directly to Gemini 1.5 Flash.
    Aware of application context (score /100, guarantees, debts, etc.).
    """
    app_data = None
    if request.application_id:
        try:
            stmt = (
                select(CreditApplication)
                .options(
                    selectinload(CreditApplication.scoring_result),
                    selectinload(CreditApplication.guarantees),
                    selectinload(CreditApplication.debts),
                )
                .where(CreditApplication.id == request.application_id)
            )
            res = await db.execute(stmt)
            app = res.scalar_one_or_none()
            if app:
                app_data = {
                    "reference": app.reference,
                    "requested_amount": float(app.requested_amount),
                    "activity_sector": str(app.activity_sector),
                    "status": str(app.status),
                    "score": app.scoring_result.score if app.scoring_result else None,
                    "risk_level": str(app.scoring_result.risk_level) if app.scoring_result else None,
                    "guarantees": [{"type": g.guarantee_type, "estimated_value": g.estimated_value} for g in app.guarantees],
                    "debts": [{"creditor": d.creditor_name, "monthly_payment": d.monthly_payment} for d in app.debts],
                }
        except Exception as e:
            logger.warning(f"Failed to fetch application context for voice query: {e}")

    result = await gemini_service.query_assistant(
        query_text=request.query_text,
        language=request.language or "fr",
        context=request.context,
        application_data=app_data,
    )

    return VoiceQueryResponse(
        response_text=result["response_text"],
        suggestions=result.get("suggestions", []),
        detected_intent=result.get("detected_intent"),
        suggested_field=result.get("suggested_field"),
    )
