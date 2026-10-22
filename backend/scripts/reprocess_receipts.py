import asyncio
import io
import sqlite3
import uuid
from decimal import Decimal
from pypdf import PdfReader
from sqlalchemy import select, func

from app.core.database import async_session_maker
import app.domains.auth.models  # noqa: F401
import app.domains.households.models  # noqa: F401
import app.domains.integrations.models  # noqa: F401
from app.domains.catalog.services import CatalogService
from app.domains.integrations.client import GoogleOAuthClient
from app.domains.receipts.extractor.pdf_parser import PDFReceiptExtractor
from app.domains.receipts.models import Receipt, ReceiptLine, ReceiptTaxLine


async def main():
    conn = sqlite3.connect("superdato_dev.db")
    c = conn.cursor()
    c.execute("SELECT encrypted_tokens, household_id FROM google_account_connections LIMIT 1")
    row = c.fetchone()
    if not row:
        print("No Google connection found")
        return
    enc, h_id_str = row
    token, _ = await GoogleOAuthClient.refresh_access_token(enc)
    messages = await GoogleOAuthClient.search_mercadona_messages(token)
    print(f"Gmail messages found: {len(messages)}")

    async with async_session_maker() as db:
        stmt = select(Receipt)
        res = await db.execute(stmt)
        all_receipts = {r.invoice_number: r for r in res.scalars().all()}

        updated_count = 0
        for m in messages:
            pdf_bytes = await GoogleOAuthClient.fetch_pdf_attachment(token, m["id"])
            if not pdf_bytes:
                continue
            reader = PdfReader(io.BytesIO(pdf_bytes))
            text = "\n".join([page.extract_text() or "" for page in reader.pages])
            extracted = PDFReceiptExtractor.extract_from_text(text)
            inv_no = extracted.get("invoice_number")

            if inv_no in all_receipts:
                receipt = all_receipts[inv_no]
                line_cnt_stmt = select(func.count(ReceiptLine.id)).where(ReceiptLine.receipt_id == receipt.id)
                cnt = (await db.execute(line_cnt_stmt)).scalar_one()

                lines_to_add = extracted.get("lines", [])
                if cnt == 0 and lines_to_add:
                    print(f"Reprocessing {inv_no}: adding {len(lines_to_add)} lines...")
                    receipt.raw_text = text
                    receipt.status = extracted.get("status", "PROCESSED")
                    receipt.extraction_warnings = extracted.get("extraction_warnings", [])

                    # Replace any existing tax lines with full tax breakdown
                    del_tax = select(ReceiptTaxLine).where(ReceiptTaxLine.receipt_id == receipt.id)
                    existing_taxes = (await db.execute(del_tax)).scalars().all()
                    for et in existing_taxes:
                        await db.delete(et)

                    for tax in extracted.get("tax_lines", []):
                        tax_line = ReceiptTaxLine(
                            id=uuid.uuid4(),
                            receipt_id=receipt.id,
                            tax_rate_percent=tax.get("tax_rate_percent", 0.0),
                            taxable_base=tax.get("taxable_base", 0.0),
                            tax_amount=tax.get("tax_amount", 0.0),
                            total_with_tax=tax.get("total_with_tax", 0.0),
                        )
                        db.add(tax_line)

                    for item in lines_to_add:
                        product = await CatalogService.get_or_create_product_for_line(
                            db=db,
                            raw_description=item.get("raw_description", ""),
                            category_hint=item.get("category_name"),
                            unit_of_measure=item.get("unit_of_measure", "ud"),
                            weight_in_kg=item.get("weight_in_kg"),
                        )

                        line_id = uuid.uuid4()
                        line = ReceiptLine(
                            id=line_id,
                            receipt_id=receipt.id,
                            line_order=item.get("line_order", 1),
                            raw_description=item.get("raw_description", ""),
                            product_id=product.id,
                            quantity=item.get("quantity", 1.0),
                            unit_of_measure=item.get("unit_of_measure", "ud"),
                            unit_price=item.get("unit_price", 0.0),
                            discount_amount=item.get("discount_amount", 0.0),
                            line_total=item.get("line_total", 0.0),
                            is_weighed_item=item.get("is_weighed_item", False),
                            weight_in_kg=item.get("weight_in_kg"),
                            validation_status="VALID",
                            is_manual_override=False,
                        )
                        db.add(line)
                        await db.flush()

                        await CatalogService.record_price_observation(
                            db=db,
                            household_id=receipt.household_id,
                            product_id=product.id,
                            receipt_line_id=line.id,
                            observed_at=receipt.purchase_datetime,
                            observed_date=receipt.purchase_date,
                            unit_price=item.get("unit_price", 0.0),
                            store_code=receipt.store_code,
                        )
                    updated_count += 1
        await db.commit()
        print(f"Done! Successfully reprocessed {updated_count} receipts.")


if __name__ == "__main__":
    asyncio.run(main())
