"""
tgju_fetcher.py — Data fetcher for tgju.org

Fetches real-time Iranian currency, gold, and coin prices from the public
TGJU API endpoint (no authentication required).

Response structure:
    {
        "current": {
            "<tgju_key>": {
                "p": "<price_rial>",   # Current price in Rial (comma-separated)
                "h": "<high_rial>",    # Day high in Rial
                "l": "<low_rial>",     # Day low in Rial
                "d": "<change_rial>",  # Absolute change in Rial
                "dp": <float>,         # Change percentage (signed)
                "dt": "<direction>",   # "high" | "low" | "stable"
                "t": "<datetime>"      # Source timestamp
            },
            ...
        }
    }

Gold ounce ("ons") is priced in USD and is NOT converted to Toman.
All other prices are Rial; divided by 10 → Toman.
"""

import aiohttp
import logging
from src.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Asset mapping: tgju API key → internal schema
#
# "code"     — shared internal identifier (primary key with source in the DB)
# "name"     — Farsi display name sent to users
# "category" — one of "currency" | "gold" | "coin"
# ---------------------------------------------------------------------------
TGJU_ASSET_MAP = {
    # Currencies
    "price_dollar_rl": {"code": "usd",           "name": "دلار آمریکا",         "category": "currency"},
    "price_eur":       {"code": "eur",           "name": "یورو",               "category": "currency"},
    "price_aed":       {"code": "aed",           "name": "درهم امارات",         "category": "currency"},
    "price_gbp":       {"code": "gbp",           "name": "پوند انگلیس",         "category": "currency"},

    # Gold
    "tgju_gold_irg18":     {"code": "gold_18k_sell", "name": "طلای ۱۸ عیار (فروش)", "category": "gold"},
    "tgju_gold_irg18_buy": {"code": "gold_18k_buy",  "name": "طلای ۱۸ عیار (خرید)", "category": "gold"},
    "mesghal":             {"code": "mesghal",        "name": "مثقال طلا",           "category": "gold"},
    "ons":                 {"code": "ounce",          "name": "انس جهانی طلا",       "category": "gold"},  # USD

    # Coins
    "sekee":         {"code": "coin_emami",  "name": "سکه امامی",       "category": "coin"},
    "sekeb":         {"code": "coin_bahar",  "name": "سکه بهار آزادی", "category": "coin"},
    "nim":           {"code": "coin_nim",    "name": "نیم سکه",         "category": "coin"},
    "rob":           {"code": "coin_rob",    "name": "ربع سکه",         "category": "coin"},
    "retail_gerami": {"code": "coin_gerami", "name": "سکه گرمی",        "category": "coin"},
}


def clean_price(val: str) -> str:
    """Convert a comma-formatted Rial price string to a Toman integer string.

    Args:
        val: Raw price string from TGJU (e.g. "850,000" or "0").

    Returns:
        Integer Toman value as a string (Rial ÷ 10), or "0" if unparseable.

    Note:
        Do NOT call this for the gold ounce ("ons") — its price is in USD
        and must not be divided by 10.
    """
    if not val:
        return "0"
    v = val.replace(",", "")
    try:
        f = float(v)
        # TGJU prices are in Rial; divide by 10 to get Toman
        return str(int(f // 10))
    except ValueError:
        return val


async def fetch() -> list[dict]:
    """Fetch and normalise all tracked assets from the TGJU API.

    Makes a single GET request to TGJU_URL, then maps the response keys
    through TGJU_ASSET_MAP to produce a list of price dicts compatible
    with PriceRepository.upsert_many().

    Returns:
        A list of price dicts (may be empty if no mapped keys are found
        in the response). An exception is raised and propagated if the
        HTTP request fails — callers should handle it via asyncio.gather
        with return_exceptions=True.
    """
    logger.info("Fetching from TGJU API...")
    async with aiohttp.ClientSession() as session:
        async with session.get(settings.TGJU_URL, timeout=15) as response:
            response.raise_for_status()
            data = await response.json()

    current = data.get("current", {})
    results = []

    for tgju_key, meta in TGJU_ASSET_MAP.items():
        item = current.get(tgju_key)
        if not item:
            # Key not present in API response — skip silently
            continue

        p = item.get("p", "")

        # Gold ounce is denominated in USD — keep as-is; all others are Rial → Toman
        if tgju_key == "ons":
            price_str = p
        else:
            price_str = clean_price(p)

        h = clean_price(item.get("h", "")) if tgju_key != "ons" else item.get("h", "")
        l = clean_price(item.get("l", "")) if tgju_key != "ons" else item.get("l", "")

        results.append({
            "asset_code":       meta["code"],
            "asset_name_fa":    meta["name"],
            "category":         meta["category"],
            "price":            price_str,
            "price_high":       h,
            "price_low":        l,
            "change_amount":    clean_price(item.get("d", "0")),
            "change_percent":   item.get("dp", 0.0),
            "change_direction": item.get("dt", "stable"),
            "source":           "tgju",
            "source_timestamp": item.get("t", ""),
        })

    return results
