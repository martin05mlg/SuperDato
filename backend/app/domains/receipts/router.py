from typing import List
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.domains.receipts.schemas import (
    ReceiptDetailResponse,
    ReceiptLineResponse,
    ReceiptLineUpdate,
    ReceiptResponse,
    ReceiptUpdate,
)
from app.domains.receipts.services import ReceiptService

router = APIRouter(prefix="/receipts", tags=["Receipts"])


@router.get("", response_model=List[ReceiptResponse])
async def list_receipts(db: AsyncSession = Depends(get_db)):
    """Returns the list of all imported Mercadona digital receipts."""
    return await ReceiptService.get_all_receipts_from_db(db)


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
async def upload_receipt_pdf(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    """Uploads a Mercadona PDF ticket, extracts its contents deterministically, and saves it."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se admiten archivos en formato PDF de tickets de Mercadona.",
        )

    try:
        content = await file.read()
        import io
        stream = io.BytesIO(content)
        receipt = await ReceiptService.process_and_save_pdf(stream, file.filename, db=db)
        return receipt
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Error al extraer los datos del ticket PDF: {str(e)}",
        )
