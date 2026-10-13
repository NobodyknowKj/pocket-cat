"""نقطه‌ی ورود بات Pocket Cat 🐈
Python + python-telegram-bot v20+ (async) + SQLite
توکن فقط از متغیر محیطی TELEGRAM_BOT_TOKEN خوانده می‌شود — هرگز هاردکد نکنید.
"""
import logging
import os
import sys

from telegram import BotCommand, Update
from telegram.ext import ApplicationBuilder, ContextTypes

import database as db
from config import BOT_TOKEN

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger("pocket_cat")


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """مدیریت خطا — پیام قابل‌فهم فارسی، بدون خراب کردن داده."""
    logger.exception("خطا در پردازش آپدیت: %s", context.error)
    try:
        if isinstance(update, Update) and update.effective_message:
            await update.effective_message.reply_text(
                "اوه! یه مشکلی پیش اومد... 😿\n\nنگران نباش، اطلاعاتت سالمه. دوباره تلاش کن."
            )
    except Exception:
        pass


COMMANDS = [
    BotCommand("start", "شروع بازی"),
    BotCommand("home", "خانه و وضعیت گربه"),
    BotCommand("feed", "غذا دادن"),
    BotCommand("pet", "نوازش"),
    BotCommand("play", "بازی"),
    BotCommand("sleep", "خوابیدن"),
    BotCommand("inventory", "وسایل"),
    BotCommand("shop", "فروشگاه"),
    BotCommand("memories", "خاطرات"),
    BotCommand("profile", "مشخصات گربه"),
    BotCommand("settings", "تنظیمات"),
    BotCommand("help", "راهنما"),
]


async def post_init(app):
    await app.bot.set_my_commands(COMMANDS)


def build_app():
    if not BOT_TOKEN:
        print("خطا: متغیر محیطی TELEGRAM_BOT_TOKEN تنظیم نشده است.", file=sys.stderr)
        print("از .env.example کپی بگیر و توکن را از @BotFather بگیر.", file=sys.stderr)
        sys.exit(1)
    db.init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()
    app.add_error_handler(on_error)
    # ثبت هندلرها — ترتیب مهم است: start اول (پیام نام)، بعد بقیه
    from handlers import start as h_start
    from handlers import home as h_home
    from handlers import feed as h_feed
    from handlers import pet as h_pet
    from handlers import play as h_play
    from handlers import sleep as h_sleep
    from handlers import shop as h_shop
    from handlers import memories as h_memories
    from handlers import settings as h_settings
    from handlers import help as h_help

    for mod in (h_start, h_home, h_feed, h_pet, h_play, h_sleep, h_shop, h_memories, h_settings, h_help):
        mod.register(app)
    return app


def main():
    app = build_app()
    logger.info("بات Pocket Cat شروع به کار کرد 🐈")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
