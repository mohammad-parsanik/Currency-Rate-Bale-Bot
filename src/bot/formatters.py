"""
formatters.py — Message construction and formatting

Responsible for converting database price records into human-readable,
Farsi-localized text messages. Handles timezone adjustments, number formatting
(commas and Persian numerals), and visual presentation (emojis and layouts).
"""

import datetime

def adjust_time(time_str: str) -> str:
    """Adjust an API timestamp to Iran Standard Time (IRST/IRDT, UTC+3:30).
    
    Handles both SQLite format ("YYYY-MM-DD HH:MM:SS") from TGJU and
    ISO-8601 format ("YYYY-MM-DDTHH:MM:SSZ") from Nerkh.io.
    """
    if not time_str:
        return ""
    try:
        # Check if SQLite format "YYYY-MM-DD HH:MM:SS"
        if len(time_str) >= 19 and time_str[4] == '-':
            dt = datetime.datetime.strptime(time_str[:19], "%Y-%m-%d %H:%M:%S")
            # TGJU timestamps are often local time already, but assuming we need
            # a fixed offset if they're UTC. We add 3h30m.
            dt += datetime.timedelta(hours=3, minutes=30)
            return dt.strftime("%Y/%m/%d %H:%M:%S")
    except Exception:
        pass
        
    try:
        # Check if ISO format e.g. "YYYY-MM-DDTHH:MM:SSZ" (from nerkh.io)
        if "T" in time_str:
            dt = datetime.datetime.fromisoformat(time_str.replace("Z", "+00:00"))
            if dt.tzinfo:
                # Convert timezone-aware datetime to IRST
                dt = dt.astimezone(datetime.timezone(datetime.timedelta(hours=3, minutes=30)))
            else:
                dt += datetime.timedelta(hours=3, minutes=30)
            return dt.strftime("%Y/%m/%d %H:%M:%S")
    except Exception:
        pass
        
    return time_str

def to_persian_digits(s: str) -> str:
    """Convert Western Arabic numerals (0-9) to Eastern Arabic (Persian) numerals."""
    mapping = {
        '0': '۰', '1': '۱', '2': '۲', '3': '۳', '4': '۴',
        '5': '۵', '6': '۶', '7': '۷', '8': '۸', '9': '۹'
    }
    return ''.join(mapping.get(c, c) for c in str(s))

def format_price_value(value: str) -> str:
    """Add thousands-separator commas and convert to Persian digits.
    
    Example:
        "85000" -> "۸۵,۰۰۰"
    """
    if not value or value == "0":
        return "نامشخص"
    try:
        # Remove any existing commas just in case, then format
        f = float(value.replace(",", ""))
        
        # Format as integer if there's no fractional part, else keep decimals
        if f.is_integer():
            formatted = f"{int(f):,}"
        else:
            formatted = f"{f:,}"
            
        return to_persian_digits(formatted)
    except Exception:
        # Fallback if value isn't numeric
        return to_persian_digits(value)

def format_change(percent: float, direction: str) -> str:
    """Format the change percentage with an appropriate emoji.
    
    Args:
        percent: The float percentage (e.g. 0.59 or -0.33)
        direction: "high", "low", or "stable"
    """
    if not percent or percent == 0.0:
        return "ثابت"
        
    # Take absolute value since the sign is represented by the emoji / plus-minus sign
    p_str = to_persian_digits(str(abs(percent)))
    
    if direction == "high":
        return f"📈 +{p_str}٪"
    elif direction == "low":
        return f"📉 -{p_str}٪"
    else:
        return "ثابت"

def format_all_prices(prices: list[dict], show_source_time: bool = False) -> str:
    """Format a list of prices into a categorized, multi-line message.
    
    Used for the /price command and the 'all' button.
    """
    if not prices:
        return "داده‌ای برای نمایش وجود ندارد."

    cats = {"currency": "💵 ارز", "coin": "🪙 سکه", "gold": "✨ طلا"}
    
    # Group the flat list into categories
    grouped = {"currency": [], "coin": [], "gold": []}
    
    source_timestamps = []
    latest_fetch = ""
    for p in prices:
        if p["category"] in grouped:
            grouped[p["category"]].append(p)
            
        if p.get("source_timestamp"):
            source_timestamps.append(p["source_timestamp"])
            
        # All records usually share the same fetched_at in a given cycle
        if p.get("fetched_at"):
            latest_fetch = p["fetched_at"]
            
    # Find the newest timestamp reported by the API across all assets
    latest_update = max(source_timestamps) if source_timestamps else ""
            
    lines = []
    lines.append("لیست قیمت‌ها 📊\n")
    
    for cat_code, cat_title in cats.items():
        if grouped[cat_code]:
            lines.append(f"{cat_title}")
            for i, p in enumerate(grouped[cat_code]):
                is_last = (i == len(grouped[cat_code]) - 1)
                
                # Use tree characters for a nicer visual layout
                prefix = "└ " if is_last else "├ "
                
                # Currencies have long names like "دلار آمریکا" — take just the first word for terseness
                name = p["asset_name_fa"].split()[0] if cat_code == "currency" else p["asset_name_fa"]
                val = format_price_value(p["price"])
                
                # Only ounce is USD; everything else is Toman
                unit = "$" if p["asset_code"] == "ounce" else "تومان"
                
                change_str = ""
                if p["change_percent"]:
                    change_str = f"  ({format_change(p['change_percent'], p['change_direction'])})"
                    
                lines.append(f"{prefix}{name}: {val} {unit}{change_str}")
                
            # Blank line between categories
            lines.append("")
            
    # Append footers
    lines.append(f"⏱ زمان استعلام ربات: {to_persian_digits(adjust_time(latest_fetch))}")
    if show_source_time and latest_update:
        lines.append(f"📡 آخرین تغییر در منبع: {to_persian_digits(adjust_time(latest_update))}")
        
    return "\n".join(lines)

def format_single_category(prices: list[dict], category: str) -> str:
    """Filter the price list to a single category and format it.
    
    Used when a user clicks a specific category button (e.g. "طلا").
    """
    filtered = [p for p in prices if p["category"] == category]
    return format_all_prices(filtered, show_source_time=True)

def format_single_price(price: dict) -> str:
    """Format a single asset with full details (high/low bounds).
    
    Currently unused in the UI, but kept as a utility for potential
    future "detail view" features.
    """
    if not price:
        return "یافت نشد."
        
    cats = {"currency": "💵", "coin": "🪙", "gold": "✨"}
    icon = cats.get(price["category"], "")
    
    unit = "$" if price["asset_code"] == "ounce" else "تومان"
    
    lines = [
        f"{icon} {price['asset_name_fa']}\n",
        f"قیمت فعلی: {format_price_value(price['price'])} {unit}",
        f"بالاترین: {format_price_value(price['price_high'])} {unit}",
        f"پایین‌ترین: {format_price_value(price['price_low'])} {unit}",
        f"تغییر: {format_change(price['change_percent'], price['change_direction'])}\n",
        f"آخرین بروزرسانی: {to_persian_digits(adjust_time(price['source_timestamp']))}"
    ]
    return "\n".join(lines)
