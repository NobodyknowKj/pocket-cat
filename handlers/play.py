"""بازی — ۴ بازی با جلسه‌ی یکتا و نتیجه‌ی از پیش تعیین‌شده.
- نخ و پنجه: ۳ انتخاب (چپ/راست/بالا) — برنده از پیش انتخاب می‌شود.
- شکار موش: ۳ محل — محل درست از پیش انتخاب می‌شود.
- قایم‌باشک: ۳ مکان — محل پنهان شدن از پیش انتخاب می‌شود.
- توپ رنگی: ۴ رنگ — رنگ برنده از پیش انتخاب می‌شود (هدف سرگرمی).
کلیک تکراری روی یک جلسه پاداش دوباره نمی‌دهد.
"""
import random

from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler, CommandHandler

import database as db
import game_logic
import keyboards as kb
import texts
from handlers.common import get_cat_or_ask_start

GAMES = {
    "thread": {"title": "🧶 نخ و پنجه", "choices": ["left", "right", "up"], "labels": {"left": "چپ", "right": "راست", "up": "بالا"}},
    "mouse":  {"title": "🐭 شکار موش اسباب‌بازی", "choices": ["sofa", "box", "bed"], "labels": {"sofa": "زیر مبل", "box": "پشت جعبه", "bed": "زیر تخت"}},
    "hide":   {"title": "🙈 قایم‌باشک", "choices": ["curtain", "box", "plant"], "labels": {"curtain": "پشت پرده", "box": "داخل جعبه", "plant": "پشت گلدون"}},
    "ball":   {"title": "🎨 توپ رنگی", "choices": ["red", "blue", "green", "yellow"], "labels": {"red": "قرمز", "blue": "آبی", "green": "سبز", "yellow": "زرد"}},
}

GAME_INTROS = {
    "thread": "🧶 نخ و پنجه!\n\nیه نخ رنگی رو تکون می‌دی... موچی با دقت نگاش می‌کنه.\n\nنخ رو کجا ببری؟",
    "mouse": "🐭 شکار موش اسباب‌بازی!\n\nموش پارچه‌ای قایم شده... موچی داره بو می‌کشه.\n\nبه نظرت موش کجاست؟",
    "hide": "🙈 قایم‌باشک!\n\nموچی قایم شده! بگرد پیداش کن...\n\nبه نظرت کجا قایم شده؟",
    "ball": "🎨 توپ رنگی!\n\nکدوم توپ رو بندازی که موچی دنبالش بدوه؟",
}


async def play_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
    cat = await get_cat_or_ask_start(update, context)
    if not cat:
        return
    ok, reason = game_logic.can_start_play(cat)
    if not ok:
        if reason == "low_energy":
            text = f"{cat['name']} خیلی خسته‌ست... خودش رو روی زمین انداخته و بازی رو نیمه‌کاره رها می‌کنه. 😴\n\nبذار اول بخوابه و انرژی بگیره! 💤"
        else:
            text = f"{cat['name']} خیلی گرسنه‌ست و حوصله‌ی بازی نداره. اول بهش غذا بده! 🍗"
        if query:
            await query.edit_message_text(text, reply_markup=kb.back_home_kb())
        else:
            await update.message.reply_text(text, reply_markup=kb.back_home_kb())
        return
    text = f"🧶 بازی با {cat['name']}\n\n⚡ انرژی: {int(cat['energy'])}٪  •  🍗 گرسنگی: {int(cat['hunger'])}٪\n\nکدوم بازی؟"
    if query:
        await query.edit_message_text(text, reply_markup=kb.play_menu_kb())
    else:
        await update.message.reply_text(text, reply_markup=kb.play_menu_kb())


async def play_start_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    game_type = query.data.split("play_", 1)[1]
    cat = await get_cat_or_ask_start(update, context)
    if not cat:
        return
    ok, reason = game_logic.can_start_play(cat)
    if not ok:
        await query.edit_message_text("موچی الان حال بازی نداره... اول غذا بده یا بذار بخوابه! 😺", reply_markup=kb.back_home_kb())
        return
    conn = db.get_conn()
    try:
        choices = GAMES[game_type]["choices"]
        winning = game_logic.pick_winning_choice(game_type, choices)
        session_id = db.create_game_session(conn, query.from_user.id, game_type, winning)
        intro = GAME_INTROS[game_type]
        if game_type == "thread":
            markup = kb.thread_kb(session_id)
        elif game_type == "mouse":
            markup = kb.mouse_kb(session_id)
        elif game_type == "hide":
            markup = kb.hide_kb(session_id)
        else:
            markup = kb.ball_kb(session_id)
        await query.edit_message_text(intro, reply_markup=markup)
    finally:
        conn.close()


async def play_pick_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    # playpick:<session_id>:<choice>
    _, session_id, picked = query.data.split(":", 2)
    cat = await get_cat_or_ask_start(update, context)
    if not cat:
        return
    conn = db.get_conn()
    try:
        session = db.get_game_session(conn, session_id)
        if not session:
            await query.edit_message_text("این بازی دیگه معتبر نیست. یه بازی جدید شروع کن! 🧶", reply_markup=kb.play_menu_kb())
            return
        if session["status"] != "pending":
            await query.edit_message_text("این دور قبلاً تموم شده! یه دور جدید شروع کن. 🧶", reply_markup=kb.play_menu_kb())
            return
        game_type = session["game_type"]
        already, result, success = game_logic.resolve_play(conn, query.from_user.id, cat, session_id, picked)
        if already:
            await query.edit_message_text("این دور قبلاً حساب شده! یه دور جدید شروع کن. 🧶", reply_markup=kb.play_menu_kb())
            return
        if result.get("capped"):
            await query.edit_message_text(
                "امروز به سقف بازی پاداش‌دار رسیدی (۱۰ دور / ۵۰ سکه). 🎯\n"
                "می‌تونی هنوز برای سرگرمی بازی کنی، ولی سکه‌ی بیشتری نمی‌گیری.\n"
                "فردا دوباره می‌تونی جایزه بگیری! 😺",
                reply_markup=kb.back_home_kb(),
            )
            return
        name = cat["name"]
        if game_type == "thread":
            win_text = f"{name} با یه جهش حرفه‌ای نخ رو می‌گیره! 🎉\n\n«گرفتمش! من بهترین شکارچی نخ دنیا هستم!» 😼"
            lose_text = f"{name} نخ رو دنبال می‌کنه... ولی نخ از دستش در می‌ره!\n\nاشکالی نداره، دفعه‌ی بعد می‌گیریش! 😹"
        elif game_type == "mouse":
            win_text = f"{name} موش رو پیدا می‌کنه و با ذوق روش می‌پره! 🐭🎉\n\nشکارچی ماهر ما!"
            lose_text = f"اوه! موش اونجا نبود... {name} با تعجب بهت نگاه می‌کنه.\n\n«میو؟ موش کجاست؟» 🐭"
        elif game_type == "hide":
            win_text = f"پیداش کردی! 🎉 {name} با خنده از مخفیگاهش بیرون می‌پره!\n\n«چطور پیدام کردی؟!» 😹"
            lose_text = f"اوه! {name} اونجا نبود... صدای خرخرش از یه جای دیگه میاد! 🙈"
        else:
            win_text = f"{name} با ذوق دنبال توپ می‌دوه و باهاش بازی می‌کنه! 🎨😺\n\nتوپ رنگی بهترین سرگرمیه!"
            lose_text = f"{name} توپ رو یه کم بو می‌کنه و بعد می‌ره سراغ یه توپ دیگه... 🎨\n\nاشکالی نداره، مهم سرگرمیه!"
        base = win_text if success else lose_text
        reward = f"\n\n{'✅ موفق!' if success else '😹 ناموفق ولی بامزه!'}\n🪙 +{result['coins']} سکه  •  ✨ +{result['xp']} تجربه"
        if result.get("level_ups"):
            reward += f"\n\n🎉🎉 سطح {name} به {result['new_level']} رسید! +{result['level_ups'] * 10} سکه‌ی جایزه‌ی سطح! ⭐"
        await query.edit_message_text(base + reward, reply_markup=kb.back_home_kb())
    finally:
        conn.close()


def register(app):
    app.add_handler(CommandHandler("play", play_menu))
    app.add_handler(CallbackQueryHandler(play_menu, pattern="^home_play$"))
    app.add_handler(CallbackQueryHandler(play_start_cb, pattern="^play_(thread|mouse|hide|ball)$"))
    app.add_handler(CallbackQueryHandler(play_pick_cb, pattern="^playpick:"))
