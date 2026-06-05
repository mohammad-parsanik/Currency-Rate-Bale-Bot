import aiohttp
import logging
from src.config import settings

logger = logging.getLogger(__name__)

# Mapping from tgju keys to our internal schema
TGJU_ASSET_MAP = {
    "price_dollar_rl": {"code": "usd", "name": "دلار آمریکا", "category": "currency"},
    "price_eur": {"code": "eur", "name": "یورو", "category": "currency"},
    "price_aed": {"code": "aed", "name": "درهم امارات", "category": "currency"},
    "price_gbp": {"code": "gbp", "name": "پوند انگلیس", "category": "currency"},
    
    "tgju_gold_irg18": {"code": "gold_18k_sell", "name": "طلای ۱۸ عیار (فروش)", "category": "gold"},
    "tgju_gold_irg18_buy": {"code": "gold_18k_buy", "name": "طلای ۱۸ عیار (خرید)", "category": "gold"},
    "mesghal": {"code": "mesghal", "name": "مثقال طلا", "category": "gold"},
    "ons": {"code": "ounce", "name": "انس جهانی طلا", "category": "gold"},
    
    "sekee": {"code": "coin_emami", "name": "سکه امامی", "category": "coin"},
    "sekeb": {"code": "coin_bahar", "name": "سکه بهار آزادی", "category": "coin"},
    "nim": {"code": "coin_nim", "name": "نیم سکه", "category": "coin"},
    "rob": {"code": "coin_rob", "name": "ربع سکه", "category": "coin"},
    "retail_gerami": {"code": "coin_gerami", "name": "سکه گرمی", "category": "coin"}
}

def clean_price(val: str) -> str:
    # remove commas and convert to float/int to handle / 10 if needed
    if not val:
        return "0"
    v = val.replace(",", "")
    try:
        f = float(v)
        # Assuming Rial -> Toman
        return str(int(f // 10))
    except ValueError:
        return val

async def fetch() -> list[dict]:
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
            continue
            
        p = item.get("p", "")
        # special case for ounce (usually USD, no //10)
        if tgju_key == "ons":
            price_str = p
        else:
            price_str = clean_price(p)
            
        h = clean_price(item.get("h", "")) if tgju_key != "ons" else item.get("h", "")
        l = clean_price(item.get("l", "")) if tgju_key != "ons" else item.get("l", "")
        
        results.append({
            "asset_code": meta["code"],
            "asset_name_fa": meta["name"],
            "category": meta["category"],
            "price": price_str,
            "price_high": h,
            "price_low": l,
            "change_amount": clean_price(item.get("d", "0")),
            "change_percent": item.get("dp", 0.0),
            "change_direction": item.get("dt", "stable"),
            "source": "tgju",
            "source_timestamp": item.get("t", "")
        })
        
    return results
