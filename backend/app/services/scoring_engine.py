"""
OpenScore Finance — Scoring Engine
Weighted scoring model (0-1000) with explainability and counter-proposal.
Designed for West African microfinance context.
"""

import math
from typing import Optional
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.database import (
    ExtractedData, CreditApplication, ScoringResult,
    ApplicationStatus, RiskLevel, AuditLog
)


# ── Scoring weights & thresholds ─────────────────────────────────────
SCORING_CONFIG = {
    "weights": {
        "debt_ratio": 0.30,           # Ratio d'endettement
        "revenue_stability": 0.20,    # Régularité des revenus
        "business_maturity": 0.15,    # Ancienneté de l'activité
        "disposable_income": 0.20,    # Reste à vivre
        "amount_to_income": 0.15,     # Montant demandé / revenus
    },
    "thresholds": {
        "approval_score": 600,
        "adjustment_score": 400,
        "max_debt_ratio": 0.40,       # 40% max des revenus
        "min_disposable_income": 75000,  # FCFA — minimum vital
    },
}


def _score_debt_ratio(debt_ratio: float) -> tuple[float, str]:
    """Score debt ratio: lower is better. Returns (0-1 score, detail)."""
    if debt_ratio <= 0.15:
        return 1.0, f"Excellent — ratio {debt_ratio:.0%} bien en dessous du seuil de 40%"
    elif debt_ratio <= 0.25:
        return 0.8, f"Bon — ratio {debt_ratio:.0%} maîtrisé"
    elif debt_ratio <= 0.35:
        return 0.5, f"Acceptable — ratio {debt_ratio:.0%} approche le seuil"
    elif debt_ratio <= 0.45:
        return 0.25, f"Risqué — ratio {debt_ratio:.0%} dépasse le seuil recommandé de 40%"
    else:
        return 0.05, f"Critique — ratio {debt_ratio:.0%} très élevé"


def _score_revenue_stability(months: int) -> tuple[float, str]:
    """Score revenue regularity (months with income / 12). Higher is better."""
    ratio = months / 12.0
    if ratio >= 0.9:
        return 1.0, f"Revenus très réguliers — {months}/12 mois"
    elif ratio >= 0.75:
        return 0.75, f"Revenus réguliers — {months}/12 mois"
    elif ratio >= 0.5:
        return 0.4, f"Revenus irréguliers — {months}/12 mois seulement"
    else:
        return 0.1, f"Revenus très irréguliers — {months}/12 mois seulement"


def _score_business_maturity(years: float) -> tuple[float, str]:
    """Score business age. Older is better for microfinance."""
    if years >= 5:
        return 1.0, f"Activité bien établie — {years:.1f} ans"
    elif years >= 3:
        return 0.75, f"Activité établie — {years:.1f} ans"
    elif years >= 1:
        return 0.45, f"Activité récente — {years:.1f} ans"
    elif years >= 0.5:
        return 0.2, f"Activité très jeune — {years:.1f} ans"
    else:
        return 0.05, f"Activité naissante — {years:.1f} ans"


def _score_disposable_income(disposable: float) -> tuple[float, str]:
    """Score remaining income after expenses and debt service."""
    min_vital = SCORING_CONFIG["thresholds"]["min_disposable_income"]
    formatted = f"{disposable:,.0f}".replace(",", " ")
    if disposable >= min_vital * 3:
        return 1.0, f"Reste à vivre confortable — {formatted} FCFA/mois"
    elif disposable >= min_vital * 2:
        return 0.75, f"Reste à vivre suffisant — {formatted} FCFA/mois"
    elif disposable >= min_vital:
        return 0.4, f"Reste à vivre juste — {formatted} FCFA/mois"
    elif disposable > 0:
        return 0.15, f"Reste à vivre insuffisant — {formatted} FCFA/mois"
    else:
        return 0.0, f"Reste à vivre négatif — {formatted} FCFA/mois"


def _score_amount_ratio(requested: float, monthly_revenue: float) -> tuple[float, str]:
    """Score ratio of requested amount to monthly revenue."""
    if monthly_revenue <= 0:
        return 0.0, "Revenus nuls — impossible d'évaluer"
    ratio = requested / monthly_revenue
    if ratio <= 3:
        return 1.0, f"Montant prudent — {ratio:.1f}x le revenu mensuel"
    elif ratio <= 6:
        return 0.7, f"Montant raisonnable — {ratio:.1f}x le revenu mensuel"
    elif ratio <= 12:
        return 0.35, f"Montant élevé — {ratio:.1f}x le revenu mensuel"
    else:
        return 0.1, f"Montant très élevé — {ratio:.1f}x le revenu mensuel"


def calculate_score(extracted: ExtractedData, application: CreditApplication) -> dict:
    """
    Calculate weighted score (0-1000) with full explainability.
    Returns dict with score, risk_level, decision, explainability, counter-proposal.
    """
    weights = SCORING_CONFIG["weights"]
    monthly_revenue = extracted.monthly_revenue or 0
    monthly_expenses = extracted.monthly_expenses or 0
    existing_debt = extracted.existing_debt or 0
    requested_amount = application.requested_amount
    duration_months = application.requested_duration_months or 12
    years_in_business = extracted.years_in_business or 0
    regularity_months = extracted.revenue_regularity_months or 6

    # Monthly debt service for the new loan (simplified: equal installments, no interest for MVP)
    monthly_payment = requested_amount / duration_months

    # Key financial ratios
    total_debt_service = existing_debt + monthly_payment
    debt_ratio = total_debt_service / monthly_revenue if monthly_revenue > 0 else 1.0
    disposable_income = monthly_revenue - monthly_expenses - total_debt_service

    # Score each variable
    s_debt, d_debt = _score_debt_ratio(debt_ratio)
    s_stability, d_stability = _score_revenue_stability(regularity_months)
    s_maturity, d_maturity = _score_business_maturity(years_in_business)
    s_disposable, d_disposable = _score_disposable_income(disposable_income)
    s_amount, d_amount = _score_amount_ratio(requested_amount, monthly_revenue)

    # Weighted total (0-1)
    weighted_score = (
        s_debt * weights["debt_ratio"]
        + s_stability * weights["revenue_stability"]
        + s_maturity * weights["business_maturity"]
        + s_disposable * weights["disposable_income"]
        + s_amount * weights["amount_to_income"]
    )

    # Scale to 0-1000
    score = round(weighted_score * 1000)
    score = max(0, min(1000, score))

    # Risk level
    if score >= 750:
        risk_level = RiskLevel.LOW
    elif score >= 600:
        risk_level = RiskLevel.MEDIUM
    elif score >= 400:
        risk_level = RiskLevel.HIGH
    else:
        risk_level = RiskLevel.VERY_HIGH

    # Decision
    thresholds = SCORING_CONFIG["thresholds"]
    if score >= thresholds["approval_score"]:
        decision = "approved"
        approved_amount = requested_amount
        proposed_amount = None
        proposed_duration = None
    elif score >= thresholds["adjustment_score"]:
        decision = "adjusted"
        approved_amount = None
        # Counter-proposal: reduce amount to bring debt ratio below threshold
        max_monthly = monthly_revenue * thresholds["max_debt_ratio"] - existing_debt
        if max_monthly > 0:
            proposed_amount = round(max_monthly * duration_months / 1000) * 1000  # round to nearest 1000
            proposed_amount = max(50000, proposed_amount)  # minimum 50,000 FCFA
        else:
            proposed_amount = 50000
        # Also propose longer duration if helpful
        proposed_duration = min(duration_months + 6, 60)
        approved_amount = None
    else:
        decision = "rejected"
        approved_amount = None
        proposed_amount = None
        proposed_duration = None

    # Explainability
    explainability = [
        {
            "variable": "debt_ratio",
            "label": "Ratio d'endettement",
            "value": f"{debt_ratio:.1%}",
            "impact": "positive" if s_debt >= 0.5 else "negative",
            "weight": weights["debt_ratio"],
            "contribution": round(s_debt * weights["debt_ratio"] * 1000),
            "detail": d_debt,
        },
        {
            "variable": "revenue_stability",
            "label": "Régularité des revenus",
            "value": f"{regularity_months}/12 mois",
            "impact": "positive" if s_stability >= 0.5 else "negative",
            "weight": weights["revenue_stability"],
            "contribution": round(s_stability * weights["revenue_stability"] * 1000),
            "detail": d_stability,
        },
        {
            "variable": "business_maturity",
            "label": "Ancienneté de l'activité",
            "value": f"{years_in_business:.1f} ans",
            "impact": "positive" if s_maturity >= 0.5 else "negative",
            "weight": weights["business_maturity"],
            "contribution": round(s_maturity * weights["business_maturity"] * 1000),
            "detail": d_maturity,
        },
        {
            "variable": "disposable_income",
            "label": "Reste à vivre",
            "value": f"{disposable_income:,.0f} FCFA".replace(",", " "),
            "impact": "positive" if s_disposable >= 0.5 else "negative",
            "weight": weights["disposable_income"],
            "contribution": round(s_disposable * weights["disposable_income"] * 1000),
            "detail": d_disposable,
        },
        {
            "variable": "amount_to_income",
            "label": "Montant / Revenus",
            "value": f"{requested_amount / monthly_revenue:.1f}x" if monthly_revenue > 0 else "N/A",
            "impact": "positive" if s_amount >= 0.5 else "negative",
            "weight": weights["amount_to_income"],
            "contribution": round(s_amount * weights["amount_to_income"] * 1000),
            "detail": d_amount,
        },
    ]

    return {
        "score": score,
        "risk_level": risk_level,
        "decision": decision,
        "approved_amount": approved_amount,
        "proposed_amount": proposed_amount,
        "proposed_duration_months": proposed_duration,
        "explainability": explainability,
        "debt_ratio": round(debt_ratio, 4),
        "disposable_income": round(disposable_income, 2),
    }


def recalculate_counter_proposal(
    extracted: ExtractedData,
    new_amount: float,
    new_duration: int,
) -> dict:
    """
    Recalculate score with a new proposed amount and duration.
    Used for dynamic counter-proposal adjustments.
    """
    # Create a temporary application-like object
    class TempApp:
        requested_amount = new_amount
        requested_duration_months = new_duration

    return calculate_score(extracted, TempApp())


async def run_scoring(db: AsyncSession, application_id: int) -> Optional[ScoringResult]:
    """
    Full scoring pipeline: load data, calculate, persist, update status.
    """
    try:
        # Load application
        stmt = select(CreditApplication).where(CreditApplication.id == application_id)
        result = await db.execute(stmt)
        application = result.scalar_one_or_none()
        if not application:
            return None

        # Load extracted data
        stmt = select(ExtractedData).where(ExtractedData.application_id == application_id)
        result = await db.execute(stmt)
        extracted = result.scalar_one_or_none()
        if not extracted:
            return None

        # Calculate score
        scoring = calculate_score(extracted, application)

        # Check if scoring result already exists
        stmt = select(ScoringResult).where(ScoringResult.application_id == application_id)
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            existing.score = scoring["score"]
            existing.risk_level = scoring["risk_level"]
            existing.decision = scoring["decision"]
            existing.approved_amount = scoring["approved_amount"]
            existing.proposed_amount = scoring["proposed_amount"]
            existing.proposed_duration_months = scoring["proposed_duration_months"]
            existing.explainability = scoring["explainability"]
            existing.debt_ratio = scoring["debt_ratio"]
            existing.disposable_income = scoring["disposable_income"]
            existing.scored_at = datetime.now(timezone.utc)
            scoring_result = existing
        else:
            scoring_result = ScoringResult(
                application_id=application_id,
                score=scoring["score"],
                risk_level=scoring["risk_level"],
                decision=scoring["decision"],
                approved_amount=scoring["approved_amount"],
                proposed_amount=scoring["proposed_amount"],
                proposed_duration_months=scoring["proposed_duration_months"],
                explainability=scoring["explainability"],
                debt_ratio=scoring["debt_ratio"],
                disposable_income=scoring["disposable_income"],
                scored_at=datetime.now(timezone.utc),
            )
            db.add(scoring_result)

        # Update application status
        status_map = {
            "approved": ApplicationStatus.APPROVED,
            "adjusted": ApplicationStatus.ADJUSTED,
            "rejected": ApplicationStatus.REJECTED,
        }
        application.status = status_map.get(scoring["decision"], ApplicationStatus.SCORED)
        application.updated_at = datetime.now(timezone.utc)

        # Audit log
        audit = AuditLog(
            application_id=application_id,
            action="scoring_completed",
            details={
                "score": scoring["score"],
                "decision": scoring["decision"],
                "risk_level": scoring["risk_level"].value if hasattr(scoring["risk_level"], "value") else scoring["risk_level"],
            },
        )
        db.add(audit)

        await db.commit()
        await db.refresh(scoring_result)
        return scoring_result

    except Exception as e:
        await db.rollback()
        raise
