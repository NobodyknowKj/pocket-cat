"""تنظیمات مرکزی بات Pocket Cat 🐈
همه‌ی مقادیر اقتصادی و عددی بازی فقط اینجاست تا بدون دست‌کاری کد
بتوان اقتصاد را تنظیم کرد. هیچ مبلغی از کلاینت پذیرفته نمی‌شود.
"""
import os
from pathlib import Path

# ---------- توکن و دیتابیس ----------
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = os.environ.get("POCKET_CAT_DB", str(BASE_DIR / "pocket_cat.db"))

DEFAULT_CAT_NAME = "موچی"

# ---------- مقادیر اولیه ----------
INITIAL = {
    "hunger": 30,      # 0 = سیر، 100 = خیلی گرسنه
    "energy": 80,
    "happiness": 65,
    "intimacy": 10,    # 0 تا 1000
    "coins": 100,
    "xp": 0,
    "level": 1,
}

# ---------- نرخ‌های زمانی (به ازای هر ساعت) ----------
RATES = {
    "hunger_per_hour": 4,
    "happiness_decay_per_hour_awake": 1,
    "energy_decay_per_hour_awake": 2,
    "energy_gain_per_hour_sleeping": 12,
    "energy_gain_per_hour_resting": 5,
}

# ---------- موجودی اولیه ----------
INITIAL_INVENTORY = {
    "food_normal": 3,   # غذای معمولی
    "treat": 1,         # تشویقی
    "ball": 1,          # توپ بازی
    "bed": 1,           # تخت خواب
}

# ---------- غذاها: قیمت (سکه) و کاهش گرسنگی ----------
FOODS = {
    "food_normal": {"name": "🥣 غذای معمولی گربه", "price": 8,  "hunger_reduction": 25},
    "chicken":     {"name": "🍗 مرغ",               "price": 12, "hunger_reduction": 35},
    "fish":        {"name": "🐟 ماهی",               "price": 15, "hunger_reduction": 40},
    "treat":       {"name": "🥛 تشویقی گربه",        "price": 6,  "hunger_reduction": 10},
}

# ---------- نوازش ----------
PET = {
    "happiness_gain": 4,
    "intimacy_gain": 1,
    "cooldown_seconds": 60,
}

# ---------- بازی ----------
PLAY = {
    "energy_cost_success": 10,
    "energy_cost_fail": 5,
    "happiness_gain_success": 12,
    "happiness_gain_fail": 3,
    "intimacy_gain_success": 2,
    "intimacy_gain_fail": 1,
    "coins_success": 5,
    "coins_fail": 2,
    "xp_success": 3,
    "xp_fail": 1,
    "base_success_prob": 0.70,
    "low_energy_success_prob": 0.50,  # وقتی انرژی < 25
    "low_energy_threshold": 25,
    "min_energy_to_play": 10,
    "max_hunger_to_play": 90,  # >= 90 بازی شروع نمی‌شود
    "max_rewarded_rounds_24h": 10,
    "max_coins_24h": 50,
}

# ---------- سطح ----------
LEVEL = {
    "intimacy_max": 1000,
    "level_up_coin_bonus": 10,
}

def xp_needed_for_next_level(level: int) -> int:
    """XP لازم برای رفتن از سطح L به L+1 — فرمول سناریو: 10*(L+1)"""
    return 10 * (level + 1)

# ---------- فروشگاه MVP ----------
# اثر = باز کردن محتوا، نه ضریب قدرت. خرید دائمی، بدون فروش مجدد.
SHOP_ITEMS = {
    "color_ball":   {"name": "🎨 توپ رنگی",      "price": 20, "category": "toy",  "effect": "باز کردن تنوع بازی توپ رنگی", "description": "توپ رنگی جدید — موچی با ذوق بیشتری دنبالش می‌کنه."},
    "toy_mouse":    {"name": "🐭 موش پارچه‌ای",   "price": 35, "category": "toy",  "effect": "باز کردن واکنش ویژه شکار", "description": "موش پارچه‌ای — شکار موردعلاقه‌ی موچی می‌شه."},
    "soft_pillow":  {"name": "🛏️ بالشت نرم",     "price": 40, "category": "home", "effect": "باز کردن واکنش خواب جدید", "description": "بالشت نرم‌تر — خواب موچی عمیق‌تر و بامزه‌تر می‌شه."},
    "cardboard_box":{"name": "📦 جعبه‌ی مقوایی",  "price": 25, "category": "home", "effect": "باز کردن رویداد تصادفی جعبه", "description": "جعبه‌ی مقوایی — موچی عاشق قایم شدن توشه!"},
    "cat_tree":     {"name": "🌳 درخت گربه",    "price": 80, "category": "home", "effect": "باز کردن محل جدید خانه", "description": "درخت گربه — موچی از بالا به همه نگاه می‌کنه."},
    # تزئینی (فاز کامل)
    "collar":       {"name": "🎀 قلاده‌ی رنگی",   "price": 30, "category": "decor", "effect": "تزئینی — واکنش ظاهری", "description": "قلاده‌ی رنگی و خوشگل برای موچی."},
    "small_hat":    {"name": "🎩 کلاه کوچک",     "price": 35, "category": "decor", "effect": "تزئینی — واکنش ظاهری", "description": "کلاه کوچک بامزه."},
    "bow":          {"name": "🎀 پاپیون",        "price": 25, "category": "decor", "effect": "تزئینی — واکنش ظاهری", "description": "پاپیون ناز برای مهمونی‌ها."},
}

# ---------- مأموریت‌های روزانه (اختیاری، بدون جریمه) ----------
DAILY_QUESTS = [
    {"id": "feed_once",  "text": "🍗 یک بار به گربه غذا بده",      "reward_coins": 5},
    {"id": "play_once",  "text": "🧶 با گربه بازی کن",             "reward_coins": 5},
    {"id": "check_home", "text": "🏠 خانه را بررسی کن",             "reward_coins": 3},
    {"id": "new_memory", "text": "📖 یک خاطره‌ی جدید ثبت کن",       "reward_coins": 3},
    {"id": "try_toy",    "text": "🎁 یک اسباب‌بازی را امتحان کن",   "reward_coins": 4},
]

# ---------- اتفاق‌های تصادفی ----------
RANDOM_EVENTS = [
    {"id": "box", "text": "موچی یه جعبه‌ی خالی پیدا کرده.\nالان بیست دقیقه‌ست که داخلشه و به هیچ‌کس توضیح نمی‌ده چرا. 📦"},
    {"id": "bird", "text": "موچی پشت پنجره نشسته و پرنده‌ها رو تماشا می‌کنه.\nدمش با تمرکز کامل تکون می‌خوره... 👀"},
    {"id": "lost_ball", "text": "توپ موچی زیر مبل رفته.\nموچی به مبل نگاه می‌کنه.\nمبل به موچی نگاه نمی‌کنه.\nیه بحران جدی شروع شده. 😾"},
    {"id": "discover", "text": "موچی یه چیز عجیب کنار دیوار پیدا کرده...\nسه بار بو می‌کشه و بعد با احتیاط بهش پنجه می‌زنه. 🔍"},
]
# نام مستعار (تایپ قدیمی)
RRANDOM_EVENTS_ALIAS = RANDOM_EVENTS

def clamp(value: float, low: float = 0, high: float = 100) -> float:
    """محدود کردن مقدار در بازه‌ی مجاز."""
    return max(low, min(high, value))
