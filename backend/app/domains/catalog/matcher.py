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
    "aguasal": "agua sal",
    "preve": "prevencion",
    "semidesn": "semidesnatada",
    "semi": "semidesnatada",
    "desnat": "desnatada",
    "solom": "solomillo",
    "pech": "pechuga",
    "pechuguita": "pechuga",
    "asa": "asada",
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
    "q": "queso",
    "ques": "queso",
    "formaggi": "quesos",
    "fontabil": "agua mineral",
    "f/l": "finas lonchas",
    "troc": "troceado",
    "coc": "cocido",
    "s/azuca": "sin azucar",
    "s/azucar": "sin azucar",
    "orig": "original",
    "salm": "salmon",
    "tortill": "tortilla",
    "patat": "patatas",
    "crem": "crema",
    "champi": "champinon",
    "desca": "descafeinado",
    "int": "integral",
    "r/anchoa": "rellenas anchoa",
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


def stem_token(word: str) -> str:
    """Stems simple Spanish plurals."""
    if len(word) > 4:
        if word.endswith("es"):
            return word[:-2]
        elif word.endswith("s"):
            return word[:-1]
    return word


def token_similarity(query_text: str, candidate_text: str) -> float:
    """Calculates token overlap and fuzzy similarity ratio between 0.0 and 1.0."""
    norm_q = normalize_string(query_text)
    norm_c = normalize_string(candidate_text)

    if not norm_q or not norm_c:
        return 0.0

    raw_q_tokens = [w for w in norm_q.split() if w]
    raw_c_tokens = [w for w in norm_c.split() if w]

    if not raw_q_tokens:
        return 0.0

    q_tokens = {stem_token(t) for t in raw_q_tokens}
    c_tokens = {stem_token(t) for t in raw_c_tokens}

    # Token overlap: percentage of ticket tokens that exist in online title
    intersection = q_tokens.intersection(c_tokens)
    if not intersection:
        # Fast exit: If there are zero common stemmed tokens, skip expensive SequenceMatcher
        return 0.0

    overlap_ratio = len(intersection) / len(q_tokens)

    # String similarity using SequenceMatcher
    seq_ratio = SequenceMatcher(None, norm_q, norm_c).ratio()

    # If all ticket tokens appear in candidate, grant a high confidence base
    if overlap_ratio >= 0.8:
        score = 0.6 * overlap_ratio + 0.4 * seq_ratio + 0.2
    elif overlap_ratio >= 0.5:
        score = 0.5 * overlap_ratio + 0.5 * seq_ratio + 0.1
    else:
        score = 0.5 * overlap_ratio + 0.5 * seq_ratio

    return min(1.0, round(score, 3))


class MercadonaMatcherService:
    """Service to match local products with Mercadona Online storefront items."""
    _CACHED_ONLINE_POOL: Optional[List[Tuple[MercadonaOnlineProduct, str, set]]] = None

    @classmethod
    def invalidate_cache(cls):
        """Invalidates in-memory candidate cache (e.g. after a catalog sync)."""
        cls._CACHED_ONLINE_POOL = None

    @classmethod
    async def get_cached_pool(
        cls, db: AsyncSession, candidate_pool: Optional[List[MercadonaOnlineProduct]] = None
    ) -> List[Tuple[MercadonaOnlineProduct, str, set]]:
        """Returns pre-tokenized pool of MercadonaOnlineProduct items."""
        if candidate_pool is not None:
            pool = []
            for item in candidate_pool:
                norm_c = normalize_string(item.display_name)
                c_tokens = {stem_token(t) for t in norm_c.split() if t}
                pool.append((item, norm_c, c_tokens))
            return pool

        if cls._CACHED_ONLINE_POOL is not None:
            return cls._CACHED_ONLINE_POOL

        stmt = select(MercadonaOnlineProduct)
        res = await db.execute(stmt)
        items = res.scalars().all()
        pool = []
        for item in items:
            norm_c = normalize_string(item.display_name)
            c_tokens = {stem_token(t) for t in norm_c.split() if t}
            pool.append((item, norm_c, c_tokens))
        cls._CACHED_ONLINE_POOL = pool
        return pool

    @classmethod
    async def find_matches_for_product(
        cls,
        db: AsyncSession,
        product: Product,
        reference_price: Optional[float] = None,
        candidate_pool: Optional[List[MercadonaOnlineProduct]] = None,
        limit: int = 5,
    ) -> List[Tuple[MercadonaOnlineProduct, float]]:
        """Finds best matching candidates from mercadona_online_products for a given product."""
        pool = await cls.get_cached_pool(db, candidate_pool)
        if not pool:
            return []

        # Gather all candidate names from product (canonical name + aliases)
        names_to_test = [product.canonical_name]
        if "aliases" in product.__dict__ and product.aliases:
            for a in product.aliases:
                if a.raw_name_normalized and a.raw_name_normalized not in names_to_test:
                    names_to_test.append(a.raw_name_normalized)

        # Pre-normalize queries once
        prepped_queries = []
        for name in names_to_test:
            norm_q = normalize_string(name)
            raw_q = [w for w in norm_q.split() if w]
            q_tokens = {stem_token(t) for t in raw_q}
            if q_tokens:
                prepped_queries.append((norm_q, q_tokens))

        if not prepped_queries:
            return []

        scored_candidates: List[Tuple[MercadonaOnlineProduct, float]] = []

        for online_item, norm_c, c_tokens in pool:
            best_base = 0.0
            for norm_q, q_tokens in prepped_queries:
                inter = q_tokens.intersection(c_tokens)
                if not inter:
                    continue
                overlap_ratio = len(inter) / len(q_tokens)
                seq_ratio = SequenceMatcher(None, norm_q, norm_c).ratio()
                if overlap_ratio >= 0.8:
                    s = 0.6 * overlap_ratio + 0.4 * seq_ratio + 0.2
                elif overlap_ratio >= 0.5:
                    s = 0.5 * overlap_ratio + 0.5 * seq_ratio + 0.1
                else:
                    s = 0.5 * overlap_ratio + 0.5 * seq_ratio
                if s > best_base:
                    best_base = min(1.0, round(s, 3))

            if best_base < 0.38:
                continue

            score = best_base

            # Price similarity weighting: if recent ticket price matches web unit price
            if reference_price and online_item.unit_price and reference_price > 0 and online_item.unit_price > 0:
                p_ref = float(reference_price)
                p_on = float(online_item.unit_price)
                diff_eur = abs(p_ref - p_on)
                diff_pct = diff_eur / max(p_ref, p_on)

                if diff_eur <= 0.02:
                    score = min(1.0, score + 0.22)
                elif diff_eur <= 0.10 or diff_pct <= 0.05:
                    score = min(1.0, score + 0.14)
                elif diff_pct <= 0.12:
                    score = min(1.0, score + 0.08)
                elif diff_pct > 0.40:
                    score = max(0.0, score - 0.25)
                elif diff_pct > 0.65:
                    score = max(0.0, score - 0.45)

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
        from sqlalchemy.orm import selectinload

        # Pre-load candidate pool once for efficiency
        online_stmt = select(MercadonaOnlineProduct)
        online_res = await db.execute(online_stmt)
        all_online = online_res.scalars().all()

        stmt = (
            select(Product)
            .where(Product.enrichment_status != "MANUALLY_CONFIRMED")
            .options(selectinload(Product.aliases), selectinload(Product.price_observations))
        )
        res = await db.execute(stmt)
        products = res.scalars().all()

        auto_enriched_count = 0
        suggestions_count = 0

        for prod in products:
            obs_list = sorted(prod.price_observations, key=lambda o: o.observed_at)
            latest_price = float(obs_list[-1].unit_price) if obs_list else None

            candidates = await cls.find_matches_for_product(
                db,
                prod,
                reference_price=latest_price,
                candidate_pool=all_online,
                limit=3,
            )
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
            elif best_score >= 0.55:
                suggestions_count += 1

        await db.commit()

        return {
            "total_products_checked": len(products),
            "auto_enriched_count": auto_enriched_count,
            "pending_suggestions_count": suggestions_count,
            "threshold_used": auto_threshold,
        }

