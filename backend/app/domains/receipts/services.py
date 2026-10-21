import glob
import os
import uuid
from typing import Dict, List, Optional
from app.domains.receipts.extractor.pdf_parser import PDFReceiptExtractor

# In-memory storage cache synchronized with parsing engine for instant testing
_RECEIPTS_STORE: Dict[str, Dict] = {}


def load_initial_samples_if_empty():
    """Scans samples/ directory and parses real Mercadona tickets if store is empty."""
    if len(_RECEIPTS_STORE) > 0:
        return

    sample_files = glob.glob("samples/*.pdf")
    # If not found in samples/, look in ../samples/
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
    def get_all_receipts() -> List[Dict]:
        load_initial_samples_if_empty()
        # Return sorted by purchase_datetime descending
        receipts = list(_RECEIPTS_STORE.values())
        receipts.sort(key=lambda r: r.get("purchase_datetime", ""), reverse=True)
        return receipts

    @staticmethod
    def get_receipt_by_id(receipt_id: str) -> Optional[Dict]:
        load_initial_samples_if_empty()
        return _RECEIPTS_STORE.get(receipt_id)

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
        # Group by purchase_date
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

