"""
keyboards.py — Inline keyboard definitions

All bot interactions (except the initial /start) are driven by inline
keyboards. These functions return dicts formatted according to the Bale API
spec for 'reply_markup.inline_keyboard'.
"""

def get_main_keyboard() -> dict:
    """The main menu keyboard shown on /start and 'main_menu' callbacks."""
    return {
        "inline_keyboard": [
            [
                {"text": "✨ طلا", "callback_data": "cat:gold"},
                {"text": "💵 ارز", "callback_data": "cat:currency"}
            ],
            [
                {"text": "🪙 سکه", "callback_data": "cat:coin"},
                {"text": "📊 همه قیمت‌ها", "callback_data": "all"}
            ],
            [
                {"text": "⚙️ منبع قیمت‌ها", "callback_data": "settings"}
            ]
        ]
    }

def get_settings_keyboard(current_source: str) -> dict:
    """The source selection keyboard.

    Adds a checkmark next to the user's currently active source.

    Args:
        current_source: 'tgju' or 'nerkh'.
    """
    tgju_text = "✅ TGJU" if current_source == "tgju" else "TGJU"
    nerkh_text = "✅ Nerkh.io" if current_source == "nerkh" else "Nerkh.io"
    return {
        "inline_keyboard": [
            [
                {"text": tgju_text, "callback_data": "set_source:tgju"},
                {"text": nerkh_text, "callback_data": "set_source:nerkh"}
            ],
            [
                {"text": "🔙 بازگشت", "callback_data": "main_menu"}
            ]
        ]
    }

def get_back_keyboard(category: str = None) -> dict:
    """Keyboard shown below price listings.

    Includes a back button and a context-aware refresh button.

    Args:
        category: The category currently being viewed ('gold', 'currency', 'coin')
                  or 'all' if viewing all prices.
    """
    if category == "all":
        refresh_data = "all"
    else:
        # If a specific category, refresh fetches just that category again
        refresh_data = f"cat:{category}" if category else "refresh"
        
    return {
        "inline_keyboard": [
            [
                {"text": "🔙 بازگشت به منوی اصلی", "callback_data": "main_menu"}
            ],
            [
                {"text": "🔄 بروزرسانی", "callback_data": refresh_data}
            ]
        ]
    }

def get_price_keyboard() -> dict:
    """A generic back/refresh keyboard (currently unused, but kept for future single-price views)."""
    return {
        "inline_keyboard": [
            [
                {"text": "🔙 بازگشت", "callback_data": "main_menu"},
                {"text": "🔄 بروزرسانی", "callback_data": "refresh"}
            ]
        ]
    }
