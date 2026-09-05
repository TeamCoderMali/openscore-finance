# OpenScore Finance — Plateforme de Scoring de Crédit IA

<div align="center">

![OpenScore Finance](https://img.shields.io/badge/OpenScore-Finance-1d4ed8?style=for-the-badge&logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI+PHBhdGggZmlsbD0id2hpdGUiIGQ9Ik0xMiAyQzYuNDggMiAyIDYuNDggMiAxMnM0LjQ4IDEwIDEwIDEwIDEwLTQuNDggMTAtMTBTMTcuNTIgMiAxMiAyeiIvPjwvc3ZnPg==)
![Flutter](https://img.shields.io/badge/Mobile-Flutter_3.44-02569B?style=for-the-badge&logo=flutter)
![FastAPI](https://img.shields.io/badge/Backend-FastAPI_0.115-009688?style=for-the-badge&logo=fastapi)
![Angular](https://img.shields.io/badge/Frontend-Angular_22-DD0031?style=for-the-badge&logo=angular)
![Gemini](https://img.shields.io/badge/IA-Gemini_1.5_Flash-4285F4?style=for-the-badge&logo=google)

**Solution digitale de scoring de crédit explicable pour la Microfinance en Afrique de l'Ouest**

*DigiCoop-WA+ Hackathon 2026 • BCEAO/UEMOA • Mali*

</div>

---

## Vue d'ensemble

**OpenScore Finance (OSF)** est une plateforme full-stack d'aide à la décision pour les Institutions de Microfinance (IMF) et Coopératives d'Épargne et de Crédit (CEC) au Mali et dans l'espace UEMOA. Elle automatise et sécurise le cycle complet d'instruction des dossiers de crédit grâce à l'intelligence artificielle.

### Problème résolu

Les IMF au Mali traitent encore la majorité des dossiers manuellement (papier, tableur), avec des délais de 5 à 15 jours ouvrés, une forte variabilité des décisions d'agent à agent, et aucune traçabilité numérique conforme aux directives BCEAO.

### Solution

| Acteur | Bénéfice |
|--------|----------|
| **Emprunteur** | Dépôt de dossier en ligne ou mobile, suivi en temps réel, récépissé officiel |
| **Agent CIF/IMF** | Tableau de bord opérationnel, extraction IA des pièces, certification assistée |
| **Décideur IMF** | Score explicable 0–1000, piste d'audit complète, conformité BCEAO |

---

## Stack Technique

```
openscore-finance/
├── backend/     FastAPI 0.115 + SQLAlchemy 2.0 (async) + MySQL + Gemini 1.5 Flash
├── frontend/    Angular 22 + Tailwind CSS v4
└── mobile/      Flutter 3.44 (Android & iOS)
```

### Dépendances clés

| Couche | Technologie | Version |
|--------|-------------|---------|
| API REST | FastAPI + Uvicorn | 0.115 / 0.34 |
| ORM | SQLAlchemy async | 2.0.36 |
| Base de données | MySQL (aiomysql) | — |
| Authentification | JWT (python-jose) + bcrypt | — |
| IA Extraction | Google Gemini 1.5 Flash | google-genai 1.14 |
| Frontend | Angular | 22.1 |
| App Mobile | Flutter + Dart | 3.44 / 3.12 |
| Navigation mobile | GoRouter | 14.x |
| HTTP mobile | Dio | 5.x |
| Stockage sécurisé | flutter_secure_storage | 9.x |

---

## Fonctionnalités

### 🏦 Portail Emprunteur (Web + Mobile)

- Inscription avec sélection du secteur d'activité (*Commerce, Agriculture, Artisanat, TPE*)
- **Vérification d'identité obligatoire** : NINA / CNI / Passeport
- **Documents PME/TPE** : NIF (DGI Mali) + RCCM (Tribunal de Commerce)
- Dépôt de pièces justificatives avec **extraction IA Gemini** + suppression immédiate
- Module d'**assistance vocale bilingue** Français/Bambara
- Suivi en temps réel du statut du dossier
- **Simulateur de remboursement** BCEAO (taux dégressif 1,5%/mois)
- Récépissé officiel numérique partageable

### 🖥️ Console Agent de Crédit (Web)

- Tableau de bord opérationnel des dossiers en attente
- Interface de comparaison : **Données IA vs Champs certifiés éditables**
- Certification des données et déclenchement du moteur décisionnel
- Piste d'audit complète horodatée

### 📊 Moteur de Scoring & Explicabilité (Web)

- Score de solvabilité **0 – 1000** par secteur
- Tableau d'explicabilité : contribution de chaque ratio (endettement, régularité, ancienneté, reste à vivre)
- **Contre-proposition dynamique** : ajustement montant/durée pour dossiers intermédiaires
- Décisions : `APPROUVÉ` / `AJUSTÉ` / `REFUSÉ`

### 📱 Application Mobile Flutter

- Login / Inscription 3 étapes avec upload de documents
- Dashboard avec KPI cards et échéancier
- Wizard de demande de crédit en 4 étapes
- Chat assistant vocal bilingue
- Récépissé officiel avec partage natif
- Mode sombre / clair persistant

---

## Démarrage Rapide

### Prérequis

- Python 3.11+
- Node.js 20+
- Flutter SDK 3.44+
- MySQL 8+ local
- Clé API Google Gemini (`GEMINI_API_KEY`)

---

### 1. Backend — FastAPI

```bash
cd backend
source venv/bin/activate          # Linux/macOS
# .\venv\Scripts\activate         # Windows

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

| Endpoint | URL |
|----------|-----|
| API Swagger | http://localhost:8000/docs |
| Health check | http://localhost:8000/api/health |
| ReDoc | http://localhost:8000/redoc |

#### Variables d'environnement (`backend/.env`)

```env
DATABASE_URL=mysql+aiomysql://root:PASSWORD@localhost:3306/openscore_db
SECRET_KEY=your-jwt-secret-key
GEMINI_API_KEY=your-gemini-api-key
ACCESS_TOKEN_EXPIRE_MINUTES=1440
```

---

### 2. Frontend Web — Angular

```bash
cd frontend
npm install
npm start
```

Application Web : **http://localhost:4200**

---

### 3. Application Mobile — Flutter

```bash
cd mobile

# iOS Simulator
flutter run -d ios

# Android Emulator (URL déjà configurée sur 10.0.2.2:8000)
flutter run -d android
```

> **Device physique** : modifiez `baseUrl` dans [`lib/core/constants/api_constants.dart`](mobile/lib/core/constants/api_constants.dart) avec l'IP locale de votre machine.

---

## Architecture

```
openscore-finance/
│
├── backend/
│   └── app/
│       ├── api/v1/
│       │   ├── auth.py              # Authentification JWT (login / register / me)
│       │   ├── applications.py      # CRUD dossiers, OCR, workflow
│       │   └── scoring.py           # Moteur ML & assistant vocal
│       ├── core/
│       │   ├── config.py            # Settings Pydantic
│       │   └── gemini_client.py     # Client Gemini 1.5 Flash
│       ├── models/
│       │   ├── database.py          # Modèles SQLAlchemy
│       │   └── schemas.py           # Schémas Pydantic
│       ├── services/
│       │   ├── extraction_service.py
│       │   └── scoring_engine.py
│       └── main.py                  # Lifespan & Seed data
│
├── frontend/
│   └── src/app/
│       ├── core/                    # Services Auth, API, Toast, Guards
│       ├── shared/                  # Composants partagés (Logo, SvgIcon, Toast)
│       └── features/
│           ├── client-portal/       # Espace emprunteur web
│           ├── agent-workspace/     # Console agent
│           ├── score-audit/         # Scoring & explicabilité
│           ├── receipt-view/        # Récépissé A4 imprimable
│           └── login/
│
└── mobile/
    └── lib/
        ├── core/
        │   ├── theme/               # Design system (light + dark)
        │   ├── constants/           # URLs API
        │   ├── services/            # API (Dio), Auth, Storage sécurisé
        │   └── router/              # GoRouter + auth guard
        ├── models/                  # User, Application, Receipt
        ├── features/
        │   ├── auth/                # Login, Inscription 3 étapes
        │   ├── home/                # Shell navigation
        │   ├── dashboard/           # KPIs + échéancier
        │   ├── applications/        # Dossiers + Wizard 4 étapes
        │   ├── documents/           # Récépissés
        │   ├── simulator/           # Simulateur BCEAO
        │   └── voice_assistant/     # Chat bilingue FR/Bambara
        └── shared/widgets/          # Composants réutilisables
```

---

## Comptes de Démonstration

| Rôle | Nom | Email | Mot de passe |
|------|-----|-------|--------------|
| Client Emprunteur | Amadou Diallo (Commerce) | `amadou.diallo@mail.ml` | `password123` |
| Client Emprunteur | Fatoumata Traoré (Agriculture) | `fatoumata.traore@mail.ml` | `password123` |
| Client Emprunteur | Moussa Keïta (Artisanat) | `moussa.keita@mail.ml` | `password123` |
| Agent CIF/IMF | Ibrahima Coulibaly | `agent@openscore.ml` | `agent123` |
| Agent CIF/IMF | Awa Sangaré | `awa.sangare@openscore.ml` | `agent123` |

---

## Documents d'identité requis à l'inscription

La plateforme respecte les exigences KYC de la BCEAO. Selon le profil :

| Secteur | Documents obligatoires | Documents recommandés |
|---------|------------------------|----------------------|
| **Commerce** | NINA ou CNI | Carte de commerçant (Mairie) |
| **Agriculture** | NINA ou CNI | Attestation d'exploitation agricole |
| **Artisanat** | NINA ou CNI | Carte d'artisan APIM |
| **TPE / PME** | CNI + NIF (DGI) + RCCM | Bilan comptable, déclaration fiscale |

---

## Flux de traitement d'un dossier

```
Emprunteur soumet     →    Agent vérifie     →    Moteur score     →    Décision
(upload docs + profil)     (certifie données)     (0-1000 + risque)     (approuvé / ajusté / refusé)
       ↓                         ↓                      ↓                       ↓
   Gemini IA               Piste d'audit          Explicabilité            Récépissé
  extraction auto          horodatée               SHAP-like               officiel
```

---

## Conformité & Sécurité

- ✅ Tokens JWT avec expiration configurable
- ✅ Mots de passe hachés bcrypt
- ✅ Documents supprimés après extraction IA (pas de stockage permanent)
- ✅ Stockage mobile chiffré AES-256 (flutter_secure_storage)
- ✅ Conforme directives **BCEAO n°01/2023** sur la microfinance digitale
- ✅ Architecture compatible espace **UEMOA/WA+**

---

## Licence

Projet développé dans le cadre du **DigiCoop-WA+ Hackathon 2026**.
Équipe : **TeamCoderMali**
