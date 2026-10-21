from typing import List
from fastapi import APIRouter, File, HTTPException, UploadFile, status
from app.domains.receipts.schemas import ReceiptDetailResponse, ReceiptResponse
from app.domains.receipts.services import ReceiptService

router = APIRouter(prefix="/receipts", tags=["Receipts"])


@router.get("", response_model=List[ReceiptResponse])
async def list_receipts():
    """Returns the list of all imported Mercadona digital receipts."""
    return ReceiptService.get_all_receipts()


@router.get("/{receipt_id}", response_model=ReceiptDetailResponse)
async def get_receipt_detail(receipt_id: str):
    """Returns detailed information of a receipt including all line items and tax breakdown."""
    receipt = ReceiptService.get_receipt_by_id(receipt_id)
    if not receipt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket con ID '{receipt_id}' no encontrado.",
        )
    return receipt


@router.post("/upload", response_model=ReceiptDetailResponse, status_code=status.HTTP_201_CREATED)
async def upload_receipt_pdf(file: UploadFile = File(...)):
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
        receipt = ReceiptService.process_and_save_pdf(stream, file.filename)
        return receipt
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Error al extraer los datos del ticket PDF: {str(e)}",
        )

