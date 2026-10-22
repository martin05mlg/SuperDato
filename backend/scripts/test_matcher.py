import asyncio
from sqlalchemy import select

from app.core.database import async_session_maker
from app.domains.catalog.matcher import MercadonaMatcherService, token_similarity
from app.domains.catalog.models import Product


async def main():
    q = "Aceite Oliva 0,4"
    c = "Aceite de oliva 0,4º Hacendado"
    print(f'Similarity between "{q}" and "{c}":', token_similarity(q, c))

    async with async_session_maker() as db:
        stmt = select(Product).where(
            Product.canonical_name.like("%aceite%") | Product.canonical_name.like("%sal%")
        )
        res = await db.execute(stmt)
        prods = res.scalars().all()
        print(f"Testing on {len(prods)} products:")
        for p in prods:
            matches = await MercadonaMatcherService.find_matches_for_product(db, p)
            if matches:
                top, score = matches[0]
                print(f" - Ticket: {p.canonical_name} -> Online: {top.display_name} ({score}) [img: {top.thumbnail_url[:35]}...]")
            else:
                print(f" - Ticket: {p.canonical_name} -> Sin coincidencia >= 0.50")


if __name__ == "__main__":
    asyncio.run(main())
