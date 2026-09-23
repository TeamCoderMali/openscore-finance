"""
OpenScore Finance — Kafo Jiginew Account Management API
Mobile membership requests, branch selection, and account validation.
"""

from __future__ import annotations

import random
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.models.database import (
    User, AccountCreationRequest, MicrofinanceAccount, CreditApplication, ApplicationStatus, get_db, UserRole
)
from app.models.schemas import (
    KafoJiginewRequestCreate, KafoJiginewRequestOut
)
from app.api.v1.auth import get_current_user_optional, require_role

BRANCH_NAMES = {
    "701": "Antenne 701 - Bamako District (Hamdallaye ACI)",
    "702": "Antenne 702 - Caisse Médina-Coura",
    "801": "Antenne 801 - Sikasso (Wayerma)",
    "802": "Antenne 802 - Caisse Rurale Koutiala",
    "901": "Antenne 901 - Ségou (Pelengana)",
    "902": "Antenne 902 - Antenne Mopti (Sévaré)",
    "903": "Antenne 903 - Antenne Kayes (Légal Ségou)",
}

STATUS_LABELS_FR = {
    "draft": "Brouillon",
    "documents_uploaded": "Pièces transmises",
    "data_extracted": "Données extraites",
    "pending_verification": "À certifier par l'agent",
    "data_verified": "Données certifiées",
    "scored": "Scoring ML calculé",
    "pending_committee_approval": "En attente comité de crédit",
    "approved": "Approuvé / En cours de décaissement",
    "adjusted": "Montant ajusté par le comité",
    "rejected": "Rejeté",
}

ACTIVE_APPLICATION_STATUSES = [
    ApplicationStatus.DRAFT,
    ApplicationStatus.DOCUMENTS_UPLOADED,
    ApplicationStatus.DATA_EXTRACTED,
    ApplicationStatus.PENDING_VERIFICATION,
    ApplicationStatus.DATA_VERIFIED,
    ApplicationStatus.SCORED,
    ApplicationStatus.PENDING_COMMITTEE_APPROVAL,
    ApplicationStatus.APPROVED,
    ApplicationStatus.ADJUSTED,
]

router = APIRouter(prefix="/accounts", tags=["Kafo Jiginew Accounts"])


@router.post("/kafo-jiginew-request", response_model=KafoJiginewRequestOut, status_code=status.HTTP_201_CREATED)
async def request_kafo_jiginew_account(
    payload: KafoJiginewRequestCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    Client or prospective member submits a Kafo Jiginew account creation / membership request from mobile.
    """
    req = AccountCreationRequest(
        full_name=payload.full_name,
        phone=payload.phone,
        email=payload.email,
        id_type=payload.id_type or "NINA",
        id_number=payload.id_number,
        birth_date=payload.birth_date,
        city=payload.city,
        address=payload.address,
        profession=payload.profession,
        branch_code=payload.branch_code or "701",
        account_type=payload.account_type or "INDIVIDUAL",
        status="PENDING",
    )
    db.add(req)
    await db.commit()
    await db.refresh(req)
    return req


@router.get("/kafo-jiginew-requests", response_model=List[KafoJiginewRequestOut])
async def list_kafo_jiginew_requests(
    branch_code: Optional[str] = None,
    status_filter: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("agent", "admin")),
):
    """
    List account requests. Agents only see requests for their regional branch.
    """
    stmt = select(AccountCreationRequest).order_by(desc(AccountCreationRequest.created_at))

    if current_user.role == UserRole.AGENT:
        agent_branch = getattr(current_user, "branch_code", "701") or "701"
        stmt = stmt.where(AccountCreationRequest.branch_code == agent_branch)
    elif branch_code and branch_code != "all":
        stmt = stmt.where(AccountCreationRequest.branch_code == branch_code)

    if status_filter and status_filter != "all":
        stmt = stmt.where(AccountCreationRequest.status == status_filter.upper())

    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/kafo-jiginew-requests/{request_id}/approve", response_model=KafoJiginewRequestOut)
async def approve_kafo_jiginew_request(
    request_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("agent", "admin")),
):
    """
    Approve membership and generate official account number with branch prefix (e.g. CMF-701-XXXXXX).
    """
    stmt = select(AccountCreationRequest).where(AccountCreationRequest.id == request_id)
    res = await db.execute(stmt)
    req = res.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Demande introuvable")

    if req.status == "APPROVED":
        return req

    # Generate account number based on regional branch code
    prefix = req.branch_code or "701"
    suffix = str(random.randint(1000, 999999)).zfill(6)
    account_number = f"CMF-{prefix}-{suffix}"

    req.status = "APPROVED"
    req.account_number_generated = account_number

    # Also register in microfinance_accounts
    mfi_acc = MicrofinanceAccount(
        account_number=account_number,
        full_name=req.full_name,
        phone=req.phone,
        email=req.email,
        id_number=req.id_number,
        id_type=req.id_type,
        activity_sector=req.profession,
        monthly_revenue=400000.0,
        monthly_expenses=200000.0,
        years_in_business=3.0,
        revenue_regularity_months=12,
        status="ACTIVE",
    )
    db.add(mfi_acc)

    await db.commit()
    await db.refresh(req)
    return req


@router.get("/lookup/{account_number}")
async def lookup_account(
    account_number: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("agent", "admin")),
):
    """
    Lookup client info by account number to auto-fill credit application modal.
    Returns account details, activity sector, financials, branch code, and cross-branch risk analysis.
    """
    clean_num = account_number.strip().upper()
    stmt = select(MicrofinanceAccount).where(MicrofinanceAccount.account_number == clean_num)
    res = await db.execute(stmt)
    acc = res.scalar_one_or_none()

    current_agent_branch = getattr(current_user, "branch_code", "701") or "701"

    if acc:
        branch = "701"
        parts = clean_num.split("-")
        if len(parts) >= 2 and parts[1] in ["701", "702", "801", "802", "901", "902", "903"]:
            branch = parts[1]

        pme_keywords = ["sarl", "sa", "gpe", "entreprise", "ets", "coopérative", "société", "import-export"]
        is_pme = any(k in (acc.full_name or "").lower() for k in pme_keywords)
        app_type = "PME" if is_pme else "INDIVIDUAL"

        # Check existing applications
        app_stmt = select(CreditApplication).where(
            or_(
                CreditApplication.account_number == clean_num,
                CreditApplication.applicant.has(account_number=clean_num),
                CreditApplication.applicant.has(phone=acc.phone) if acc.phone else False,
            )
        ).order_by(desc(CreditApplication.created_at))
        app_res = await db.execute(app_stmt)
        all_apps = app_res.scalars().all()

        current_branch_active = [
            a for a in all_apps
            if (a.branch_code or "701") == current_agent_branch and a.status in ACTIVE_APPLICATION_STATUSES
        ]
        other_branch_active = [
            a for a in all_apps
            if (a.branch_code or "701") != current_agent_branch and a.status in ACTIVE_APPLICATION_STATUSES
        ]

        has_active_other_branch = len(other_branch_active) > 0
        has_no_dossier_in_current_branch = len(current_branch_active) == 0

        other_branch_summary = [
            {
                "id": a.id,
                "reference": a.reference,
                "branch_code": a.branch_code or "701",
                "branch_name": BRANCH_NAMES.get(a.branch_code or "701", f"Antenne {a.branch_code}"),
                "status": a.status.value if hasattr(a.status, "value") else str(a.status),
                "status_label": STATUS_LABELS_FR.get(a.status.value if hasattr(a.status, "value") else str(a.status), str(a.status)),
                "requested_amount": float(a.requested_amount),
                "approved_amount": float(a.approved_amount) if a.approved_amount else None,
                "activity_sector": a.activity_sector.value if hasattr(a.activity_sector, "value") else str(a.activity_sector),
                "application_type": getattr(a, "application_type", "INDIVIDUAL"),
                "created_at": a.created_at.strftime("%d/%m/%Y") if a.created_at else "",
            }
            for a in other_branch_active
        ]

        current_branch_summary = [
            {
                "id": a.id,
                "reference": a.reference,
                "branch_code": a.branch_code or "701",
                "branch_name": BRANCH_NAMES.get(a.branch_code or "701", f"Antenne {a.branch_code}"),
                "status": a.status.value if hasattr(a.status, "value") else str(a.status),
                "status_label": STATUS_LABELS_FR.get(a.status.value if hasattr(a.status, "value") else str(a.status), str(a.status)),
                "requested_amount": float(a.requested_amount),
                "created_at": a.created_at.strftime("%d/%m/%Y") if a.created_at else "",
            }
            for a in current_branch_active
        ]

        warning_msg = None
        if has_active_other_branch and has_no_dossier_in_current_branch:
            first_b_name = other_branch_summary[0]["branch_name"]
            first_ref = other_branch_summary[0]["reference"]
            warning_msg = (
                f"ALERTE CENTRALE DES RISQUES : Le sociétaire n'a aucun dossier dans votre antenne ({BRANCH_NAMES.get(current_agent_branch, current_agent_branch)}), "
                f"mais possède déjà un dossier en cours ({first_ref}) dans l'antenne {first_b_name}. "
                "Conformément aux règles prudentielles BCEAO contre le surendettement croisé, il est recommandé de ne pas ouvrir de nouveau dossier."
            )
        elif has_active_other_branch:
            warning_msg = (
                "ALERTE RISQUE MULTI-ANTENNES : Le sociétaire possède des dossiers en cours dans plusieurs antennes. "
                "Consultez l'historique avant toute action."
            )

        return {
            "found": True,
            "account_number": acc.account_number,
            "full_name": acc.full_name,
            "phone": acc.phone,
            "email": acc.email,
            "id_number": acc.id_number,
            "id_type": acc.id_type,
            "activity_sector": acc.activity_sector,
            "monthly_revenue": acc.monthly_revenue,
            "monthly_expenses": acc.monthly_expenses,
            "years_in_business": acc.years_in_business,
            "branch_code": branch,
            "suggested_application_type": app_type,
            "has_active_other_branch": has_active_other_branch,
            "has_no_dossier_in_current_branch": has_no_dossier_in_current_branch,
            "current_agent_branch": current_agent_branch,
            "current_agent_branch_name": BRANCH_NAMES.get(current_agent_branch, f"Antenne {current_agent_branch}"),
            "other_branch_applications": other_branch_summary,
            "current_branch_applications": current_branch_summary,
            "warning_message": warning_msg,
        }

    # Fallback to AccountCreationRequest
    req_stmt = select(AccountCreationRequest).where(
        (AccountCreationRequest.account_number_generated == clean_num) |
        (AccountCreationRequest.phone == clean_num)
    )
    req_res = await db.execute(req_stmt)
    req = req_res.scalar_one_or_none()
    if req:
        return {
            "found": True,
            "account_number": req.account_number_generated or clean_num,
            "full_name": req.full_name,
            "phone": req.phone,
            "email": req.email,
            "id_number": req.id_number,
            "id_type": req.id_type,
            "activity_sector": req.profession or "Commerce",
            "monthly_revenue": 400000.0,
            "monthly_expenses": 200000.0,
            "years_in_business": 2.0,
            "branch_code": req.branch_code or "701",
            "suggested_application_type": req.account_type or "INDIVIDUAL",
            "has_active_other_branch": False,
            "has_no_dossier_in_current_branch": True,
            "current_agent_branch": current_agent_branch,
            "current_agent_branch_name": BRANCH_NAMES.get(current_agent_branch, f"Antenne {current_agent_branch}"),
            "other_branch_applications": [],
            "current_branch_applications": [],
            "warning_message": None,
        }

    raise HTTPException(status_code=404, detail="Aucun compte trouvé avec ce numéro.")

