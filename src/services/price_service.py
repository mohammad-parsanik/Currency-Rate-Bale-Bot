"""
price_service.py — Orchestrates the price-fetch cycle

Runs TGJU and Nerkh.io fetches concurrently using asyncio.gather, then
persists the results to the database. Fetch errors are caught individually
so a failure from one source does not prevent the other source from being saved.
"""

import asyncio
import logging
from src.services import tgju_fetcher
from src.services import nerkh_fetcher
from src.database.repositories import PriceRepository, ErrorRepository

logger = logging.getLogger(__name__)


async def fetch_and_store():
    """Run a full price-fetch cycle: fetch from all sources, store to DB.

    Both fetchers are launched as concurrent asyncio tasks. If one fails
    (network error, HTTP error, parse error), its exception is caught and
    logged to the fetch_errors table; the other source is still saved.

    This function is called:
      - Once immediately on startup (from scheduler.py).
      - On the configured interval (default: every 5 minutes).
      - On demand via the admin panel's "Manual Update" button (POST /api/scrape).
    """
    logger.info("Starting price fetch cycle...")

    # Run both fetchers concurrently; return_exceptions=True prevents one
    # failure from cancelling the other task.
    tgju_task  = asyncio.create_task(tgju_fetcher.fetch())
    nerkh_task = asyncio.create_task(nerkh_fetcher.fetch())
    results = await asyncio.gather(tgju_task, nerkh_task, return_exceptions=True)

    tgju_result  = results[0]
    nerkh_result = results[1]

    # --- TGJU ---
    if isinstance(tgju_result, Exception):
        logger.error(f"TGJU fetch failed: {tgju_result}")
        await ErrorRepository.log_error("tgju", str(tgju_result), type(tgju_result).__name__)
    else:
        logger.info(f"Successfully fetched {len(tgju_result)} prices from TGJU.")
        await PriceRepository.upsert_many(tgju_result)

    # --- Nerkh.io ---
    if isinstance(nerkh_result, Exception):
        logger.error(f"Nerkh.io fetch failed: {nerkh_result}")
        await ErrorRepository.log_error("nerkh", str(nerkh_result), type(nerkh_result).__name__)
    else:
        # nerkh_result is an empty list when no token is configured — that's fine
        if nerkh_result:
            logger.info(f"Successfully fetched {len(nerkh_result)} prices from Nerkh.")
            await PriceRepository.upsert_many(nerkh_result)

    logger.info("Price fetch cycle complete.")
