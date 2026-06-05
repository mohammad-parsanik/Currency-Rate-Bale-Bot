"""
handlers.py — Bot update handlers

Parses incoming webhook/polling updates and routes them based on their type
(message vs. callback query). Interactions with the DB are fully async and
use the repository classes.
"""

import logging
from src.bot.client import client
from src.bot import formatters
from src.bot import keyboards
from src.database.repositories import PriceRepository, UserRepository, InteractionRepository

logger = logging.getLogger(__name__)


async def handle_update(update: dict):
    """Main routing function for incoming updates.

    Delegates to handle_message or handle_callback_query based on payload keys.
    """
    if "message" in update:
        await handle_message(update["message"])
    elif "callback_query" in update:
        await handle_callback_query(update["callback_query"])


async def handle_message(message: dict):
    """Process incoming text messages.

    Every message results in a user upsert and an interaction log entry.
    All text inputs (except /price) fall back to the /start menu since the bot
    is designed to be operated via inline buttons.
    """
    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "")
    from_user = message.get("from", {})

    if not chat_id or not text:
        return

    user_id = from_user.get("id")
    first_name = from_user.get("first_name", "")
    last_name = from_user.get("last_name", "")
    username = from_user.get("username", "")

    # Ensure user exists in DB and update their last_seen timestamp
    await UserRepository.upsert_user(user_id, first_name, last_name, username)
    # Log the typed text for analytics
    await InteractionRepository.log_interaction(user_id, text)

    if text.startswith("/start"):
        await handle_start(chat_id, first_name)
    elif text.startswith("/price"):
        await send_all_prices(chat_id, user_id)
    else:
        # Default fallback: treat any unknown text as a /start command
        await handle_start(chat_id, first_name)


async def handle_start(chat_id: int, first_name: str):
    """Send the welcome message and main menu keyboard."""
    text = (
        f"سلام {first_name}! خوش اومدی 🌹\n\n"
        "من ربات اعلام قیمت لحظه‌ای ارز، طلا و سکه هستم.\n"
        "برای دیدن قیمت‌ها از دکمه‌های زیر استفاده کن:"
    )
    await client.send_message(chat_id, text, reply_markup=keyboards.get_main_keyboard())


async def send_all_prices(chat_id: int, user_id: int):
    """Send a new message containing all prices.

    Respects the user's preferred source.
    """
    user = await UserRepository.get_user(user_id)
    source = user.get("preferred_source", "tgju") if user else "tgju"
    
    prices = await PriceRepository.get_all_prices(source)
    if not prices:
        await client.send_message(chat_id, "متأسفانه در حال حاضر قیمت‌ها در دسترس نیستند. لطفاً بعداً تلاش کنید.")
        return

    text = formatters.format_all_prices(prices)
    await client.send_message(chat_id, text, reply_markup=keyboards.get_back_keyboard("all"))


async def handle_callback_query(callback: dict):
    """Process incoming inline button presses.

    Edits the existing message instead of sending new ones, resulting in a
    snappier and cleaner UI.
    """
    query_id = callback.get("id")
    data = callback.get("data", "")
    from_user = callback.get("from", {})
    message = callback.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    message_id = message.get("message_id")

    user_id = from_user.get("id")
    # Log button presses with a 'btn:' prefix to differentiate from text
    await InteractionRepository.log_interaction(user_id, f"btn:{data}")

    # Acknowledge immediately to stop the loading spinner on the user's client
    await client.answer_callback_query(query_id)

    if not chat_id or not message_id:
        return

    try:
        user = await UserRepository.get_user(user_id)
        source = user.get("preferred_source", "tgju") if user else "tgju"

        # --- Settings Menu ---
        if data == "settings":
            text = "منبع دریافت قیمت‌ها را انتخاب کنید:"
            await client.edit_message_text(chat_id, message_id, text, reply_markup=keyboards.get_settings_keyboard(source))
            return

        # --- Changing Source ---
        if data.startswith("set_source:"):
            from src.database.repositories import UserSourceLogRepository
            new_source = data.split(":")[1]
            
            # Only update DB if the source actually changed
            if source != new_source:
                await UserRepository.update_preferred_source(user_id, new_source)
                await UserSourceLogRepository.log_source_change(user_id, source, new_source)
                source = new_source
                
            text = "منبع دریافت قیمت‌ها تغییر یافت."
            await client.edit_message_text(chat_id, message_id, text, reply_markup=keyboards.get_settings_keyboard(source))
            return

        # --- Main Menu ---
        if data == "main_menu":
            text = "لطفاً دسته‌بندی مورد نظر خود را انتخاب کنید:"
            await client.edit_message_text(chat_id, message_id, text, reply_markup=keyboards.get_main_keyboard())
            return

        # --- Fetch prices for the active source ---
        prices = await PriceRepository.get_all_prices(source)

        if not prices:
            await client.edit_message_text(
                chat_id, message_id,
                "متأسفانه در حال حاضر قیمت‌ها برای این منبع در دسترس نیستند. لطفاً از طریق تنظیمات منبع دیگری را امتحان کنید.",
                reply_markup=keyboards.get_main_keyboard()
            )
            return

        # --- All Prices View ---
        if data == "all" or data == "refresh":
            text = formatters.format_all_prices(prices)
            await client.edit_message_text(chat_id, message_id, text, reply_markup=keyboards.get_back_keyboard("all"))

        # --- Category View ---
        elif data.startswith("cat:"):
            category = data.split(":")[1]
            text = formatters.format_single_category(prices, category)
            
            # Handle empty category gracefully (e.g. if nerkh source doesn't have a specific category at the moment)
            if text == "داده‌ای برای نمایش وجود ندارد.":
                cats = {"currency": "ارز", "gold": "طلا", "coin": "سکه"}
                text = f"داده‌های مربوط به بخش {cats.get(category, category)} یافت نشد."
                
            await client.edit_message_text(chat_id, message_id, text, reply_markup=keyboards.get_back_keyboard(category))

    except Exception as e:
        logger.error(f"Error handling callback {data}: {e}")
        # Safe fallback in case of formatting or DB errors
        await client.send_message(chat_id, "خطایی رخ داد. لطفاً دوباره تلاش کنید.")
