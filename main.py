"""
Main entry point for the Currency Rate Bale Bot.
Initializes the database, starts the FastAPI admin server,
runs the price-fetching scheduler, and starts the bot poller.
"""

import asyncio
import logging
import uvicorn
from src.config import settings
from src.database.connection import init_db
from src.services.scheduler import start_scheduler
from src.bot.poller import start_polling

# Setup logging with format and level from configuration
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """
    Main asynchronous loop setup.
    Starts all concurrent services: Database, Admin Dashboard, Scheduler, and Bot Poller.
    """
    logger.info("Starting Currency Rate Bale Bot...")
    
    # 1. Initialize SQLite Database schema and tables
    await init_db()
    
    # 2. Start background tasks
    # Run FastAPI via uvicorn in an asyncio task for the admin dashboard
    from src.admin.app import app
    config = uvicorn.Config(app=app, host="0.0.0.0", port=settings.ADMIN_PORT, log_level="info")
    server = uvicorn.Server(config)
    admin_task = asyncio.create_task(server.serve())
    
    # Start the scheduled task that fetches currency/gold prices periodically
    await start_scheduler()
    
    # Start bot long-polling loop to receive and handle updates from Bale
    bot_task = asyncio.create_task(start_polling())
    
    # Keep the main event loop running by awaiting these infinite tasks
    await asyncio.gather(admin_task, bot_task)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")

