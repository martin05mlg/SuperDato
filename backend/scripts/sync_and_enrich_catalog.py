import asyncio
import os
import sys

# Ensure backend directory is in path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import app.domains.auth.models
import app.domains.households.models
import app.domains.receipts.models
from app.core.database import async_session_maker
from app.domains.catalog.mercadona_client import MercadonaStorefrontClient
from app.domains.catalog.matcher import MercadonaMatcherService


async def main():
    async with async_session_maker() as db:
        print("==> 1. Downloading FULL Mercadona Online storefront categories & products for zar1...")
        sync_res = await MercadonaStorefrontClient.sync_catalog_to_db(db, warehouse_code="zar1", limit_subcategories=None)
        print("Sync summary:", sync_res)

        print("\n==> 2. Running fuzzy matching and auto-enrichment for household products...")
        enrich_res = await MercadonaMatcherService.enrich_all_household_products(db, auto_threshold=0.75)
        print("Enrichment summary:", enrich_res)


if __name__ == "__main__":
    asyncio.run(main())
