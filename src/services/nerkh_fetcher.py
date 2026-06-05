import aiohttp
import logging
from src.config import settings

logger = logging.getLogger(__name__)

# Map nerkh symbols to our internal codes
NERKH_ASSET_MAP = {
    "USD": {"code": "usd", "name": "دلار آمریکا", "category": "currency"},
    "EUR": {"code": "eur", "name": "یورو", "category": "currency"},
    "AED": {"code": "aed", "name": "درهم امارات", "category": "currency"},
    "GBP": {"code": "gbp", "name": "پوند انگلیس", "category": "currency"},
    
    "GOLD18K": {"code": "gold_18k_sell", "name": "طلای ۱۸ عیار", "category": "gold"},
    "MAZANEH": {"code": "mesghal", "name": "مثقال طلا", "category": "gold"},
    "OUNCE": {"code": "ounce", "name": "انس جهانی طلا", "category": "gold"},
    
    "SEKE_EMAMI": {"code": "coin_emami", "name": "سکه امامی", "category": "coin"},
    "SEKE_BAHAR": {"code": "coin_bahar", "name": "سکه بهار آزادی", "category": "coin"},
    "SEKE_NIM": {"code": "coin_nim", "name": "نیم سکه", "category": "coin"},
    "SEKE_ROB": {"code": "coin_rob", "name": "ربع سکه", "category": "coin"},
    "SEKE_1G": {"code": "coin_gerami", "name": "سکه گرمی", "category": "coin"}
}

def clean_price(val, divide_by_10=False) -> str:
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
            
    results = []
    # Data is expected to be a dict or list. Assume structure provides a list/dict of items
    # Example: {"data": {"currencies": [{"symbol": "USD", "price": "123"}], "golds": [...]}}
    # Or {"USD": {"price": "123"}, "EUR": ...}
    # We will need to adapt slightly if the payload format differs.
    # The documentation didn't show the exact json response format of `/all` endpoint.
    # For now, let's parse a flat dictionary assuming {"USD": {"price": ...}, ...}
    # or iterate through lists if "data" is provided.
    
    # Generic approach:
    items = {}
    if "data" in data and isinstance(data["data"], dict):
        for category, items_dict in data["data"].items():
            if isinstance(items_dict, dict):
                for symbol, details in items_dict.items():
                    if isinstance(details, dict) and "current" in details:
                        items[symbol] = details
    else:
        items = data

    for symbol, meta in NERKH_ASSET_MAP.items():
        # Nerkh.io JSON structure needs to be mapped. Assuming it has fields like 'price', 'high', 'low'
        # based on typical API designs
        item = items.get(symbol)
        if not item:
            continue
            
        p = item.get("current", "")
        is_rial = symbol != "OUNCE" and meta["category"] in ["gold", "coin"]
        
        # special case for ounce
        if symbol == "OUNCE":
            price_str = str(p)
        else:
            price_str = clean_price(p, divide_by_10=is_rial)
            
        max_val = item.get("max", {}).get("12hour", "")
        min_val = item.get("min", {}).get("12hour", "")
        h = clean_price(max_val, divide_by_10=is_rial) if symbol != "OUNCE" else str(max_val)
        l = clean_price(min_val, divide_by_10=is_rial) if symbol != "OUNCE" else str(min_val)
        
        change_val = item.get("change", 0)
        
        results.append({
            "asset_code": meta["code"],
            "asset_name_fa": meta["name"],
            "category": meta["category"],
            "price": price_str,
            "price_high": h,
            "price_low": l,
            "change_amount": clean_price(change_val, divide_by_10=is_rial),
            "change_percent": item.get("change_percent", 0.0),
            "change_direction": "high" if float(change_val or 0) > 0 else ("low" if float(change_val or 0) < 0 else "stable"),
            "source": "nerkh",
            "source_timestamp": item.get("updated_at", "")
        })
        
    return results
