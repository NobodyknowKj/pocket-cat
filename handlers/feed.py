"""غذا دادن — منوی غذا، مصرف از موجودی، خرید غذا، واکنش‌های داستانی."""
import random

from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler, CommandHandler

import database as db
import game_logic
import keyboards as kb
import texts
from config import FOODS
from handlers.common import get_cat_or_ask_start


async def feed_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
    cat = await get_cat_or_ask_start(update, context)
    if not cat:
        return
    conn = db.get_conn()
    try:
        inv = db.get_inventory(conn, update.effective_user.id)
        lines = [f"🍗 غذا دادن به {cat['name']}\n🍗 گرسنگی: {int(cat['hunger'])}٪\n"]
        for fid, f in FOODS.items():
            lines.append(f"{f['name']} — موجودی: {inv.get(fid, 0)} — کاهش گرسنگی: {f['hunger_reduction']}")
        text = "\n".join(lines)
        if query:
            await query.edit_message_text(text, reply_markup=kb.feed_kb())
        else:
            await update.message.reply_text(text, reply_markup=kb.feed_kb())
    finally:
        conn.close()


async def feed_pick_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    food_id = query.data.split("feed_", 1)[1]
    cat = await get_cat_or_ask_start(update, context)
    if not cat:
        return
    conn = db.get_conn()
    try:
        # حافظه‌ی علاقه‌مندی: اگر این غذا ۳+ بار داده شده، واکنش ویژه‌ی ماهی
        prefs = db.get_preferences(conn, cat["id"])
        fav_foods = [f for f in str(prefs["favorite_foods"]).split(",") if f]
        ok, msg, _ = game_logic.feed_cat(conn, query.from_user.id, cat, food_id)
        if not ok:
            if msg == "full":
                await query.edit_message_text(texts.FEED_FULL.format(name=cat["name"]), reply_markup=kb.back_home_kb())
            elif msg == "no_stock":
                await query.edit_message_text(texts.FEED_NO_STOCK, reply_markup=kb.feed_buy_kb())
            else:
                await query.edit_message_text(msg, reply_markup=kb.back_home_kb())
            return
        # ثبت علاقه‌مندی ساده: اگر غذای ماهی بود و قبلاً هم داده شده، واکنش ویژه
        if food_id == "fish" and "fish" in fav_foods:
            reaction = random.choice(texts.FEED_REACTIONS["fish"])
        else:
            reaction = random.choice(texts.FEED_REACTIONS.get(food_id, texts.FEED_REACTIONS["food_normal"]))
        # به‌روز کردن علاقه‌مندی‌ها: اگر غذای جدیدی ۳ بار در خاطرات/تراکنش‌ها دیده شد، اضافه کن
        # (نسخه‌ی ساده و پایدار: هر غذای مصرف‌شده را در لیست نگه می‌داریم)
        if food_id not in fav_foods:
            fav_foods.append(food_id)
            db.update_preferences(conn, cat["id"], favorite_foods=",".join(fav_foods))
        # خاطره‌ی غذای موردعلاقه — فقط یک بار
        if food_id == "fish" and not db.memory_exists(conn, cat["id"], "loves_fish"):
            db.add_memory(conn, cat["id"], "loves_fish", f"{cat['name']} عاشق ماهیه! هر بار بوی ماهی رو حس می‌کنه، از اون سر خونه می‌دوه سمتت. 🐟")
        # وضعیت بعد از غذا: ممکن است خواب‌آلود شود
        await query.edit_message_text(
            reaction.format(name=cat["name"]) + f"\n\n🍗 گرسنگی حالا: {int(max(0, cat['hunger'] - FOODS[food_id]['hunger_reduction']))}٪",
            reply_markup=kb.back_home_kb(),
        )
    finally:
        conn.close()


async def feed_buy_menu_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cat = await get_cat_or_ask_start(update, context)
    if not cat:
        return
    conn = db.get_conn()
    try:
        inv = db.get_inventory(conn, query.from_user.id)
        await query.edit_message_text(texts.food_shop_text(cat, inv), reply_markup=kb.feed_buy_kb())
    finally:
        conn.close()


async def buy_food_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    food_id = query.data.split("buyfood_", 1)[1]
    cat = await get_cat_or_ask_start(update, context)
    if not cat:
        return
    conn = db.get_conn()
    try:
        ok, msg = game_logic.buy_food(conn, query.from_user.id, cat, food_id, 1)
        if not ok:
            if msg == "not_enough_coins":
                await query.edit_message_text("سکه‌ت کافی نیست! با بازی کردن سکه جمع کن. 🪙🧶", reply_markup=kb.back_home_kb())
            else:
                await query.edit_message_text(msg, reply_markup=kb.back_home_kb())
            return
        await query.edit_message_text(
            f"خریدی! ✅\n{FOODS[food_id]['name']} به موجودیت اضافه شد.\nحالا می‌تونی به {cat['name']} غذا بدی. 🍗",
            reply_markup=kb.feed_kb(),
        )
    finally:
        conn.close()


def register(app):
    app.add_handler(CommandHandler("feed", feed_menu))
    app.add_handler(CallbackQueryHandler(feed_menu, pattern="^home_feed$"))
    app.add_handler(CallbackQueryHandler(feed_pick_cb, pattern="^feed_(fish|chicken|food_normal|treat)$"))
    app.add_handler(CallbackQueryHandler(feed_buy_menu_cb, pattern="^feed_buy$"))
    app.add_handler(CallbackQueryHandler(buy_food_cb, pattern="^buyfood_"))
