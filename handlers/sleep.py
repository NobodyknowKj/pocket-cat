"""خواب — شروع خواب، بیدار کردن، بازیابی انرژی بر اساس زمان واقعی."""
from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler, CommandHandler

import database as db
import game_logic
import keyboards as kb
import texts
from handlers.common import get_cat_or_ask_start


async def sleep_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
    cat = await get_cat_or_ask_start(update, context)
    if not cat:
        return
    if cat["status"] == "sleeping":
        text = f"{cat['name']} خوابه... 💤\n\n⚡ انرژی: {int(cat['energy'])}٪\nبذار استراحت کنه تا انرژی‌ش پر بشه. وقتی به ۱۰۰٪ برسه خودش بیدار می‌شه."
    else:
        text = f"💤 خواب {cat['name']}\n\n⚡ انرژی فعلی: {int(cat['energy'])}٪\n\nمی‌خوای بخوابه؟"
    if query:
        await query.edit_message_text(text, reply_markup=kb.sleep_kb())
    else:
        await update.message.reply_text(text, reply_markup=kb.sleep_kb())


async def sleep_do_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cat = await get_cat_or_ask_start(update, context)
    if not cat:
        return
    conn = db.get_conn()
    try:
        game_logic.start_sleep(conn, cat)
        if not db.memory_exists(conn, cat["id"], "first_sleep"):
            db.add_memory(conn, cat["id"], "first_sleep", "امروز اولین بار روی بالشتم خوابیدم. رسماً مال منه. 🛏️")
        await query.edit_message_text(texts.SLEEP_TEXT.format(name=cat["name"]), reply_markup=kb.back_home_kb())
    finally:
        conn.close()


async def sleep_wake_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cat = await get_cat_or_ask_start(update, context)
    if not cat:
        return
    conn = db.get_conn()
    try:
        game_logic.wake_up(conn, cat)
        await query.edit_message_text(texts.WAKE_TEXT.format(name=cat["name"]), reply_markup=kb.back_home_kb())
    finally:
        conn.close()


def register(app):
    app.add_handler(CommandHandler("sleep", sleep_menu))
    app.add_handler(CallbackQueryHandler(sleep_menu, pattern="^home_sleep$"))
    app.add_handler(CallbackQueryHandler(sleep_do_cb, pattern="^sleep_do$"))
    app.add_handler(CallbackQueryHandler(sleep_wake_cb, pattern="^sleep_wake$"))
