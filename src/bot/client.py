import aiohttp
import asyncio
import logging
from src.config import settings

logger = logging.getLogger(__name__)

class BaleClient:
    def __init__(self, token: str):
        self.token = token
        self.base_url = f"{settings.BALE_API_URL}{self.token}"

    async def _post(self, method: str, json_data: dict) -> dict:
        url = f"{self.base_url}/{method}"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, json=json_data, timeout=15) as response:
                    if response.status == 429:
                        # Rate limit
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
        url = f"{self.base_url}/getUpdates"
        params = {"timeout": timeout}
        if offset:
            params["offset"] = offset
            
        async with aiohttp.ClientSession() as session:
            try:
                # Use a larger client timeout to allow long polling
                async with session.get(url, params=params, timeout=timeout + 5) as response:
                    response.raise_for_status()
                    data = await response.json()
                    if data.get("ok"):
                        return data.get("result", [])
                    return []
            except asyncio.TimeoutError:
                return []
            except Exception as e:
                logger.error(f"Error getting updates: {e}")
                return []

    async def send_message(self, chat_id: int, text: str, reply_markup: dict = None) -> dict:
        payload = {
            "chat_id": chat_id,
            "text": text
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
            
        return await self._post("sendMessage", payload)

    async def edit_message_text(self, chat_id: int, message_id: int, text: str, reply_markup: dict = None) -> dict:
        payload = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
            
        return await self._post("editMessageText", payload)

    async def answer_callback_query(self, callback_query_id: str, text: str = None) -> dict:
        payload = {
            "callback_query_id": callback_query_id
        }
        if text:
            payload["text"] = text
            
        return await self._post("answerCallbackQuery", payload)

client = BaleClient(settings.BOT_TOKEN)
