"""
Tests for src.services.price_service — fetch_and_store() orchestration.

Every test mocks both fetchers and both repository helpers so that
nothing touches the network or the database.
"""

import pytest
from unittest.mock import AsyncMock, patch

from src.services.price_service import fetch_and_store


# ---------------------------------------------------------------------------
# Helpers – sample payloads returned by the fetchers
# ---------------------------------------------------------------------------

TGJU_SAMPLE = [
    {"key": "usd", "source": "tgju", "price": 62000},
    {"key": "eur", "source": "tgju", "price": 68000},
]

NERKH_SAMPLE = [
    {"key": "gold_18k", "source": "nerkh", "price": 4500000},
]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("src.services.price_service.ErrorRepository.log_error", new_callable=AsyncMock)
@patch("src.services.price_service.PriceRepository.upsert_many", new_callable=AsyncMock)
@patch("src.services.price_service.nerkh_fetcher.fetch", new_callable=AsyncMock)
@patch("src.services.price_service.tgju_fetcher.fetch", new_callable=AsyncMock)
async def test_fetch_and_store_both_succeed(
    mock_tgju_fetch,
    mock_nerkh_fetch,
    mock_upsert_many,
    mock_log_error,
):
    """When both fetchers return data, upsert_many is called twice and no
    errors are logged."""
    mock_tgju_fetch.return_value = TGJU_SAMPLE
    mock_nerkh_fetch.return_value = NERKH_SAMPLE

    await fetch_and_store()

    assert mock_upsert_many.call_count == 2
    mock_upsert_many.assert_any_call(TGJU_SAMPLE)
    mock_upsert_many.assert_any_call(NERKH_SAMPLE)
    mock_log_error.assert_not_called()


@pytest.mark.asyncio
@patch("src.services.price_service.ErrorRepository.log_error", new_callable=AsyncMock)
@patch("src.services.price_service.PriceRepository.upsert_many", new_callable=AsyncMock)
@patch("src.services.price_service.nerkh_fetcher.fetch", new_callable=AsyncMock)
@patch("src.services.price_service.tgju_fetcher.fetch", new_callable=AsyncMock)
async def test_fetch_and_store_tgju_fails(
    mock_tgju_fetch,
    mock_nerkh_fetch,
    mock_upsert_many,
    mock_log_error,
):
    """When tgju raises RuntimeError, its error is logged and nerkh data
    is still stored via upsert_many."""
    mock_tgju_fetch.side_effect = RuntimeError("tgju timeout")
    mock_nerkh_fetch.return_value = NERKH_SAMPLE

    await fetch_and_store()

    # Error logged for tgju
    mock_log_error.assert_called_once_with("tgju", "tgju timeout", "RuntimeError")

    # Nerkh data still persisted
    mock_upsert_many.assert_called_once_with(NERKH_SAMPLE)


@pytest.mark.asyncio
@patch("src.services.price_service.ErrorRepository.log_error", new_callable=AsyncMock)
@patch("src.services.price_service.PriceRepository.upsert_many", new_callable=AsyncMock)
@patch("src.services.price_service.nerkh_fetcher.fetch", new_callable=AsyncMock)
@patch("src.services.price_service.tgju_fetcher.fetch", new_callable=AsyncMock)
async def test_fetch_and_store_nerkh_fails(
    mock_tgju_fetch,
    mock_nerkh_fetch,
    mock_upsert_many,
    mock_log_error,
):
    """When nerkh raises ConnectionError, its error is logged and tgju
    data is still stored via upsert_many."""
    mock_tgju_fetch.return_value = TGJU_SAMPLE
    mock_nerkh_fetch.side_effect = ConnectionError("nerkh unreachable")

    await fetch_and_store()

    # Error logged for nerkh
    mock_log_error.assert_called_once_with("nerkh", "nerkh unreachable", "ConnectionError")

    # TGJU data still persisted
    mock_upsert_many.assert_called_once_with(TGJU_SAMPLE)


@pytest.mark.asyncio
@patch("src.services.price_service.ErrorRepository.log_error", new_callable=AsyncMock)
@patch("src.services.price_service.PriceRepository.upsert_many", new_callable=AsyncMock)
@patch("src.services.price_service.nerkh_fetcher.fetch", new_callable=AsyncMock)
@patch("src.services.price_service.tgju_fetcher.fetch", new_callable=AsyncMock)
async def test_fetch_and_store_both_fail(
    mock_tgju_fetch,
    mock_nerkh_fetch,
    mock_upsert_many,
    mock_log_error,
):
    """When both fetchers raise, both errors are logged, upsert_many is
    never called, and no unhandled exception escapes."""
    mock_tgju_fetch.side_effect = RuntimeError("tgju down")
    mock_nerkh_fetch.side_effect = ConnectionError("nerkh down")

    await fetch_and_store()  # must not raise

    assert mock_log_error.call_count == 2
    mock_log_error.assert_any_call("tgju", "tgju down", "RuntimeError")
    mock_log_error.assert_any_call("nerkh", "nerkh down", "ConnectionError")
    mock_upsert_many.assert_not_called()


@pytest.mark.asyncio
@patch("src.services.price_service.ErrorRepository.log_error", new_callable=AsyncMock)
@patch("src.services.price_service.PriceRepository.upsert_many", new_callable=AsyncMock)
@patch("src.services.price_service.nerkh_fetcher.fetch", new_callable=AsyncMock)
@patch("src.services.price_service.tgju_fetcher.fetch", new_callable=AsyncMock)
async def test_fetch_and_store_nerkh_empty(
    mock_tgju_fetch,
    mock_nerkh_fetch,
    mock_upsert_many,
    mock_log_error,
):
    """When nerkh returns an empty list, upsert_many is called only once
    (for tgju) because `if nerkh_result:` guards the nerkh branch."""
    mock_tgju_fetch.return_value = TGJU_SAMPLE
    mock_nerkh_fetch.return_value = []  # empty → skipped

    await fetch_and_store()

    # Only tgju data persisted
    mock_upsert_many.assert_called_once_with(TGJU_SAMPLE)
    mock_log_error.assert_not_called()


@pytest.mark.asyncio
@patch("src.services.price_service.ErrorRepository.log_error", new_callable=AsyncMock)
@patch("src.services.price_service.PriceRepository.upsert_many", new_callable=AsyncMock)
@patch("src.services.price_service.nerkh_fetcher.fetch", new_callable=AsyncMock)
@patch("src.services.price_service.tgju_fetcher.fetch", new_callable=AsyncMock)
async def test_error_logged_with_correct_type(
    mock_tgju_fetch,
    mock_nerkh_fetch,
    mock_upsert_many,
    mock_log_error,
):
    """The third argument to log_error must be the exception class name
    (e.g. 'ValueError'), not a generic string."""
    mock_tgju_fetch.side_effect = ValueError("bad")
    mock_nerkh_fetch.return_value = NERKH_SAMPLE

    await fetch_and_store()

    mock_log_error.assert_called_once_with("tgju", "bad", "ValueError")
