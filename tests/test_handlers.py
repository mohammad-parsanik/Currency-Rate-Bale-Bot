"""
Tests for src/bot/handlers.py

Every test mocks the BaleClient instance (`client`) and repository classes
at the *handlers module* level so no network or database I/O occurs.
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from src.bot import keyboards


# ---------------------------------------------------------------------------
# Helpers – reusable mock factories and sample data
# ---------------------------------------------------------------------------

def _make_message(chat_id=12345, text="/start", user_id=12345,
                  first_name="علی", last_name="محمدی", username="ali_m"):
    """Build a Bale message dict."""
    msg = {
        "from": {
            "id": user_id,
            "first_name": first_name,
            "last_name": last_name,
            "username": username,
        },
        "chat": {"id": chat_id},
        "text": text,
    }
    return msg


def _make_callback(data="all", query_id="cb_001", chat_id=12345,
                   message_id=50, user_id=12345):
    """Build a Bale callback_query dict."""
    return {
        "id": query_id,
        "from": {"id": user_id, "first_name": "علی", "last_name": "محمدی", "username": "ali_m"},
        "message": {
            "message_id": message_id,
            "chat": {"id": chat_id},
        },
        "data": data,
    }


SAMPLE_PRICES = [
    {
        "asset_code": "usd", "asset_name_fa": "دلار آمریکا", "category": "currency",
        "price": "85000", "price_high": "85500", "price_low": "84500",
        "change_amount": "500", "change_percent": 0.59, "change_direction": "high",
        "source": "tgju", "source_timestamp": "2026-06-05 12:00:00",
        "fetched_at": "2026-06-05 12:01:00",
    },
    {
        "asset_code": "eur", "asset_name_fa": "یورو", "category": "currency",
        "price": "92000", "price_high": "92500", "price_low": "91500",
        "change_amount": "-300", "change_percent": -0.33, "change_direction": "low",
        "source": "tgju", "source_timestamp": "2026-06-05 12:00:00",
        "fetched_at": "2026-06-05 12:01:00",
    },
    {
        "asset_code": "gold_18k_sell", "asset_name_fa": "طلای ۱۸ عیار (فروش)", "category": "gold",
        "price": "5260000", "price_high": "5300000", "price_low": "5200000",
        "change_amount": "20000", "change_percent": 0.38, "change_direction": "high",
        "source": "tgju", "source_timestamp": "2026-06-05 12:00:00",
        "fetched_at": "2026-06-05 12:01:00",
    },
    {
        "asset_code": "ounce", "asset_name_fa": "انس جهانی طلا", "category": "gold",
        "price": "2345.67", "price_high": "2350.00", "price_low": "2340.00",
        "change_amount": "5", "change_percent": 0.21, "change_direction": "high",
        "source": "tgju", "source_timestamp": "2026-06-05 12:00:00",
        "fetched_at": "2026-06-05 12:01:00",
    },
    {
        "asset_code": "coin_emami", "asset_name_fa": "سکه امامی", "category": "coin",
        "price": "38000000", "price_high": "38500000", "price_low": "37500000",
        "change_amount": "200000", "change_percent": 0.53, "change_direction": "high",
        "source": "tgju", "source_timestamp": "2026-06-05 12:00:00",
        "fetched_at": "2026-06-05 12:01:00",
    },
]


# Common patch targets (all on the handlers module so imports are intercepted)
PATCH_CLIENT = "src.bot.handlers.client"
PATCH_USER_REPO = "src.bot.handlers.UserRepository"
PATCH_PRICE_REPO = "src.bot.handlers.PriceRepository"
PATCH_INTERACTION_REPO = "src.bot.handlers.InteractionRepository"


def _default_patches():
    """Return a dict of patches with sensible defaults."""
    mock_client = MagicMock()
    mock_client.send_message = AsyncMock(return_value={})
    mock_client.edit_message_text = AsyncMock(return_value={})
    mock_client.answer_callback_query = AsyncMock(return_value={})

    mock_user_repo = MagicMock()
    mock_user_repo.upsert_user = AsyncMock()
    mock_user_repo.get_user = AsyncMock(return_value={"preferred_source": "tgju"})
    mock_user_repo.update_preferred_source = AsyncMock()

    mock_price_repo = MagicMock()
    mock_price_repo.get_all_prices = AsyncMock(return_value=SAMPLE_PRICES)

    mock_interaction_repo = MagicMock()
    mock_interaction_repo.log_interaction = AsyncMock()

    return mock_client, mock_user_repo, mock_price_repo, mock_interaction_repo


# ===========================================================================
# 1–7  handle_message / handle_start / send_all_prices
# ===========================================================================


class TestHandleMessage:
    """Tests for message-level routing and edge cases."""

    @pytest.mark.asyncio
    @patch(PATCH_INTERACTION_REPO)
    @patch(PATCH_PRICE_REPO)
    @patch(PATCH_USER_REPO)
    @patch(PATCH_CLIENT)
    async def test_handle_start_command(self, mock_client, mock_user_repo,
                                        mock_price_repo, mock_interaction_repo):
        """1. /start command sends welcome text containing first_name and main keyboard."""
        mock_client.send_message = AsyncMock(return_value={})
        mock_user_repo.upsert_user = AsyncMock()
        mock_interaction_repo.log_interaction = AsyncMock()

        from src.bot.handlers import handle_message

        msg = _make_message(text="/start", first_name="علی")
        await handle_message(msg)

        mock_client.send_message.assert_called_once()
        call_args = mock_client.send_message.call_args
        # First positional arg: chat_id
        assert call_args[0][0] == 12345
        # Second positional arg: text should contain the first_name
        assert "علی" in call_args[0][1]
        # reply_markup should be the main keyboard
        assert call_args[1]["reply_markup"] == keyboards.get_main_keyboard()

    @pytest.mark.asyncio
    @patch(PATCH_INTERACTION_REPO)
    @patch(PATCH_PRICE_REPO)
    @patch(PATCH_USER_REPO)
    @patch(PATCH_CLIENT)
    async def test_handle_price_command(self, mock_client, mock_user_repo,
                                        mock_price_repo, mock_interaction_repo):
        """2. /price command with existing prices sends formatted prices."""
        mock_client.send_message = AsyncMock(return_value={})
        mock_user_repo.upsert_user = AsyncMock()
        mock_user_repo.get_user = AsyncMock(return_value={"preferred_source": "tgju"})
        mock_price_repo.get_all_prices = AsyncMock(return_value=SAMPLE_PRICES)
        mock_interaction_repo.log_interaction = AsyncMock()

        from src.bot.handlers import handle_message

        msg = _make_message(text="/price")
        await handle_message(msg)

        mock_client.send_message.assert_called_once()
        call_args = mock_client.send_message.call_args
        sent_text = call_args[0][1]
        # Should contain the price list header
        assert "قیمت" in sent_text
        # reply_markup should be back keyboard for "all"
        assert call_args[1]["reply_markup"] == keyboards.get_back_keyboard("all")

    @pytest.mark.asyncio
    @patch(PATCH_INTERACTION_REPO)
    @patch(PATCH_PRICE_REPO)
    @patch(PATCH_USER_REPO)
    @patch(PATCH_CLIENT)
    async def test_handle_price_no_data(self, mock_client, mock_user_repo,
                                         mock_price_repo, mock_interaction_repo):
        """3. /price with no prices available sends a fallback message."""
        mock_client.send_message = AsyncMock(return_value={})
        mock_user_repo.upsert_user = AsyncMock()
        mock_user_repo.get_user = AsyncMock(return_value={"preferred_source": "tgju"})
        mock_price_repo.get_all_prices = AsyncMock(return_value=[])
        mock_interaction_repo.log_interaction = AsyncMock()

        from src.bot.handlers import handle_message

        msg = _make_message(text="/price")
        await handle_message(msg)

        mock_client.send_message.assert_called_once()
        sent_text = mock_client.send_message.call_args[0][1]
        assert "در دسترس نیست" in sent_text or "بعداً" in sent_text

    @pytest.mark.asyncio
    @patch(PATCH_INTERACTION_REPO)
    @patch(PATCH_PRICE_REPO)
    @patch(PATCH_USER_REPO)
    @patch(PATCH_CLIENT)
    async def test_handle_unknown_text(self, mock_client, mock_user_repo,
                                        mock_price_repo, mock_interaction_repo):
        """4. Unknown text falls back to the start handler (welcome message)."""
        mock_client.send_message = AsyncMock(return_value={})
        mock_user_repo.upsert_user = AsyncMock()
        mock_interaction_repo.log_interaction = AsyncMock()

        from src.bot.handlers import handle_message

        msg = _make_message(text="سلام", first_name="علی")
        await handle_message(msg)

        mock_client.send_message.assert_called_once()
        sent_text = mock_client.send_message.call_args[0][1]
        # Falls back to handle_start → welcome message with first_name
        assert "علی" in sent_text

    @pytest.mark.asyncio
    @patch(PATCH_INTERACTION_REPO)
    @patch(PATCH_PRICE_REPO)
    @patch(PATCH_USER_REPO)
    @patch(PATCH_CLIENT)
    async def test_handle_message_no_chat_id(self, mock_client, mock_user_repo,
                                              mock_price_repo, mock_interaction_repo):
        """5. Message without chat.id returns early — no send_message call."""
        from src.bot.handlers import handle_message

        msg = {"from": {"id": 1}, "text": "/start"}  # missing chat
        await handle_message(msg)

        mock_client.send_message.assert_not_called()

    @pytest.mark.asyncio
    @patch(PATCH_INTERACTION_REPO)
    @patch(PATCH_PRICE_REPO)
    @patch(PATCH_USER_REPO)
    @patch(PATCH_CLIENT)
    async def test_handle_message_no_text(self, mock_client, mock_user_repo,
                                           mock_price_repo, mock_interaction_repo):
        """6. Message with empty text returns early — no send_message call."""
        from src.bot.handlers import handle_message

        msg = {"from": {"id": 1}, "chat": {"id": 12345}, "text": ""}
        await handle_message(msg)

        mock_client.send_message.assert_not_called()

    @pytest.mark.asyncio
    @patch(PATCH_INTERACTION_REPO)
    @patch(PATCH_PRICE_REPO)
    @patch(PATCH_USER_REPO)
    @patch(PATCH_CLIENT)
    async def test_handle_message_logs_interaction(self, mock_client, mock_user_repo,
                                                     mock_price_repo, mock_interaction_repo):
        """7. Every valid message upserts user and logs the interaction."""
        mock_client.send_message = AsyncMock(return_value={})
        mock_user_repo.upsert_user = AsyncMock()
        mock_interaction_repo.log_interaction = AsyncMock()

        from src.bot.handlers import handle_message

        msg = _make_message(text="/start", user_id=999, first_name="علی",
                            last_name="محمدی", username="ali_m")
        await handle_message(msg)

        mock_user_repo.upsert_user.assert_called_once_with(999, "علی", "محمدی", "ali_m")
        mock_interaction_repo.log_interaction.assert_called_once_with(999, "/start")


# ===========================================================================
# 8–20  handle_callback_query
# ===========================================================================


class TestHandleCallbackQuery:
    """Tests for callback query handling – all data variants."""

    @pytest.mark.asyncio
    @patch(PATCH_INTERACTION_REPO)
    @patch(PATCH_PRICE_REPO)
    @patch(PATCH_USER_REPO)
    @patch(PATCH_CLIENT)
    async def test_callback_all_prices(self, mock_client, mock_user_repo,
                                        mock_price_repo, mock_interaction_repo):
        """8. data='all' edits message with formatted prices."""
        mock_client.answer_callback_query = AsyncMock(return_value={})
        mock_client.edit_message_text = AsyncMock(return_value={})
        mock_user_repo.get_user = AsyncMock(return_value={"preferred_source": "tgju"})
        mock_price_repo.get_all_prices = AsyncMock(return_value=SAMPLE_PRICES)
        mock_interaction_repo.log_interaction = AsyncMock()

        from src.bot.handlers import handle_callback_query

        cb = _make_callback(data="all")
        await handle_callback_query(cb)

        mock_client.edit_message_text.assert_called_once()
        call_args = mock_client.edit_message_text.call_args
        assert call_args[0][0] == 12345  # chat_id
        assert call_args[0][1] == 50     # message_id
        assert "قیمت" in call_args[0][2]  # formatted text
        assert call_args[1]["reply_markup"] == keyboards.get_back_keyboard("all")

    @pytest.mark.asyncio
    @patch(PATCH_INTERACTION_REPO)
    @patch(PATCH_PRICE_REPO)
    @patch(PATCH_USER_REPO)
    @patch(PATCH_CLIENT)
    async def test_callback_category_currency(self, mock_client, mock_user_repo,
                                               mock_price_repo, mock_interaction_repo):
        """9. data='cat:currency' shows only currency prices."""
        mock_client.answer_callback_query = AsyncMock(return_value={})
        mock_client.edit_message_text = AsyncMock(return_value={})
        mock_user_repo.get_user = AsyncMock(return_value={"preferred_source": "tgju"})
        mock_price_repo.get_all_prices = AsyncMock(return_value=SAMPLE_PRICES)
        mock_interaction_repo.log_interaction = AsyncMock()

        from src.bot.handlers import handle_callback_query

        cb = _make_callback(data="cat:currency")
        await handle_callback_query(cb)

        mock_client.edit_message_text.assert_called_once()
        call_args = mock_client.edit_message_text.call_args
        sent_text = call_args[0][2]
        # Currency assets should be present
        assert "دلار" in sent_text or "ارز" in sent_text
        assert call_args[1]["reply_markup"] == keyboards.get_back_keyboard("currency")

    @pytest.mark.asyncio
    @patch(PATCH_INTERACTION_REPO)
    @patch(PATCH_PRICE_REPO)
    @patch(PATCH_USER_REPO)
    @patch(PATCH_CLIENT)
    async def test_callback_category_gold(self, mock_client, mock_user_repo,
                                           mock_price_repo, mock_interaction_repo):
        """10. data='cat:gold' shows only gold prices."""
        mock_client.answer_callback_query = AsyncMock(return_value={})
        mock_client.edit_message_text = AsyncMock(return_value={})
        mock_user_repo.get_user = AsyncMock(return_value={"preferred_source": "tgju"})
        mock_price_repo.get_all_prices = AsyncMock(return_value=SAMPLE_PRICES)
        mock_interaction_repo.log_interaction = AsyncMock()

        from src.bot.handlers import handle_callback_query

        cb = _make_callback(data="cat:gold")
        await handle_callback_query(cb)

        mock_client.edit_message_text.assert_called_once()
        sent_text = mock_client.edit_message_text.call_args[0][2]
        assert "طلا" in sent_text
        assert mock_client.edit_message_text.call_args[1]["reply_markup"] == keyboards.get_back_keyboard("gold")

    @pytest.mark.asyncio
    @patch(PATCH_INTERACTION_REPO)
    @patch(PATCH_PRICE_REPO)
    @patch(PATCH_USER_REPO)
    @patch(PATCH_CLIENT)
    async def test_callback_category_coin(self, mock_client, mock_user_repo,
                                           mock_price_repo, mock_interaction_repo):
        """11. data='cat:coin' shows only coin prices."""
        mock_client.answer_callback_query = AsyncMock(return_value={})
        mock_client.edit_message_text = AsyncMock(return_value={})
        mock_user_repo.get_user = AsyncMock(return_value={"preferred_source": "tgju"})
        mock_price_repo.get_all_prices = AsyncMock(return_value=SAMPLE_PRICES)
        mock_interaction_repo.log_interaction = AsyncMock()

        from src.bot.handlers import handle_callback_query

        cb = _make_callback(data="cat:coin")
        await handle_callback_query(cb)

        mock_client.edit_message_text.assert_called_once()
        sent_text = mock_client.edit_message_text.call_args[0][2]
        assert "سکه" in sent_text
        assert mock_client.edit_message_text.call_args[1]["reply_markup"] == keyboards.get_back_keyboard("coin")

    @pytest.mark.asyncio
    @patch(PATCH_INTERACTION_REPO)
    @patch(PATCH_PRICE_REPO)
    @patch(PATCH_USER_REPO)
    @patch(PATCH_CLIENT)
    async def test_callback_settings(self, mock_client, mock_user_repo,
                                      mock_price_repo, mock_interaction_repo):
        """12. data='settings' edits message with settings keyboard showing current source."""
        mock_client.answer_callback_query = AsyncMock(return_value={})
        mock_client.edit_message_text = AsyncMock(return_value={})
        mock_user_repo.get_user = AsyncMock(return_value={"preferred_source": "tgju"})
        mock_interaction_repo.log_interaction = AsyncMock()

        from src.bot.handlers import handle_callback_query

        cb = _make_callback(data="settings")
        await handle_callback_query(cb)

        mock_client.edit_message_text.assert_called_once()
        call_args = mock_client.edit_message_text.call_args
        assert "منبع" in call_args[0][2]
        assert call_args[1]["reply_markup"] == keyboards.get_settings_keyboard("tgju")

    @pytest.mark.asyncio
    @patch("src.database.repositories.UserSourceLogRepository.log_source_change", new_callable=AsyncMock)
    @patch(PATCH_INTERACTION_REPO)
    @patch(PATCH_PRICE_REPO)
    @patch(PATCH_USER_REPO)
    @patch(PATCH_CLIENT)
    async def test_callback_set_source_tgju(self, mock_client, mock_user_repo,
                                             mock_price_repo, mock_interaction_repo,
                                             mock_log_source_change):
        """13. data='set_source:tgju' when user was on nerkh → updates source and logs change."""
        mock_client.answer_callback_query = AsyncMock(return_value={})
        mock_client.edit_message_text = AsyncMock(return_value={})
        mock_user_repo.get_user = AsyncMock(return_value={"preferred_source": "nerkh"})
        mock_user_repo.update_preferred_source = AsyncMock()
        mock_interaction_repo.log_interaction = AsyncMock()

        from src.bot.handlers import handle_callback_query

        cb = _make_callback(data="set_source:tgju")
        await handle_callback_query(cb)

        mock_user_repo.update_preferred_source.assert_called_once_with(12345, "tgju")
        mock_log_source_change.assert_called_once_with(12345, "nerkh", "tgju")
        # After update, settings keyboard should reflect new source
        assert mock_client.edit_message_text.call_args[1]["reply_markup"] == keyboards.get_settings_keyboard("tgju")

    @pytest.mark.asyncio
    @patch("src.database.repositories.UserSourceLogRepository.log_source_change", new_callable=AsyncMock)
    @patch(PATCH_INTERACTION_REPO)
    @patch(PATCH_PRICE_REPO)
    @patch(PATCH_USER_REPO)
    @patch(PATCH_CLIENT)
    async def test_callback_set_source_nerkh(self, mock_client, mock_user_repo,
                                              mock_price_repo, mock_interaction_repo,
                                              mock_log_source_change):
        """14. data='set_source:nerkh' when user was on tgju → updates source."""
        mock_client.answer_callback_query = AsyncMock(return_value={})
        mock_client.edit_message_text = AsyncMock(return_value={})
        mock_user_repo.get_user = AsyncMock(return_value={"preferred_source": "tgju"})
        mock_user_repo.update_preferred_source = AsyncMock()
        mock_interaction_repo.log_interaction = AsyncMock()

        from src.bot.handlers import handle_callback_query

        cb = _make_callback(data="set_source:nerkh")
        await handle_callback_query(cb)

        mock_user_repo.update_preferred_source.assert_called_once_with(12345, "nerkh")
        mock_log_source_change.assert_called_once_with(12345, "tgju", "nerkh")
        assert mock_client.edit_message_text.call_args[1]["reply_markup"] == keyboards.get_settings_keyboard("nerkh")

    @pytest.mark.asyncio
    @patch("src.database.repositories.UserSourceLogRepository.log_source_change", new_callable=AsyncMock)
    @patch(PATCH_INTERACTION_REPO)
    @patch(PATCH_PRICE_REPO)
    @patch(PATCH_USER_REPO)
    @patch(PATCH_CLIENT)
    async def test_callback_set_source_same(self, mock_client, mock_user_repo,
                                             mock_price_repo, mock_interaction_repo,
                                             mock_log_source_change):
        """15. Setting source to the current value → no update_preferred_source, no log_source_change."""
        mock_client.answer_callback_query = AsyncMock(return_value={})
        mock_client.edit_message_text = AsyncMock(return_value={})
        mock_user_repo.get_user = AsyncMock(return_value={"preferred_source": "tgju"})
        mock_user_repo.update_preferred_source = AsyncMock()
        mock_interaction_repo.log_interaction = AsyncMock()

        from src.bot.handlers import handle_callback_query

        cb = _make_callback(data="set_source:tgju")
        await handle_callback_query(cb)

        # Source didn't change, so neither update nor log should be called
        mock_user_repo.update_preferred_source.assert_not_called()
        mock_log_source_change.assert_not_called()
        # But the confirmation message is still sent
        mock_client.edit_message_text.assert_called_once()

    @pytest.mark.asyncio
    @patch(PATCH_INTERACTION_REPO)
    @patch(PATCH_PRICE_REPO)
    @patch(PATCH_USER_REPO)
    @patch(PATCH_CLIENT)
    async def test_callback_main_menu(self, mock_client, mock_user_repo,
                                       mock_price_repo, mock_interaction_repo):
        """16. data='main_menu' edits message with main keyboard."""
        mock_client.answer_callback_query = AsyncMock(return_value={})
        mock_client.edit_message_text = AsyncMock(return_value={})
        mock_user_repo.get_user = AsyncMock(return_value={"preferred_source": "tgju"})
        mock_interaction_repo.log_interaction = AsyncMock()

        from src.bot.handlers import handle_callback_query

        cb = _make_callback(data="main_menu")
        await handle_callback_query(cb)

        mock_client.edit_message_text.assert_called_once()
        call_args = mock_client.edit_message_text.call_args
        assert "دسته‌بندی" in call_args[0][2]
        assert call_args[1]["reply_markup"] == keyboards.get_main_keyboard()

    @pytest.mark.asyncio
    @patch(PATCH_INTERACTION_REPO)
    @patch(PATCH_PRICE_REPO)
    @patch(PATCH_USER_REPO)
    @patch(PATCH_CLIENT)
    async def test_callback_refresh(self, mock_client, mock_user_repo,
                                     mock_price_repo, mock_interaction_repo):
        """17. data='refresh' re-fetches prices and edits message."""
        mock_client.answer_callback_query = AsyncMock(return_value={})
        mock_client.edit_message_text = AsyncMock(return_value={})
        mock_user_repo.get_user = AsyncMock(return_value={"preferred_source": "tgju"})
        mock_price_repo.get_all_prices = AsyncMock(return_value=SAMPLE_PRICES)
        mock_interaction_repo.log_interaction = AsyncMock()

        from src.bot.handlers import handle_callback_query

        cb = _make_callback(data="refresh")
        await handle_callback_query(cb)

        # Prices should have been fetched
        mock_price_repo.get_all_prices.assert_called_once_with("tgju")
        mock_client.edit_message_text.assert_called_once()
        sent_text = mock_client.edit_message_text.call_args[0][2]
        assert "قیمت" in sent_text

    @pytest.mark.asyncio
    @patch(PATCH_INTERACTION_REPO)
    @patch(PATCH_PRICE_REPO)
    @patch(PATCH_USER_REPO)
    @patch(PATCH_CLIENT)
    async def test_callback_no_prices_available(self, mock_client, mock_user_repo,
                                                 mock_price_repo, mock_interaction_repo):
        """18. Callback with no prices → edits message with fallback text."""
        mock_client.answer_callback_query = AsyncMock(return_value={})
        mock_client.edit_message_text = AsyncMock(return_value={})
        mock_user_repo.get_user = AsyncMock(return_value={"preferred_source": "tgju"})
        mock_price_repo.get_all_prices = AsyncMock(return_value=[])
        mock_interaction_repo.log_interaction = AsyncMock()

        from src.bot.handlers import handle_callback_query

        cb = _make_callback(data="all")
        await handle_callback_query(cb)

        mock_client.edit_message_text.assert_called_once()
        sent_text = mock_client.edit_message_text.call_args[0][2]
        assert "در دسترس نیست" in sent_text or "منبع" in sent_text

    @pytest.mark.asyncio
    @patch(PATCH_INTERACTION_REPO)
    @patch(PATCH_PRICE_REPO)
    @patch(PATCH_USER_REPO)
    @patch(PATCH_CLIENT)
    async def test_callback_missing_chat_or_message(self, mock_client, mock_user_repo,
                                                      mock_price_repo, mock_interaction_repo):
        """19. Callback without chat_id or message_id → answers callback then returns early."""
        mock_client.answer_callback_query = AsyncMock(return_value={})
        mock_client.edit_message_text = AsyncMock(return_value={})
        mock_interaction_repo.log_interaction = AsyncMock()

        from src.bot.handlers import handle_callback_query

        cb = {
            "id": "cb_002",
            "from": {"id": 12345},
            "message": {},  # no chat.id or message_id
            "data": "all",
        }
        await handle_callback_query(cb)

        # Should acknowledge the callback
        mock_client.answer_callback_query.assert_called_once_with("cb_002")
        # Should NOT attempt to edit
        mock_client.edit_message_text.assert_not_called()

    @pytest.mark.asyncio
    @patch(PATCH_INTERACTION_REPO)
    @patch(PATCH_PRICE_REPO)
    @patch(PATCH_USER_REPO)
    @patch(PATCH_CLIENT)
    async def test_callback_handler_exception(self, mock_client, mock_user_repo,
                                               mock_price_repo, mock_interaction_repo):
        """20. Exception during callback processing → sends error message to user."""
        mock_client.answer_callback_query = AsyncMock(return_value={})
        mock_client.edit_message_text = AsyncMock(return_value={})
        mock_client.send_message = AsyncMock(return_value={})
        mock_interaction_repo.log_interaction = AsyncMock()
        # Simulate an exception inside the try block
        mock_user_repo.get_user = AsyncMock(side_effect=RuntimeError("DB exploded"))

        from src.bot.handlers import handle_callback_query

        cb = _make_callback(data="all")
        await handle_callback_query(cb)

        # Should send an error message via send_message (not edit)
        mock_client.send_message.assert_called_once()
        error_text = mock_client.send_message.call_args[0][1]
        assert "خطا" in error_text


# ===========================================================================
# 21–23  handle_update (dispatch)
# ===========================================================================


class TestHandleUpdate:
    """Tests for top-level update dispatching."""

    @pytest.mark.asyncio
    @patch(PATCH_INTERACTION_REPO)
    @patch(PATCH_PRICE_REPO)
    @patch(PATCH_USER_REPO)
    @patch(PATCH_CLIENT)
    async def test_handle_update_message(self, mock_client, mock_user_repo,
                                          mock_price_repo, mock_interaction_repo):
        """21. Update with 'message' key dispatches to handle_message."""
        mock_client.send_message = AsyncMock(return_value={})
        mock_user_repo.upsert_user = AsyncMock()
        mock_interaction_repo.log_interaction = AsyncMock()

        from src.bot.handlers import handle_update

        update = {"update_id": 100, "message": _make_message(text="/start")}
        await handle_update(update)

        # handle_message was called → client.send_message should have been invoked
        mock_client.send_message.assert_called_once()

    @pytest.mark.asyncio
    @patch(PATCH_INTERACTION_REPO)
    @patch(PATCH_PRICE_REPO)
    @patch(PATCH_USER_REPO)
    @patch(PATCH_CLIENT)
    async def test_handle_update_callback(self, mock_client, mock_user_repo,
                                           mock_price_repo, mock_interaction_repo):
        """22. Update with 'callback_query' dispatches to handle_callback_query."""
        mock_client.answer_callback_query = AsyncMock(return_value={})
        mock_client.edit_message_text = AsyncMock(return_value={})
        mock_user_repo.get_user = AsyncMock(return_value={"preferred_source": "tgju"})
        mock_price_repo.get_all_prices = AsyncMock(return_value=SAMPLE_PRICES)
        mock_interaction_repo.log_interaction = AsyncMock()

        from src.bot.handlers import handle_update

        update = {"update_id": 101, "callback_query": _make_callback(data="all")}
        await handle_update(update)

        # handle_callback_query was called → answer + edit should have been invoked
        mock_client.answer_callback_query.assert_called_once()
        mock_client.edit_message_text.assert_called_once()

    @pytest.mark.asyncio
    @patch(PATCH_INTERACTION_REPO)
    @patch(PATCH_PRICE_REPO)
    @patch(PATCH_USER_REPO)
    @patch(PATCH_CLIENT)
    async def test_handle_update_empty(self, mock_client, mock_user_repo,
                                        mock_price_repo, mock_interaction_repo):
        """23. Update with neither message nor callback_query → no crash, no calls."""
        from src.bot.handlers import handle_update

        update = {"update_id": 200}
        await handle_update(update)

        mock_client.send_message.assert_not_called()
        mock_client.edit_message_text.assert_not_called()
