import io
import logging
from typing import Any, Dict, List, Optional
import uuid
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.domains.auth.models import User
from app.domains.households.models import HouseholdMembership
from app.domains.households.permissions import Role, get_current_user
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

logger = logging.getLogger(__name__)

MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB maximum upload size

router = APIRouter(prefix="/receipts", tags=["Receipts"])


async def check_receipt_access(
    receipt: Dict[str, Any],
    current_user: User,
    db: AsyncSession,
) -> None:
    """Verifies that the current user has access to view the receipt (IDOR protection)."""
    if current_user.is_superuser:
        return

    hh_id_str = receipt.get("household_id")
    if hh_id_str:
        try:
            hh_id = uuid.UUID(hh_id_str)
            res = await db.execute(
                select(HouseholdMembership).where(
                    HouseholdMembership.household_id == hh_id,
                    HouseholdMembership.user_id == current_user.id,
                )
            )
            if res.scalar_one_or_none():
                return
        except ValueError:
            pass

    uploaded_by = receipt.get("uploaded_by_user_id") or receipt.get("imported_by_user_id")
    if uploaded_by and str(uploaded_by) == str(current_user.id):
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Acceso denegado: No perteneces al hogar propietario de este ticket.",
    )


async def check_receipt_edit_permission(
    receipt: Dict[str, Any],
    current_user: User,
    db: AsyncSession,
) -> None:
    """Verifies that the current user has OWNER or ADMIN role to modify the receipt."""
    if current_user.is_superuser:
        return

    hh_id_str = receipt.get("household_id")
    if hh_id_str:
        try:
            hh_id = uuid.UUID(hh_id_str)
            res = await db.execute(
                select(HouseholdMembership).where(
                    HouseholdMembership.household_id == hh_id,
                    HouseholdMembership.user_id == current_user.id,
                )
            )
            m = res.scalar_one_or_none()
            if m and Role(m.role) in [Role.OWNER, Role.ADMIN]:
                return
        except ValueError:
            pass

    uploaded_by = receipt.get("uploaded_by_user_id") or receipt.get("imported_by_user_id")
    if uploaded_by and str(uploaded_by) == str(current_user.id):
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Permiso denegado: Se requiere rol de Propietario o Administrador para modificar este ticket.",
    )


@router.get("", response_model=List[ReceiptResponse])
async def list_receipts(
    household_id: Optional[uuid.UUID] = Query(None, description="Filtrar por ID de hogar"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns the list of Mercadona digital receipts scoped to the selected household or user."""
    if household_id and not current_user.is_superuser:
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
async def get_receipt_detail(
    receipt_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns detailed information of a receipt including all line items and tax breakdown."""
    receipt = await ReceiptService.get_receipt_detail(db, receipt_id)
    if not receipt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket con ID '{receipt_id}' no encontrado.",
        )
    await check_receipt_access(receipt, current_user, db)
    return receipt


@router.patch("/{receipt_id}", response_model=ReceiptDetailResponse)
async def update_receipt(
    receipt_id: str,
    data: ReceiptUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Manually updates receipt metadata (store, date, total amount).
    Marks the receipt with is_manual_override=True to protect user edits.
    """
    receipt = await ReceiptService.get_receipt_detail(db, receipt_id)
    if not receipt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket con ID '{receipt_id}' no encontrado.",
        )
    await check_receipt_edit_permission(receipt, current_user, db)

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
    current_user: User = Depends(get_current_user),
):
    """
    Manually edits a receipt line (quantity, price, description, product link).
    Marks is_manual_override=True and validation_status='MANUALLY_EDITED'.
    """
    receipt = await ReceiptService.get_receipt_detail(db, receipt_id)
    if not receipt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket con ID '{receipt_id}' no encontrado.",
        )
    await check_receipt_edit_permission(receipt, current_user, db)

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
    filename = file.filename or "ticket.pdf"
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se admiten archivos en formato PDF de tickets de Mercadona.",
        )

    # Enforce strict maximum upload size (10 MB) via chunked read to prevent DoS/OOM
    content_chunks = []
    total_size = 0
    chunk_size = 65536
    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        total_size += len(chunk)
        if total_size > MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail="El archivo excede el tamaño máximo permitido (10 MB).",
            )
        content_chunks.append(chunk)

    content = b"".join(content_chunks)

    # Validate PDF magic header
    if not content.startswith(b"%PDF-"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo proporcionado no es un documento PDF válido.",
        )

    target_hh_uuid: Optional[uuid.UUID] = None
    if household_id and household_id.strip():
        try:
            target_hh_uuid = uuid.UUID(household_id.strip())
        except ValueError:
            target_hh_uuid = None

    if target_hh_uuid and not current_user.is_superuser:
        res = await db.execute(
            select(HouseholdMembership).where(
                HouseholdMembership.household_id == target_hh_uuid,
                HouseholdMembership.user_id == current_user.id,
            )
        )
        if not res.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acceso denegado: No perteneces al hogar indicado para la subida.",
            )

    try:
        stream = io.BytesIO(content)
        receipt = await ReceiptService.process_and_save_pdf(
            stream,
            filename,
            db=db,
            household_id=target_hh_uuid,
            user_id=current_user.id,
        )
        return receipt
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error al procesar ticket PDF '%s': %s", filename, str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="No se pudo procesar el ticket PDF. Verifica que sea un ticket digital oficial de Mercadona no dañado.",
        )
