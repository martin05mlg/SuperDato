import glob
import io
import os
import uuid
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import async_session_maker
from app.domains.catalog.models import Category, PriceObservation, Product, ProductAlias
from app.domains.catalog.services import CatalogService
from app.domains.households.models import Household
from app.domains.receipts.extractor.pdf_parser import PDFReceiptExtractor
from app.domains.receipts.models import Receipt, ReceiptLine, ReceiptTaxLine

# In-memory storage cache synchronized with parsing engine for instant testing & responses
_RECEIPTS_STORE: Dict[str, Dict] = {}


def load_initial_samples_if_empty():
    """Scans samples/ directory and parses real Mercadona tickets into in-memory store if empty."""
    if len(_RECEIPTS_STORE) > 0:
        return

    sample_files = glob.glob("samples/*.pdf")
    if not sample_files:
        sample_files = glob.glob("../samples/*.pdf")

    for pdf_path in sample_files:
        try:
            with open(pdf_path, "rb") as f:
                extracted = PDFReceiptExtractor.extract_from_stream(f)
                receipt_id = str(uuid.uuid4())
                extracted["id"] = receipt_id
                extracted["household_id"] = "default-household"
                extracted["created_at"] = extracted.get("purchase_datetime", "2026-10-15T15:43:00")
                extracted["lines_count"] = len(extracted.get("lines", []))

                # Assign IDs to lines and tax lines
                for line in extracted.get("lines", []):
                    line["id"] = str(uuid.uuid4())
                for tax in extracted.get("tax_lines", []):
                    tax["id"] = str(uuid.uuid4())

                _RECEIPTS_STORE[receipt_id] = extracted
        except Exception as e:
            print(f"Error loading sample {pdf_path}: {e}")


class ReceiptService:
    @staticmethod
    async def sync_sample_receipts_to_db(db: AsyncSession):
        """Idempotently seeds database with sample receipts, normalized products, and price observations."""
        stmt = select(func.count(Receipt.id))
        count = (await db.execute(stmt)).scalar_one()
        if count > 0:
            return

        # Ensure default categories
        await CatalogService.ensure_system_categories(db)

        # Ensure default household
        hh_stmt = select(Household).limit(1)
        hh_res = await db.execute(hh_stmt)
        household = hh_res.scalar_one_or_none()
        if not household:
            household = Household(
                id=uuid.uuid4(),
                name="Casa Principal",
                currency="EUR",
                created_by_user_id=uuid.uuid4(),
            )
            db.add(household)
            await db.flush()

        sample_files = glob.glob("samples/*.pdf")
        if not sample_files:
            sample_files = glob.glob("../samples/*.pdf")

        for pdf_path in sample_files:
            try:
                with open(pdf_path, "rb") as f:
                    extracted = PDFReceiptExtractor.extract_from_stream(f)

                    # Parse datetime
                    dt_str = extracted.get("purchase_datetime")
                    if dt_str:
                        try:
                            dt = datetime.fromisoformat(dt_str)
                            if dt.tzinfo is None:
                                dt = dt.replace(tzinfo=timezone.utc)
                        except Exception:
                            dt = datetime.now(timezone.utc)
                    else:
                        dt = datetime.now(timezone.utc)

                    d_str = extracted.get("purchase_date")
                    if d_str:
                        try:
                            d = date.fromisoformat(d_str)
                        except Exception:
                            d = dt.date()
                    else:
                        d = dt.date()

                    receipt_id = uuid.uuid4()
                    receipt = Receipt(
                        id=receipt_id,
                        household_id=household.id,
                        company_name=extracted.get("company_name", "MERCADONA, S.A."),
                        company_cif=extracted.get("company_cif", "A-46103834"),
                        store_address=extracted.get("store_address"),
                        store_postal_code=extracted.get("store_postal_code"),
                        store_city=extracted.get("store_city"),
                        store_code=extracted.get("store_code"),
                        pos_register=extracted.get("pos_register"),
                        invoice_number=extracted.get("invoice_number", "UNKNOWN"),
                        purchase_datetime=dt,
                        purchase_date=d,
                        purchase_time=extracted.get("purchase_time", "12:00"),
                        total_amount=extracted.get("total_amount", 0.0),
                        discounts_total=extracted.get("discounts_total", 0.0),
                        payment_method=extracted.get("payment_method"),
                        card_last_four=extracted.get("card_last_four"),
                        deduplication_hash=extracted.get("deduplication_hash", str(uuid.uuid4())),
                        status="PROCESSED",
                        extraction_warnings=extracted.get("extraction_warnings", []),
                        is_manual_override=False,
                    )
                    db.add(receipt)
                    await db.flush()

                    # Add tax lines
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

                    # Add receipt lines and link normalized products and price observations
                    for item in extracted.get("lines", []):
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

                        # Price observation
                        price_kg_l = item.get("unit_price") if item.get("is_weighed_item") else None
                        await CatalogService.record_price_observation(
                            db=db,
                            household_id=household.id,
                            product_id=product.id,
                            receipt_line_id=line.id,
                            observed_at=dt,
                            observed_date=d,
                            unit_price=item.get("unit_price", 0.0),
                            price_per_kg_or_l=price_kg_l,
                            store_code=extracted.get("store_code"),
                        )

                    await db.commit()
            except Exception as e:
                print(f"Error syncing {pdf_path} to DB: {e}")

    @staticmethod
    async def save_extracted_receipt_to_db(
        db: AsyncSession,
        extracted: Dict[str, Any],
        household_id: uuid.UUID,
        import_job_id: Optional[uuid.UUID] = None,
    ) -> Optional[Receipt]:
        """Saves an extracted receipt to database, preventing duplicates, linking catalog and price observations."""
        dedup_hash = extracted.get("deduplication_hash")
        if not dedup_hash:
            return None

        # Check deduplication
        existing_stmt = select(Receipt).where(Receipt.deduplication_hash == dedup_hash)
        res_existing = await db.execute(existing_stmt)
        if res_existing.scalar_one_or_none():
            return None

        # Parse datetime
        dt_str = extracted.get("purchase_datetime")
        if dt_str:
            try:
                dt = datetime.fromisoformat(dt_str)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
            except Exception:
                dt = datetime.now(timezone.utc)
        else:
            dt = datetime.now(timezone.utc)

        d_str = extracted.get("purchase_date")
        if d_str:
            try:
                d = date.fromisoformat(d_str)
            except Exception:
                d = dt.date()
        else:
            d = dt.date()

        receipt_id = uuid.uuid4()
        receipt = Receipt(
            id=receipt_id,
            household_id=household_id,
            import_job_id=import_job_id,
            company_name=extracted.get("company_name", "MERCADONA, S.A."),
            company_cif=extracted.get("company_cif", "A-46103834"),
            store_address=extracted.get("store_address"),
            store_postal_code=extracted.get("store_postal_code"),
            store_city=extracted.get("store_city"),
            store_code=extracted.get("store_code"),
            pos_register=extracted.get("pos_register"),
            invoice_number=extracted.get("invoice_number", "UNKNOWN"),
            purchase_datetime=dt,
            purchase_date=d,
            purchase_time=extracted.get("purchase_time", "12:00"),
            total_amount=extracted.get("total_amount", 0.0),
            discounts_total=extracted.get("discounts_total", 0.0),
            payment_method=extracted.get("payment_method"),
            card_last_four=extracted.get("card_last_four"),
            deduplication_hash=dedup_hash,
            status="PROCESSED",
            extraction_warnings=extracted.get("extraction_warnings", []),
            raw_text=extracted.get("raw_text"),
            is_manual_override=False,
        )
        db.add(receipt)
        await db.flush()

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

        for item in extracted.get("lines", []):
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

            price_kg_l = item.get("unit_price") if item.get("is_weighed_item") else None
            await CatalogService.record_price_observation(
                db=db,
                household_id=household_id,
                product_id=product.id,
                receipt_line_id=line.id,
                observed_at=dt,
                observed_date=d,
                unit_price=item.get("unit_price", 0.0),
                price_per_kg_or_l=price_kg_l,
                store_code=extracted.get("store_code"),
            )

        await db.commit()

        # Update in-memory cache
        extracted_copy = dict(extracted)
        extracted_copy["id"] = str(receipt_id)
        extracted_copy["household_id"] = str(household_id)
        extracted_copy["created_at"] = dt.isoformat()
        extracted_copy["lines_count"] = len(extracted.get("lines", []))
        for l in extracted_copy.get("lines", []):
            if "id" not in l:
                l["id"] = str(uuid.uuid4())
        for t in extracted_copy.get("tax_lines", []):
            if "id" not in t:
                t["id"] = str(uuid.uuid4())
        _RECEIPTS_STORE[str(receipt_id)] = extracted_copy

        return receipt

    @staticmethod
    def get_all_receipts() -> List[Dict]:
        load_initial_samples_if_empty()
        receipts = list(_RECEIPTS_STORE.values())
        receipts.sort(key=lambda r: r.get("purchase_datetime", ""), reverse=True)
        return receipts

    @staticmethod
    async def get_all_receipts_from_db(db: AsyncSession) -> List[Dict]:
        """Queries all receipts from database with line counts, falling back to samples if empty."""
        stmt = (
            select(Receipt)
            .options(selectinload(Receipt.lines))
            .order_by(Receipt.purchase_datetime.desc())
        )
        res = await db.execute(stmt)
        receipts = res.scalars().all()
        if not receipts:
            await ReceiptService.sync_sample_receipts_to_db(db)
            res = await db.execute(stmt)
            receipts = res.scalars().all()

        if not receipts:
            return ReceiptService.get_all_receipts()

        result = []
        for r in receipts:
            result.append({
                "id": str(r.id),
                "household_id": str(r.household_id),
                "company_name": r.company_name,
                "company_cif": r.company_cif,
                "store_address": r.store_address,
                "store_city": r.store_city,
                "store_postal_code": r.store_postal_code,
                "invoice_number": r.invoice_number,
                "store_code": r.store_code,
                "purchase_datetime": r.purchase_datetime.isoformat() if r.purchase_datetime else "",
                "purchase_date": r.purchase_date.isoformat() if r.purchase_date else "",
                "total_amount": float(r.total_amount),
                "payment_method": r.payment_method,
                "card_last_four": r.card_last_four,
                "status": r.status,
                "extraction_warnings": r.extraction_warnings or [],
                "is_manual_override": r.is_manual_override,
                "lines_count": len(r.lines),
                "created_at": r.created_at.isoformat() if r.created_at else (r.purchase_datetime.isoformat() if r.purchase_datetime else ""),
            })
        return result

    @staticmethod
    def get_receipt_by_id(receipt_id: str) -> Optional[Dict]:
        load_initial_samples_if_empty()
        receipt = _RECEIPTS_STORE.get(receipt_id)
        if receipt:
            for l in receipt.get("lines", []):
                if "id" not in l:
                    l["id"] = str(uuid.uuid4())
            for t in receipt.get("tax_lines", []):
                if "id" not in t:
                    t["id"] = str(uuid.uuid4())
        return receipt

    @staticmethod
    async def get_receipt_detail(db: AsyncSession, receipt_id: str) -> Optional[Dict]:
        """Loads complete receipt detail with lines, canonical product names, categories, and tax lines."""
        try:
            r_uuid = uuid.UUID(receipt_id)
        except ValueError:
            r_uuid = None

        if r_uuid:
            stmt = (
                select(Receipt)
                .options(
                    selectinload(Receipt.lines).selectinload(ReceiptLine.product).selectinload(Product.category),
                    selectinload(Receipt.tax_lines),
                )
                .where(Receipt.id == r_uuid)
            )
            res = await db.execute(stmt)
            receipt = res.scalar_one_or_none()
            if receipt:
                lines = []
                for l in receipt.lines:
                    prod_name = l.product.canonical_name if l.product else l.raw_description
                    cat_name = l.product.category.name if (l.product and l.product.category) else "Otros"
                    lines.append({
                        "id": str(l.id),
                        "line_order": l.line_order,
                        "raw_description": l.raw_description,
                        "product_id": str(l.product_id) if l.product_id else None,
                        "product_name": prod_name,
                        "category_name": cat_name,
                        "quantity": float(l.quantity),
                        "unit_of_measure": l.unit_of_measure,
                        "unit_price": float(l.unit_price),
                        "discount_amount": float(l.discount_amount),
                        "line_total": float(l.line_total),
                        "is_weighed_item": l.is_weighed_item,
                        "weight_in_kg": float(l.weight_in_kg) if l.weight_in_kg is not None else None,
                        "validation_status": l.validation_status,
                        "is_manual_override": l.is_manual_override,
                        "image_url": l.product.image_url if l.product else None,
                        "brand": l.product.brand if l.product else None,
                        "enriched_name": l.product.enriched_name if l.product else None,
                        "packaging": l.product.packaging if l.product else None,
                    })

                taxes = []
                for t in receipt.tax_lines:
                    taxes.append({
                        "id": str(t.id),
                        "tax_rate_percent": float(t.tax_rate_percent),
                        "taxable_base": float(t.taxable_base),
                        "tax_amount": float(t.tax_amount),
                        "total_with_tax": float(t.total_with_tax),
                    })

                return {
                    "id": str(receipt.id),
                    "household_id": str(receipt.household_id),
                    "company_name": receipt.company_name,
                    "company_cif": receipt.company_cif,
                    "store_address": receipt.store_address,
                    "store_city": receipt.store_city,
                    "store_postal_code": receipt.store_postal_code,
                    "invoice_number": receipt.invoice_number,
                    "store_code": receipt.store_code,
                    "purchase_datetime": receipt.purchase_datetime.isoformat() if receipt.purchase_datetime else "",
                    "purchase_date": receipt.purchase_date.isoformat() if receipt.purchase_date else "",
                    "total_amount": float(receipt.total_amount),
                    "payment_method": receipt.payment_method,
                    "card_last_four": receipt.card_last_four,
                    "status": receipt.status,
                    "extraction_warnings": receipt.extraction_warnings or [],
                    "is_manual_override": receipt.is_manual_override,
                    "lines_count": len(lines),
                    "created_at": receipt.created_at.isoformat() if receipt.created_at else (receipt.purchase_datetime.isoformat() if receipt.purchase_datetime else ""),
                    "lines": lines,
                    "tax_lines": taxes,
                }

        # Fallback to in-memory store
        return ReceiptService.get_receipt_by_id(receipt_id)

    @staticmethod
    async def update_receipt_in_db(db: AsyncSession, receipt_id: str, updates: Dict[str, Any]) -> Optional[Dict]:
        """Manually updates receipt metadata in DB, setting is_manual_override=True."""
        try:
            r_uuid = uuid.UUID(receipt_id)
        except ValueError:
            r_uuid = None

        if r_uuid:
            stmt = select(Receipt).where(Receipt.id == r_uuid)
            res = await db.execute(stmt)
            receipt = res.scalar_one_or_none()
            if receipt:
                if "store_address" in updates and updates["store_address"] is not None:
                    receipt.store_address = updates["store_address"]
                if "store_city" in updates and updates["store_city"] is not None:
                    receipt.store_city = updates["store_city"]
                if "store_postal_code" in updates and updates["store_postal_code"] is not None:
                    receipt.store_postal_code = updates["store_postal_code"]
                if "purchase_date" in updates and updates["purchase_date"] is not None:
                    try:
                        receipt.purchase_date = date.fromisoformat(updates["purchase_date"])
                    except Exception:
                        pass
                if "total_amount" in updates and updates["total_amount"] is not None:
                    receipt.total_amount = updates["total_amount"]
                if "payment_method" in updates and updates["payment_method"] is not None:
                    receipt.payment_method = updates["payment_method"]
                if "status" in updates and updates["status"] is not None:
                    receipt.status = updates["status"]

                receipt.is_manual_override = True
                await db.commit()
                return await ReceiptService.get_receipt_detail(db, receipt_id)

        return ReceiptService.update_receipt(receipt_id, updates)

    @staticmethod
    def update_receipt(receipt_id: str, updates: Dict[str, Any]) -> Optional[Dict]:
        """Manually updates receipt metadata in memory, setting is_manual_override=True."""
        load_initial_samples_if_empty()
        receipt = _RECEIPTS_STORE.get(receipt_id)
        if not receipt:
            return None

        for k, v in updates.items():
            if v is not None and k in receipt:
                receipt[k] = v

        receipt["is_manual_override"] = True
        return receipt

    @staticmethod
    async def update_receipt_line_in_db(
        db: AsyncSession,
        receipt_id: str,
        line_id: str,
        updates: Dict[str, Any],
    ) -> Optional[Dict]:
        """Manually updates a specific receipt line in DB, recalculates total and marks overrides."""
        try:
            l_uuid = uuid.UUID(line_id)
            r_uuid = uuid.UUID(receipt_id)
        except ValueError:
            l_uuid = None
            r_uuid = None

        if l_uuid and r_uuid:
            stmt = (
                select(ReceiptLine)
                .options(selectinload(ReceiptLine.product).selectinload(Product.category))
                .where(ReceiptLine.id == l_uuid, ReceiptLine.receipt_id == r_uuid)
            )
            res = await db.execute(stmt)
            line = res.scalar_one_or_none()
            if line:
                if "raw_description" in updates and updates["raw_description"] is not None:
                    line.raw_description = updates["raw_description"]
                if "quantity" in updates and updates["quantity"] is not None:
                    line.quantity = updates["quantity"]
                if "unit_of_measure" in updates and updates["unit_of_measure"] is not None:
                    line.unit_of_measure = updates["unit_of_measure"]
                if "unit_price" in updates and updates["unit_price"] is not None:
                    line.unit_price = updates["unit_price"]
                if "discount_amount" in updates and updates["discount_amount"] is not None:
                    line.discount_amount = updates["discount_amount"]
                if "line_total" in updates and updates["line_total"] is not None:
                    line.line_total = updates["line_total"]

                line.is_manual_override = True
                line.validation_status = "MANUALLY_EDITED"

                # Recalculate receipt total
                r_stmt = select(Receipt).options(selectinload(Receipt.lines)).where(Receipt.id == r_uuid)
                r_res = await db.execute(r_stmt)
                receipt = r_res.scalar_one_or_none()
                if receipt:
                    receipt.is_manual_override = True
                    new_total = sum(float(l.line_total) for l in receipt.lines)
                    receipt.total_amount = round(new_total, 2)

                await db.commit()

                prod_name = line.product.canonical_name if line.product else line.raw_description
                cat_name = line.product.category.name if (line.product and line.product.category) else "Otros"

                return {
                    "id": str(line.id),
                    "line_order": line.line_order,
                    "raw_description": line.raw_description,
                    "product_id": str(line.product_id) if line.product_id else None,
                    "product_name": prod_name,
                    "category_name": cat_name,
                    "quantity": float(line.quantity),
                    "unit_of_measure": line.unit_of_measure,
                    "unit_price": float(line.unit_price),
                    "discount_amount": float(line.discount_amount),
                    "line_total": float(line.line_total),
                    "is_weighed_item": line.is_weighed_item,
                    "weight_in_kg": float(line.weight_in_kg) if line.weight_in_kg is not None else None,
                    "validation_status": line.validation_status,
                    "is_manual_override": line.is_manual_override,
                }

        return ReceiptService.update_receipt_line(receipt_id, line_id, updates)

    @staticmethod
    def update_receipt_line(receipt_id: str, line_id: str, updates: Dict[str, Any]) -> Optional[Dict]:
        """Manually updates a specific receipt line in memory, protecting it from auto-overwrite."""
        load_initial_samples_if_empty()
        receipt = _RECEIPTS_STORE.get(receipt_id)
        if not receipt:
            return None

        target_line = None
        for line in receipt.get("lines", []):
            if str(line.get("id")) == str(line_id):
                target_line = line
                break

        if not target_line:
            return None

        for k, v in updates.items():
            if v is not None:
                target_line[k] = v

        target_line["is_manual_override"] = True
        target_line["validation_status"] = "MANUALLY_EDITED"
        receipt["is_manual_override"] = True

        # Recalculate total amount from lines
        new_total = sum(l.get("line_total", 0.0) for l in receipt.get("lines", []))
        receipt["total_amount"] = round(new_total, 2)

        return target_line

    @staticmethod
    async def process_and_save_pdf(stream, filename: str, db: Optional[AsyncSession] = None) -> Dict:
        extracted = PDFReceiptExtractor.extract_from_stream(stream)
        receipt_id = str(uuid.uuid4())
        extracted["id"] = receipt_id
        extracted["household_id"] = "default-household"
        extracted["created_at"] = extracted.get("purchase_datetime", "2026-10-15T12:00:00")
        extracted["lines_count"] = len(extracted.get("lines", []))

        for line in extracted.get("lines", []):
            line["id"] = str(uuid.uuid4())
        for tax in extracted.get("tax_lines", []):
            tax["id"] = str(uuid.uuid4())

        _RECEIPTS_STORE[receipt_id] = extracted

        if db:
            hh_stmt = select(Household).limit(1)
            hh_res = await db.execute(hh_stmt)
            household = hh_res.scalar_one_or_none()
            if household:
                await ReceiptService.save_extracted_receipt_to_db(
                    db=db,
                    extracted=extracted,
                    household_id=household.id,
                )

        return extracted

    @staticmethod
    async def get_analytics_summary_from_db(db: AsyncSession) -> Dict:
        """Calculates aggregated KPIs directly from database receipts."""
        receipts = await ReceiptService.get_all_receipts_from_db(db)
        if not receipts:
            return ReceiptService.get_analytics_summary()

        total_spend = sum(r["total_amount"] for r in receipts)
        count = len(receipts)
        avg = round(total_spend / count, 2) if count > 0 else 0.0

        sorted_totals = sorted(r["total_amount"] for r in receipts)
        median = sorted_totals[count // 2] if count > 0 else 0.0

        last_date = receipts[0].get("purchase_date") if receipts else None

        return {
            "total_spend": round(total_spend, 2),
            "previous_spend": 0.0,
            "spend_variation_pct": 0.0,
            "receipt_count": count,
            "average_ticket": avg,
            "median_ticket": round(median, 2),
            "last_purchase_date": last_date,
            "last_sync_at": "Sincronizado vía Gmail / PDF",
        }

    @staticmethod
    def get_analytics_summary() -> Dict:
        receipts = ReceiptService.get_all_receipts()
        if not receipts:
            return {
                "total_spend": 0.0,
                "previous_spend": 0.0,
                "spend_variation_pct": 0.0,
                "receipt_count": 0,
                "average_ticket": 0.0,
                "median_ticket": 0.0,
                "last_purchase_date": None,
                "last_sync_at": None,
            }

        total_spend = sum(r["total_amount"] for r in receipts)
        count = len(receipts)
        avg = round(total_spend / count, 2) if count > 0 else 0.0

        sorted_totals = sorted(r["total_amount"] for r in receipts)
        median = sorted_totals[count // 2] if count > 0 else 0.0

        last_date = receipts[0].get("purchase_date") if receipts else None

        return {
            "total_spend": round(total_spend, 2),
            "previous_spend": 0.0,
            "spend_variation_pct": 0.0,
            "receipt_count": count,
            "average_ticket": avg,
            "median_ticket": round(median, 2),
            "last_purchase_date": last_date,
            "last_sync_at": "Sincronizado vía PDF",
        }

    @staticmethod
    async def get_category_distribution_from_db(db: AsyncSession) -> List[Dict]:
        """Calculates spend breakdown grouped by product category from database."""
        stmt = (
            select(ReceiptLine)
            .options(selectinload(ReceiptLine.product).selectinload(Product.category))
        )
        res = await db.execute(stmt)
        lines = res.scalars().all()
        if not lines:
            return ReceiptService.get_category_distribution()

        category_totals: Dict[str, float] = {}
        for line in lines:
            cat = line.product.category.name if (line.product and line.product.category) else "Otros"
            category_totals[cat] = category_totals.get(cat, 0.0) + float(line.line_total)

        total_all = sum(category_totals.values()) or 1.0

        colors = {
            "Frutas y Verduras": "#10B981",
            "Carnicería y Aves": "#EF4444",
            "Pescadería": "#06B6D4",
            "Lácteos y Quesos": "#F59E0B",
            "Platos Preparados": "#8B5CF6",
            "Bebidas": "#3B82F6",
            "Cuidado Personal": "#EC4899",
            "Aperitivos y Snacks": "#F97316",
            "Alimentación General": "#6B7280",
            "Servicios": "#9CA3AF",
            "Otros": "#64748B",
        }

        distribution = []
        for cat, amount in sorted(category_totals.items(), key=lambda x: x[1], reverse=True):
            pct = round((amount / total_all) * 100, 1)
            distribution.append({
                "category_name": cat,
                "color_hex": colors.get(cat, "#10B981"),
                "total_spend": round(amount, 2),
                "percentage": pct,
            })

        return distribution

    @staticmethod
    def get_category_distribution() -> List[Dict]:
        receipts = ReceiptService.get_all_receipts()
        category_totals: Dict[str, float] = {}

        for r in receipts:
            for line in r.get("lines", []):
                cat = line.get("category_name", "Otros")
                category_totals[cat] = category_totals.get(cat, 0.0) + line.get("line_total", 0.0)

        total_all = sum(category_totals.values()) or 1.0

        colors = {
            "Frutas y Verduras": "#10B981",
            "Carnicería y Aves": "#EF4444",
            "Pescadería": "#06B6D4",
            "Lácteos y Quesos": "#F59E0B",
            "Platos Preparados": "#8B5CF6",
            "Bebidas": "#3B82F6",
            "Cuidado Personal": "#EC4899",
            "Aperitivos y Snacks": "#F97316",
            "Alimentación General": "#6B7280",
            "Servicios": "#9CA3AF",
            "Otros": "#64748B",
        }

        distribution = []
        for cat, amount in sorted(category_totals.items(), key=lambda x: x[1], reverse=True):
            pct = round((amount / total_all) * 100, 1)
            distribution.append({
                "category_name": cat,
                "color_hex": colors.get(cat, "#10B981"),
                "total_spend": round(amount, 2),
                "percentage": pct,
            })

        return distribution

    @staticmethod
    async def get_spending_evolution_from_db(db: AsyncSession) -> List[Dict]:
        """Calculates daily spend time series directly from database."""
        receipts = await ReceiptService.get_all_receipts_from_db(db)
        if not receipts:
            return ReceiptService.get_spending_evolution()

        by_date: Dict[str, Dict] = {}
        for r in receipts:
            d = r.get("purchase_date", "")
            if d:
                if d not in by_date:
                    by_date[d] = {"date": d, "total_amount": 0.0, "receipt_count": 0}
                by_date[d]["total_amount"] += r.get("total_amount", 0.0)
                by_date[d]["receipt_count"] += 1

        points = list(by_date.values())
        points.sort(key=lambda p: p["date"])
        for p in points:
            p["total_amount"] = round(p["total_amount"], 2)
        return points

    @staticmethod
    def get_spending_evolution() -> List[Dict]:
        receipts = ReceiptService.get_all_receipts()
        by_date: Dict[str, Dict] = {}
        for r in receipts:
            d = r.get("purchase_date", "")
            if d:
                if d not in by_date:
                    by_date[d] = {"date": d, "total_amount": 0.0, "receipt_count": 0}
                by_date[d]["total_amount"] += r.get("total_amount", 0.0)
                by_date[d]["receipt_count"] += 1

        points = list(by_date.values())
        points.sort(key=lambda p: p["date"])
        for p in points:
            p["total_amount"] = round(p["total_amount"], 2)
        return points
