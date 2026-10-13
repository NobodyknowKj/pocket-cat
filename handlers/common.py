"""توابع مشترک هندلرها — خواندن گربه، همگام‌سازی زمان، نمایش خانه."""
from telegram import Update
from telegram.ext import ContextTypes

import database as db
import game_logic
import keyboards as kb
import texts


async def get_cat_or_ask_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """گربه‌ی کاربر را (با اعمال گذشت زمان) برمی‌گرداند؛ اگر گربه‌ای نباشد پیام شروع می‌فرستد."""
    user = update.effective_user
    conn = db.get_conn()
    try:
        cat_row = db.get_cat(conn, user.id)
        if not cat_row:
            msg = update.callback_query.message if update.callback_query else update.message
            if msg:
                await msg.reply_text("اول با /start یه گربه‌ی کوچولو به سرپرستی بگیر! 🐈", reply_markup=kb.start_kb())
            return None
        cat = game_logic.sync_cat(conn, user.id)
        return cat
    finally:
        conn.close()


async def send_home(update: Update, context: ContextTypes.DEFAULT_TYPE, cat: dict | None = None):
    """نمایش صفحه‌ی اصلی با وضعیت به‌روز."""
    user = update.effective_user
    conn = db.get_conn()
    try:
        if cat is None:
            cat = game_logic.sync_cat(conn, user.id)
        if not cat:
            return
        status_label = game_logic.cat_status_label(cat)
        text = texts.home_text(cat, status_label, cat.get("location", "خانه"))
        msg = update.callback_query.message if update.callback_query else update.message
        if update.callback_query:
            try:
                await update.callback_query.edit_message_text(text, reply_markup=kb.main_kb())
            except Exception:
                await msg.reply_text(text, reply_markup=kb.main_kb())
        else:
            await msg.reply_text(text, reply_markup=kb.main_kb())
    finally:
        conn.close()


def safe_edit_text(query, text: str, markup=None):
    """ویرایش پیام با مدیریت خطای «پیام یکسان» تلگرام."""
    return query.edit_message_text(text, reply_markup=markup)
