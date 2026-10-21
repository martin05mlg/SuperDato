import enum
import uuid
from typing import Callable, List, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import decode_token
from app.domains.auth.models import User
from app.domains.households.models import HouseholdMembership

security_bearer = HTTPBearer(auto_error=True)


class Role(str, enum.Enum):
    OWNER = "OWNER"
    ADMIN = "ADMIN"
    MEMBER = "MEMBER"


class Permission(str, enum.Enum):
    VIEW_RECEIPTS = "VIEW_RECEIPTS"
    UPLOAD_RECEIPTS = "UPLOAD_RECEIPTS"
    EDIT_RECEIPTS = "EDIT_RECEIPTS"
    DELETE_RECEIPTS = "DELETE_RECEIPTS"
    VIEW_ANALYTICS = "VIEW_ANALYTICS"
    MANAGE_MEMBERS = "MANAGE_MEMBERS"
    MANAGE_HOUSEHOLD = "MANAGE_HOUSEHOLD"
    CONNECT_INTEGRATIONS = "CONNECT_INTEGRATIONS"


# Default Role-Permission Mapping Matrix
ROLE_PERMISSIONS = {
    Role.OWNER: {
        Permission.VIEW_RECEIPTS,
        Permission.UPLOAD_RECEIPTS,
        Permission.EDIT_RECEIPTS,
        Permission.DELETE_RECEIPTS,
        Permission.VIEW_ANALYTICS,
        Permission.MANAGE_MEMBERS,
        Permission.MANAGE_HOUSEHOLD,
        Permission.CONNECT_INTEGRATIONS,
    },
    Role.ADMIN: {
        Permission.VIEW_RECEIPTS,
        Permission.UPLOAD_RECEIPTS,
        Permission.EDIT_RECEIPTS,
        Permission.DELETE_RECEIPTS,
        Permission.VIEW_ANALYTICS,
        Permission.MANAGE_MEMBERS,
        Permission.CONNECT_INTEGRATIONS,
    },
    Role.MEMBER: {
        Permission.VIEW_RECEIPTS,
        Permission.UPLOAD_RECEIPTS,
        Permission.VIEW_ANALYTICS,
    },
}


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Validates the JWT access token and returns the current user."""
    token = credentials.credentials
    payload = decode_token(token)

    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de acceso inválido o caducado.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token malformado.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_uuid = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ID de usuario inválido en token.",
        )

    result = await db.execute(select(User).where(User.id == user_uuid))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cuenta de usuario inactiva o deshabilitada.",
        )

    return user


def require_household_permission(required_permission: Permission):
    """Dependency factory checking that the current user belongs to the household and has the required permission."""
    async def permission_checker(
        household_id: uuid.UUID,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> HouseholdMembership:
        # Query membership
        query = select(HouseholdMembership).where(
            HouseholdMembership.household_id == household_id,
            HouseholdMembership.user_id == current_user.id,
        )
        result = await db.execute(query)
        membership = result.scalar_one_or_none()

        if not membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acceso denegado: No perteneces a este hogar.",
            )

        role = Role(membership.role)
        allowed_permissions = ROLE_PERMISSIONS.get(role, set())

        if required_permission not in allowed_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permiso insuficiente: La acción requiere '{required_permission.value}'.",
            )

        return membership

    return permission_checker

