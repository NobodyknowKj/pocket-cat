"""فروشگاه — خرید با سکه، بدون پرداخت واقعی، جلوگیری از خرید تکراری."""
from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler, CommandHandler

import database as db
import game_logic
import keyboards as kb
import texts
from handlers.common import get_cat_or_ask_start


async def shop_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
    cat = await get_cat_or_ask_start(update, context)
    if not cat:
        return
    text = texts.shop_text(cat)
    if query:
        await query.edit_message_text(text, reply_markup=kb.shop_kb())
    else:
        await update.message.reply_text(text, reply_markup=kb.shop_kb())


async def buy_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    item_id = query.data.split("buy_", 1)[1]
    cat = await get_cat_or_ask_start(update, context)
    if not cat:
        return
    conn = db.get_conn()
    try:
        ok, msg = game_logic.buy_item(conn, query.from_user.id, cat, item_id)
        if not ok:
            if msg == "already_owned":
                text = "این وسیله رو قبلاً داری! 🎁"
            elif msg == "not_enough_coins":
                text = "سکه‌ت کافی نیست! با بازی کردن سکه جمع کن. 🪙🧶"
            else:
                text = msg
            await query.edit_message_text(text, reply_markup=kb.back_home_kb())
            return
        from config import SHOP_ITEMS
        item = SHOP_ITEMS[item_id]
        await query.edit_message_text(
            f"خریدی! ✅\n\n{item['name']}\n{item['description']}\n\nاثر: {item['effect']}",
            reply_markup=kb.back_home_kb(),
        )
    finally:
        conn.close()


def register(app):
    app.add_handler(CommandHandler("shop", shop_menu))
    app.add_handler(CallbackQueryHandler(shop_menu, pattern="^home_shop$"))
    app.add_handler(CallbackQueryHandler(buy_cb, pattern="^buy_"))
