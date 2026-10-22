import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.domains.auth.models import User
from app.domains.households.models import Household, HouseholdInvitation, HouseholdMembership
from app.domains.households.schemas import (
    HouseholdCreate,
    HouseholdResponse,
    HouseholdUpdate,
    InvitationCreate,
    InvitationResponse,
    MemberResponse,
    MemberRoleUpdate,
)


class HouseholdService:
    @staticmethod
    async def list_user_households(db: AsyncSession, user_id: uuid.UUID) -> List[HouseholdResponse]:
        query = (
            select(Household, HouseholdMembership.role)
            .join(HouseholdMembership, Household.id == HouseholdMembership.household_id)
            .where(HouseholdMembership.user_id == user_id)
            .order_by(Household.created_at.desc())
        )
        result = await db.execute(query)
        rows = result.all()

        responses = []
        for household, role in rows:
            responses.append(
                HouseholdResponse(
                    id=household.id,
                    name=household.name,
                    currency=household.currency,
                    role=role,
                    settings=household.settings or {},
                    created_at=household.created_at,
                )
            )
        return responses

    @staticmethod
    async def create_household(db: AsyncSession, user_id: uuid.UUID, data: HouseholdCreate) -> HouseholdResponse:
        household = Household(
            name=data.name.strip(),
            currency=data.currency.upper().strip(),
            created_by_user_id=user_id,
            settings=data.settings or {},
        )
        db.add(household)
        await db.flush()

        membership = HouseholdMembership(
            household_id=household.id,
            user_id=user_id,
            role="OWNER",
        )
        db.add(membership)
        await db.commit()
        await db.refresh(household)

        return HouseholdResponse(
            id=household.id,
            name=household.name,
            currency=household.currency,
            role="OWNER",
            settings=household.settings or {},
            created_at=household.created_at,
        )

    @staticmethod
    async def get_household(db: AsyncSession, household_id: uuid.UUID, role: str) -> HouseholdResponse:
        query = select(Household).where(Household.id == household_id)
        result = await db.execute(query)
        household = result.scalar_one_or_none()
        if not household:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Hogar no encontrado.",
            )
        return HouseholdResponse(
            id=household.id,
            name=household.name,
            currency=household.currency,
            role=role,
            settings=household.settings or {},
            created_at=household.created_at,
        )

    @staticmethod
    async def update_household(
        db: AsyncSession, household_id: uuid.UUID, data: HouseholdUpdate, role: str
    ) -> HouseholdResponse:
        query = select(Household).where(Household.id == household_id)
        result = await db.execute(query)
        household = result.scalar_one_or_none()
        if not household:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hogar no encontrado.")

        if data.name is not None:
            household.name = data.name.strip()
        if data.currency is not None:
            household.currency = data.currency.upper().strip()
        if data.settings is not None:
            current_settings = dict(household.settings or {})
            current_settings.update(data.settings)
            household.settings = current_settings

        await db.commit()
        await db.refresh(household)

        return HouseholdResponse(
            id=household.id,
            name=household.name,
            currency=household.currency,
            role=role,
            settings=household.settings or {},
            created_at=household.created_at,
        )

    @staticmethod
    async def list_members(db: AsyncSession, household_id: uuid.UUID) -> List[MemberResponse]:
        query = (
            select(HouseholdMembership, User)
            .join(User, HouseholdMembership.user_id == User.id)
            .where(HouseholdMembership.household_id == household_id)
            .order_by(HouseholdMembership.joined_at.asc())
        )
        result = await db.execute(query)
        rows = result.all()

        members = []
        for membership, user in rows:
            members.append(
                MemberResponse(
                    id=membership.id,
                    household_id=membership.household_id,
                    user_id=membership.user_id,
                    user_email=user.email,
                    user_name=user.full_name,
                    role=membership.role,
                    joined_at=membership.joined_at,
                )
            )
        return members

    @staticmethod
    async def update_member_role(
        db: AsyncSession,
        household_id: uuid.UUID,
        target_user_id: uuid.UUID,
        data: MemberRoleUpdate,
        current_user_id: uuid.UUID,
    ) -> MemberResponse:
        if target_user_id == current_user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No puedes modificar tu propio rol. Transfiere la propiedad si deseas cambiarla.",
            )

        query = select(HouseholdMembership).where(
            HouseholdMembership.household_id == household_id,
            HouseholdMembership.user_id == target_user_id,
        )
        result = await db.execute(query)
        membership = result.scalar_one_or_none()

        if not membership:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Miembro no encontrado.")

        if membership.role == "OWNER":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se puede cambiar el rol del propietario directamente.",
            )

        membership.role = data.role
        await db.commit()

        # Fetch user details
        user_res = await db.execute(select(User).where(User.id == target_user_id))
        user = user_res.scalar_one()

        return MemberResponse(
            id=membership.id,
            household_id=membership.household_id,
            user_id=membership.user_id,
            user_email=user.email,
            user_name=user.full_name,
            role=membership.role,
            joined_at=membership.joined_at,
        )

    @staticmethod
    async def remove_member(
        db: AsyncSession,
        household_id: uuid.UUID,
        target_user_id: uuid.UUID,
        current_user_id: uuid.UUID,
    ):
        query = select(HouseholdMembership).where(
            HouseholdMembership.household_id == household_id,
            HouseholdMembership.user_id == target_user_id,
        )
        result = await db.execute(query)
        membership = result.scalar_one_or_none()

        if not membership:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Miembro no encontrado.")

        if membership.role == "OWNER":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El propietario no puede ser expulsado del hogar.",
            )

        await db.delete(membership)
        await db.commit()

    @staticmethod
    async def create_invitation(
        db: AsyncSession,
        household_id: uuid.UUID,
        invited_by_user_id: uuid.UUID,
        data: InvitationCreate,
    ) -> InvitationResponse:
        email_clean = data.invited_email.lower().strip()

        # Check if already a member
        user_res = await db.execute(select(User).where(User.email == email_clean))
        existing_user = user_res.scalar_one_or_none()
        if existing_user:
            mem_res = await db.execute(
                select(HouseholdMembership).where(
                    HouseholdMembership.household_id == household_id,
                    HouseholdMembership.user_id == existing_user.id,
                )
            )
            if mem_res.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Este usuario ya es miembro de este hogar.",
                )

        token = secrets.token_urlsafe(32)
        invitation = HouseholdInvitation(
            household_id=household_id,
            invited_email=email_clean,
            role=data.role,
            token_hash=token,
            status="PENDING",
            invited_by_user_id=invited_by_user_id,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        db.add(invitation)
        await db.commit()
        await db.refresh(invitation)

        resp = InvitationResponse.model_validate(invitation)
        resp.invitation_token = token
        return resp

    @staticmethod
    async def accept_invitation(
        db: AsyncSession,
        token: str,
        current_user: User,
    ) -> HouseholdResponse:
        query = select(HouseholdInvitation).where(
            HouseholdInvitation.token_hash == token,
            HouseholdInvitation.status == "PENDING",
        )
        result = await db.execute(query)
        invitation = result.scalar_one_or_none()

        if not invitation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invitación no encontrada o ya utilizada.",
            )

        expires_at = invitation.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if expires_at < datetime.now(timezone.utc):
            invitation.status = "EXPIRED"
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="Esta invitación ha caducado.",
            )

        # Verify email match (or allow user with different email if accepted)
        # Add membership
        membership = HouseholdMembership(
            household_id=invitation.household_id,
            user_id=current_user.id,
            role=invitation.role,
        )
        db.add(membership)
        invitation.status = "ACCEPTED"
        await db.commit()

        # Return household info
        return await HouseholdService.get_household(db, invitation.household_id, invitation.role)

