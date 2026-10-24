from typing import Optional

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.ratelimit import rate_limit
from app.domains.auth.models import User
from app.domains.auth.schemas import (
    AccountDeleteRequest,
    InitialAdminSetupRequest,
    SetupStatusResponse,
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

REFRESH_COOKIE_NAME = "sd_refresh"
REFRESH_COOKIE_PATH = f"{settings.API_V1_PREFIX}/auth"


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    """Guarda el refresh token en una cookie HttpOnly (no accesible desde JavaScript)."""
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
        httponly=True,
        secure=settings.SERVER_PUBLIC_URL.lower().startswith("https://"),
        samesite="strict",
        path=REFRESH_COOKIE_PATH,
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key=REFRESH_COOKIE_NAME, path=REFRESH_COOKIE_PATH)


@router.get("/setup-status", response_model=SetupStatusResponse)
async def get_setup_status(
    db: AsyncSession = Depends(get_db),
):
    """Indica si el sistema requiere configuración inicial de superadministrador (First-Run Setup)."""
    return await AuthService.get_setup_status(db)


@router.post(
    "/setup-initial-admin",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit("setup_admin", 5, 300))],
)
async def setup_initial_admin(
    data: InitialAdminSetupRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Configura el superadministrador inicial en el primer arranque si no existe ningún usuario."""
    tokens = await AuthService.setup_initial_admin(db, data)
    _set_refresh_cookie(response, tokens.refresh_token)
    return tokens


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit("register", 10, 3600))],
)
async def register(
    data: UserRegister,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Registers a new user, automatically creates their initial household, and issues JWT tokens."""
    tokens = await AuthService.register(db, data)
    _set_refresh_cookie(response, tokens.refresh_token)
    return tokens


@router.post(
    "/login",
    response_model=TokenResponse,
    dependencies=[Depends(rate_limit("login", 10, 300))],
)
async def login(
    data: UserLogin,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Authenticates a user with email and password and returns JWT tokens."""
    tokens = await AuthService.login(db, data)
    _set_refresh_cookie(response, tokens.refresh_token)
    return tokens


@router.post(
    "/refresh",
    response_model=TokenResponse,
    dependencies=[Depends(rate_limit("refresh", 60, 300))],
)
async def refresh_token(
    request: Request,
    response: Response,
    data: Optional[TokenRefresh] = None,
    db: AsyncSession = Depends(get_db),
):
    """Renews an access token using the HttpOnly refresh cookie (or an explicit token for API clients)."""
    token_value = (data.refresh_token if data and data.refresh_token else None) or request.cookies.get(
        REFRESH_COOKIE_NAME
    )
    if not token_value:
        from fastapi import HTTPException

        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sesión no iniciada.")
    tokens = await AuthService.refresh_token(db, token_value)
    _set_refresh_cookie(response, tokens.refresh_token)
    return tokens


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout():
    """Cierra la sesión eliminando la cookie del refresh token."""
    resp = Response(status_code=status.HTTP_204_NO_CONTENT)
    _clear_refresh_cookie(resp)
    return resp


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


@router.get("/me/export")
async def export_my_data(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Exporta todos los datos personales del usuario en JSON (derecho de acceso y portabilidad)."""
    return await AuthService.export_account_data(db, current_user)


@router.post(
    "/me/delete",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(rate_limit("delete_account", 5, 3600))],
)
async def delete_my_account(
    data: AccountDeleteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Elimina definitivamente la cuenta del usuario y sus datos (derecho de supresión). Requiere contraseña."""
    await AuthService.delete_account(db, current_user, data.effective_password)
    resp = Response(status_code=status.HTTP_204_NO_CONTENT)
    _clear_refresh_cookie(resp)
    return resp
