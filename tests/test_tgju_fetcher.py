"""
Tests for src/services/tgju_fetcher.py

All HTTP calls are mocked via unittest.mock to avoid aioresponses/aiohttp
version incompatibilities. Tests cover:
- Successful fetch with full and partial API responses
- Empty / missing data graceful handling
- HTTP error codes (500), timeouts, network errors
- Invalid JSON responses
- Malformed price values
- clean_price edge cases
- Ounce special-case (not divided by 10)
"""

import asyncio

import aiohttp
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from src.services.tgju_fetcher import fetch, clean_price, TGJU_ASSET_MAP

TGJU_URL = "https://call2.tgju.org/ajax.json"


# ── Mock helpers ─────────────────────────────────────────────────────────

def _mock_response(payload=None, status=200, raise_for_status=None,
                    json_side_effect=None):
    """Build a mock aiohttp response."""
    resp = AsyncMock()
    resp.status = status
    if raise_for_status:
        resp.raise_for_status = MagicMock(side_effect=raise_for_status)
    else:
        resp.raise_for_status = MagicMock()
    if json_side_effect:
        resp.json = AsyncMock(side_effect=json_side_effect)
    else:
        resp.json = AsyncMock(return_value=payload)
    return resp


def _mock_session(response=None, get_side_effect=None):
    """Build a mock aiohttp.ClientSession context manager."""
    session = AsyncMock()
    if get_side_effect:
        cm = MagicMock()
        cm.__aenter__ = AsyncMock(side_effect=get_side_effect)
        cm.__aexit__ = AsyncMock(return_value=False)
        session.get = MagicMock(return_value=cm)
    else:
        cm = MagicMock()
        cm.__aenter__ = AsyncMock(return_value=response)
        cm.__aexit__ = AsyncMock(return_value=False)
        session.get = MagicMock(return_value=cm)

    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=session)
    session_cm.__aexit__ = AsyncMock(return_value=False)
    return session_cm


# ── 1. Full successful fetch ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_fetch_success(sample_tgju_response):
    """Fetch with a full 13-asset TGJU response returns all 13 items
    with correct field names, categories, and source tag."""
    resp = _mock_response(payload=sample_tgju_response)
    session_cm = _mock_session(response=resp)

    with patch("src.services.tgju_fetcher.aiohttp.ClientSession", return_value=session_cm):
        results = await fetch()

    assert len(results) == 13

    asset_codes = {r["asset_code"] for r in results}
    expected_codes = {meta["code"] for meta in TGJU_ASSET_MAP.values()}
    assert asset_codes == expected_codes

    required_keys = {
        "asset_code", "asset_name_fa", "category", "price",
        "price_high", "price_low", "change_amount", "change_percent",
        "change_direction", "source", "source_timestamp",
    }
    for item in results:
        assert required_keys.issubset(item.keys()), (
            f"Missing keys in {item['asset_code']}: "
            f"{required_keys - item.keys()}"
        )
        assert item["source"] == "tgju"

    # Spot-check USD: 850,000 / 10 → 85000
    usd = next(r for r in results if r["asset_code"] == "usd")
    assert usd["price"] == "85000"
    assert usd["category"] == "currency"
    assert usd["asset_name_fa"] == "دلار آمریکا"
    assert usd["change_direction"] == "high"
    assert usd["change_percent"] == 0.59
    assert usd["source_timestamp"] == "2026-06-05 12:00:00"


# ── 2. Partial data (only two keys present) ──────────────────────────────


@pytest.mark.asyncio
async def test_fetch_partial_data(sample_tgju_partial_response):
    """When the API returns only a subset of asset keys, fetch returns
    only the matching items without crashing."""
    resp = _mock_response(payload=sample_tgju_partial_response)
    session_cm = _mock_session(response=resp)

    with patch("src.services.tgju_fetcher.aiohttp.ClientSession", return_value=session_cm):
        results = await fetch()

    assert len(results) == 2
    codes = {r["asset_code"] for r in results}
    assert codes == {"usd", "ounce"}


# ── 3. Empty `current` dict ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_fetch_empty_current():
    """An empty 'current' dict yields an empty list."""
    resp = _mock_response(payload={"current": {}})
    session_cm = _mock_session(response=resp)

    with patch("src.services.tgju_fetcher.aiohttp.ClientSession", return_value=session_cm):
        results = await fetch()

    assert results == []


# ── 4. HTTP 500 raises ClientResponseError ────────────────────────────────


@pytest.mark.asyncio
async def test_fetch_http_500():
    """A 500 server error causes raise_for_status() to throw."""
    error = aiohttp.ClientResponseError(
        request_info=MagicMock(), history=(), status=500, message="Internal Server Error"
    )
    resp = _mock_response(status=500, raise_for_status=error)
    session_cm = _mock_session(response=resp)

    with patch("src.services.tgju_fetcher.aiohttp.ClientSession", return_value=session_cm):
        with pytest.raises(aiohttp.ClientResponseError) as exc_info:
            await fetch()
        assert exc_info.value.status == 500


# ── 5. Timeout error propagates ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_fetch_http_timeout():
    """An asyncio.TimeoutError during the request propagates to the caller."""
    session_cm = _mock_session(get_side_effect=asyncio.TimeoutError())

    with patch("src.services.tgju_fetcher.aiohttp.ClientSession", return_value=session_cm):
        with pytest.raises(asyncio.TimeoutError):
            await fetch()


# ── 6. Invalid JSON response ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_fetch_invalid_json():
    """A non-JSON body causes an exception during parsing."""
    resp = _mock_response(json_side_effect=aiohttp.ContentTypeError(
        MagicMock(), MagicMock(), message="Invalid content type"
    ))
    session_cm = _mock_session(response=resp)

    with patch("src.services.tgju_fetcher.aiohttp.ClientSession", return_value=session_cm):
        with pytest.raises(aiohttp.ContentTypeError):
            await fetch()


# ── 7. Malformed prices handled gracefully ────────────────────────────────


@pytest.mark.asyncio
async def test_fetch_malformed_prices():
    """Prices with non-numeric 'p', empty 'p', or missing 'p' key
    should not crash — clean_price returns fallback values."""
    payload = {
        "current": {
            "price_dollar_rl": {
                "p": "abc",       # not a number → clean_price returns "abc"
                "h": "",          # empty → "0"
                "l": "100",       # normal → "10"
                "d": "0",
                "dp": 0.0,
                "dt": "stable",
                "t": "",
            },
            "price_eur": {
                # "p" key missing entirely → defaults to ""
                "h": "500,000",
                "l": "490,000",
                "d": "0",
                "dp": 0.0,
                "dt": "stable",
                "t": "",
            },
        },
    }
    resp = _mock_response(payload=payload)
    session_cm = _mock_session(response=resp)

    with patch("src.services.tgju_fetcher.aiohttp.ClientSession", return_value=session_cm):
        results = await fetch()

    assert len(results) == 2

    usd = next(r for r in results if r["asset_code"] == "usd")
    assert usd["price"] == "abc"       # clean_price("abc") → "abc"
    assert usd["price_high"] == "0"    # clean_price("") → "0"
    assert usd["price_low"] == "10"    # clean_price("100") → "10"

    eur = next(r for r in results if r["asset_code"] == "eur")
    assert eur["price"] == "0"         # clean_price("") → "0"


# ── 8. clean_price unit tests ────────────────────────────────────────────


class TestCleanPriceEdgeCases:
    """Direct unit tests for the clean_price helper."""

    def test_empty_string(self):
        assert clean_price("") == "0"

    def test_comma_separated(self):
        assert clean_price("1,234,567") == "123456"

    def test_non_numeric(self):
        assert clean_price("abc") == "abc"

    def test_large_comma_value(self):
        assert clean_price("52,600,000") == "5260000"

    def test_plain_integer(self):
        assert clean_price("1000") == "100"

    def test_zero(self):
        assert clean_price("0") == "0"

    def test_negative_value(self):
        assert clean_price("-5,000") == "-500"


# ── 9. Ounce price is NOT divided by 10 ──────────────────────────────────


@pytest.mark.asyncio
async def test_fetch_ounce_not_divided():
    """The ounce ('ons') price, high, and low are returned as-is
    without being divided by 10."""
    payload = {
        "current": {
            "ons": {
                "p": "2345.67",
                "h": "2350.00",
                "l": "2340.00",
                "d": "5.00",
                "dp": 0.21,
                "dt": "high",
                "t": "2026-06-05 12:00:00",
            },
        },
    }
    resp = _mock_response(payload=payload)
    session_cm = _mock_session(response=resp)

    with patch("src.services.tgju_fetcher.aiohttp.ClientSession", return_value=session_cm):
        results = await fetch()

    assert len(results) == 1
    ounce = results[0]
    assert ounce["asset_code"] == "ounce"
    assert ounce["price"] == "2345.67"
    assert ounce["price_high"] == "2350.00"
    assert ounce["price_low"] == "2340.00"
    # change_amount for ounce IS still passed through clean_price
    # clean_price("5.00") → int(5.0 // 10) → "0"
    assert ounce["change_amount"] == "0"


# ── 10. Network error propagates ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_fetch_network_error():
    """A generic aiohttp.ClientError propagates to the caller."""
    session_cm = _mock_session(
        get_side_effect=aiohttp.ClientError("Connection refused")
    )

    with patch("src.services.tgju_fetcher.aiohttp.ClientSession", return_value=session_cm):
        with pytest.raises(aiohttp.ClientError):
            await fetch()
