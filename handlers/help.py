"""راهنما + دستورهای کمکی."""
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

import texts
import keyboards as kb


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(texts.HELP_TEXT, reply_markup=kb.back_home_kb())


def register(app):
    app.add_handler(CommandHandler("help", help_cmd))
