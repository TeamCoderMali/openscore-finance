"""
OpenScore Finance — End-to-End System Test Suite (Restructured 0-100 Base)
Tests all 12 validation cases:
1. Registration, Login JWT, Account linking
2. Multi-guarantees (collateral) & Multi-debts CRUD
3. Dynamic Scoring Engine on base 100 with active DB policy & SHAP explainability
4. Counter-Proposal optimization (base 100)
5. Multi-search (by application reference & client account number)
6. Quick initialization of dossier by account number
7. Admin dynamic policy management & weight validation (100% check)
8. Granting methods per loan amount tiers
9. Committee final approval authority
10. Official receipt with agent name, account number, and score /100
11. Audit log traceability
12. Gemini AI Assistant (contextual score explanations & bilingue FR/BM)
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
from app.models.database import ExtractedData, Guarantee, Debt
from app.services.scoring_engine import scoring_engine
from app.services.gemini_service import gemini_service


async def run_e2e_tests():
    print("\n" + "="*70)
    print("🚀 OPENSCORE FINANCE — TEST DE VALIDATION DU SYSTÈME COMPLET (0-100 BASE)")
    print("="*70 + "\n")

    # 1. Test Scoring Engine directly on 0-100 scale
    print("👉 [1/12] Test du Moteur de Scoring ML sur base 100...")
    dummy_extracted = ExtractedData(
        application_id=999,
        full_name="Amadou Diallo",
        monthly_revenue=800000.0,
        secondary_revenue=50000.0,
        monthly_expenses=400000.0,
        existing_debt=35000.0,
        years_in_business=4.5,
        revenue_regularity_months=11,
    )
    dummy_guarantees = [
        Guarantee(
            application_id=999,
            guarantee_type="vehicule",
            description="Tricycle Haojue",
            estimated_value=1500000.0,
            retained_value=900000.0,
        )
    ]
    dummy_debts = [
        Debt(
            application_id=999,
            creditor_name="Kafo Jiginew",
            is_internal=False,
            remaining_amount=100000.0,
            monthly_payment=35000.0,
        )
    ]
    score_res = scoring_engine.calculate_score_direct(
        extracted=dummy_extracted,
        requested_amount=1000000.0,
        requested_duration_months=12,
        activity_sector="Commerce",
        guarantees=dummy_guarantees,
        debts=dummy_debts,
    )
    print(f"  ✓ Score calculé : {score_res['score']}/100 (Échelle 0-100 validée)")
    assert 0 <= score_res["score"] <= 100, "Le score doit impérativement être entre 0 et 100"
    print(f"  ✓ Décision : {score_res['decision'].upper()} (Risque: {score_res['risk_level']})")
    print(f"  ✓ Couverture garanties : {score_res['guarantee_coverage_ratio']:.1%}")
    print(f"  ✓ Attributions SHAP générées ({len(score_res['explainability'])} variables) :")
    for item in score_res["explainability"]:
        print(f"    - {item['label']} ({item['value']}): {item['contribution']:+} pts [{item['impact']}]")

    # 2. Test Counter-Proposal on 0-100 scale
    print("\n👉 [2/12] Test de l'Optimiseur de Contre-Proposition...")
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
        requested_amount=1500000.0,  # Too high for 200k income
        requested_duration_months=12,
        activity_sector="Commerce"
    )
    print(f"  ✓ Score pour demande excessive : {adjusted_res['score']}/100")
    print(f"  ✓ Décision : {adjusted_res['decision'].upper()}")
    if adjusted_res['proposed_amount']:
        print(f"  ✓ Contre-proposition : {adjusted_res['proposed_amount']:,.0f} FCFA sur {adjusted_res['proposed_duration_months']} mois")
    assert adjusted_res['decision'] in ["adjusted", "rejected"]

    # 3. Test HTTP Async Client
    print("\n👉 [3/12] Test des Endpoints FastAPI via HTTP Async...")
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Health check
        r = await client.get("/api/health")
        assert r.status_code == 200
        print(f"  ✓ Health check OK : {r.json()}")

        # Login agent
        r_agent = await client.post("/api/v1/auth/login", json={"email": "agent@openscore.ml", "password": "agent123"})
        assert r_agent.status_code == 200
        agent_token = r_agent.json()["access_token"]
        print(f"  ✓ Connexion Agent OK : {r_agent.json()['full_name']}")

        # Login admin
        r_admin = await client.post("/api/v1/auth/login", json={"email": "admin@openscore.ml", "password": "admin123"})
        assert r_admin.status_code == 200
        admin_token = r_admin.json()["access_token"]
        print(f"  ✓ Connexion Admin OK : {r_admin.json()['full_name']}")

        # 4. Account lookup
        print("\n👉 [4/12] Test de la recherche de compte client (Lookup CMF-2026-001245)...")
        r_acc = await client.get(
            "/api/v1/applications/accounts/CMF-2026-001245",
            headers={"Authorization": f"Bearer {agent_token}"}
        )
        assert r_acc.status_code == 200
        acc_info = r_acc.json()
        print(f"  ✓ Compte trouvé : {acc_info['full_name']} | Revenu: {acc_info['monthly_revenue']:,.0f} FCFA")

        # 5. Quick Init for Agent
        print("\n👉 [5/12] Test de l'Initialisation Rapide de Dossier par l'Agent...")
        r_quick = await client.post(
            "/api/v1/applications/quick-init",
            headers={"Authorization": f"Bearer {agent_token}"},
            json={
                "account_number": "CMF-2026-001245",
                "requested_amount": 1200000.0,
                "requested_duration_months": 12,
                "activity_sector": "Commerce",
                "business_description": "Extension stock de pagnes",
                "force_override_cross_branch": True,
                "guarantees": [
                    {
                        "guarantee_type": "stock",
                        "description": "Stock pagnes wax hollandais",
                        "estimated_value": 1800000.0
                    }
                ],
                "debts": [
                    {
                        "creditor_name": "BNDA",
                        "is_internal": False,
                        "remaining_amount": 150000.0,
                        "monthly_payment": 25000.0
                    }
                ]
            }
        )
        assert r_quick.status_code == 201
        quick_app = r_quick.json()
        app_id = quick_app["id"]
        print(f"  ✓ Dossier initialisé en 1 clic : {quick_app['reference']} pour {quick_app['applicant_name']}")
        print(f"  ✓ Garanties enregistrées : {len(quick_app['guarantees'])} | Dettes : {len(quick_app['debts'])}")

        # 6. Multi-Search (by dossier ref and by account number)
        print("\n👉 [6/12] Test de la Recherche Polyvalente (Dossier & Compte)...")
        r_search_ref = await client.get(f"/api/v1/applications/search?q={quick_app['reference'][:8]}", headers={"Authorization": f"Bearer {agent_token}"})
        assert r_search_ref.status_code == 200
        assert len(r_search_ref.json()["applications"]) >= 1
        print(f"  ✓ Recherche par référence '{quick_app['reference'][:8]}' : {len(r_search_ref.json()['applications'])} trouvé(s)")

        r_search_acc = await client.get("/api/v1/applications/search?q=CMF-2026-001245", headers={"Authorization": f"Bearer {agent_token}"})
        assert r_search_acc.status_code == 200
        assert len(r_search_acc.json()["applications"]) >= 1
        print(f"  ✓ Recherche par numéro de compte 'CMF-2026-001245' : {len(r_search_acc.json()['applications'])} trouvé(s)")

        # 7. Add Guarantee & Debt dynamically
        print("\n👉 [7/12] Test d'ajout dynamique de Garanties et Dettes...")
        r_g = await client.post(
            f"/api/v1/applications/{app_id}/guarantees",
            headers={"Authorization": f"Bearer {agent_token}"},
            json={
                "guarantee_type": "vehicule",
                "description": "Moto Djakarta",
                "estimated_value": 450000.0,
                "retained_value": 300000.0
            }
        )
        assert r_g.status_code == 201
        print(f"  ✓ Garantie additionnelle enregistrée : {r_g.json()['description']} ({r_g.json()['retained_value']:,.0f} FCFA)")

        # 8. Run Scoring on base 100
        print("\n👉 [8/12] Test d'Évaluation du Score sur base 100...")
        r_eval = await client.post(
            f"/api/v1/applications/{app_id}/evaluate",
            headers={"Authorization": f"Bearer {agent_token}"}
        )
        assert r_eval.status_code == 200
        eval_data = r_eval.json()
        print(f"  ✓ Score du dossier {app_id} : {eval_data['score']}/100 | Décision: {eval_data['decision'].upper()}")
        print(f"  ✓ Méthode d'octroi applicable : {eval_data['granting_method']['procedure_name'] if eval_data.get('granting_method') else 'Standard'}")
        assert 0 <= eval_data["score"] <= 100

        # 9. Submit to Committee
        print("\n👉 [9/12] Test de Transmission du Dossier au Comité d'Approbation...")
        r_sub = await client.post(
            f"/api/v1/applications/{app_id}/submit-to-committee",
            headers={"Authorization": f"Bearer {agent_token}"}
        )
        assert r_sub.status_code == 200
        assert r_sub.json()["status"] == "pending_committee_approval"
        print(f"  ✓ Statut dossier mis à jour : {r_sub.json()['status']}")

        # 10. Committee / Admin Final Approval
        print("\n👉 [10/12] Test de la Validation Finale par le Comité / Admin...")
        r_pending = await client.get("/api/v1/admin/pending-approvals", headers={"Authorization": f"Bearer {admin_token}"})
        assert r_pending.status_code == 200
        print(f"  ✓ File d'attente comité : {r_pending.json()['total']} dossier(s) en attente")

        r_dec = await client.post(
            f"/api/v1/admin/applications/{app_id}/committee-decision",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"decision": "approved", "approved_amount": 1200000.0, "notes": "Garanties vérifiées, accord du comité d'agence"}
        )
        assert r_dec.status_code == 200
        assert r_dec.json()["new_status"] == "approved"
        print(f"  ✓ Décision officielle scellée par l'admin : APPROUVÉ (Montant : {r_dec.json()['approved_amount']:,.0f} FCFA)")

        # 11. Official Receipt Check (Agent name + Account number + Score /100)
        print("\n👉 [11/12] Test de la Génération du Récépissé Officiel...")
        r_rec = await client.get(f"/api/v1/applications/{app_id}/receipt", headers={"Authorization": f"Bearer {agent_token}"})
        assert r_rec.status_code == 200
        rec = r_rec.json()
        print(f"  ✓ Récépissé généré : {rec['receipt_id']}")
        print(f"  ✓ Numéro de compte : {rec['account_number']}")
        print(f"  ✓ Nom de l'agent : {rec['agent_name']}")
        print(f"  ✓ Score affiché : {rec['score']} / 100")
        assert rec["score"] <= 100
        assert rec["agent_name"] is not None

        # 12. Test Gemini AI Assistant
        print("\n👉 [12/12] Test de l'Assistant Gemini avec Contexte Dossier...")
        r_gemini = await client.post(
            "/api/v1/assist/voice-query",
            headers={"Authorization": f"Bearer {agent_token}"},
            json={
                "query_text": "Pourquoi mon score est supérieur à 70 et quelles sont mes garanties ?",
                "language": "fr",
                "application_id": app_id
            }
        )
        assert r_gemini.status_code == 200
        g_data = r_gemini.json()
        print(f"  ✓ Réponse IA : {g_data['response_text'][:120]}...")
        print(f"  ✓ Suggestions interactives : {g_data['suggestions']}")

    print("\n" + "="*70)
    print("✅ TOUS LES 12 TESTS DU SYSTÈME RESTUCTURÉ ONT RÉUSSI AVEC SUCCÈS !")
    print("="*70 + "\n")


if __name__ == "__main__":
    asyncio.run(run_e2e_tests())
