# OpenScore Finance — MVP Platform (DigiCoop-WA+ Hackathon 2026)

**OpenScore Finance (OSF)** est une solution digitale d'aide à la décision et de scoring de crédit explicable conçue pour les Institutions de Microfinance (IMF) et Coopératives d'Épargne et de Crédit (CIF) en Afrique de l'Ouest (Mali / UEMOA).

---

## Fonctionnalités Clés

1. **Portail Emprunteur (`client-portal`)** :
   - Sélection du profil d'activité (*Commerce, Agriculture, Artisanat, TPE*) et saisie du montant souhaité en FCFA.
   - Dépôt de pièces justificatives (CNI/NINA, attestations, registres) avec **extraction IA via Gemini 1.5 Flash** et **destruction immédiate post-extraction** pour respect strict de la confidentialité.
   - Module d'**assistance vocale** contextualisé pour guider les demandeurs.
   - Suivi en temps réel de l'état du dossier de crédit.

2. **Console Agent de Crédit (`agent-workspace`)** :
   - Tableau de bord opérationnel des dossiers en attente de vérification technique.
   - Interface de comparaison côte-à-côte : **Données extraites par l'IA vs Champs certifiés éditables**.
   - Certification des données et déclenchement du moteur de décision.

3. **Moteur Décisionnel & Explicabilité (`score-audit`)** :
   - Score de solvabilité (0 - 1000) et jauge de risque sectorielle.
   - **Tableau d'explicabilité complet** détaillant la contribution de chaque ratio (endettement, régularité des revenus, ancienneté d'activité, reste à vivre).
   - **Panneau de contre-proposition dynamique** : ajustement en temps réel du montant et de la durée pour les dossiers à risque intermédiaire.

4. **Bordereau Officiel d'Archivage (`receipt-view`)** :
   - Récépissé numérique conforme au format A4 prêt à l'impression (`@media print`).
   - Identifiant unique sécurisé, synthèse décisionnelle et encarts d'émargement légal.

---

## Identifiants de Démonstration (Hackathon)

| Rôle | Nom | Email | Mot de passe |
|---|---|---|---|
| **Client Emprunteur** | Amadou Diallo (Commerce - Grand Marché) | `amadou.diallo@mail.ml` | `password123` |
| **Client Emprunteur** | Fatoumata Traoré (Agriculture - Baguinéda) | `fatoumata.traore@mail.ml` | `password123` |
| **Agent CIF / IMF** | Ibrahima Coulibaly | `agent@openscore.ml` | `agent123` |
| **Agent CIF / IMF** | Awa Sangaré | `awa.sangare@openscore.ml` | `agent123` |

---

## Démarrage Rapide

### 1. Prérequis
- Python 3.11+
- Node.js 20+
- Serveur MySQL local (`root:skypper19@localhost:3306`)

### 2. Lancer le Backend (FastAPI + MySQL)
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
- API Swagger interactive : `http://localhost:8000/docs`
- Health check : `http://localhost:8000/api/health`

### 3. Lancer le Frontend (Angular + Tailwind)
```bash
cd frontend
npm start
```
- Application Web : `http://localhost:4200`

---

## Architecture Technique

```text
openscore-finance/
├── backend/
│   ├── app/
│   │   ├── api/v1/
│   │   │   ├── auth.py          # Authentification JWT
│   │   │   ├── applications.py  # CRUD dossiers & extraction
│   │   │   └── scoring.py       # Moteur de scoring & vocal
│   │   ├── core/
│   │   │   ├── config.py        # Settings Pydantic
│   │   │   └── gemini_client.py # Client Gemini 1.5 Flash
│   │   ├── models/
│   │   │   ├── database.py      # Modèles SQLAlchemy MySQL
│   │   │   └── schemas.py       # Schémas Pydantic
│   │   ├── services/
│   │   │   ├── extraction_service.py
│   │   │   └── scoring_engine.py
│   │   └── main.py              # Lifespan & Seed data
│   ├── requirements.txt
│   └── .env
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── core/            # Services Auth, API, Toast, Guards
│   │   │   ├── shared/          # Logo OSF, SvgIcon, Toast, Modèles
│   │   │   ├── features/        # Client Portal, Agent Workspace, Score Audit, Receipt View, Login
│   │   │   ├── app.component.*  # Shell applicatif
│   │   │   └── app.routes.ts    # Routing sécurisé
│   │   ├── styles.css           # Thème Utilitarian Ledger / Tailwind v4
│   │   └── main.ts
│   └── package.json
└── README.md
```
