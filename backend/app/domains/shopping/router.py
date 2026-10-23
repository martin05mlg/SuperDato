import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.domains.auth.models import User
from app.domains.households.models import HouseholdMembership
from app.domains.households.permissions import get_current_user
from app.domains.shopping.schemas import (
    ShoppingItemCreate,
    ShoppingItemResponse,
    ShoppingItemUpdate,
    ShoppingListSummaryResponse,
    ShoppingSuggestionItem,
)
from app.domains.shopping.services import ShoppingService

router = APIRouter(prefix="/shopping", tags=["Shopping List"])


async def verify_household_access(
    household_id: uuid.UUID,
    current_user: User,
    db: AsyncSession,
) -> None:
    """Verifies that the authenticated user belongs to the requested household."""
    if not current_user.is_superuser:
        res = await db.execute(
            select(HouseholdMembership).where(
                HouseholdMembership.household_id == household_id,
                HouseholdMembership.user_id == current_user.id,
            )
        )
        if not res.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acceso denegado: No perteneces a este hogar.",
            )


@router.get("/items", response_model=ShoppingListSummaryResponse)
async def get_shopping_list(
    household_id: uuid.UUID = Query(..., description="ID del hogar"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Returns the current shopping list with items, checked state, and cost estimates."""
    await verify_household_access(household_id, current_user, db)
    return await ShoppingService.get_shopping_list(db, household_id)


@router.post("/items", response_model=ShoppingItemResponse, status_code=status.HTTP_201_CREATED)
async def add_shopping_item(
    data: ShoppingItemCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Adds a new item to the household's shopping list."""
    await verify_household_access(data.household_id, current_user, db)
    return await ShoppingService.add_item(db, data, current_user.id)


@router.patch("/items/{item_id}", response_model=ShoppingItemResponse)
async def update_shopping_item(
    item_id: uuid.UUID,
    data: ShoppingItemUpdate,
    household_id: uuid.UUID = Query(..., description="ID del hogar"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Updates an item (e.g. check/uncheck in supermarket mode, change quantity or price)."""
    await verify_household_access(household_id, current_user, db)
    return await ShoppingService.update_item(db, item_id, household_id, data)


@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_shopping_item(
    item_id: uuid.UUID,
    household_id: uuid.UUID = Query(..., description="ID del hogar"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Deletes an item from the shopping list."""
    await verify_household_access(household_id, current_user, db)
    await ShoppingService.delete_item(db, item_id, household_id)


@router.post("/clear-checked")
async def clear_checked_items(
    household_id: uuid.UUID = Query(..., description="ID del hogar"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Removes all checked items from the shopping list."""
    await verify_household_access(household_id, current_user, db)
    count = await ShoppingService.clear_checked(db, household_id)
    return {"cleared_count": count}


@router.get("/suggestions", response_model=List[ShoppingSuggestionItem])
async def get_shopping_suggestions(
    household_id: uuid.UUID = Query(..., description="ID del hogar"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Returns predictive replenishment suggestions based on past purchase cycles."""
    await verify_household_access(household_id, current_user, db)
    return await ShoppingService.get_replenishment_suggestions(db, household_id)

