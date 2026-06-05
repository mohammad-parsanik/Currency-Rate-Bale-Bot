"""
Tests for src/services/nerkh_fetcher.py

All HTTP calls are mocked via unittest.mock to avoid aioresponses/aiohttp
version incompatibilities. Tests cover:
- Successful fetch with all 12 mapped assets
- No-token early return
- HTTP error codes (401, 500)
- Timeout handling
- Invalid JSON responses
- Flat dict (no "data" key) format parsing
- Partial asset responses
- clean_price with divide_by_10 and None input
- Change direction logic (high / low / stable)
- Missing nested max/min fields
"""

import asyncio
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from src.services.nerkh_fetcher import fetch, clean_price, NERKH_ASSET_MAP


NERKH_URL = "https://api.nerkh.io/v1/prices/json/all"


# ---- helpers ---------------------------------------------------------------

def _build_flat_response(*symbols):
    """Build a flat dict (no 'data' wrapper) with the given symbols."""
    out = {}
    for sym in symbols:
        out[sym] = {
            "current": 100000,
            "max": {"12hour": 110000},
            "min": {"12hour": 90000},
            "change": 500,
            "change_percent": 0.5,
            "updated_at": "2026-06-05T12:00:00Z",
        }
    return out


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
    return session_cm, session


# ---- clean_price -----------------------------------------------------------

class TestCleanPrice:
    """Unit tests for the clean_price helper."""

    def test_clean_price_divide_by_10(self):
        assert clean_price(520000, divide_by_10=True) == "52000"

    def test_clean_price_no_divide(self):
        assert clean_price(520000, divide_by_10=False) == "520000"

    def test_clean_price_none_returns_zero(self):
        assert clean_price(None) == "0"
        assert clean_price(None, divide_by_10=True) == "0"

    def test_clean_price_string_number(self):
        assert clean_price("123456") == "123456"
        assert clean_price("123456", divide_by_10=True) == "12345"

    def test_clean_price_invalid_value(self):
        assert clean_price("N/A") == "N/A"
        assert clean_price("---") == "---"


# ---- fetch -----------------------------------------------------------------

class TestFetch:
    """Tests for the async fetch() function."""

    @pytest.mark.asyncio
    async def test_fetch_success(self, sample_nerkh_response):
        """200 response with full payload returns all 12 mapped assets."""
        resp = _mock_response(payload=sample_nerkh_response)
        session_cm, _ = _mock_session(response=resp)

        with patch("src.services.nerkh_fetcher.settings") as mock_settings, \
             patch("src.services.nerkh_fetcher.aiohttp.ClientSession", return_value=session_cm):
            mock_settings.NERKH_API_TOKEN = "test-token"
            mock_settings.NERKH_URL = NERKH_URL

            results = await fetch()

        assert len(results) == 12
        codes = {r["asset_code"] for r in results}
        expected_codes = {meta["code"] for meta in NERKH_ASSET_MAP.values()}
        assert codes == expected_codes

        required_keys = {
            "asset_code", "asset_name_fa", "category", "price",
            "price_high", "price_low", "change_amount", "change_percent",
            "change_direction", "source", "source_timestamp",
        }
        for r in results:
            assert required_keys.issubset(r.keys())
            assert r["source"] == "nerkh"

    @pytest.mark.asyncio
    async def test_fetch_no_token(self):
        """Empty NERKH_API_TOKEN returns [] and makes no HTTP call."""
        with patch("src.services.nerkh_fetcher.settings") as mock_settings:
            mock_settings.NERKH_API_TOKEN = ""
            mock_settings.NERKH_URL = NERKH_URL

            results = await fetch()

        assert results == []

    @pytest.mark.asyncio
    async def test_fetch_auth_failure_401(self):
        """401 response raises via raise_for_status."""
        from aiohttp import ClientResponseError
        error = ClientResponseError(
            request_info=MagicMock(), history=(), status=401, message="Unauthorized"
        )
        resp = _mock_response(status=401, raise_for_status=error)
        session_cm, _ = _mock_session(response=resp)

        with patch("src.services.nerkh_fetcher.settings") as mock_settings, \
             patch("src.services.nerkh_fetcher.aiohttp.ClientSession", return_value=session_cm):
            mock_settings.NERKH_API_TOKEN = "bad-token"
            mock_settings.NERKH_URL = NERKH_URL

            with pytest.raises(ClientResponseError) as exc_info:
                await fetch()
            assert exc_info.value.status == 401

    @pytest.mark.asyncio
    async def test_fetch_http_500(self):
        """500 server error raises via raise_for_status."""
        from aiohttp import ClientResponseError
        error = ClientResponseError(
            request_info=MagicMock(), history=(), status=500, message="Internal Server Error"
        )
        resp = _mock_response(status=500, raise_for_status=error)
        session_cm, _ = _mock_session(response=resp)

        with patch("src.services.nerkh_fetcher.settings") as mock_settings, \
             patch("src.services.nerkh_fetcher.aiohttp.ClientSession", return_value=session_cm):
            mock_settings.NERKH_API_TOKEN = "test-token"
            mock_settings.NERKH_URL = NERKH_URL

            with pytest.raises(ClientResponseError) as exc_info:
                await fetch()
            assert exc_info.value.status == 500

    @pytest.mark.asyncio
    async def test_fetch_timeout(self):
        """Network timeout raises asyncio.TimeoutError."""
        session_cm, _ = _mock_session(get_side_effect=asyncio.TimeoutError())

        with patch("src.services.nerkh_fetcher.settings") as mock_settings, \
             patch("src.services.nerkh_fetcher.aiohttp.ClientSession", return_value=session_cm):
            mock_settings.NERKH_API_TOKEN = "test-token"
            mock_settings.NERKH_URL = NERKH_URL

            with pytest.raises(asyncio.TimeoutError):
                await fetch()

    @pytest.mark.asyncio
    async def test_fetch_invalid_json(self):
        """Non-JSON body raises an error during parsing."""
        resp = _mock_response(json_side_effect=Exception("Invalid JSON"))
        session_cm, _ = _mock_session(response=resp)

        with patch("src.services.nerkh_fetcher.settings") as mock_settings, \
             patch("src.services.nerkh_fetcher.aiohttp.ClientSession", return_value=session_cm):
            mock_settings.NERKH_API_TOKEN = "test-token"
            mock_settings.NERKH_URL = NERKH_URL

            with pytest.raises(Exception):
                await fetch()

    @pytest.mark.asyncio
    async def test_fetch_flat_dict_format(self):
        """Top-level dict without 'data' key is parsed via the flat path."""
        flat_payload = _build_flat_response("USD", "EUR", "GOLD18K")
        resp = _mock_response(payload=flat_payload)
        session_cm, _ = _mock_session(response=resp)

        with patch("src.services.nerkh_fetcher.settings") as mock_settings, \
             patch("src.services.nerkh_fetcher.aiohttp.ClientSession", return_value=session_cm):
            mock_settings.NERKH_API_TOKEN = "test-token"
            mock_settings.NERKH_URL = NERKH_URL

            results = await fetch()

        codes = {r["asset_code"] for r in results}
        assert codes == {"usd", "eur", "gold_18k_sell"}
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_fetch_partial_assets(self):
        """Response containing only USD and EUR yields exactly 2 items."""
        partial_payload = {
            "data": {
                "currencies": {
                    "USD": {
                        "current": 850000,
                        "max": {"12hour": 855000},
                        "min": {"12hour": 845000},
                        "change": 5000,
                        "change_percent": 0.59,
                        "updated_at": "2026-06-05T12:00:00Z",
                    },
                    "EUR": {
                        "current": 920000,
                        "max": {"12hour": 925000},
                        "min": {"12hour": 915000},
                        "change": -3000,
                        "change_percent": -0.33,
                        "updated_at": "2026-06-05T12:00:00Z",
                    },
                }
            }
        }
        resp = _mock_response(payload=partial_payload)
        session_cm, _ = _mock_session(response=resp)

        with patch("src.services.nerkh_fetcher.settings") as mock_settings, \
             patch("src.services.nerkh_fetcher.aiohttp.ClientSession", return_value=session_cm):
            mock_settings.NERKH_API_TOKEN = "test-token"
            mock_settings.NERKH_URL = NERKH_URL

            results = await fetch()

        assert len(results) == 2
        codes = {r["asset_code"] for r in results}
        assert codes == {"usd", "eur"}

    @pytest.mark.asyncio
    async def test_change_direction_logic(self):
        """Verify change_direction: positive→high, negative→low, zero→stable."""
        payload = {
            "data": {
                "currencies": {
                    "USD": {
                        "current": 850000,
                        "max": {"12hour": 855000}, "min": {"12hour": 845000},
                        "change": 5000, "change_percent": 0.59, "updated_at": "",
                    },
                    "EUR": {
                        "current": 920000,
                        "max": {"12hour": 925000}, "min": {"12hour": 915000},
                        "change": -3000, "change_percent": -0.33, "updated_at": "",
                    },
                    "AED": {
                        "current": 232000,
                        "max": {"12hour": 234000}, "min": {"12hour": 230000},
                        "change": 0, "change_percent": 0.0, "updated_at": "",
                    },
                }
            }
        }
        resp = _mock_response(payload=payload)
        session_cm, _ = _mock_session(response=resp)

        with patch("src.services.nerkh_fetcher.settings") as mock_settings, \
             patch("src.services.nerkh_fetcher.aiohttp.ClientSession", return_value=session_cm):
            mock_settings.NERKH_API_TOKEN = "test-token"
            mock_settings.NERKH_URL = NERKH_URL

            results = await fetch()

        direction_map = {r["asset_code"]: r["change_direction"] for r in results}
        assert direction_map["usd"] == "high"
        assert direction_map["eur"] == "low"
        assert direction_map["aed"] == "stable"

    @pytest.mark.asyncio
    async def test_fetch_missing_nested_fields(self):
        """Items with max/min keys entirely missing default gracefully."""
        payload = {
            "data": {
                "currencies": {
                    "USD": {
                        "current": 850000,
                        # "max" and "min" keys missing
                        "change": 0,
                        "change_percent": 0.0,
                        "updated_at": "",
                    },
                }
            }
        }
        resp = _mock_response(payload=payload)
        session_cm, _ = _mock_session(response=resp)

        with patch("src.services.nerkh_fetcher.settings") as mock_settings, \
             patch("src.services.nerkh_fetcher.aiohttp.ClientSession", return_value=session_cm):
            mock_settings.NERKH_API_TOKEN = "test-token"
            mock_settings.NERKH_URL = NERKH_URL

            results = await fetch()

        assert len(results) == 1
        usd = results[0]
        assert usd["price"] == "850000"
        assert usd["change_direction"] == "stable"

    @pytest.mark.asyncio
    async def test_gold_coin_rial_division(self, sample_nerkh_response):
        """Gold/coin items (except OUNCE) have prices divided by 10."""
        resp = _mock_response(payload=sample_nerkh_response)
        session_cm, _ = _mock_session(response=resp)

        with patch("src.services.nerkh_fetcher.settings") as mock_settings, \
             patch("src.services.nerkh_fetcher.aiohttp.ClientSession", return_value=session_cm):
            mock_settings.NERKH_API_TOKEN = "test-token"
            mock_settings.NERKH_URL = NERKH_URL

            results = await fetch()

        by_code = {r["asset_code"]: r for r in results}

        # GOLD18K: current=52600000, is_rial=True → 52600000 // 10 = 5260000
        assert by_code["gold_18k_sell"]["price"] == "5260000"
        # SEKE_EMAMI: current=380000000 → 38000000
        assert by_code["coin_emami"]["price"] == "38000000"
        # OUNCE: returned as-is
        assert by_code["ounce"]["price"] == "2345.67"
        # Currencies: no division
        assert by_code["usd"]["price"] == "850000"

    @pytest.mark.asyncio
    async def test_fetch_bearer_auth_header(self, sample_nerkh_response):
        """Verify the Authorization: Bearer header is sent with the request."""
        resp = _mock_response(payload=sample_nerkh_response)
        session_cm, session = _mock_session(response=resp)

        with patch("src.services.nerkh_fetcher.settings") as mock_settings, \
             patch("src.services.nerkh_fetcher.aiohttp.ClientSession", return_value=session_cm):
            mock_settings.NERKH_API_TOKEN = "my-secret-token"
            mock_settings.NERKH_URL = NERKH_URL

            await fetch()

        # Check the headers passed to session.get()
        session.get.assert_called_once()
        call_kwargs = session.get.call_args
        headers = call_kwargs[1].get("headers", {}) if call_kwargs[1] else call_kwargs.kwargs.get("headers", {})
        assert headers.get("Authorization") == "Bearer my-secret-token"
