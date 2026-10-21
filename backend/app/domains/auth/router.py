from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.domains.auth.models import User
from app.domains.auth.schemas import (
    TokenRefresh,
    TokenResponse,
    UserLogin,
    UserRegister,
    UserResponse,
    UserUpdate,
)
from app.domains.auth.services import AuthService
from app.domains.households.permissions import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    data: UserRegister,
    db: AsyncSession = Depends(get_db),
):
    """Registers a new user, automatically creates their initial household, and issues JWT tokens."""
    return await AuthService.register(db, data)


@router.post("/login", response_model=TokenResponse)
async def login(
    data: UserLogin,
    db: AsyncSession = Depends(get_db),
):
    """Authenticates a user with email and password and returns JWT tokens."""
    return await AuthService.login(db, data)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    data: TokenRefresh,
    db: AsyncSession = Depends(get_db),
):
    """Renews an access token using a valid refresh token."""
    return await AuthService.refresh_token(db, data.refresh_token)


@router.get("/me", response_model=UserResponse)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
):
    """Returns the profile of the currently authenticated user."""
    return UserResponse.model_validate(current_user)


@router.patch("/me", response_model=UserResponse)
async def update_my_profile(
    data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Updates the profile name or password of the currently authenticated user."""
    return await AuthService.update_profile(db, current_user, data)

