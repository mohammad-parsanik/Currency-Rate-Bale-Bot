import asyncio
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from src.config import settings
from src.services.price_service import fetch_and_store

logger = logging.getLogger(__name__)

async def start_scheduler():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(fetch_and_store, 'interval', minutes=settings.FETCH_INTERVAL_MINUTES)
    scheduler.start()
    logger.info(f"Scheduler started. Fetching every {settings.FETCH_INTERVAL_MINUTES} minutes.")
    
    # Run once immediately
    await fetch_and_store()
