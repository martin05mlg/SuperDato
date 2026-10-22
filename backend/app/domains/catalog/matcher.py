import re
import unicodedata
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.catalog.models import MercadonaOnlineProduct, Product, PriceObservation

# Abbreviation replacement dictionary for Mercadona TPV labels
ABBREVIATIONS: Dict[str, str] = {
    "deo": "desodorante",
    "aguasal": "agua sal sal",
    "preve": "prevencion",
    "semidesn": "semidesnatada",
    "semi": "semidesnatada",
    "desnat": "desnatada",
    "solom": "solomillo",
    "pech": "pechuga",
    "hamb": "hamburguesa",
    "pipa": "pipas",
    "choc": "chocolate",
    "virg": "virgen",
    "extr": "extra",
    "aceit": "aceite",
    "p-6x1,5l": "pack 6",
    "bande": "bandeja",
    "limon": "limon",
    "atun": "atun",
}

# Stopwords to remove from matching comparison
STOPWORDS = {"de", "del", "la", "el", "los", "las", "y", "en", "con", "sin", "al", "para", "un", "una", "por"}


def normalize_string(text: str) -> str:
    """Removes accents, special symbols, and lowercases the text."""
    if not text:
        return ""
    # Normalize unicode accents
    nfkd = unicodedata.normalize("NFKD", text)
    cleaned = "".join([c for c in nfkd if not unicodedata.combining(c)])
    cleaned = cleaned.lower()
    cleaned = re.sub(r"[^\w\s]", " ", cleaned)
    tokens = [w.strip() for w in cleaned.split() if w.strip()]

    # Expand abbreviations
    expanded = [ABBREVIATIONS.get(t, t) for t in tokens if t not in STOPWORDS]
    return " ".join(expanded)


def token_similarity(query_text: str, candidate_text: str) -> float:
    """Calculates token overlap and fuzzy similarity ratio between 0.0 and 1.0."""
    norm_q = normalize_string(query_text)
    norm_c = normalize_string(candidate_text)

    if not norm_q or not norm_c:
        return 0.0

    q_tokens = set(norm_q.split())
    c_tokens = set(norm_c.split())

    if not q_tokens:
        return 0.0

    # Token overlap: percentage of ticket tokens that exist in online title
    intersection = q_tokens.intersection(c_tokens)
    overlap_ratio = len(intersection) / len(q_tokens)

    # String similarity using SequenceMatcher
    seq_ratio = SequenceMatcher(None, norm_q, norm_c).ratio()

    # If all ticket tokens appear in candidate, grant a high confidence base
    if overlap_ratio >= 0.8:
        score = 0.6 * overlap_ratio + 0.4 * seq_ratio + 0.2
    else:
        score = 0.5 * overlap_ratio + 0.5 * seq_ratio

    return min(1.0, round(score, 3))


class MercadonaMatcherService:
    """Service to match local products with Mercadona Online storefront items."""

    @classmethod
    async def find_matches_for_product(
        cls,
        db: AsyncSession,
        product: Product,
        reference_price: Optional[float] = None,
        limit: int = 5,
    ) -> List[Tuple[MercadonaOnlineProduct, float]]:
        """Finds best matching candidates from mercadona_online_products for a given product."""
        # Query candidate pool
        stmt = select(MercadonaOnlineProduct)
        res = await db.execute(stmt)
        all_online = res.scalars().all()

        if not all_online:
            return []

        scored_candidates: List[Tuple[MercadonaOnlineProduct, float]] = []
        target_name = product.canonical_name

        for online_item in all_online:
            score = token_similarity(target_name, online_item.display_name)

            # Price penalty if price discrepancy is very large
            if reference_price and online_item.unit_price and reference_price > 0 and online_item.unit_price > 0:
                p_ref = float(reference_price)
                p_on = float(online_item.unit_price)
                diff_pct = abs(p_ref - p_on) / max(p_ref, p_on)
                if diff_pct > 0.45:
                    score = max(0.0, score - 0.25)
                elif diff_pct <= 0.15:
                    score = min(1.0, score + 0.05)

            if score >= 0.50:
                scored_candidates.append((online_item, score))

        scored_candidates.sort(key=lambda x: x[1], reverse=True)
        return scored_candidates[:limit]

    @classmethod
    async def enrich_all_household_products(
        cls,
        db: AsyncSession,
        household_id: Optional[str] = None,
        auto_threshold: float = 0.85,
    ) -> Dict[str, Any]:
        """Automatically enriches products that have matching scores >= auto_threshold."""
        stmt = select(Product).where(Product.enrichment_status != "MANUALLY_CONFIRMED")
        res = await db.execute(stmt)
        products = res.scalars().all()

        auto_enriched_count = 0
        suggestions_count = 0

        for prod in products:
            # Get latest price observation for this product if available
            price_stmt = (
                select(PriceObservation.unit_price)
                .where(PriceObservation.product_id == prod.id)
                .order_by(PriceObservation.observed_at.desc())
            )
            price_res = await db.execute(price_stmt)
            latest_price = price_res.scalars().first()

            candidates = await cls.find_matches_for_product(db, prod, reference_price=latest_price, limit=3)
            if not candidates:
                continue

            best_candidate, best_score = candidates[0]

            if best_score >= auto_threshold:
                prod.mercadona_online_id = best_candidate.id
                prod.enriched_name = best_candidate.display_name
                prod.image_url = best_candidate.thumbnail_url
                prod.brand = best_candidate.brand
                prod.packaging = best_candidate.packaging
                prod.mercadona_url = best_candidate.share_url
                prod.enrichment_status = "AUTO"
                prod.enrichment_confidence = best_score
                auto_enriched_count += 1
            elif best_score >= 0.60:
                suggestions_count += 1

        await db.commit()

        return {
            "total_products_checked": len(products),
            "auto_enriched_count": auto_enriched_count,
            "pending_suggestions_count": suggestions_count,
            "threshold_used": auto_threshold,
        }
