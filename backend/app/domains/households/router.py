import uuid
from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.domains.auth.models import User
from app.domains.households.models import HouseholdMembership
from app.domains.households.permissions import (
    Permission,
    get_current_user,
    require_household_permission,
)
from app.domains.households.schemas import (
    HouseholdCreate,
    HouseholdResponse,
    HouseholdUpdate,
    InvitationCreate,
    InvitationResponse,
    MemberResponse,
    MemberRoleUpdate,
)
from app.domains.households.services import HouseholdService

router = APIRouter(prefix="/households", tags=["Households"])


@router.get("", response_model=List[HouseholdResponse])
async def list_households(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lists all households the current authenticated user belongs to."""
    return await HouseholdService.list_user_households(db, current_user.id)


@router.post("", response_model=HouseholdResponse, status_code=status.HTTP_201_CREATED)
async def create_household(
    data: HouseholdCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Creates a new household and assigns the current user as OWNER."""
    return await HouseholdService.create_household(db, current_user.id, data)


@router.get("/{household_id}", response_model=HouseholdResponse)
async def get_household(
    household_id: uuid.UUID,
    membership: HouseholdMembership = Depends(require_household_permission(Permission.VIEW_ANALYTICS)),
    db: AsyncSession = Depends(get_db),
):
    """Gets details of a household if the current user is a member."""
    return await HouseholdService.get_household(db, household_id, membership.role)


@router.patch("/{household_id}", response_model=HouseholdResponse)
async def update_household(
    household_id: uuid.UUID,
    data: HouseholdUpdate,
    membership: HouseholdMembership = Depends(require_household_permission(Permission.MANAGE_HOUSEHOLD)),
    db: AsyncSession = Depends(get_db),
):
    """Updates household settings (name, currency). Requires MANAGE_HOUSEHOLD (OWNER role)."""
    return await HouseholdService.update_household(db, household_id, data, membership.role)


@router.get("/{household_id}/members", response_model=List[MemberResponse])
async def list_members(
    household_id: uuid.UUID,
    membership: HouseholdMembership = Depends(require_household_permission(Permission.VIEW_ANALYTICS)),
    db: AsyncSession = Depends(get_db),
):
    """Lists all active members of the household."""
    return await HouseholdService.list_members(db, household_id)


@router.patch("/{household_id}/members/{user_id}", response_model=MemberResponse)
async def update_member_role(
    household_id: uuid.UUID,
    user_id: uuid.UUID,
    data: MemberRoleUpdate,
    membership: HouseholdMembership = Depends(require_household_permission(Permission.MANAGE_MEMBERS)),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Updates a member's role (ADMIN or MEMBER). Requires MANAGE_MEMBERS permission."""
    return await HouseholdService.update_member_role(db, household_id, user_id, data, current_user.id)


@router.delete("/{household_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    household_id: uuid.UUID,
    user_id: uuid.UUID,
    membership: HouseholdMembership = Depends(require_household_permission(Permission.MANAGE_MEMBERS)),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Removes a member from the household. Requires MANAGE_MEMBERS permission."""
    await HouseholdService.remove_member(db, household_id, user_id, current_user.id)


@router.post("/{household_id}/invitations", response_model=InvitationResponse, status_code=status.HTTP_201_CREATED)
async def invite_member(
    household_id: uuid.UUID,
    data: InvitationCreate,
    membership: HouseholdMembership = Depends(require_household_permission(Permission.MANAGE_MEMBERS)),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generates an invitation token for a new member. Requires MANAGE_MEMBERS permission."""
    return await HouseholdService.create_invitation(db, household_id, current_user.id, data)


@router.post("/invitations/{token}/accept", response_model=HouseholdResponse)
async def accept_invitation(
    token: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Accepts a pending invitation and joins the household."""
    return await HouseholdService.accept_invitation(db, token, current_user)

