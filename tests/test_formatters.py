"""
Tests for src/bot/formatters.py

Covers:
  - to_persian_digits
  - format_price_value
  - format_change
  - format_all_prices
  - format_single_category
  - format_single_price
  - adjust_time
"""

import pytest

from src.bot.formatters import (
    adjust_time,
    to_persian_digits,
    format_price_value,
    format_change,
    format_all_prices,
    format_single_category,
    format_single_price,
)


# ═══════════════════════════════════════════════════════════════════════════
# to_persian_digits
# ═══════════════════════════════════════════════════════════════════════════

class TestToPersianDigits:
    """Tests for the to_persian_digits helper."""

    def test_to_persian_digits_all(self):
        """All ten ASCII digits are converted to their Persian equivalents."""
        assert to_persian_digits("0123456789") == "۰۱۲۳۴۵۶۷۸۹"

    def test_to_persian_digits_no_digits(self):
        """A string without any digits passes through unchanged."""
        assert to_persian_digits("abc") == "abc"

    def test_to_persian_digits_empty(self):
        """An empty string returns an empty string."""
        assert to_persian_digits("") == ""

    def test_to_persian_digits_mixed(self):
        """Only digit characters are converted; letters are kept."""
        assert to_persian_digits("abc12def") == "abc۱۲def"


# ═══════════════════════════════════════════════════════════════════════════
# format_price_value
# ═══════════════════════════════════════════════════════════════════════════

class TestFormatPriceValue:
    """Tests for format_price_value (comma-formatting + Persian digits)."""

    def test_format_price_value_normal(self):
        """An integer string is comma-formatted and persianised."""
        assert format_price_value("1234567") == "۱,۲۳۴,۵۶۷"

    def test_format_price_value_zero(self):
        """'0' is treated as unknown / unavailable."""
        assert format_price_value("0") == "نامشخص"

    def test_format_price_value_none(self):
        """None is treated as unknown / unavailable."""
        assert format_price_value(None) == "نامشخص"

    def test_format_price_value_empty(self):
        """Empty string is treated as unknown / unavailable."""
        assert format_price_value("") == "نامشخص"

    def test_format_price_value_float(self):
        """A float string keeps its decimal part and gets commas."""
        assert format_price_value("1744200.5") == "۱,۷۴۴,۲۰۰.۵"

    def test_format_price_value_with_commas(self):
        """Input that already contains commas is handled correctly."""
        assert format_price_value("1,234,567") == "۱,۲۳۴,۵۶۷"

    def test_format_price_value_garbage(self):
        """Non-numeric text falls through to to_persian_digits as-is."""
        result = format_price_value("xyz")
        # "xyz" has no ASCII digits, so Persian-digit conversion is a no-op
        assert result == "xyz"


# ═══════════════════════════════════════════════════════════════════════════
# format_change
# ═══════════════════════════════════════════════════════════════════════════

class TestFormatChange:
    """Tests for format_change (emoji + signed percentage)."""

    def test_format_change_high(self):
        """A 'high' direction produces a green chart emoji and +sign."""
        result = format_change(1.23, "high")
        assert result == "📈 +۱.۲۳٪"

    def test_format_change_low(self):
        """A 'low' direction produces a red chart emoji and −sign."""
        result = format_change(0.47, "low")
        assert result == "📉 -۰.۴۷٪"

    def test_format_change_low_negative_percent(self):
        """Negative percent with 'low' uses abs() – no double negative."""
        result = format_change(-0.47, "low")
        assert result == "📉 -۰.۴۷٪"

    def test_format_change_stable(self):
        """Zero percent returns the 'stable' string."""
        assert format_change(0.0, "stable") == "ثابت"

    def test_format_change_none_percent(self):
        """None percent is treated as stable."""
        assert format_change(None, "high") == "ثابت"


# ═══════════════════════════════════════════════════════════════════════════
# format_all_prices
# ═══════════════════════════════════════════════════════════════════════════

class TestFormatAllPrices:
    """Tests for format_all_prices (full price list formatting)."""

    def test_format_all_prices_happy(self, sample_prices):
        """All 3 category headers and all 5 asset names appear in output."""
        output = format_all_prices(sample_prices)

        # Category headers
        assert "💵 ارز" in output
        assert "🪙 سکه" in output
        assert "✨ طلا" in output

        # Asset names (first token for currency, full name for others)
        assert "دلار" in output          # first word of "دلار آمریکا"
        assert "یورو" in output
        assert "طلای ۱۸ عیار (فروش)" in output
        assert "انس جهانی طلا" in output
        assert "سکه امامی" in output

    def test_format_all_prices_empty(self):
        """An empty list returns the 'no data' message."""
        assert format_all_prices([]) == "داده‌ای برای نمایش وجود ندارد."

    def test_format_all_prices_single_category(self, sample_prices):
        """When only currency prices are passed, only the 💵 section appears."""
        currencies_only = [p for p in sample_prices if p["category"] == "currency"]
        output = format_all_prices(currencies_only)

        assert "💵 ارز" in output
        assert "🪙 سکه" not in output
        assert "✨ طلا" not in output


# ═══════════════════════════════════════════════════════════════════════════
# format_single_category
# ═══════════════════════════════════════════════════════════════════════════

class TestFormatSingleCategory:
    """Tests for format_single_category (filter + format)."""

    def test_format_single_category_filters(self, sample_prices):
        """Filtering by 'gold' returns only gold items."""
        output = format_single_category(sample_prices, "gold")

        assert "✨ طلا" in output
        assert "طلای ۱۸ عیار (فروش)" in output
        assert "انس جهانی طلا" in output

        # Currency / coin items must NOT be present
        assert "💵 ارز" not in output
        assert "🪙 سکه" not in output

    def test_format_single_category_empty(self, sample_prices):
        """A category with no matching prices returns the 'no data' message."""
        output = format_single_category(sample_prices, "crypto")
        assert "داده‌ای برای نمایش وجود ندارد." == output


# ═══════════════════════════════════════════════════════════════════════════
# format_single_price
# ═══════════════════════════════════════════════════════════════════════════

class TestFormatSinglePrice:
    """Tests for format_single_price (detailed single-asset output)."""

    def test_format_single_price_normal(self, sample_prices):
        """A full price dict produces output containing name, prices, and change."""
        price = sample_prices[0]  # USD
        output = format_single_price(price)

        assert "دلار آمریکا" in output
        assert "قیمت فعلی" in output
        assert "بالاترین" in output
        assert "پایین‌ترین" in output
        assert "تغییر" in output
        # Should contain the formatted change emoji for a 'high' direction
        assert "📈" in output

    def test_format_single_price_none(self):
        """None input returns the 'not found' message."""
        assert format_single_price(None) == "یافت نشد."


# ═══════════════════════════════════════════════════════════════════════════
# adjust_time
# ═══════════════════════════════════════════════════════════════════════════

class TestAdjustTime:
    """Tests for adjust_time (UTC → Tehran +03:30 conversion)."""

    def test_adjust_time_sqlite_format(self):
        """SQLite-style 'YYYY-MM-DD HH:MM:SS' is shifted +3:30 to Tehran."""
        result = adjust_time("2026-06-05 08:30:00")
        assert result == "2026/06/05 12:00:00"

    def test_adjust_time_iso_format(self):
        """ISO 'YYYY-MM-DDTHH:MM:SSZ' is converted to Tehran time."""
        result = adjust_time("2026-06-05T08:30:00Z")
        assert result == "2026/06/05 12:00:00"

    def test_adjust_time_empty(self):
        """An empty string returns an empty string."""
        assert adjust_time("") == ""

    def test_adjust_time_garbage(self):
        """Un-parseable input is returned as-is."""
        assert adjust_time("not-a-date") == "not-a-date"
