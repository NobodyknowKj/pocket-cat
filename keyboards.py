"""دکمه‌های شیشه‌ای (Inline Keyboard) — همه‌ی عملیات هم با دستور هم با دکمه در دسترس‌اند."""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from config import FOODS, SHOP_ITEMS


def _kb(rows: list[list[tuple[str, str]]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(text, callback_data=data) for text, data in row] for row in rows]
    )


def start_kb() -> InlineKeyboardMarkup:
    return _kb([
        [("🐾 آره، بیا دوست بشیم!", "start_friend")],
        [("🐈 اول یه نگاه بهت بندازم", "start_peek")],
    ])


def main_kb() -> InlineKeyboardMarkup:
    return _kb([
        [("🍗 غذا دادن", "home_feed"), ("🫳 نوازش کردن", "home_pet")],
        [("🧶 بازی کردن", "home_play"), ("💤 خوابیدن", "home_sleep")],
        [("🏠 خونه‌ی موچی", "home_house"), ("🎒 وسایل من", "home_inventory")],
        [("📖 خاطرات موچی", "home_memories"), ("⚙️ تنظیمات", "home_settings")],
        [("🔄 به‌روزرسانی وضعیت", "home_refresh")],
    ])


def back_home_kb() -> InlineKeyboardMarkup:
    return _kb([[("🏠 برگشت به خانه", "home_refresh")]])


def feed_kb() -> InlineKeyboardMarkup:
    rows = [[(f["name"], f"feed_{fid}")] for fid, f in FOODS.items()]
    rows.append([("🛒 خرید غذا", "feed_buy")])
    rows.append([("🏠 برگشت", "home_refresh")])
    return _kb(rows)


def feed_buy_kb() -> InlineKeyboardMarkup:
    rows = [[(f"خرید {f['name']} — {f['price']} سکه", f"buyfood_{fid}")] for fid, f in FOODS.items()]
    rows.append([("⬅️ برگشت به غذا", "home_feed")])
    return _kb(rows)


def play_menu_kb() -> InlineKeyboardMarkup:
    return _kb([
        [("🧶 نخ و پنجه", "play_thread")],
        [("🐭 شکار موش اسباب‌بازی", "play_mouse")],
        [("🙈 قایم‌باشک", "play_hide")],
        [("🎨 توپ رنگی", "play_ball")],
        [("🏠 برگشت", "home_refresh")],
    ])


def thread_kb(session_id: str) -> InlineKeyboardMarkup:
    return _kb([
        [("⬅️ نخ رو سمت چپ ببر!", f"playpick:{session_id}:left")],
        [("➡️ نخ رو سمت راست ببر!", f"playpick:{session_id}:right")],
        [("⬆️ نخ رو بالا ببر!", f"playpick:{session_id}:up")],
    ])


def mouse_kb(session_id: str) -> InlineKeyboardMarkup:
    return _kb([
        [("🛋️ زیر مبل", f"playpick:{session_id}:sofa")],
        [("📦 پشت جعبه", f"playpick:{session_id}:box")],
        [("🛏️ زیر تخت", f"playpick:{session_id}:bed")],
    ])


def hide_kb(session_id: str) -> InlineKeyboardMarkup:
    return _kb([
        [("🪟 پشت پرده", f"playpick:{session_id}:curtain")],
        [("📦 داخل جعبه", f"playpick:{session_id}:box")],
        [("🌿 پشت گلدون", f"playpick:{session_id}:plant")],
    ])


def ball_kb(session_id: str) -> InlineKeyboardMarkup:
    return _kb([
        [("🔴 قرمز", f"playpick:{session_id}:red"), ("🔵 آبی", f"playpick:{session_id}:blue")],
        [("🟢 سبز", f"playpick:{session_id}:green"), ("🟡 زرد", f"playpick:{session_id}:yellow")],
    ])


def shop_kb() -> InlineKeyboardMarkup:
    rows = [[(f"{item['name']} — {item['price']} سکه", f"buy_{item_id}")] for item_id, item in SHOP_ITEMS.items()]
    rows.append([("🏠 برگشت", "home_refresh")])
    return _kb(rows)


def settings_kb(notifications_enabled: bool) -> InlineKeyboardMarkup:
    label = "🔔 اعلان‌ها: روشن" if notifications_enabled else "🔕 اعلان‌ها: خاموش"
    return _kb([
        [(label, "settings_toggle_notif")],
        [("🗑️ پاک کردن داده‌ی بازی", "settings_clear_ask")],
        [("🏠 برگشت", "home_refresh")],
    ])


def settings_clear_kb() -> InlineKeyboardMarkup:
    return _kb([
        [("✅ بله، پاک کن", "settings_clear_yes"), ("❌ نه، منصرف شدم", "home_settings")],
    ])


def sleep_kb() -> InlineKeyboardMarkup:
    return _kb([
        [("💤 بذار بخوابه", "sleep_do"), ("⏰ بیدارش کن", "sleep_wake")],
        [("🏠 برگشت", "home_refresh")],
    ])
