"""
OpenScore Finance — FastAPI Application Entry Point
Initializes DB, seeds demo data, mounts API routers, configures CORS.
"""

import logging
import sys
from pathlib import Path
from contextlib import asynccontextmanager

# Ensure backend directory is in sys.path even when executed directly via python app/main.py
backend_dir = str(Path(__file__).resolve().parent.parent)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, text

from app.core.config import get_settings
from app.models.database import engine, async_session, Base, User, UserRole, CreditApplication, ApplicationStatus, ExtractedData, ActivitySector, AuditLog
from app.api.v1.auth import router as auth_router, hash_password
from app.api.v1.applications import router as applications_router
from app.api.v1.scoring import router as scoring_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
settings = get_settings()


# ── Seed demo data (Malian profiles) ─────────────────────────────────
async def seed_demo_data():
    """Pre-populate database with Malian demo users and sample applications."""
    async with async_session() as db:
        # Check if data already exists
        result = await db.execute(select(User).limit(1))
        if result.scalar_one_or_none():
            logger.info("Demo data already exists — skipping seed")
            return

        logger.info("Seeding demo data...")

        # Demo users — Malian profiles
        users = [
            User(
                email="amadou.diallo@mail.ml",
                full_name="Amadou Diallo",
                hashed_password=hash_password("password123"),
                role=UserRole.CLIENT,
                phone="+223 76 45 23 18",
            ),
            User(
                email="fatoumata.traore@mail.ml",
                full_name="Fatoumata Traoré",
                hashed_password=hash_password("password123"),
                role=UserRole.CLIENT,
                phone="+223 65 32 87 41",
            ),
            User(
                email="moussa.keita@mail.ml",
                full_name="Moussa Keïta",
                hashed_password=hash_password("password123"),
                role=UserRole.CLIENT,
                phone="+223 78 91 56 03",
            ),
            User(
                email="agent@openscore.ml",
                full_name="Ibrahima Coulibaly",
                hashed_password=hash_password("agent123"),
                role=UserRole.AGENT,
                phone="+223 70 12 34 56",
            ),
            User(
                email="awa.sangare@openscore.ml",
                full_name="Awa Sangaré",
                hashed_password=hash_password("agent123"),
                role=UserRole.AGENT,
                phone="+223 66 78 90 12",
            ),
        ]
        db.add_all(users)
        await db.flush()

        # Demo applications
        applications = [
            CreditApplication(
                reference="OSF-20260829-A1B2",
                applicant_id=users[0].id,
                activity_sector=ActivitySector.COMMERCE,
                requested_amount=1500000,
                requested_duration_months=12,
                business_description="Commerce de tissus et bazin au Grand Marché de Bamako",
                status=ApplicationStatus.PENDING_VERIFICATION,
            ),
            CreditApplication(
                reference="OSF-20260828-C3D4",
                applicant_id=users[1].id,
                activity_sector=ActivitySector.AGRICULTURE,
                requested_amount=750000,
                requested_duration_months=18,
                business_description="Culture maraîchère à Baguinéda — tomates, oignons, laitue",
                status=ApplicationStatus.PENDING_VERIFICATION,
            ),
            CreditApplication(
                reference="OSF-20260827-E5F6",
                applicant_id=users[2].id,
                activity_sector=ActivitySector.ARTISANAT,
                requested_amount=500000,
                requested_duration_months=6,
                business_description="Atelier de couture et broderie traditionnelle à Médina Coura",
                status=ApplicationStatus.DRAFT,
            ),
        ]
        db.add_all(applications)
        await db.flush()

        # Demo extracted data for first two applications
        extracted_data = [
            ExtractedData(
                application_id=applications[0].id,
                full_name="Amadou Diallo",
                date_of_birth="15/03/1985",
                id_number="ML-BKO-1985-04521",
                id_type="NINA",
                monthly_revenue=450000,
                monthly_expenses=280000,
                existing_debt=50000,
                business_registration_number="ML-RC-BKO-2019-3847",
                business_start_date="10/06/2019",
                years_in_business=5.2,
                revenue_regularity_months=10,
                extraction_confidence=0.92,
                raw_extraction_json={
                    "document_type": "attestation_revenus",
                    "confidence": 0.92,
                    "source": "demo_seed"
                },
            ),
            ExtractedData(
                application_id=applications[1].id,
                full_name="Fatoumata Traoré",
                date_of_birth="22/07/1990",
                id_number="ML-SGU-1990-08734",
                id_type="NINA",
                monthly_revenue=280000,
                monthly_expenses=190000,
                existing_debt=30000,
                business_registration_number="ML-RC-SGU-2021-1562",
                business_start_date="15/03/2021",
                years_in_business=3.4,
                revenue_regularity_months=8,
                extraction_confidence=0.87,
                raw_extraction_json={
                    "document_type": "registre_commerce",
                    "confidence": 0.87,
                    "source": "demo_seed"
                },
            ),
        ]
        db.add_all(extracted_data)

        await db.commit()
        logger.info("Demo data seeded: 5 users, 3 applications, 2 extractions")


# ── Lifespan ──────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: create tables & seed data. Shutdown: dispose engine."""
    # Create database if it doesn't exist (MySQL)
    from sqlalchemy.ext.asyncio import create_async_engine as _cae
    db_url = settings.DATABASE_URL
    # Extract database name to create it if needed
    if "localhost/" in db_url:
        base_url = db_url.rsplit("/", 1)[0]
        db_name = db_url.rsplit("/", 1)[1].split("?")[0]
        try:
            tmp_engine = _cae(base_url + "/mysql", echo=False)
            async with tmp_engine.begin() as conn:
                await conn.execute(text(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
            await tmp_engine.dispose()
            logger.info(f"Database '{db_name}' ensured")
        except Exception as e:
            logger.warning(f"Could not auto-create database: {e}")

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created")

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
    description="Plateforme d'aide à la décision pour institutions de microfinance en Afrique de l'Ouest",
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


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "app": settings.APP_NAME, "version": settings.APP_VERSION}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
