"""Tests for src/bot/keyboards.py — pure keyboard builder functions."""

from src.bot.keyboards import (
    get_main_keyboard,
    get_settings_keyboard,
    get_back_keyboard,
    get_price_keyboard,
)


class TestMainKeyboard:
    """Tests for get_main_keyboard()."""

    def test_main_keyboard_structure(self):
        """Verify 3 rows, 5 buttons total, and correct callback_data values."""
        kb = get_main_keyboard()

        rows = kb["inline_keyboard"]
        assert len(rows) == 3, "Main keyboard must have exactly 3 rows"

        # Flatten all buttons and check total count
        all_buttons = [btn for row in rows for btn in row]
        assert len(all_buttons) == 5, "Main keyboard must have exactly 5 buttons"

        # Row 0: gold, currency  (2 buttons)
        assert len(rows[0]) == 2
        assert rows[0][0]["callback_data"] == "cat:gold"
        assert rows[0][1]["callback_data"] == "cat:currency"

        # Row 1: coin, all  (2 buttons)
        assert len(rows[1]) == 2
        assert rows[1][0]["callback_data"] == "cat:coin"
        assert rows[1][1]["callback_data"] == "all"

        # Row 2: settings  (1 button)
        assert len(rows[2]) == 1
        assert rows[2][0]["callback_data"] == "settings"


class TestSettingsKeyboard:
    """Tests for get_settings_keyboard(current_source)."""

    def test_settings_keyboard_tgju_selected(self):
        """When source is 'tgju', TGJU button text starts with ✅ and Nerkh does not."""
        kb = get_settings_keyboard("tgju")
        rows = kb["inline_keyboard"]

        source_row = rows[0]
        tgju_btn = source_row[0]
        nerkh_btn = source_row[1]

        assert tgju_btn["text"].startswith("✅"), "TGJU button should show ✅ when selected"
        assert not nerkh_btn["text"].startswith("✅"), "Nerkh button should NOT show ✅ when TGJU is selected"

        # Verify callback_data is still correct
        assert tgju_btn["callback_data"] == "set_source:tgju"
        assert nerkh_btn["callback_data"] == "set_source:nerkh"

        # Verify back button exists in the last row
        assert rows[-1][0]["callback_data"] == "main_menu"

    def test_settings_keyboard_nerkh_selected(self):
        """When source is 'nerkh', Nerkh button text starts with ✅ and TGJU does not."""
        kb = get_settings_keyboard("nerkh")
        rows = kb["inline_keyboard"]

        source_row = rows[0]
        tgju_btn = source_row[0]
        nerkh_btn = source_row[1]

        assert not tgju_btn["text"].startswith("✅"), "TGJU button should NOT show ✅ when Nerkh is selected"
        assert nerkh_btn["text"].startswith("✅"), "Nerkh button should show ✅ when selected"


class TestBackKeyboard:
    """Tests for get_back_keyboard(category)."""

    def test_back_keyboard_all(self):
        """When category is 'all', refresh callback_data should be 'all'."""
        kb = get_back_keyboard("all")
        rows = kb["inline_keyboard"]

        # First row is back button
        assert rows[0][0]["callback_data"] == "main_menu"
        # Second row is refresh button
        assert rows[1][0]["callback_data"] == "all"

    def test_back_keyboard_category(self):
        """When category is 'gold', refresh callback_data should be 'cat:gold'."""
        kb = get_back_keyboard("gold")
        rows = kb["inline_keyboard"]

        assert rows[0][0]["callback_data"] == "main_menu"
        assert rows[1][0]["callback_data"] == "cat:gold"

    def test_back_keyboard_none(self):
        """When no category is given, refresh callback_data should be 'refresh'."""
        kb = get_back_keyboard()
        rows = kb["inline_keyboard"]

        assert rows[0][0]["callback_data"] == "main_menu"
        assert rows[1][0]["callback_data"] == "refresh"


class TestPriceKeyboard:
    """Tests for get_price_keyboard()."""

    def test_price_keyboard_structure(self):
        """Price keyboard has 1 row with exactly 2 buttons (back + refresh)."""
        kb = get_price_keyboard()
        rows = kb["inline_keyboard"]

        assert len(rows) == 1, "Price keyboard must have exactly 1 row"
        assert len(rows[0]) == 2, "Price keyboard row must have exactly 2 buttons"

        back_btn, refresh_btn = rows[0]
        assert back_btn["callback_data"] == "main_menu"
        assert refresh_btn["callback_data"] == "refresh"
