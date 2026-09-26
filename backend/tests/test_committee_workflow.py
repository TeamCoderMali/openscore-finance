import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.models.database import async_session, CreditApplication, ApplicationStatus, User, ScoringResult
from app.api.v1.admin import process_committee_decision, request_committee_document
from app.api.v1.applications import upload_requested_document
from app.models.schemas import CommitteeDecisionRequest, CommitteeDocumentRequest
from sqlalchemy import select
from fastapi import UploadFile
import io

async def test_flow():
    async with async_session() as db:
        # Find application 22 or latest
        stmt = select(CreditApplication).where(CreditApplication.id == 22)
        res = await db.execute(stmt)
        app = res.scalar_one_or_none()
        if not app:
            stmt = select(CreditApplication).order_by(CreditApplication.id.desc()).limit(1)
            res = await db.execute(stmt)
            app = res.scalar_one()

        print(f"Testing on Application #{app.id} ({app.reference})")
        print(f"Initial: Status={app.status}, Amount={app.approved_amount or app.requested_amount}, Duration={app.requested_duration_months}")

        # Reset document requests for testing
        app.form_data = dict(app.form_data or {})
        app.form_data["document_requests"] = []
        app.form_data["has_pending_document_request"] = False
        await db.commit()

        # 1. Admin / Committee updates decision to 2,000,000 FCFA and 24 months
        fake_admin = User(id=1, role="admin", full_name="Super Administrateur")
        decision_req = CommitteeDecisionRequest(
            decision="approved",
            approved_amount=2000000.0,
            approved_duration_months=24,
            notes="Accordé avec quotité réajustée à 2 000 000 FCFA sur 24 mois par le Comité."
        )
        dec_res = await process_committee_decision(app.id, decision_req, db, fake_admin)
        print("Decision processed:", dec_res)

        # Re-fetch app
        res = await db.execute(select(CreditApplication).where(CreditApplication.id == app.id))
        app = res.scalar_one()
        assert app.status == ApplicationStatus.APPROVED
        assert float(app.approved_amount) == 2000000.0
        assert app.requested_duration_months == 24
        print(f"Verified Application #{app.id} updated in DB: approved_amount={app.approved_amount}, duration={app.requested_duration_months}")

        # 2. Committee requests a complementary document
        doc_req = CommitteeDocumentRequest(
            document_name="Attestation d'irrévocabilité de virement de salaire",
            description="Le comité requiert l'attestation signée par la DRH de l'employeur."
        )
        doc_res = await request_committee_document(app.id, doc_req, db, fake_admin)
        print("Document request added:", doc_res["document_request"])
        assert doc_res["form_data"]["has_pending_document_request"] is True

        # 3. Agent uploads the requested document
        fake_agent = User(id=app.agent_id or 1, role="agent", full_name="Agent Instructeur")
        dummy_file = UploadFile(
            filename="attestation_salaire_drh.pdf",
            file=io.BytesIO(b"%PDF-1.4 test document content for committee"),
            headers={"content-type": "application/pdf"}
        )
        req_id = doc_res["document_request"]["id"]
        up_res = await upload_requested_document(
            app_id=app.id,
            file=dummy_file,
            request_id=req_id,
            notes="Attestation obtenue auprès de la DRH ce matin.",
            db=db,
            current_user=fake_agent
        )
        print("Agent uploaded document response:", up_res["message"])
        assert up_res["form_data"]["has_pending_document_request"] is False
        print("All committee + agent document request flows passed successfully!")

if __name__ == "__main__":
    asyncio.run(test_flow())
