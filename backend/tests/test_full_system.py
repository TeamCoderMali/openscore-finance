"""
OpenScore Finance — End-to-End System Test Suite
Tests all Phase 2 features:
1. Registration & Login JWT
2. Document Extraction & OCR (Gemini 1.5 Flash structured pipeline)
3. Agent Certification & Verification
4. Machine Learning Scoring & SHAP Explainability Engine
5. Counter-Proposal Optimization & Persistence
6. Tamper-Evident Receipt Generation
7. Chronological Audit Logs
8. Bilingual Voice Query NLP (French / Bambara)
"""

import asyncio
import os
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = str(Path(__file__).resolve().parent.parent)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import httpx
from app.main import app
from app.models.database import engine, Base, async_session, User, CreditApplication, ExtractedData, ScoringResult, AuditLog
from app.services.scoring_engine import CreditScoringEngine, scoring_engine


async def run_e2e_tests():
    print("\n" + "="*70)
    print("🚀 OPENSCORE FINANCE — TEST DE VALIDATION DU SYSTÈME COMPLET (PHASE 2)")
    print("="*70 + "\n")

    # 1. Test ML Scoring Engine directly
    print("👉 [1/6] Test du Moteur de Scoring ML & Explicabilité SHAP...")
    dummy_extracted = ExtractedData(
        application_id=999,
        full_name="Moussa Keïta",
        monthly_revenue=400000.0,
        monthly_expenses=220000.0,
        existing_debt=40000.0,
        years_in_business=4.5,
        revenue_regularity_months=11,
    )
    score_res = scoring_engine.calculate_score_direct(
        extracted=dummy_extracted,
        requested_amount=1000000.0,
        requested_duration_months=12,
        activity_sector="Commerce"
    )
    print(f"  ✓ Score calculé : {score_res['score']}/1000")
    print(f"  ✓ Décision : {score_res['decision'].upper()} (Risque: {score_res['risk_level']})")
    print(f"  ✓ Ratio d'endettement : {score_res['debt_ratio']:.1%}")
    print(f"  ✓ Reste à vivre : {score_res['disposable_income']:,.0f} FCFA")
    print(f"  ✓ Attributions SHAP générées : {len(score_res['explainability'])} variables décomposées")
    for item in score_res["explainability"]:
        print(f"    - {item['label']} ({item['value']}): {item['contribution']:+} pts [{item['impact']}] -> {item['detail']}")

    # Test Counter-Proposal on high amount
    print("\n👉 [2/6] Test de l'Optimiseur de Contre-Proposition...")
    risky_extracted = ExtractedData(
        application_id=998,
        full_name="Ousmane Coulibaly",
        monthly_revenue=200000.0,
        monthly_expenses=140000.0,
        existing_debt=30000.0,
        years_in_business=1.5,
        revenue_regularity_months=7,
    )
    adjusted_res = scoring_engine.calculate_score_direct(
        extracted=risky_extracted,
        requested_amount=1500000.0, # Too high for 200k income
        requested_duration_months=12,
        activity_sector="Commerce"
    )
    print(f"  ✓ Score initial pour montant excessif (1 500 000 FCFA) : {adjusted_res['score']}/1000")
    print(f"  ✓ Décision algorithmique : {adjusted_res['decision'].upper()}")
    if adjusted_res['proposed_amount']:
        print(f"  ✓ Contre-proposition automatique calculée : {adjusted_res['proposed_amount']:,.0f} FCFA sur {adjusted_res['proposed_duration_months']} mois")
    assert adjusted_res['decision'] in ["adjusted", "rejected"]

    # 3. Test HTTP Endpoints via Async Client
    print("\n👉 [3/6] Test des Endpoints FastAPI via HTTP Async...")
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Health check
        r = await client.get("/api/health")
        assert r.status_code == 200
        print(f"  ✓ Health check OK : {r.json()}")

        # Register a new user
        reg_payload = {
            "email": f"test.user.{os.getpid()}@mail.ml",
            "password": "password123",
            "full_name": "Test Emprunteur Mali",
            "phone": "+223 70 00 11 22",
            "role": "client"
        }
        r_reg = await client.post("/api/v1/auth/register", json=reg_payload)
        assert r_reg.status_code == 201
        client_token = r_reg.json()["access_token"]
        print(f"  ✓ Inscription client OK : {r_reg.json()['full_name']} (ID: {r_reg.json()['user_id']})")

        # Login agent
        r_agent = await client.post("/api/v1/auth/login", json={"email": "agent@openscore.ml", "password": "agent123"})
        assert r_agent.status_code == 200
        agent_token = r_agent.json()["access_token"]
        print(f"  ✓ Connexion Agent OK : {r_agent.json()['full_name']}")

        # Create credit application
        r_app = await client.post(
            "/api/v1/applications",
            headers={"Authorization": f"Bearer {client_token}"},
            json={
                "activity_sector": "Commerce",
                "requested_amount": 600000,
                "requested_duration_months": 12,
                "business_description": "Vente de quincaillerie et outillage",
            }
        )
        assert r_app.status_code == 201
        app_data = r_app.json()
        app_id = app_data["id"]
        print(f"  ✓ Création de dossier OK : Référence {app_data['reference']} (ID: {app_id})")

        # Document extraction (simulated/Gemini)
        print("\n👉 [4/6] Test de l'Extraction OCR Gemini 1.5 Flash...")
        dummy_file = b"SIMULATED_NINA_CARD_IMAGE_BINARY_BYTES"
        files = {"file": ("nina_card.jpg", dummy_file, "image/jpeg")}
        r_ocr = await client.post(
            f"/api/v1/applications/{app_id}/extract-docs",
            headers={"Authorization": f"Bearer {client_token}"},
            files=files
        )
        assert r_ocr.status_code == 200
        extracted_res = r_ocr.json()
        print(f"  ✓ Extraction OCR réussie : {extracted_res['full_name']} | Confiance: {extracted_res['extraction_confidence']}")

        # Agent certification
        print("\n👉 [5/6] Test de la Certification Agent & Audit...")
        r_cert = await client.put(
            f"/api/v1/applications/{app_id}/verify-data",
            headers={"Authorization": f"Bearer {agent_token}"},
            json={
                "full_name": "Test Emprunteur Mali",
                "monthly_revenue": 380000,
                "monthly_expenses": 200000,
                "existing_debt": 20000,
                "years_in_business": 4.0,
                "revenue_regularity_months": 11,
                "verification_notes": "Conforme après visite physique du point de vente."
            }
        )
        assert r_cert.status_code == 200
        print(f"  ✓ Certification effectuée par l'agent : is_verified={r_cert.json()['is_verified']}")

        # Run scoring
        r_eval = await client.post(
            f"/api/v1/applications/{app_id}/evaluate",
            headers={"Authorization": f"Bearer {agent_token}"}
        )
        assert r_eval.status_code == 200
        eval_data = r_eval.json()
        print(f"  ✓ Scoring ML terminé : Score {eval_data['score']}/1000 | Décision: {eval_data['decision'].upper()}")

        # Test official receipt
        r_rec = await client.get(
            f"/api/v1/applications/{app_id}/receipt",
            headers={"Authorization": f"Bearer {client_token}"}
        )
        assert r_rec.status_code == 200
        print(f"  ✓ Récépissé officiel généré : {r_rec.json()['receipt_id']}")

        # Test audit logs
        r_audit = await client.get(
            f"/api/v1/applications/{app_id}/audit-logs",
            headers={"Authorization": f"Bearer {client_token}"}
        )
        assert r_audit.status_code == 200
        print(f"  ✓ Traçabilité Audit Logs : {r_audit.json()['total']} actions enregistrées")
        for l in r_audit.json()["logs"]:
            print(f"    - [{l['timestamp'][:19]}] {l['action']} (User: {l.get('user_name') or 'Système'})")

        # 6. Test Voice Query (Bilingual French / Bambara)
        print("\n👉 [6/6] Test du Module Vocal Bilingue (Français / Bambara)...")
        queries = [
            ("N b'a fɛ ka wari ta n ka sugu kama", "bm"),
            ("Quels sont les justificatifs obligatoires pour mon dossier ?", "fr"),
            ("Quel montant pour mon activité maraîchère à Baguinéda (Sɛnɛ) ?", "fr"),
        ]
        for q, lang in queries:
            r_v = await client.post(
                "/api/v1/assist/voice-query",
                headers={"Authorization": f"Bearer {client_token}"},
                json={"query_text": q, "language": lang}
            )
            assert r_v.status_code == 200
            v_res = r_v.json()
            print(f"  ✓ Question [{lang}] : '{q}'")
            print(f"    -> Réponse : {v_res['response_text'][:90]}...")
            if v_res.get('detected_intent'):
                print(f"    -> Intention détectée : {v_res['detected_intent']}")

    print("\n" + "="*70)
    print("✅ TOUS LES TESTS FONCTIONNELS ET TECHNIQUES DU SYSTÈME ONT RÉUSSI !")
    print("="*70 + "\n")


if __name__ == "__main__":
    asyncio.run(run_e2e_tests())
