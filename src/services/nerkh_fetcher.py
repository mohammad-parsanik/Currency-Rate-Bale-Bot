"""
nerkh_fetcher.py — Data fetcher for nerkh.io

Fetches real-time Iranian currency, gold, and coin prices from the Nerkh.io
API. Requires a Bearer token set via the NERKH_API_TOKEN environment variable.
If the token is absent the fetcher skips gracefully (returns an empty list).

Expected API response structure (`/v1/prices/json/all`):
    {
        "data": {
            "currencies": {
                "USD": {
                    "current":        <int>,         # Current price in Rial
                    "max":            {"12hour": <int>},
                    "min":            {"12hour": <int>},
                    "change":         <int>,          # Absolute change in Rial
                    "change_percent": <float>,
                    "updated_at":     "<ISO datetime>"
                },
                ...
            },
            "golds":   { ... },   # Same structure as currencies
            "coins":   { ... }    # Same structure as currencies
        }
    }

Gold ounce ("OUNCE") is priced in USD and is NOT converted to Toman.
All other prices are Rial; divided by 10 → Toman.
"""

import aiohttp
import logging
from src.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Asset mapping: nerkh.io symbol → internal schema
#
# "code"     — must match the TGJU_ASSET_MAP "code" for the same asset,
#              because (asset_code, source) is the primary key in the DB.
# "name"     — Farsi display name
# "category" — one of "currency" | "gold" | "coin"
# ---------------------------------------------------------------------------
NERKH_ASSET_MAP = {
    # Currencies
    "USD":       {"code": "usd",           "name": "دلار آمریکا",   "category": "currency"},
    "EUR":       {"code": "eur",           "name": "یورو",           "category": "currency"},
    "AED":       {"code": "aed",           "name": "درهم امارات",   "category": "currency"},
    "GBP":       {"code": "gbp",           "name": "پوند انگلیس",   "category": "currency"},

    # Gold
    "GOLD18K":   {"code": "gold_18k_sell", "name": "طلای ۱۸ عیار", "category": "gold"},
    "MAZANEH":   {"code": "mesghal",       "name": "مثقال طلا",     "category": "gold"},
    "OUNCE":     {"code": "ounce",         "name": "انس جهانی طلا", "category": "gold"},  # USD

    # Coins
    "SEKE_EMAMI": {"code": "coin_emami",  "name": "سکه امامی",       "category": "coin"},
    "SEKE_BAHAR": {"code": "coin_bahar",  "name": "سکه بهار آزادی", "category": "coin"},
    "SEKE_NIM":   {"code": "coin_nim",    "name": "نیم سکه",         "category": "coin"},
    "SEKE_ROB":   {"code": "coin_rob",    "name": "ربع سکه",         "category": "coin"},
    "SEKE_1G":    {"code": "coin_gerami", "name": "سکه گرمی",        "category": "coin"},
}


def clean_price(val, divide_by_10: bool = False) -> str:
    """Convert a raw Nerkh.io price value to a clean integer string.

    Args:
        val:           Raw value from the API (int, float, or string).
        divide_by_10:  If True, converts Rial to Toman by integer-dividing by 10.
                       Should be True for all assets except the gold ounce (USD).

    Returns:
        Integer value as a string, or "0" if val is None.
    """
    if val is None:
        return "0"
    try:
        f = float(val)
        if divide_by_10:
            return str(int(f // 10))
        return str(int(f))
    except ValueError:
        return str(val)


async def fetch() -> list[dict]:
    """Fetch and normalise all tracked assets from the Nerkh.io API.

    Returns an empty list (without raising) if NERKH_API_TOKEN is not set.

    The function parses the nested `data.<category>.<symbol>` structure
    returned by `/v1/prices/json/all`, flattening it into the same format
    as tgju_fetcher.fetch() so both can be passed to PriceRepository.upsert_many().

    Returns:
        A list of price dicts. An exception is raised on HTTP failure —
        callers should catch it via asyncio.gather(return_exceptions=True).
    """
    if not settings.NERKH_API_TOKEN:
        logger.warning("No Nerkh.io API token provided. Skipping nerkh fetch.")
        return []

    logger.info("Fetching from Nerkh.io API...")
    headers = {
        "Authorization": f"Bearer {settings.NERKH_API_TOKEN}"
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(settings.NERKH_URL, headers=headers, timeout=15) as response:
            response.raise_for_status()
            data = await response.json()

    # ---------------------------------------------------------------------------
    # Parse the response into a flat {symbol: item_dict} mapping.
    #
    # The `/all` endpoint wraps data in nested category dicts:
    #   data.currencies.USD, data.golds.GOLD18K, data.coins.SEKE_EMAMI, ...
    #
    # We merge all categories into one flat dict keyed by symbol so we can
    # look up each symbol from NERKH_ASSET_MAP in O(1).
    # ---------------------------------------------------------------------------
    items: dict = {}
    if "data" in data and isinstance(data["data"], dict):
        for _category_name, items_dict in data["data"].items():
            if isinstance(items_dict, dict):
                for symbol, details in items_dict.items():
                    # Only include entries that have a "current" price field
                    if isinstance(details, dict) and "current" in details:
                        items[symbol] = details
    else:
        # Fallback: assume the top-level object is already a flat symbol map
        items = data

    results = []

    for symbol, meta in NERKH_ASSET_MAP.items():
        item = items.get(symbol)
        if not item:
            # Symbol not present in the API response — skip silently
            continue

        p = item.get("current", "")

        # Gold/coin prices are Rial → Toman; ounce is USD (no conversion)
        is_rial = symbol != "OUNCE" and meta["category"] in ["gold", "coin"]

        if symbol == "OUNCE":
            price_str = str(p)
        else:
            price_str = clean_price(p, divide_by_10=is_rial)

        # 12-hour high/low are nested under max/min dicts
        max_val = item.get("max", {}).get("12hour", "")
        min_val = item.get("min", {}).get("12hour", "")
        h = clean_price(max_val, divide_by_10=is_rial) if symbol != "OUNCE" else str(max_val)
        l = clean_price(min_val, divide_by_10=is_rial) if symbol != "OUNCE" else str(min_val)

        change_val = item.get("change", 0)

        results.append({
            "asset_code":       meta["code"],
            "asset_name_fa":    meta["name"],
            "category":         meta["category"],
            "price":            price_str,
            "price_high":       h,
            "price_low":        l,
            "change_amount":    clean_price(change_val, divide_by_10=is_rial),
            "change_percent":   item.get("change_percent", 0.0),
            # Derive direction from the sign of change_val
            "change_direction": "high" if float(change_val or 0) > 0 else (
                                "low"  if float(change_val or 0) < 0 else "stable"),
            "source":           "nerkh",
            "source_timestamp": item.get("updated_at", ""),
        })

    return results
