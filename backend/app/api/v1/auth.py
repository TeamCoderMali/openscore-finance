"""
OpenScore Finance — Auth API (JWT multi-role + Registration)
POST /api/v1/auth/login
POST /api/v1/auth/register
GET /api/v1/auth/me
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import jwt, JWTError
from passlib.context import CryptContext

from app.core.config import get_settings
from app.models.database import (
    User, UserRole, CreditApplication, ExtractedData,
    ActivitySector, ApplicationStatus, AuditLog, get_db
)
from app.models.schemas import LoginRequest, UserRegisterRequest, TokenResponse, UserOut

router = APIRouter(prefix="/auth", tags=["Authentication"])
settings = get_settings()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


# ── Utilities ─────────────────────────────────────────────────────────
def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Dependency: extract and validate current user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token invalide ou expiré",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        sub = payload.get("sub")
        if sub is None:
            raise credentials_exception
        user_id = int(sub)
    except (JWTError, ValueError):
        raise credentials_exception

    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None or not bool(user.is_active):
        raise credentials_exception
    return user


def require_role(*roles: str):
    """Dependency factory: restrict access to specific roles."""
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        user_role = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
        if user_role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Accès réservé aux rôles : {', '.join(roles)}",
            )
        return current_user
    return role_checker


# ── Routes ────────────────────────────────────────────────────────────
@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(request: UserRegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new client borrower account and return JWT access token."""
    # Check if email already exists
    stmt = select(User).where(User.email == request.email)
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Un compte avec cette adresse email existe déjà.",
        )

    # Restrict public registration to CLIENT role
    user_role = UserRole.CLIENT

    new_user = User(
        email=request.email,
        full_name=request.full_name,
        hashed_password=hash_password(request.password),
        role=user_role,
        phone=request.phone,
        is_active=True,
    )
    db.add(new_user)
    await db.flush()

    # If salary / financial details were provided, initialize borrower application and extracted data
    if request.monthly_revenue or request.requested_amount:
        sector_str = (request.activity_sector or "Commerce").capitalize()
        try:
            sec_enum = ActivitySector(sector_str)
        except ValueError:
            sec_enum = ActivitySector.COMMERCE

        now = datetime.now(timezone.utc)
        ref = f"OSF-{now.strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"
        initial_amount = float(request.requested_amount or 500000.0)

        app = CreditApplication(
            reference=ref,
            applicant_id=new_user.id,
            activity_sector=sec_enum,
            requested_amount=initial_amount,
            requested_duration_months=12,
            business_description=request.business_description or f"Activité {sector_str} déclarée à l'inscription",
            status=ApplicationStatus.PENDING_VERIFICATION,
        )
        db.add(app)
        await db.flush()

        ext = ExtractedData(
            application_id=app.id,
            raw_extraction_json={"source": "profil_inscription"},
            extraction_confidence=1.0,
            full_name=request.full_name,
            id_number=request.id_number or "NINA-INSCRIPTION",
            id_type=request.id_type or "NINA",
            monthly_revenue=float(request.monthly_revenue or 350000.0),
            monthly_expenses=float(request.monthly_expenses or 120000.0),
            existing_debt=float(request.existing_debt or 0.0),
            years_in_business=float(request.years_in_business or 3.0),
            revenue_regularity_months=int(request.revenue_regularity_months or 12),
        )
        db.add(ext)

        audit = AuditLog(
            application_id=app.id,
            user_id=new_user.id,
            action="client_account_registered_with_profile",
            details={
                "monthly_revenue": request.monthly_revenue,
                "monthly_expenses": request.monthly_expenses,
                "activity_sector": sector_str,
                "city": request.city,
            },
        )
        db.add(audit)

    await db.commit()
    await db.refresh(new_user)

    access_token = create_access_token(
        data={"sub": str(new_user.id), "role": new_user.role.value, "email": new_user.email}
    )

    return TokenResponse(
        access_token=access_token,
        role=new_user.role.value,
        full_name=new_user.full_name,
        user_id=new_user.id,
    )


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate user by email + password. Returns JWT with role embedded."""
    stmt = select(User).where(User.email == request.email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not verify_password(request.password, str(user.hashed_password)):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
        )

    if not bool(user.is_active):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Compte désactivé",
        )

    access_token = create_access_token(
        data={"sub": str(user.id), "role": user.role.value, "email": user.email}
    )

    return TokenResponse(
        access_token=access_token,
        role=user.role.value,
        full_name=str(user.full_name),
        user_id=int(user.id),
    )


@router.get("/me", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current authenticated user profile."""
    return current_user
