import asyncio
import logging
from src.bot.client import client
from src.bot.handlers import handle_update

logger = logging.getLogger(__name__)

async def start_polling():
    offset = None
    logger.info("Bot started polling...")
    while True:
        try:
            updates = await client.get_updates(offset=offset, timeout=30)
            for update in updates:
                offset = update["update_id"] + 1
                # Run handler as a background task to not block polling
                asyncio.create_task(handle_update(update))
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Polling error: {e}")
            await asyncio.sleep(5) # Prevent spamming on error
