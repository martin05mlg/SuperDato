#!/usr/bin/env python3
"""
Script de mantenimiento para reparar líneas de ticket y observaciones de precio corruptas
donde números en la descripción del producto (ej: Alcohol 96) fueron erróneamente tomados
como precio unitario.
"""
import asyncio
import logging
import sys

from app.core.bootstrap import heal_inconsistent_receipt_line_prices
from app.core.database import async_session_maker

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("fix_corrupted_prices")


async def main():
    logger.info("Iniciando escaneo y corrección de precios corruptos en tickets...")
    async with async_session_maker() as session:
        repaired = await heal_inconsistent_receipt_line_prices(session)
        if repaired > 0:
            logger.info(f"✅ Se han reparado con éxito {repaired} líneas y observaciones de precio.")
        else:
            logger.info("✨ No se encontraron líneas con precios inconsistentes. Todo está en orden.")


if __name__ == "__main__":
    asyncio.run(main())

