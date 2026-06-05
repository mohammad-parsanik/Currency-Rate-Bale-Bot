"""
Main entry point for the Currency Rate Bale Bot.

Initializes the database, starts the FastAPI admin server,
runs the price-fetching scheduler, and starts the bot poller.
All services run concurrently in a single asyncio event loop.
"""

import asyncio
import logging
import uvicorn
from src.config import settings
from src.database.connection import init_db
from src.services.scheduler import start_scheduler
from src.bot.poller import start_polling

# Setup root logging with format and level from configuration (.env)
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Main asynchronous application loop.
    
    Sets up all concurrent services:
    1. Database schema initialization
    2. FastAPI Admin Dashboard (via uvicorn)
    3. Background Price Fetcher (via APScheduler)
    4. Bot Update Listener (Long-Polling)
    """
    logger.info("Starting Currency Rate Bale Bot...")
    
    # 1. Initialize SQLite Database schema and tables
    # Must happen first so other services don't crash on missing tables.
    await init_db()
    
    # 2. Start Admin Dashboard (FastAPI)
    # We run uvicorn programmatically inside an asyncio task rather than via CLI,
    # so it shares the same event loop as the bot poller.
    from src.admin.app import app
    config = uvicorn.Config(app=app, host="0.0.0.0", port=settings.ADMIN_PORT, log_level="info")
    server = uvicorn.Server(config)
    admin_task = asyncio.create_task(server.serve())
    
    # 3. Start the scheduled task that fetches currency/gold prices periodically
    # This also does an immediate initial fetch so the DB is populated right away.
    await start_scheduler()
    
    # 4. Start bot long-polling loop to receive and handle updates from Bale
    bot_task = asyncio.create_task(start_polling())
    
    # Keep the main event loop running by awaiting these infinite tasks.
    # If either crashes, gather will propagate the exception and crash the app.
    await asyncio.gather(admin_task, bot_task)

if __name__ == "__main__":
    try:
        # Run the main coroutine; handles event loop creation and teardown
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")
