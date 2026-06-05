"""
client.py — Bale Messenger API client

A lightweight, asynchronous wrapper around the Bale Bot API using aiohttp.
We use raw HTTP requests rather than a heavy library (like python-telegram-bot)
because Bale's API is simple enough and this keeps dependencies minimal.
"""

import aiohttp
import asyncio
import logging
from src.config import settings

logger = logging.getLogger(__name__)

class BaleClient:
    """HTTP client for interacting with the Bale tapi.bale.ai endpoints."""

    def __init__(self, token: str):
        """Initialise the client with the bot token.

        Args:
            token: The BotFather token (from settings.BOT_TOKEN).
        """
        self.token = token
        # Construct the base URL e.g. "https://tapi.bale.ai/bot<TOKEN>"
        self.base_url = f"{settings.BALE_API_URL}{self.token}"

    async def _post(self, method: str, json_data: dict) -> dict:
        """Internal helper for making POST requests to the API.

        Args:
            method: The API method name (e.g. "sendMessage").
            json_data: The JSON payload dictionary.

        Returns:
            The parsed JSON response dict, or an empty dict on error.
        """
        url = f"{self.base_url}/{method}"
        async with aiohttp.ClientSession() as session:
            try:
                # 15s timeout for normal API calls (sending messages)
                async with session.post(url, json=json_data, timeout=15) as response:
                    if response.status == 429:
                        # Rate limit hit — log it but still try to parse response
                        logger.warning("Bale API rate limited (429).")
                    response.raise_for_status()
                    data = await response.json()
                    
                    if not data.get("ok"):
                        logger.error(f"Bale API Error: {data}")
                    return data
                    
            except Exception as e:
                logger.error(f"Error calling {method}: {e}")
                return {}

    async def get_updates(self, offset: int = None, timeout: int = 30) -> list[dict]:
        """Fetch new messages/callbacks via long-polling.

        Args:
            offset: ID of the first update to be returned. Must be 1 + the ID
                    of the last previously processed update.
            timeout: Long-polling timeout in seconds. The API holds the connection
                     open until a message arrives or the timeout expires.

        Returns:
            A list of update dictionaries.
        """
        url = f"{self.base_url}/getUpdates"
        params = {"timeout": timeout}
        if offset:
            params["offset"] = offset

        async with aiohttp.ClientSession() as session:
            try:
                # The client timeout must be slightly larger than the API timeout
                # to prevent the client from dropping the connection prematurely.
                async with session.get(url, params=params, timeout=timeout + 5) as response:
                    response.raise_for_status()
                    data = await response.json()
                    if data.get("ok"):
                        return data.get("result", [])
                    return []
            except asyncio.TimeoutError:
                # Normal behaviour in long-polling when no messages arrive
                return []
            except Exception as e:
                logger.error(f"Error getting updates: {e}")
                return []

    async def send_message(self, chat_id: int, text: str, reply_markup: dict = None) -> dict:
        """Send a new text message.

        Args:
            chat_id: The target chat (or user) ID.
            text: The message content.
            reply_markup: Optional inline keyboard dictionary.
        """
        payload = {
            "chat_id": chat_id,
            "text": text
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup

        return await self._post("sendMessage", payload)

    async def edit_message_text(self, chat_id: int, message_id: int, text: str, reply_markup: dict = None) -> dict:
        """Edit the text and keyboard of an existing message.

        Used extensively when users click inline buttons to update the message
        in-place rather than sending a new one.
        """
        payload = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup

        return await self._post("editMessageText", payload)

    async def answer_callback_query(self, callback_query_id: str, text: str = None) -> dict:
        """Acknowledge an inline button press.

        Must be called for every callback query, otherwise the button will
        show a loading spinner indefinitely in the user's client.
        """
        payload = {
            "callback_query_id": callback_query_id
        }
        if text:
            # If text is provided, the client shows it as a toast/tooltip
            payload["text"] = text

        return await self._post("answerCallbackQuery", payload)


# Singleton instance used by the handlers and poller
client = BaleClient(settings.BOT_TOKEN)
