import io
from typing import Any, Dict, List, Optional
import uuid
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.domains.auth.models import User
from app.domains.households.permissions import get_current_user
from app.domains.receipts.schemas import (
    ReceiptAssignHouseholdRequest,
    ReceiptBulkAssignRequest,
    ReceiptDetailResponse,
    ReceiptLineResponse,
    ReceiptLineUpdate,
    ReceiptResponse,
    ReceiptUpdate,
)
from app.domains.receipts.services import ReceiptService

router = APIRouter(prefix="/receipts", tags=["Receipts"])


@router.get("", response_model=List[ReceiptResponse])
async def list_receipts(
    household_id: Optional[uuid.UUID] = Query(None, description="Filtrar por ID de hogar"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns the list of Mercadona digital receipts scoped to the selected household or user."""
    return await ReceiptService.get_all_receipts_from_db(
        db,
        household_id=household_id,
        user_id=current_user.id if current_user else None,
    )


@router.get("/pending", response_model=List[ReceiptResponse])
async def get_pending_receipts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns all receipts waiting to be assigned to a household for the current user."""
    return await ReceiptService.get_pending_receipts(db, current_user.id)


@router.get("/pending-count")
async def get_pending_count(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns count of unassigned receipts for the current user."""
    count = await ReceiptService.get_pending_count(db, current_user.id)
    return {"count": count}


@router.post("/bulk-assign")
async def bulk_assign_receipts(
    data: ReceiptBulkAssignRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Assigns multiple pending receipts to a target household."""
    try:
        target_household_id = uuid.UUID(data.household_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ID de hogar no válido.",
        )
    return await ReceiptService.bulk_assign_household(
        db, data.receipt_ids, target_household_id, current_user.id
    )


@router.post("/{receipt_id}/assign", response_model=ReceiptDetailResponse)
async def assign_receipt(
    receipt_id: str,
    data: ReceiptAssignHouseholdRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Assigns a pending receipt to a target household."""
    try:
        target_household_id = uuid.UUID(data.household_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ID de hogar no válido.",
        )
    return await ReceiptService.assign_household(
        db, receipt_id, target_household_id, current_user.id
    )


@router.get("/{receipt_id}", response_model=ReceiptDetailResponse)
async def get_receipt_detail(receipt_id: str, db: AsyncSession = Depends(get_db)):
    """Returns detailed information of a receipt including all line items and tax breakdown."""
    receipt = await ReceiptService.get_receipt_detail(db, receipt_id)
    if not receipt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket con ID '{receipt_id}' no encontrado.",
        )
    return receipt


@router.patch("/{receipt_id}", response_model=ReceiptDetailResponse)
async def update_receipt(receipt_id: str, data: ReceiptUpdate, db: AsyncSession = Depends(get_db)):
    """
    Manually updates receipt metadata (store, date, total amount).
    Marks the receipt with is_manual_override=True to protect user edits.
    """
    updated = await ReceiptService.update_receipt_in_db(db, receipt_id, data.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket con ID '{receipt_id}' no encontrado.",
        )
    return updated


@router.patch("/{receipt_id}/lines/{line_id}", response_model=ReceiptLineResponse)
async def update_receipt_line(
    receipt_id: str,
    line_id: str,
    data: ReceiptLineUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    Manually edits a receipt line (quantity, price, description, product link).
    Marks is_manual_override=True and validation_status='MANUALLY_EDITED'.
    """
    updated_line = await ReceiptService.update_receipt_line_in_db(
        db,
        receipt_id,
        line_id,
        data.model_dump(exclude_unset=True),
    )
    if not updated_line:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Línea con ID '{line_id}' en ticket '{receipt_id}' no encontrada.",
        )
    return updated_line


@router.post("/upload", response_model=ReceiptDetailResponse, status_code=status.HTTP_201_CREATED)
async def upload_receipt_pdf(
    file: UploadFile = File(...),
    household_id: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Uploads a Mercadona PDF ticket, extracts its contents deterministically, and saves it."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se admiten archivos en formato PDF de tickets de Mercadona.",
        )

    target_hh_uuid: Optional[uuid.UUID] = None
    if household_id and household_id.strip():
        try:
            target_hh_uuid = uuid.UUID(household_id.strip())
        except ValueError:
            target_hh_uuid = None

    try:
        content = await file.read()
        stream = io.BytesIO(content)
        receipt = await ReceiptService.process_and_save_pdf(
            stream,
            file.filename,
            db=db,
            household_id=target_hh_uuid,
            user_id=current_user.id if current_user else None,
        )
        return receipt
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Error al extraer los datos del ticket PDF: {str(e)}",
        )
