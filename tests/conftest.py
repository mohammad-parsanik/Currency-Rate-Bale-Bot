"""
Shared test fixtures for the Currency Rate Bale Bot test suite.

All tests use mocked HTTP and a temporary SQLite database —
no network calls, no file artifacts.
"""
import os
import asyncio
import pytest
import pytest_asyncio
from unittest.mock import patch, AsyncMock
from aioresponses import aioresponses


# ---------------------------------------------------------------------------
# Event-loop scope: use a single loop for the whole test session
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ---------------------------------------------------------------------------
# Database – temp file per test so every test starts with a clean schema
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture
async def db(tmp_path):
    """Initialize a fresh in-test database and patch settings to use it."""
    db_file = str(tmp_path / "test.db")
    with patch("src.config.settings.DB_PATH", db_file), \
         patch("src.database.connection.settings.DB_PATH", db_file):
        from src.database.connection import init_db
        await init_db()
        yield db_file


# ---------------------------------------------------------------------------
# HTTP mocking
# ---------------------------------------------------------------------------
@pytest.fixture
def mock_aiohttp():
    """Yields an aioresponses context manager for mocking aiohttp requests."""
    with aioresponses() as m:
        yield m


# ---------------------------------------------------------------------------
# Sample TGJU API response
# ---------------------------------------------------------------------------
@pytest.fixture
def sample_tgju_response():
    """A realistic TGJU JSON response with a few assets."""
    return {
        "current": {
            "price_dollar_rl": {
                "p": "850,000",
                "h": "855,000",
                "l": "845,000",
                "d": "5,000",
                "dp": 0.59,
                "dt": "high",
                "t": "2026-06-05 12:00:00"
            },
            "price_eur": {
                "p": "920,000",
                "h": "925,000",
                "l": "915,000",
                "d": "-3,000",
                "dp": -0.33,
                "dt": "low",
                "t": "2026-06-05 12:00:00"
            },
            "price_aed": {
                "p": "232,000",
                "h": "234,000",
                "l": "230,000",
                "d": "0",
                "dp": 0.0,
                "dt": "stable",
                "t": "2026-06-05 12:00:00"
            },
            "price_gbp": {
                "p": "1,080,000",
                "h": "1,085,000",
                "l": "1,075,000",
                "d": "2,000",
                "dp": 0.19,
                "dt": "high",
                "t": "2026-06-05 12:00:00"
            },
            "tgju_gold_irg18": {
                "p": "52,600,000",
                "h": "53,000,000",
                "l": "52,000,000",
                "d": "200,000",
                "dp": 0.38,
                "dt": "high",
                "t": "2026-06-05 12:00:00"
            },
            "tgju_gold_irg18_buy": {
                "p": "52,100,000",
                "h": "52,500,000",
                "l": "51,800,000",
                "d": "100,000",
                "dp": 0.19,
                "dt": "high",
                "t": "2026-06-05 12:00:00"
            },
            "mesghal": {
                "p": "228,500,000",
                "h": "229,000,000",
                "l": "228,000,000",
                "d": "500,000",
                "dp": 0.22,
                "dt": "high",
                "t": "2026-06-05 12:00:00"
            },
            "ons": {
                "p": "2345.67",
                "h": "2350.00",
                "l": "2340.00",
                "d": "5.00",
                "dp": 0.21,
                "dt": "high",
                "t": "2026-06-05 12:00:00"
            },
            "sekee": {
                "p": "380,000,000",
                "h": "385,000,000",
                "l": "375,000,000",
                "d": "2,000,000",
                "dp": 0.53,
                "dt": "high",
                "t": "2026-06-05 12:00:00"
            },
            "sekeb": {
                "p": "340,000,000",
                "h": "345,000,000",
                "l": "335,000,000",
                "d": "-1,000,000",
                "dp": -0.29,
                "dt": "low",
                "t": "2026-06-05 12:00:00"
            },
            "nim": {
                "p": "220,000,000",
                "h": "222,000,000",
                "l": "218,000,000",
                "d": "0",
                "dp": 0.0,
                "dt": "stable",
                "t": "2026-06-05 12:00:00"
            },
            "rob": {
                "p": "140,000,000",
                "h": "142,000,000",
                "l": "138,000,000",
                "d": "500,000",
                "dp": 0.36,
                "dt": "high",
                "t": "2026-06-05 12:00:00"
            },
            "retail_gerami": {
                "p": "98,000,000",
                "h": "99,000,000",
                "l": "97,000,000",
                "d": "-200,000",
                "dp": -0.20,
                "dt": "low",
                "t": "2026-06-05 12:00:00"
            }
        }
    }


@pytest.fixture
def sample_tgju_partial_response():
    """TGJU response missing several asset keys."""
    return {
        "current": {
            "price_dollar_rl": {
                "p": "850,000",
                "h": "855,000",
                "l": "845,000",
                "d": "5,000",
                "dp": 0.59,
                "dt": "high",
                "t": "2026-06-05 12:00:00"
            },
            "ons": {
                "p": "2345.67",
                "h": "2350.00",
                "l": "2340.00",
                "d": "5.00",
                "dp": 0.21,
                "dt": "high",
                "t": "2026-06-05 12:00:00"
            }
        }
    }


# ---------------------------------------------------------------------------
# Sample Nerkh API response
# ---------------------------------------------------------------------------
@pytest.fixture
def sample_nerkh_response():
    """A realistic Nerkh.io JSON response."""
    return {
        "data": {
            "currencies": {
                "USD": {
                    "current": 850000,
                    "max": {"12hour": 855000},
                    "min": {"12hour": 845000},
                    "change": 5000,
                    "change_percent": 0.59,
                    "updated_at": "2026-06-05T12:00:00Z"
                },
                "EUR": {
                    "current": 920000,
                    "max": {"12hour": 925000},
                    "min": {"12hour": 915000},
                    "change": -3000,
                    "change_percent": -0.33,
                    "updated_at": "2026-06-05T12:00:00Z"
                },
                "AED": {
                    "current": 232000,
                    "max": {"12hour": 234000},
                    "min": {"12hour": 230000},
                    "change": 0,
                    "change_percent": 0.0,
                    "updated_at": "2026-06-05T12:00:00Z"
                },
                "GBP": {
                    "current": 1080000,
                    "max": {"12hour": 1085000},
                    "min": {"12hour": 1075000},
                    "change": 2000,
                    "change_percent": 0.19,
                    "updated_at": "2026-06-05T12:00:00Z"
                }
            },
            "golds": {
                "GOLD18K": {
                    "current": 52600000,
                    "max": {"12hour": 53000000},
                    "min": {"12hour": 52000000},
                    "change": 200000,
                    "change_percent": 0.38,
                    "updated_at": "2026-06-05T12:00:00Z"
                },
                "MAZANEH": {
                    "current": 228500000,
                    "max": {"12hour": 229000000},
                    "min": {"12hour": 228000000},
                    "change": 500000,
                    "change_percent": 0.22,
                    "updated_at": "2026-06-05T12:00:00Z"
                },
                "OUNCE": {
                    "current": 2345.67,
                    "max": {"12hour": 2350.00},
                    "min": {"12hour": 2340.00},
                    "change": 5.00,
                    "change_percent": 0.21,
                    "updated_at": "2026-06-05T12:00:00Z"
                }
            },
            "coins": {
                "SEKE_EMAMI": {
                    "current": 380000000,
                    "max": {"12hour": 385000000},
                    "min": {"12hour": 375000000},
                    "change": 2000000,
                    "change_percent": 0.53,
                    "updated_at": "2026-06-05T12:00:00Z"
                },
                "SEKE_BAHAR": {
                    "current": 340000000,
                    "max": {"12hour": 345000000},
                    "min": {"12hour": 335000000},
                    "change": -1000000,
                    "change_percent": -0.29,
                    "updated_at": "2026-06-05T12:00:00Z"
                },
                "SEKE_NIM": {
                    "current": 220000000,
                    "max": {"12hour": 222000000},
                    "min": {"12hour": 218000000},
                    "change": 0,
                    "change_percent": 0.0,
                    "updated_at": "2026-06-05T12:00:00Z"
                },
                "SEKE_ROB": {
                    "current": 140000000,
                    "max": {"12hour": 142000000},
                    "min": {"12hour": 138000000},
                    "change": 500000,
                    "change_percent": 0.36,
                    "updated_at": "2026-06-05T12:00:00Z"
                },
                "SEKE_1G": {
                    "current": 98000000,
                    "max": {"12hour": 99000000},
                    "min": {"12hour": 97000000},
                    "change": -200000,
                    "change_percent": -0.20,
                    "updated_at": "2026-06-05T12:00:00Z"
                }
            }
        }
    }


# ---------------------------------------------------------------------------
# Sample price dicts (as stored in DB / returned by repositories)
# ---------------------------------------------------------------------------
@pytest.fixture
def sample_prices():
    """Price dicts matching the schema used throughout the app."""
    return [
        {
            "asset_code": "usd",
            "asset_name_fa": "دلار آمریکا",
            "category": "currency",
            "price": "85000",
            "price_high": "85500",
            "price_low": "84500",
            "change_amount": "500",
            "change_percent": 0.59,
            "change_direction": "high",
            "source": "tgju",
            "source_timestamp": "2026-06-05 12:00:00",
            "fetched_at": "2026-06-05 12:01:00"
        },
        {
            "asset_code": "eur",
            "asset_name_fa": "یورو",
            "category": "currency",
            "price": "92000",
            "price_high": "92500",
            "price_low": "91500",
            "change_amount": "-300",
            "change_percent": -0.33,
            "change_direction": "low",
            "source": "tgju",
            "source_timestamp": "2026-06-05 12:00:00",
            "fetched_at": "2026-06-05 12:01:00"
        },
        {
            "asset_code": "gold_18k_sell",
            "asset_name_fa": "طلای ۱۸ عیار (فروش)",
            "category": "gold",
            "price": "5260000",
            "price_high": "5300000",
            "price_low": "5200000",
            "change_amount": "20000",
            "change_percent": 0.38,
            "change_direction": "high",
            "source": "tgju",
            "source_timestamp": "2026-06-05 12:00:00",
            "fetched_at": "2026-06-05 12:01:00"
        },
        {
            "asset_code": "ounce",
            "asset_name_fa": "انس جهانی طلا",
            "category": "gold",
            "price": "2345.67",
            "price_high": "2350.00",
            "price_low": "2340.00",
            "change_amount": "5",
            "change_percent": 0.21,
            "change_direction": "high",
            "source": "tgju",
            "source_timestamp": "2026-06-05 12:00:00",
            "fetched_at": "2026-06-05 12:01:00"
        },
        {
            "asset_code": "coin_emami",
            "asset_name_fa": "سکه امامی",
            "category": "coin",
            "price": "38000000",
            "price_high": "38500000",
            "price_low": "37500000",
            "change_amount": "200000",
            "change_percent": 0.53,
            "change_direction": "high",
            "source": "tgju",
            "source_timestamp": "2026-06-05 12:00:00",
            "fetched_at": "2026-06-05 12:01:00"
        },
    ]


# ---------------------------------------------------------------------------
# Bale Client fixture
# ---------------------------------------------------------------------------
@pytest.fixture
def bale_client():
    """Returns a BaleClient instance with a dummy token."""
    from src.bot.client import BaleClient
    return BaleClient("DUMMY_TOKEN_12345")


# ---------------------------------------------------------------------------
# Sample Bale update payloads
# ---------------------------------------------------------------------------
@pytest.fixture
def sample_message_update():
    """A Bale update containing a text message."""
    return {
        "update_id": 100,
        "message": {
            "message_id": 1,
            "from": {
                "id": 12345,
                "first_name": "علی",
                "last_name": "محمدی",
                "username": "ali_m"
            },
            "chat": {"id": 12345},
            "text": "/start"
        }
    }


@pytest.fixture
def sample_callback_update():
    """A Bale update containing a callback query."""
    return {
        "update_id": 101,
        "callback_query": {
            "id": "cb_001",
            "from": {
                "id": 12345,
                "first_name": "علی",
                "last_name": "محمدی",
                "username": "ali_m"
            },
            "message": {
                "message_id": 50,
                "chat": {"id": 12345}
            },
            "data": "all"
        }
    }
