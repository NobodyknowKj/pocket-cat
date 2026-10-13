"""تنظیمات — اعلان‌ها (پیش‌فرض خاموش/محدود)، پاک کردن داده."""
from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler, CommandHandler

import database as db
import keyboards as kb
import texts
from handlers.common import get_cat_or_ask_start


async def settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
    cat = await get_cat_or_ask_start(update, context)
    if not cat:
        return
    conn = db.get_conn()
    try:
        user = db.get_or_create_user(conn, update.effective_user.id)
        enabled = bool(user["notifications_enabled"])
        if query:
            await query.edit_message_text(texts.SETTINGS_TEXT, reply_markup=kb.settings_kb(enabled))
        else:
            await update.message.reply_text(texts.SETTINGS_TEXT, reply_markup=kb.settings_kb(enabled))
    finally:
        conn.close()


async def toggle_notif_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    conn = db.get_conn()
    try:
        user = db.get_or_create_user(conn, query.from_user.id)
        new_val = 0 if user["notifications_enabled"] else 1
        conn.execute("UPDATE users SET notifications_enabled = ? WHERE telegram_id = ?", (new_val, query.from_user.id))
        conn.commit()
        label = "روشن شد 🔔" if new_val else "خاموش شد 🔕"
        await query.edit_message_text(f"اعلان‌ها {label}.\n\n{settings_hint()}", reply_markup=kb.settings_kb(bool(new_val)))
    finally:
        conn.close()


def settings_hint() -> str:
    return "پیش‌فرض اعلان‌ها محدود است و هیچ اعلان غیرضروری ارسال نمی‌شود."


async def clear_ask_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "مطمئنی می‌خوای همه‌ی داده‌ی بازیت (گربه، وسایل، خاطرات، سکه) پاک بشه؟ 🗑️\n\nاین کار برگشت‌پذیر نیست!",
        reply_markup=kb.settings_clear_kb(),
    )


async def clear_yes_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    conn = db.get_conn()
    try:
        uid = query.from_user.id
        cat = db.get_cat(conn, uid)
        if cat:
            conn.execute("DELETE FROM memories WHERE cat_id = ?", (cat["id"],))
            conn.execute("DELETE FROM preferences WHERE cat_id = ?", (cat["id"],))
            conn.execute("DELETE FROM cats WHERE user_id = ?", (uid,))
        conn.execute("DELETE FROM inventory WHERE user_id = ?", (uid,))
        conn.execute("DELETE FROM transactions WHERE user_id = ?", (uid,))
        conn.execute("DELETE FROM game_sessions WHERE user_id = ?", (uid,))
        conn.execute("DELETE FROM daily_earnings WHERE user_id = ?", (uid,))
        conn.execute("DELETE FROM quests WHERE user_id = ?", (uid,))
        conn.execute("UPDATE users SET state = 'idle' WHERE telegram_id = ?", (uid,))
        conn.commit()
        await query.edit_message_text("داده‌ی بازیت پاک شد. 🗑️\n\nبا /start می‌تونی یه گربه‌ی جدید به سرپرستی بگیری. 🐈")
    finally:
        conn.close()


def register(app):
    app.add_handler(CommandHandler("settings", settings_menu))
    app.add_handler(CallbackQueryHandler(settings_menu, pattern="^home_settings$"))
    app.add_handler(CallbackQueryHandler(toggle_notif_cb, pattern="^settings_toggle_notif$"))
    app.add_handler(CallbackQueryHandler(clear_ask_cb, pattern="^settings_clear_ask$"))
    app.add_handler(CallbackQueryHandler(clear_yes_cb, pattern="^settings_clear_yes$"))
