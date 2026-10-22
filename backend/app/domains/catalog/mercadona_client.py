import asyncio
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.catalog.models import MercadonaOnlineProduct

logger = logging.getLogger(__name__)

MERCADONA_API_BASE = "https://tienda.mercadona.es/api"

# Default warehouse codes mapped by postal code province prefixes
POSTAL_CODE_WAREHOUSE_MAP: Dict[str, str] = {
    "50": "zar1",  # Zaragoza
    "28": "mad1",  # Madrid
    "08": "bcn1",  # Barcelona
    "46": "vlc1",  # Valencia
    "41": "sev1",  # Sevilla
    "03": "alc1",  # Alicante
    "29": "agp1",  # Málaga
    "30": "mur1",  # Murcia
    "48": "bio1",  # Bilbao / Vizcaya
    "36": "vgo1",  # Vigo / Pontevedra
    "15": "lcg1",  # A Coruña
    "33": "ovd1",  # Asturias
    "39": "sdr1",  # Santander / Cantabria
}

DEFAULT_WAREHOUSE = "zar1"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "es-ES,es;q=0.9",
}


class MercadonaStorefrontClient:
    """Asynchronous client to interact with Mercadona's online storefront public endpoints."""

    @staticmethod
    def resolve_warehouse_code(postal_code: Optional[str]) -> str:
        """Resolves postal code to internal Mercadona warehouse identifier (e.g. 50007 -> zar1)."""
        if not postal_code or len(postal_code.strip()) < 2:
            return DEFAULT_WAREHOUSE
        prefix = postal_code.strip()[:2]
        return POSTAL_CODE_WAREHOUSE_MAP.get(prefix, DEFAULT_WAREHOUSE)

    @staticmethod
    def extract_brand(display_name: str) -> Optional[str]:
        """Detects Mercadona private labels or common brands in product title."""
        name_lower = display_name.lower()
        if "hacendado" in name_lower:
            return "Hacendado"
        elif "deliplus" in name_lower:
            return "Deliplus"
        elif "bosque verde" in name_lower:
            return "Bosque Verde"
        elif "compy" in name_lower:
            return "Compy"
        elif "baby seco" in name_lower or "deliplus baby" in name_lower:
            return "Deliplus"
        return None

    @classmethod
    async def get_categories_tree(cls, warehouse_code: str = DEFAULT_WAREHOUSE) -> List[Dict[str, Any]]:
        """Fetches root categories and nested subcategories from Mercadona API."""
        url = f"{MERCADONA_API_BASE}/categories/?lang=es&wh={warehouse_code}"
        async with httpx.AsyncClient(headers=HEADERS, timeout=15.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
            return data.get("results", [])

    @classmethod
    async def get_subcategory_products(
        cls, subcategory_id: int, warehouse_code: str = DEFAULT_WAREHOUSE
    ) -> List[Dict[str, Any]]:
        """Fetches product items inside a specific leaf subcategory."""
        url = f"{MERCADONA_API_BASE}/categories/{subcategory_id}/?lang=es&wh={warehouse_code}"
        async with httpx.AsyncClient(headers=HEADERS, timeout=15.0) as client:
            resp = await client.get(url)
            if resp.status_code == 404:
                return []
            resp.raise_for_status()
            data = resp.json()

            products: List[Dict[str, Any]] = []
            for sub in data.get("categories", []):
                for prod in sub.get("products", []):
                    # Attach category hierarchy context
                    prod["_category_name"] = data.get("name")
                    prod["_sub_category_name"] = sub.get("name")
                    products.append(prod)
            return products

    @classmethod
    async def fetch_and_save_product_by_id(
        cls,
        db: AsyncSession,
        product_id: str,
        warehouse_code: str = DEFAULT_WAREHOUSE,
    ) -> Optional[MercadonaOnlineProduct]:
        """Fetches a specific product from Mercadona API by its ID, checking fallback warehouses if needed."""
        clean_id = str(product_id).strip()
        warehouses_to_try = [warehouse_code]
        for fallback in ["mad1", "vlc1", "bcn1", "sev1", "alc1"]:
            if fallback not in warehouses_to_try:
                warehouses_to_try.append(fallback)

        p = None
        used_wh = warehouse_code

        async with httpx.AsyncClient(headers=HEADERS, timeout=10.0) as client:
            for wh in warehouses_to_try:
                url = f"{MERCADONA_API_BASE}/products/{clean_id}/?lang=es&wh={wh}"
                try:
                    resp = await client.get(url)
                    if resp.status_code == 200:
                        p = resp.json()
                        used_wh = wh
                        break
                except Exception as e:
                    logger.debug(f"Warehouse {wh} failed for product {clean_id}: {e}")
                    continue

        if not p:
            return None

        try:
            display_name = p.get("display_name", "").strip()
            if not display_name:
                return None

            price_info = p.get("price_instructions", {})
            unit_p = None
            if price_info.get("unit_price"):
                try:
                    unit_p = float(price_info.get("unit_price"))
                except Exception:
                    unit_p = None

            ref_p = None
            if price_info.get("reference_price"):
                try:
                    ref_p = float(price_info.get("reference_price"))
                except Exception:
                    ref_p = None

            brand = cls.extract_brand(display_name)
            now = datetime.now(timezone.utc)

            existing_stmt = select(MercadonaOnlineProduct).where(MercadonaOnlineProduct.id == clean_id)
            res = await db.execute(existing_stmt)
            existing = res.scalar_one_or_none()

            share_url = p.get("share_url") or f"https://tienda.mercadona.es/product/{clean_id}"

            if existing:
                existing.display_name = display_name
                existing.slug = p.get("slug", "")
                existing.brand = brand
                existing.packaging = p.get("packaging")
                existing.thumbnail_url = p.get("thumbnail", "")
                existing.share_url = share_url
                existing.unit_price = unit_p
                existing.reference_price = ref_p
                existing.reference_format = price_info.get("reference_format")
                existing.warehouse_code = used_wh
                existing.raw_payload = p
                existing.last_synced_at = now
                m_prod = existing
            else:
                m_prod = MercadonaOnlineProduct(
                    id=clean_id,
                    display_name=display_name,
                    slug=p.get("slug", ""),
                    brand=brand,
                    packaging=p.get("packaging"),
                    thumbnail_url=p.get("thumbnail", ""),
                    share_url=share_url,
                    unit_price=unit_p,
                    reference_price=ref_p,
                    reference_format=price_info.get("reference_format"),
                    category_path="Búsqueda Directa",
                    warehouse_code=used_wh,
                    raw_payload=p,
                    last_synced_at=now,
                )
                db.add(m_prod)

            await db.commit()
            await db.refresh(m_prod)
            return m_prod
        except Exception as e:
            logger.warning(f"Error saving product {clean_id} directly from Mercadona: {e}")
            return None

    @classmethod
    async def sync_catalog_to_db(
        cls,
        db: AsyncSession,
        warehouse_code: str = DEFAULT_WAREHOUSE,
        limit_subcategories: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Downloads categories and products, upserting them into mercadona_online_products table."""
        categories_tree = await cls.get_categories_tree(warehouse_code)
        subcat_ids: List[Dict[str, Any]] = []

        for cat in categories_tree:
            cat_name = cat.get("name", "")
            for sub in cat.get("categories", []):
                subcat_ids.append({
                    "id": sub.get("id"),
                    "name": sub.get("name"),
                    "parent_name": cat_name,
                })

        if limit_subcategories:
            subcat_ids = subcat_ids[:limit_subcategories]

        total_upserted = 0
        total_subcats = len(subcat_ids)
        now = datetime.now(timezone.utc)

        for idx, sub_info in enumerate(subcat_ids):
            sub_id = sub_info["id"]
            if not sub_id:
                continue

            try:
                raw_products = await cls.get_subcategory_products(sub_id, warehouse_code)
                seen_in_subcat = set()
                for p in raw_products:
                    prod_id = str(p.get("id"))
                    display_name = p.get("display_name", "").strip()
                    if not prod_id or not display_name:
                        continue
                    if prod_id in seen_in_subcat:
                        continue
                    seen_in_subcat.add(prod_id)

                    price_info = p.get("price_instructions", {})
                    unit_p = None
                    if price_info.get("unit_price"):
                        try:
                            unit_p = float(price_info.get("unit_price"))
                        except Exception:
                            unit_p = None

                    ref_p = None
                    if price_info.get("reference_price"):
                        try:
                            ref_p = float(price_info.get("reference_price"))
                        except Exception:
                            ref_p = None

                    category_path = f"{sub_info['parent_name']} > {sub_info['name']}"
                    brand = cls.extract_brand(display_name)

                    # Upsert into DB
                    existing_stmt = select(MercadonaOnlineProduct).where(MercadonaOnlineProduct.id == prod_id)
                    res = await db.execute(existing_stmt)
                    existing = res.scalar_one_or_none()

                    if existing:
                        existing.display_name = display_name
                        existing.slug = p.get("slug", "")
                        existing.brand = brand
                        existing.packaging = p.get("packaging")
                        existing.thumbnail_url = p.get("thumbnail", "")
                        existing.share_url = p.get("share_url")
                        existing.unit_price = unit_p
                        existing.reference_price = ref_p
                        existing.reference_format = price_info.get("reference_format")
                        existing.category_path = category_path
                        existing.warehouse_code = warehouse_code
                        existing.raw_payload = p
                        existing.last_synced_at = now
                    else:
                        m_prod = MercadonaOnlineProduct(
                            id=prod_id,
                            display_name=display_name,
                            slug=p.get("slug", ""),
                            brand=brand,
                            packaging=p.get("packaging"),
                            thumbnail_url=p.get("thumbnail", ""),
                            share_url=p.get("share_url"),
                            unit_price=unit_p,
                            reference_price=ref_p,
                            reference_format=price_info.get("reference_format"),
                            category_path=category_path,
                            warehouse_code=warehouse_code,
                            raw_payload=p,
                            last_synced_at=now,
                        )
                        db.add(m_prod)
                    total_upserted += 1

                await db.commit()
                # Friendly pause to be polite with Mercadona CDN/API
                await asyncio.sleep(0.02)

            except Exception as e:
                logger.warning(f"Error syncing subcategory {sub_id} ({sub_info['name']}): {e}")
                continue

        return {
            "warehouse_code": warehouse_code,
            "subcategories_processed": total_subcats,
            "products_upserted": total_upserted,
            "synced_at": now.isoformat(),
        }
