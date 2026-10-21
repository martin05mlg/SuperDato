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
        _RECEIPTS_STORE[str(receipt_id)] = extracted_copy

        return receipt

    @staticmethod
    def get_all_receipts() -> List[Dict]:
        load_initial_samples_if_empty()
        receipts = list(_RECEIPTS_STORE.values())
        receipts.sort(key=lambda r: r.get("purchase_datetime", ""), reverse=True)
        return receipts

    @staticmethod
    def get_receipt_by_id(receipt_id: str) -> Optional[Dict]:
        load_initial_samples_if_empty()
        return _RECEIPTS_STORE.get(receipt_id)

    @staticmethod
    def update_receipt(receipt_id: str, updates: Dict[str, Any]) -> Optional[Dict]:
        """Manually updates receipt metadata, setting is_manual_override=True."""
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
    def update_receipt_line(receipt_id: str, line_id: str, updates: Dict[str, Any]) -> Optional[Dict]:
        """Manually updates a specific receipt line, protecting it from auto-overwrite."""
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
    def process_and_save_pdf(stream, filename: str) -> Dict:
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
        return extracted

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
