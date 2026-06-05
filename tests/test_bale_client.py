"""
Tests for src.bot.client — BaleClient HTTP wrapper.

Every test is fully offline; aiohttp calls are intercepted by the
``mock_aiohttp`` (aioresponses) fixture from conftest, or by directly
mocking the internal ``_post`` / ``get_updates`` methods to avoid
aiohttp/aioresponses version incompatibilities.
"""

import asyncio
import aiohttp
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.bot.client import BaleClient

BASE_URL = "https://tapi.bale.ai/botDUMMY_TOKEN_12345"


# ── send_message ─────────────────────────────────────────────────────────────

class TestSendMessage:
    """Tests for BaleClient.send_message."""

    @pytest.mark.asyncio
    async def test_send_message_success(self, bale_client):
        """A successful _post returns the full JSON dict."""
        bale_client._post = AsyncMock(return_value={"ok": True, "result": {}})

        result = await bale_client.send_message(chat_id=1, text="hello")

        assert result == {"ok": True, "result": {}}
        bale_client._post.assert_called_once_with(
            "sendMessage", {"chat_id": 1, "text": "hello"}
        )

    @pytest.mark.asyncio
    async def test_send_message_with_keyboard(self, bale_client):
        """When reply_markup is given it must appear in the posted payload."""
        bale_client._post = AsyncMock(return_value={"ok": True, "result": {}})

        keyboard = {"inline_keyboard": [[{"text": "btn", "callback_data": "x"}]]}
        await bale_client.send_message(chat_id=1, text="hi", reply_markup=keyboard)

        call_args = bale_client._post.call_args[0]
        payload = call_args[1]
        assert "reply_markup" in payload
        assert payload["reply_markup"] == keyboard

    @pytest.mark.asyncio
    async def test_send_message_api_error(self, bale_client):
        """A 200 response with ok=false is logged but the dict is still returned."""
        body = {"ok": False, "description": "Bad Request"}
        bale_client._post = AsyncMock(return_value=body)

        result = await bale_client.send_message(chat_id=1, text="oops")

        assert result == body

    @pytest.mark.asyncio
    async def test_send_message_http_error(self, bale_client, mock_aiohttp):
        """A 500 HTTP error is caught and an empty dict is returned."""
        mock_aiohttp.post(
            f"{BASE_URL}/sendMessage",
            status=500,
        )

        result = await bale_client.send_message(chat_id=1, text="fail")

        assert result == {}

    @pytest.mark.asyncio
    async def test_send_message_rate_limit_429(self, bale_client, mock_aiohttp):
        """A 429 rate-limit response is logged and returns an empty dict."""
        mock_aiohttp.post(
            f"{BASE_URL}/sendMessage",
            status=429,
        )

        result = await bale_client.send_message(chat_id=1, text="spam")

        assert result == {}

    @pytest.mark.asyncio
    async def test_send_message_network_error(self, bale_client, mock_aiohttp):
        """A network-level exception (ClientError) returns an empty dict."""
        mock_aiohttp.post(
            f"{BASE_URL}/sendMessage",
            exception=aiohttp.ClientError("connection reset"),
        )

        result = await bale_client.send_message(chat_id=1, text="offline")

        assert result == {}


# ── get_updates ──────────────────────────────────────────────────────────────

class TestGetUpdates:
    """Tests for BaleClient.get_updates."""

    @pytest.mark.asyncio
    async def test_get_updates_success(self, bale_client):
        """A 200/ok response returns the result list."""
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json = AsyncMock(return_value={"ok": True, "result": [{"update_id": 1}]})

        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_cm.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_cm)

        mock_session_cm = MagicMock()
        mock_session_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_cm.__aexit__ = AsyncMock(return_value=False)

        with patch("src.bot.client.aiohttp.ClientSession", return_value=mock_session_cm):
            updates = await bale_client.get_updates(offset=1, timeout=5)

        assert updates == [{"update_id": 1}]

    @pytest.mark.asyncio
    async def test_get_updates_timeout(self, bale_client, mock_aiohttp):
        """An asyncio.TimeoutError during long-polling returns an empty list."""
        mock_aiohttp.get(
            f"{BASE_URL}/getUpdates",
            exception=asyncio.TimeoutError(),
        )

        updates = await bale_client.get_updates(offset=0, timeout=5)

        assert updates == []

    @pytest.mark.asyncio
    async def test_get_updates_not_ok(self, bale_client, mock_aiohttp):
        """A 200 response where ok=false returns an empty list."""
        mock_aiohttp.get(
            f"{BASE_URL}/getUpdates",
            payload={"ok": False},
            status=200,
        )

        updates = await bale_client.get_updates(offset=1, timeout=5)

        assert updates == []


# ── edit_message_text ────────────────────────────────────────────────────────

class TestEditMessageText:
    """Tests for BaleClient.edit_message_text."""

    @pytest.mark.asyncio
    async def test_edit_message_text(self, bale_client):
        """Correct payload (chat_id, message_id, text) is sent and response returned."""
        bale_client._post = AsyncMock(return_value={"ok": True, "result": {}})

        result = await bale_client.edit_message_text(
            chat_id=10, message_id=42, text="edited"
        )

        assert result == {"ok": True, "result": {}}
        call_args = bale_client._post.call_args[0]
        assert call_args[0] == "editMessageText"
        payload = call_args[1]
        assert payload["chat_id"] == 10
        assert payload["message_id"] == 42
        assert payload["text"] == "edited"

    @pytest.mark.asyncio
    async def test_edit_message_text_with_keyboard(self, bale_client):
        """reply_markup is included in payload when provided."""
        bale_client._post = AsyncMock(return_value={"ok": True, "result": {}})

        keyboard = {"inline_keyboard": [[{"text": "btn", "callback_data": "x"}]]}
        await bale_client.edit_message_text(
            chat_id=10, message_id=42, text="edited", reply_markup=keyboard
        )

        payload = bale_client._post.call_args[0][1]
        assert payload["reply_markup"] == keyboard


# ── answer_callback_query ───────────────────────────────────────────────────

class TestAnswerCallbackQuery:
    """Tests for BaleClient.answer_callback_query."""

    @pytest.mark.asyncio
    async def test_answer_callback_query(self, bale_client):
        """Payload contains callback_query_id and response is returned."""
        bale_client._post = AsyncMock(return_value={"ok": True, "result": {}})

        result = await bale_client.answer_callback_query(callback_query_id="cb_99")

        assert result == {"ok": True, "result": {}}
        payload = bale_client._post.call_args[0][1]
        assert payload["callback_query_id"] == "cb_99"
        assert "text" not in payload

    @pytest.mark.asyncio
    async def test_answer_callback_query_with_text(self, bale_client):
        """When text is provided it appears in the payload."""
        bale_client._post = AsyncMock(return_value={"ok": True, "result": {}})

        result = await bale_client.answer_callback_query(
            callback_query_id="cb_100", text="Done!"
        )

        assert result == {"ok": True, "result": {}}
        payload = bale_client._post.call_args[0][1]
        assert payload["callback_query_id"] == "cb_100"
        assert payload["text"] == "Done!"
