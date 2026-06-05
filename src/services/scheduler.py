"""
scheduler.py — Periodic price-fetch scheduler

Wraps APScheduler's AsyncIOScheduler to run fetch_and_store() on a
configurable interval. The first fetch also runs immediately on startup
so the bot has fresh data before the first interval elapses.
"""

import asyncio
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from src.config import settings
from src.services.price_service import fetch_and_store

logger = logging.getLogger(__name__)


async def start_scheduler():
    """Start the background price-fetch scheduler.

    Creates an APScheduler AsyncIOScheduler, registers fetch_and_store()
    as an interval job (period = FETCH_INTERVAL_MINUTES), starts it, then
    runs one immediate fetch so the bot has data from the very first second.

    The scheduler runs in the same asyncio event loop as the rest of the app
    and does not require a separate thread.
    """
    scheduler = AsyncIOScheduler()
    # Add the periodic job; it will first fire after FETCH_INTERVAL_MINUTES
    scheduler.add_job(fetch_and_store, 'interval', minutes=settings.FETCH_INTERVAL_MINUTES)
    scheduler.start()
    logger.info(f"Scheduler started. Fetching every {settings.FETCH_INTERVAL_MINUTES} minutes.")

    # Immediate fetch on startup so users don't see stale/empty data
    await fetch_and_store()
