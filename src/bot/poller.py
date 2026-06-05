"""
poller.py — Bot long-polling loop

Continuously requests updates from the Bale API and dispatches them
to the handlers as background tasks.
"""

import asyncio
import logging
from src.bot.client import client
from src.bot.handlers import handle_update

logger = logging.getLogger(__name__)

async def start_polling():
    """Start the infinite long-polling loop.

    This function blocks forever (until cancelled). It fetches updates using
    an offset. When updates arrive, it updates the offset to avoid receiving
    the same messages again, and spawns a new async task for each update
    so that slow handlers do not block the polling loop.
    """
    offset = None
    logger.info("Bot started polling...")
    while True:
        try:
            # Blocks for up to 30s waiting for new messages
            updates = await client.get_updates(offset=offset, timeout=30)
            
            for update in updates:
                # Update offset to the highest seen update_id + 1
                offset = update["update_id"] + 1
                
                # Run handler as a background task to not block the next poll iteration
                asyncio.create_task(handle_update(update))
                
        except asyncio.CancelledError:
            # Graceful shutdown when the main event loop stops
            break
        except Exception as e:
            logger.error(f"Polling error: {e}")
            # Sleep briefly on error to prevent CPU spinning/API spamming
            await asyncio.sleep(5)
