def get_main_keyboard() -> dict:
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
    if category == "all":
        refresh_data = "all"
    else:
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
    return {
        "inline_keyboard": [
            [
                {"text": "🔙 بازگشت", "callback_data": "main_menu"},
                {"text": "🔄 بروزرسانی", "callback_data": "refresh"}
            ]
        ]
    }
