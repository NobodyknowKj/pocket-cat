"""شروع بازی — /start، انتخاب دوست شدن، نگاه کردن، انتخاب نام.
قانون: /start تکراری هرگز گربه را بازنشانی نمی‌کند.
"""
import random

from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler, CommandHandler, MessageHandler, filters

import database as db
import keyboards as kb
import texts
from handlers.common import send_home


async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    conn = db.get_conn()
    try:
        db.get_or_create_user(conn, user.id, user.username or "", user.first_name or "")
        cat = db.get_cat(conn, user.id)
        if cat:
            # قبلاً گربه دارد — فقط به خانه برگردد، ریست نشود
            await send_home(update, context, dict(cat))
            return
        await update.message.reply_text(texts.WELCOME, reply_markup=kb.start_kb())
    finally:
        conn.close()


async def start_friend_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    conn = db.get_conn()
    try:
        db.set_user_state(conn, query.from_user.id, "awaiting_name")
    finally:
        conn.close()
    await query.edit_message_text(texts.ASK_NAME)


async def start_peek_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    line = random.choice(texts.PEEK_LINES)
    await query.edit_message_text(
        f"{line}\n\nدوست داری با هم دوست بشیم؟",
        reply_markup=kb.start_kb(),
    )


async def name_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت نام گربه وقتی کاربر در حالت awaiting_name است."""
    user = update.effective_user
    conn = db.get_conn()
    try:
        if db.get_user_state(conn, user.id) != "awaiting_name":
            return
        if db.get_cat(conn, user.id):
            db.set_user_state(conn, user.id, "idle")
            return
        name = (update.message.text or "").strip()
        if not name or len(name) > 30 or name.startswith("/"):
            await update.message.reply_text("یه اسم کوچولو و بامزه برام انتخاب کن! 🐱 (مثلاً موچی)")
            return
        db.get_or_create_user(conn, user.id, user.username or "", user.first_name or "")
        cat = db.create_cat(conn, user.id, name)
        db.set_user_state(conn, user.id, "idle")
        await update.message.reply_text(texts.named(name))
        await send_home(update, context, dict(cat))
    finally:
        conn.close()


def register(app):
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CallbackQueryHandler(start_friend_cb, pattern="^start_friend$"))
    app.add_handler(CallbackQueryHandler(start_peek_cb, pattern="^start_peek$"))
    # پیام متنی نام — فقط وقتی state برابر awaiting_name است (در خود تابع بررسی می‌شود)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, name_message))
