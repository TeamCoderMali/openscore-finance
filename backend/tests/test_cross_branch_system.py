"""
OpenScore Finance — Test de Validation Multi-Antennes & Détection de Conflits Cross-Branch
"""

import asyncio
import os
import sys
from pathlib import Path

backend_dir = str(Path(__file__).resolve().parent.parent)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import httpx
from app.main import app


async def run_cross_branch_tests():
    print("\n" + "="*70)
    print("🚀 TEST DE VALIDATION : CLASSEMENT MULTI-ANTENNES & GESTION DES DOUBLONS")
    print("="*70 + "\n")

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Login Agent (Branch 701 - Bamako)
        print("👉 [1/5] Connexion de l'Agent Bamako (Antenne 701)...")
        agent_login = await client.post(
            "/api/v1/auth/login",
            json={"email": "agent@openscore.ml", "password": "agent123"}
        )
        assert agent_login.status_code == 200, f"Erreur login agent: {agent_login.text}"
        agent_token = agent_login.json()["access_token"]
        agent_headers = {"Authorization": f"Bearer {agent_token}"}
        print("  ✓ Agent connecté avec succès.")

        # 2. Login Super Admin to set up cross-branch test scenario
        print("👉 [2/5] Initialisation du compte sociétaire et d'un dossier actif dans l'Antenne 801 (Sikasso)...")
        admin_login = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@openscore.ml", "password": "admin123"}
        )
        assert admin_login.status_code == 200, f"Erreur login admin: {admin_login.text}"
        admin_token = admin_login.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # Create account in branch 801 (Sikasso)
        import time
        unique_suffix = str(int(time.time()))[-6:]
        req_res = await client.post(
            "/api/v1/accounts/kafo-jiginew-request",
            json={
                "full_name": f"Bakary Traoré {unique_suffix}",
                "phone": f"+223 79 {unique_suffix[:3]} {unique_suffix[3:]}",
                "id_number": f"NINA-801-{unique_suffix}",
                "profession": "Agriculture",
                "branch_code": "801",
                "city": "Sikasso",
                "account_type": "INDIVIDUAL",
            }
        )
        assert req_res.status_code == 201, f"Erreur demande compte: {req_res.text}"
        req_id = req_res.json()["id"]

        appr_res = await client.post(
            f"/api/v1/accounts/kafo-jiginew-requests/{req_id}/approve",
            headers=admin_headers,
        )
        assert appr_res.status_code == 200, f"Erreur approbation compte: {appr_res.text}"
        test_account = appr_res.json()["account_number_generated"]
        print(f"  ✓ Compte sociétaire Kafo Jiginew Sikasso généré : {test_account}")

        # We create an active application in branch 801 as admin
        sikasso_app_res = await client.post(
            "/api/v1/applications/quick-init",
            headers=admin_headers,
            json={
                "account_number": test_account,
                "requested_amount": 2500000,
                "requested_duration_months": 18,
                "branch_code": "801",
                "application_type": "INDIVIDUAL",
                "activity_sector": "Agriculture",
                "business_description": "Financement intrants coton & maraîchage Sikasso",
                "force_override_cross_branch": True,
            }
        )
        assert sikasso_app_res.status_code in [200, 201], f"Erreur création dossier Sikasso: {sikasso_app_res.text}"
        sikasso_app = sikasso_app_res.json()
        print(f"  ✓ Dossier actif créé dans l'Antenne 801 (Sikasso) : {sikasso_app['reference']}")

        # 3. Agent Bamako (701) searches for this client
        print("👉 [3/5] Recherche du compte par l'Agent Bamako (Antenne 701)...")
        lookup_res = await client.get(
            f"/api/v1/applications/accounts/{test_account}",
            headers=agent_headers,
        )
        assert lookup_res.status_code == 200, f"Erreur lookup compte: {lookup_res.text}"
        lookup_data = lookup_res.json()
        assert lookup_data["has_active_other_branch"] is True, "has_active_other_branch doit être True"
        assert lookup_data["has_no_dossier_in_current_branch"] is True, "has_no_dossier_in_current_branch doit être True"
        assert len(lookup_data["other_branch_applications"]) >= 1, "Doit lister au moins 1 dossier dans une autre antenne"
        first_other = lookup_data["other_branch_applications"][0]
        assert first_other["branch_code"] == "801", "L'antenne du dossier conflictuel doit être 801"
        assert lookup_data["warning_message"] is not None, "warning_message doit être présent"
        print(f"  ✓ Détection cross-branch réussie !")
        print(f"    - Alerte : {lookup_data['warning_message'][:80]}...")
        print(f"    - Dossier détecté dans autre antenne : {first_other['reference']} ({first_other['branch_name']})")

        # 4. Agent Bamako attempts to create duplicate application WITHOUT override -> Must be 409 Conflict
        print("👉 [4/5] Tentative de création d'un dossier doublon sans dérogation (blocage prudentiel)...")
        dup_attempt = await client.post(
            "/api/v1/applications/quick-init",
            headers=agent_headers,
            json={
                "account_number": test_account,
                "requested_amount": 1000000,
                "requested_duration_months": 12,
                "branch_code": "701",
                "application_type": "INDIVIDUAL",
                "activity_sector": "Commerce",
                "force_override_cross_branch": False,
            }
        )
        assert dup_attempt.status_code == 409, f"Doit renvoyer 409 Conflict mais a renvoyé: {dup_attempt.status_code}"
        print(f"  ✓ Création bloquée avec succès (409 Conflict) : {dup_attempt.json()['detail']}")

        # 5. Agent Bamako creates with explicit exception override -> Must succeed
        print("👉 [5/5] Création avec dérogation explicite autorisée...")
        override_attempt = await client.post(
            "/api/v1/applications/quick-init",
            headers=agent_headers,
            json={
                "account_number": test_account,
                "requested_amount": 1000000,
                "requested_duration_months": 12,
                "branch_code": "701",
                "application_type": "INDIVIDUAL",
                "activity_sector": "Commerce",
                "force_override_cross_branch": True,
            }
        )
        assert override_attempt.status_code in [200, 201], f"Erreur création avec dérogation: {override_attempt.text}"
        new_app = override_attempt.json()
        print(f"  ✓ Dossier créé avec succès sous dérogation formelle : {new_app['reference']}")

    print("\n" + "="*70)
    print("✅ TOUS LES TESTS DE CLASSEMENT MULTI-ANTENNES ET GESTION DES DOUBLONS ONT RÉUSSI !")
    print("="*70 + "\n")


if __name__ == "__main__":
    asyncio.run(run_cross_branch_tests())
