"""
OpenScore Finance — FastAPI Application Entry Point
Initializes DB, seeds demo data, mounts API routers, configures CORS.
"""

import logging
import sys
from pathlib import Path
from contextlib import asynccontextmanager
from datetime import datetime, timezone

# Ensure backend directory is in sys.path
backend_dir = str(Path(__file__).resolve().parent.parent)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, text

from app.core.config import get_settings
from app.models.database import (
    engine, async_session, Base, User, UserRole,
    CreditApplication, ApplicationStatus, ExtractedData, ActivitySector,
    ScoringResult, RiskLevel, AuditLog
)
from app.api.v1.auth import router as auth_router, hash_password
from app.api.v1.applications import router as applications_router
from app.api.v1.scoring import router as scoring_router
from app.api.v1.admin import router as admin_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
settings = get_settings()


# ── Seed demo data (Malian profiles) ─────────────────────────────────
async def seed_demo_data():
    """Pre-populate database with Malian demo users and sample applications."""
    async with async_session() as db:
        logger.info("Verifying & seeding demo data with Malian microfinance profiles...")

        # Demo users
        users = [
            User(
                email="amadou.diallo@mail.ml",
                full_name="Amadou Diallo",
                hashed_password=hash_password("password123"),
                role=UserRole.CLIENT,
                phone="+223 76 45 23 18",
                is_active=True,
            ),
            User(
                email="fatoumata.traore@mail.ml",
                full_name="Fatoumata Traoré",
                hashed_password=hash_password("password123"),
                role=UserRole.CLIENT,
                phone="+223 65 32 87 41",
                is_active=True,
            ),
            User(
                email="moussa.keita@mail.ml",
                full_name="Moussa Keïta",
                hashed_password=hash_password("password123"),
                role=UserRole.CLIENT,
                phone="+223 78 91 56 03",
                is_active=True,
            ),
            User(
                email="agent@openscore.ml",
                full_name="Ibrahima Coulibaly",
                hashed_password=hash_password("agent123"),
                role=UserRole.AGENT,
                phone="+223 70 12 34 56",
                is_active=True,
            ),
            User(
                email="awa.sangare@openscore.ml",
                full_name="Awa Sangaré",
                hashed_password=hash_password("agent123"),
                role=UserRole.AGENT,
                phone="+223 66 78 90 12",
                is_active=True,
            ),
            User(
                email="admin@openscore.ml",
                full_name="Fatoumata Cissé",
                hashed_password=hash_password("admin123"),
                role=UserRole.ADMIN,
                phone="+223 70 99 88 77",
                is_active=True,
            ),
        ]

        # Ensure each demo user exists
        for u in users:
            stmt = select(User).where(User.email == u.email)
            res = await db.execute(stmt)
            existing = res.scalar_one_or_none()
            if not existing:
                db.add(u)
                logger.info(f"Seeded user: {u.email} ({u.role})")
        await db.flush()

        # Check if applications already exist
        app_check = await db.execute(select(CreditApplication).limit(1))
        if app_check.scalar_one_or_none():
            await db.commit()
            return

        # Demo applications
        applications = [
            # Application 1: Commerce - Scored & Approved
            CreditApplication(
                reference="OSF-20260829-A1B2",
                applicant_id=users[0].id,
                activity_sector=ActivitySector.COMMERCE,
                requested_amount=1500000.0,
                requested_duration_months=12,
                business_description="Commerce de tissus et bazin riche au Grand Marché de Bamako",
                status=ApplicationStatus.APPROVED,
                agent_id=users[3].id,
            ),
            # Application 2: Agriculture - Pending verification
            CreditApplication(
                reference="OSF-20260828-C3D4",
                applicant_id=users[1].id,
                activity_sector=ActivitySector.AGRICULTURE,
                requested_amount=750000.0,
                requested_duration_months=18,
                business_description="Culture maraîchère à Baguinéda — production de tomates et oignons",
                status=ApplicationStatus.PENDING_VERIFICATION,
                agent_id=users[4].id,
            ),
            # Application 3: Artisanat - Draft
            CreditApplication(
                reference="OSF-20260827-E5F6",
                applicant_id=users[2].id,
                activity_sector=ActivitySector.ARTISANAT,
                requested_amount=500000.0,
                requested_duration_months=6,
                business_description="Atelier de couture et broderie traditionnelle à Médina Coura",
                status=ApplicationStatus.DRAFT,
            ),
        ]
        db.add_all(applications)
        await db.flush()

        # Extracted data
        extracted_records = [
            ExtractedData(
                application_id=applications[0].id,
                full_name="Amadou Diallo",
                date_of_birth="15/03/1985",
                id_number="ML-BKO-1985-04521",
                id_type="NINA",
                monthly_revenue=450000.0,
                monthly_expenses=250000.0,
                existing_debt=45000.0,
                business_registration_number="ML-RC-BKO-2019-3847",
                business_start_date="10/06/2019",
                years_in_business=5.2,
                revenue_regularity_months=11,
                is_verified=True,
                verified_by_agent_id=users[3].id,
                verified_at=datetime.now(timezone.utc),
                verification_notes="Activité vérifiée sur place au Grand Marché. Justificatifs NINA et RCCM concordants.",
                extraction_confidence=0.94,
                raw_extraction_json={
                    "nom_complet": "Amadou Diallo",
                    "document_type": "attestation_revenus",
                    "confidence": 0.94
                },
            ),
            ExtractedData(
                application_id=applications[1].id,
                full_name="Fatoumata Traoré",
                date_of_birth="22/07/1990",
                id_number="ML-SGU-1990-08734",
                id_type="CARNET_RECUS",
                monthly_revenue=280000.0,
                monthly_expenses=180000.0,
                existing_debt=30000.0,
                business_registration_number=None,
                business_start_date="15/03/2021",
                years_in_business=3.4,
                revenue_regularity_months=9,
                is_verified=False,
                extraction_confidence=0.88,
                raw_extraction_json={
                    "nom_complet": "Fatoumata Traoré",
                    "document_type": "carnet_recus",
                    "confidence": 0.88
                },
            ),
        ]
        db.add_all(extracted_records)
        await db.flush()

        # Scoring result for Application 1
        scoring_app1 = ScoringResult(
            application_id=applications[0].id,
            score=785,
            risk_level=RiskLevel.LOW,
            decision="approved",
            approved_amount=1500000.0,
            proposed_amount=None,
            proposed_duration_months=None,
            explainability=[
                {
                    "variable": "debt_ratio",
                    "label": "Ratio d'endettement",
                    "value": "26.5%",
                    "impact": "positive",
                    "weight": 0.30,
                    "contribution": 80,
                    "detail": "Ratio d'endettement maîtrisé (26.5%), bien inférieur au plafond réglementaire UEMOA de 40%."
                },
                {
                    "variable": "disposable_income",
                    "label": "Reste à vivre",
                    "value": "155 000 FCFA",
                    "impact": "positive",
                    "weight": 0.20,
                    "contribution": 60,
                    "detail": "Reste à vivre confortable de 155 000 FCFA/mois (> 2x minimum vital)."
                },
                {
                    "variable": "revenue_stability",
                    "label": "Régularité des revenus",
                    "value": "11/12 mois",
                    "impact": "positive",
                    "weight": 0.20,
                    "contribution": 50,
                    "detail": "Flux d'activité réguliers et continus documentés sur l'année."
                },
                {
                    "variable": "business_maturity",
                    "label": "Ancienneté d'activité",
                    "value": "5.2 ans",
                    "impact": "positive",
                    "weight": 0.15,
                    "contribution": 40,
                    "detail": "Activité commerciale solidement établie au Grand Marché."
                },
                {
                    "variable": "amount_to_income",
                    "label": "Levier / Revenus",
                    "value": "3.3x",
                    "impact": "positive",
                    "weight": 0.15,
                    "contribution": 25,
                    "detail": "Montant proportionné à la rotation des stocks de tissus."
                }
            ],
            debt_ratio=0.265,
            disposable_income=155000.0,
            scored_at=datetime.now(timezone.utc),
        )
        db.add(scoring_app1)

        # Audit logs for traceability
        logs = [
            AuditLog(
                application_id=applications[0].id,
                user_id=users[0].id,
                action="application_created",
                details={"requested_amount": 1500000.0, "sector": "Commerce"},
            ),
            AuditLog(
                application_id=applications[0].id,
                action="document_extracted",
                details={"document_type": "attestation_revenus", "confidence": 0.94},
            ),
            AuditLog(
                application_id=applications[0].id,
                user_id=users[3].id,
                action="data_certified",
                details={"certified_by": "Ibrahima Coulibaly"},
            ),
            AuditLog(
                application_id=applications[0].id,
                action="scoring_completed",
                details={"score": 785, "decision": "approved", "risk_level": "low"},
            ),
        ]
        db.add_all(logs)

        await db.commit()
        logger.info("Demo data successfully seeded: 5 users, 3 applications, 1 complete scored case.")


# ── Lifespan ──────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: create tables & seed data. Shutdown: dispose engine."""
    from sqlalchemy.ext.asyncio import create_async_engine as _cae
    db_url = settings.DATABASE_URL
    if "localhost/" in db_url:
        base_url = db_url.rsplit("/", 1)[0]
        db_name = db_url.rsplit("/", 1)[1].split("?")[0]
        try:
            tmp_engine = _cae(base_url + "/mysql", echo=False)
            async with tmp_engine.begin() as conn:
                await conn.execute(text(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
            await tmp_engine.dispose()
            logger.info(f"Database '{db_name}' verified")
        except Exception as e:
            logger.warning(f"Database creation check: {e}")

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created / verified")

    # Seed demo data
    await seed_demo_data()

    yield

    # Shutdown
    await engine.dispose()
    logger.info("Database engine disposed")


# ── App ───────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Plateforme d'aide à la décision et scoring explicable pour IMF en Afrique de l'Ouest",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200", "http://127.0.0.1:4200", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(auth_router, prefix="/api/v1")
app.include_router(applications_router, prefix="/api/v1")
app.include_router(scoring_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "app": settings.APP_NAME, "version": settings.APP_VERSION}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
