"""صفحه‌ی اصلی، خانه، وسایل، پروفایل."""
from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler, CommandHandler

import database as db
import game_logic
import keyboards as kb
import texts
from handlers.common import get_cat_or_ask_start, send_home


async def home_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cat = await get_cat_or_ask_start(update, context)
    if cat:
        await send_home(update, context, cat)


async def home_refresh_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cat = await get_cat_or_ask_start(update, context)
    if cat:
        await send_home(update, context, cat)


async def house_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cat = await get_cat_or_ask_start(update, context)
    if not cat:
        return
    conn = db.get_conn()
    try:
        inv = db.get_inventory(conn, query.from_user.id)
        await query.edit_message_text(texts.house_text(cat, inv), reply_markup=kb.back_home_kb())
    finally:
        conn.close()


async def inventory_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cat = await get_cat_or_ask_start(update, context)
    if not cat:
        return
    conn = db.get_conn()
    try:
        inv = db.get_inventory(conn, query.from_user.id)
        from config import FOODS, SHOP_ITEMS
        lines = [f"🎒 وسایل {cat['name']}\n"]
        if not inv:
            lines.append("هنوز چیزی نداری! از فروشگاه بخر. 🛒")
        else:
            for item_id, qty in sorted(inv.items()):
                if qty <= 0:
                    continue
                if item_id in FOODS:
                    label = FOODS[item_id]["name"]
                elif item_id in SHOP_ITEMS:
                    label = SHOP_ITEMS[item_id]["name"]
                else:
                    label = {"ball": "🧶 توپ بازی", "bed": "🛏️ تخت خواب"}.get(item_id, item_id)
                lines.append(f"• {label} × {qty}")
        lines.append(f"\n🪙 سکه: {int(cat['coins'])}")
        await query.edit_message_text("\n".join(lines), reply_markup=kb.back_home_kb())
    finally:
        conn.close()


async def profile_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
    cat = await get_cat_or_ask_start(update, context)
    if not cat:
        return
    conn = db.get_conn()
    try:
        prefs = dict(db.get_preferences(conn, cat["id"]))
        mems = db.get_memories(conn, cat["id"])
        text = texts.profile_text(cat, prefs, len(mems))
        if query:
            await query.edit_message_text(text, reply_markup=kb.back_home_kb())
        else:
            await update.message.reply_text(text)
    finally:
        conn.close()


def register(app):
    app.add_handler(CommandHandler("home", home_cmd))
    app.add_handler(CommandHandler("profile", profile_cb))
    app.add_handler(CommandHandler("inventory", inventory_cb))
    app.add_handler(CallbackQueryHandler(home_refresh_cb, pattern="^home_refresh$"))
    app.add_handler(CallbackQueryHandler(house_cb, pattern="^home_house$"))
    app.add_handler(CallbackQueryHandler(inventory_cb, pattern="^home_inventory$"))
    app.add_handler(CallbackQueryHandler(profile_cb, pattern="^home_profile$"))
