"""نوازش — ۴ حالت، کول‌داون ۶۰ ثانیه، در خواب بیدار نمی‌کند."""
import random

from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler, CommandHandler

import database as db
import game_logic
import keyboards as kb
import texts
from handlers.common import get_cat_or_ask_start


async def pet_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
    cat = await get_cat_or_ask_start(update, context)
    if not cat:
        return
    conn = db.get_conn()
    try:
        mood, rewarded, was_sleeping = game_logic.pet_cat(conn, update.effective_user.id, cat)
        if was_sleeping:
            text = texts.PET_SLEEPING.format(name=cat["name"])
        else:
            reaction = random.choice(texts.PET_REACTIONS[mood])
            text = reaction.format(name=cat["name"])
            if not rewarded:
                text += f"\n\n{texts.PET_COOLDOWN}"
            else:
                text += "\n\n💗 +۱ صمیمیت  •  🎀 +۴ شادی"
        if query:
            await query.edit_message_text(text, reply_markup=kb.back_home_kb())
        else:
            await update.message.reply_text(text, reply_markup=kb.back_home_kb())
    finally:
        conn.close()


def register(app):
    app.add_handler(CommandHandler("pet", pet_action))
    app.add_handler(CallbackQueryHandler(pet_action, pattern="^home_pet$"))
