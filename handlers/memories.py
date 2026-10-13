"""خاطرات + اتفاق‌های تصادفی.
خاطرات فقط از اتفاقات واقعی ثبت‌شده در بازی ساخته می‌شوند — هیچ خاطره‌ی جعلی ساخته نمی‌شود.
"""
import random
import time

from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler, CommandHandler

import database as db
import game_logic
import keyboards as kb
from config import RANDOM_EVENTS
from handlers.common import get_cat_or_ask_start


async def memories_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
    cat = await get_cat_or_ask_start(update, context)
    if not cat:
        return
    conn = db.get_conn()
    try:
        mems = db.get_memories(conn, cat["id"])
        if not mems:
            text = f"📖 خاطرات {cat['name']}\n\nهنوز خاطره‌ای ثبت نشده... با هم خاطره بسازیم! 🐾"
        else:
            lines = [f"📖 خاطرات {cat['name']}\n"]
            for m in mems:
                day = time.strftime("%Y-%m-%d", time.localtime(m["created_at"]))
                lines.append(f"• {day} — {m['description']}")
            text = "\n".join(lines)
        if query:
            await query.edit_message_text(text, reply_markup=kb.back_home_kb())
        else:
            await update.message.reply_text(text, reply_markup=kb.back_home_kb())
    finally:
        conn.close()


async def random_event_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش یک اتفاق تصادفی — رویداد مهم در حافظه ثبت می‌شود."""
    cat = await get_cat_or_ask_start(update, context)
    if not cat:
        return
    conn = db.get_conn()
    try:
        event = random.choice(RANDOM_EVENTS)
        # رویداد جعبه فقط اگر جعبه داشته باشد، معنادارتر است — ولی برای تنوع، همه مجازند
        if not db.memory_exists(conn, cat["id"], f"event_{event['id']}"):
            db.add_memory(conn, cat["id"], f"event_{event['id']}", event["text"].split("\n")[0])
        msg = update.callback_query.message if update.callback_query else update.message
        await msg.reply_text(f"✨ یه اتفاق تازه!\n\n{event['text']}", reply_markup=kb.back_home_kb())
    finally:
        conn.close()


def register(app):
    app.add_handler(CommandHandler("memories", memories_cmd))
    app.add_handler(CallbackQueryHandler(memories_cmd, pattern="^home_memories$"))
