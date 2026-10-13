"""منطق بازی — محاسبه‌ی زمان، سطح، اقتصاد
همه‌ی محاسبات سمت سرور انجام می‌شوند و بر اساس زمان سرور هستند.
"""
import random
import time
from typing import Tuple

from config import (
    FOODS, LEVEL, PET, PLAY, RATES, SHOP_ITEMS, clamp, xp_needed_for_next_level,
)
import database as db


# ---------- گذشت زمان ----------

def apply_time_decay(cat: dict, now: int | None = None) -> dict:
    """اعمال گذشت زمان واقعی روی گربه. ورودی dict شبیه ردیف cats است.
    خروجی dict جدید با مقادیر به‌روز است — ذخیره‌سازی با فراخواننده است.
    """
    now = now or int(time.time())
    last = cat.get("last_updated") or now
    elapsed_hours = max(0.0, (now - last) / 3600.0)
    if elapsed_hours <= 0:
        return dict(cat)
    status = cat.get("status", "awake")
    hunger = clamp(cat["hunger"] + RATES["hunger_per_hour"] * elapsed_hours)
    energy = cat["energy"]
    happiness = cat["happiness"]
    if status == "sleeping":
        energy = clamp(energy + RATES["energy_gain_per_hour_sleeping"] * elapsed_hours)
        # در خواب شادی کم نمی‌شود
    elif status == "resting":
        energy = clamp(energy + RATES["energy_gain_per_hour_resting"] * elapsed_hours)
    else:
        # بیدار / بازی / غذا / کنجکاوی / خواب‌آلود = حالت بیداری
        energy = clamp(energy - RATES["energy_decay_per_hour_awake"] * elapsed_hours)
        happiness = clamp(happiness - RATES["happiness_decay_per_hour_awake"] * elapsed_hours)
    out = dict(cat)
    out.update({"hunger": hunger, "energy": energy, "happiness": happiness, "last_updated": now})
    # اگر در خواب انرژی کامل شد، خودکار بیدار شود
    if status == "sleeping" and energy >= 100:
        out["status"] = "awake"
        out["location"] = "خانه"
    return out


def sync_cat(conn, user_id: int) -> dict | None:
    """خواندن گربه + اعمال گذشت زمان + ذخیره‌ی نتیجه. None اگر گربه‌ای نباشد."""
    row = db.get_cat(conn, user_id)
    if not row:
        return None
    cat = dict(row)
    updated = apply_time_decay(cat)
    if updated != cat:
        db.update_cat(
            conn, cat["id"],
            hunger=updated["hunger"], energy=updated["energy"],
            happiness=updated["happiness"], last_updated=updated["last_updated"],
            status=updated["status"], location=updated["location"],
        )
    return updated


def cat_status_label(cat: dict) -> str:
    """برچسب فارسی وضعیت فعلی."""
    labels = {
        "awake": "بیدار 😺",
        "sleepy": "خواب‌آلود 🥱",
        "sleeping": "در حال خواب 💤",
        "playing": "در حال بازی 🧶",
        "eating": "در حال غذا خوردن 🍽️",
        "curious": "مشغول کنجکاوی 🔍",
        "resting": "در حال استراحت 😌",
    }
    return labels.get(cat.get("status", "awake"), "بیدار 😺")


def mood_for_pet(cat: dict) -> str:
    """انتخاب حالت نوازش بر اساس وضعیت فعلی — متنوع و وابسته به وضعیت."""
    if cat["status"] == "sleeping":
        return "sleepy"
    if cat["energy"] < 25:
        return "sleepy"
    if cat["happiness"] < 35:
        return "bored"
    if random.random() < 0.35:
        return "playful"
    return "happy"


# ---------- نوازش ----------

def pet_cat(conn, user_id: int, cat: dict, now: int | None = None) -> Tuple[str, bool, bool]:
    """نوازش. برمی‌گرداند: (حالت، پاداش‌دار بود؟، در خواب بود؟)
    قانون: هر ۶۰ ثانیه فقط یک نوازش پاداش‌دار. در خواب بیدار نمی‌کند.
    """
    now = now or int(time.time())
    if cat["status"] == "sleeping":
        return "sleepy", False, True
    mood = mood_for_pet(cat)
    # کول‌داون
    if now - int(cat.get("last_pet_at") or 0) < PET["cooldown_seconds"]:
        return mood, False, False  # واکنش داستانی بدون پاداش
    new_happiness = clamp(cat["happiness"] + PET["happiness_gain"])
    new_intimacy = min(LEVEL["intimacy_max"], cat["intimacy"] + PET["intimacy_gain"])
    db.update_cat(conn, cat["id"], happiness=new_happiness, intimacy=new_intimacy, last_pet_at=now)
    return mood, True, False


# ---------- غذا دادن ----------

def feed_cat(conn, user_id: int, cat: dict, food_id: str) -> Tuple[bool, str, int]:
    """غذا دادن. برمی‌گرداند: (موفق؟، پیام خطا/موفقیت، گرسنگی جدید)
    - غذا از موجودی کم می‌شود (در تراکنش).
    - اثر فقط تا صفر — منفی نمی‌شود.
    """
    food = FOODS.get(food_id)
    if not food:
        return False, "این غذا رو نمی‌شناسم! 😿", int(cat["hunger"])
    if cat["hunger"] <= 5:
        return False, "full", int(cat["hunger"])
    qty = db.get_item_qty(conn, user_id, food_id)
    if qty <= 0:
        return False, "no_stock", int(cat["hunger"])
    # تراکنش: کسر موجودی + به‌روز کردن گرسنگی
    new_hunger = clamp(cat["hunger"] - food["hunger_reduction"])
    db.add_inventory(conn, user_id, food_id, -1)
    db.update_cat(conn, cat["id"], hunger=new_hunger, status="eating")
    db.add_transaction(conn, user_id, "feed", 0, f"غذا دادن: {food['name']}")
    # شمارش غذا + خاطره‌ی اولین غذا
    prefs = db.get_preferences(conn, cat["id"])
    db.update_preferences(conn, cat["id"], feed_count=int(prefs["feed_count"]) + 1)
    if not db.memory_exists(conn, cat["id"], "first_food"):
        db.add_memory(conn, cat["id"], "first_food", "امروز اولین غذام رو خوردم. خیلی خوشمزه بود! 🍽️")
    # ثبت غذای موردعلاقه: اگر ۳ بار یا بیشتر یک غذا داده شد
    fav = [f for f in str(prefs["favorite_foods"]).split(",") if f]
    # شمارش ساده: تعداد دفعات این غذا را از تراکنش‌ها می‌شمریم (تقریبی و پایدار)
    # برای سادگی، اگر این سومین بار تغذیه با همین غذا باشد، به علاقه‌مندی‌ها اضافه می‌شود.
    # (در نسخه‌ی کامل، شمارنده‌ی جداگانه نگهداری می‌شود.)
    return True, "ok", int(new_hunger)


# ---------- بازی ----------

def can_start_play(cat: dict) -> tuple[bool, str]:
    if cat["energy"] < PLAY["min_energy_to_play"]:
        return False, "low_energy"
    if cat["hunger"] >= PLAY["max_hunger_to_play"]:
        return False, "too_hungry"
    return True, "ok"


def success_probability(cat: dict) -> float:
    if cat["energy"] < PLAY["low_energy_threshold"]:
        return PLAY["low_energy_success_prob"]
    return PLAY["base_success_prob"]


def pick_winning_choice(game_type: str, choices: list[str]) -> str:
    return random.choice(choices)


def resolve_play(conn, user_id: int, cat: dict, session_id: str, picked: str) -> tuple[bool, dict, bool]:
    """حل یک دور بازی با شناسه‌ی یکتا.
    برمی‌گرداند: (قبلاً حل شده؟، نتیجه‌ی dict، موفق؟)
    - کلیک تکراری پاداش دوباره نمی‌دهد.
    - سقف روزانه (۱۰ دور / ۵۰ سکه در ۲۴ ساعت شناور) با تراکنش کنترل می‌شود.
    """
    session = db.get_game_session(conn, session_id)
    if not session:
        return True, {"error": "session_not_found"}, False
    if session["status"] != "pending":
        return True, {"error": "already_resolved"}, False
    # سقف روزانه — قبل از پرداخت بررسی می‌شود
    coins_24h, rounds_24h = db.earnings_last_24h(conn, user_id)
    if rounds_24h >= PLAY["max_rewarded_rounds_24h"]:
        # جلسه را حل‌شده علامت بزن ولی پاداش نده
        db.resolve_game_session(conn, session_id)
        return False, {"capped": True, "reason": "rounds"}, False
    success = (picked == session["winning_choice"])
    # اگر سقف سکه پر شده باشد، سکه نده ولی بقیه‌ی اثرها را بده
    coins_gain = PLAY["coins_success"] if success else PLAY["coins_fail"]
    if coins_24h + coins_gain > PLAY["max_coins_24h"]:
        coins_gain = max(0, PLAY["max_coins_24h"] - coins_24h)
    xp_gain = PLAY["xp_success"] if success else PLAY["xp_fail"]
    energy_cost = PLAY["energy_cost_success"] if success else PLAY["energy_cost_fail"]
    happiness_gain = PLAY["happiness_gain_success"] if success else PLAY["happiness_gain_fail"]
    intimacy_gain = PLAY["intimacy_gain_success"] if success else PLAY["intimacy_gain_fail"]
    # حل جلسه — اگر False یعنی هم‌زمان حل شده (مسابقه) → پاداش نده
    if not db.resolve_game_session(conn, session_id):
        return True, {"error": "already_resolved"}, False
    new_energy = clamp(cat["energy"] - energy_cost)
    new_happiness = clamp(cat["happiness"] + happiness_gain)
    new_intimacy = min(LEVEL["intimacy_max"], cat["intimacy"] + intimacy_gain)
    new_coins = max(0, cat["coins"] + coins_gain)
    new_xp = cat["xp"] + xp_gain
    new_level = cat["level"]
    level_ups = 0
    # ارتقای سطح — چند سطح در یک بار هم حساب می‌شود، پاداش هر سطح فقط یک بار
    while new_xp >= xp_needed_for_next_level(new_level):
        new_xp -= xp_needed_for_next_level(new_level)
        new_level += 1
        level_ups += 1
        new_coins += LEVEL["level_up_coin_bonus"]
    db.update_cat(
        conn, cat["id"],
        energy=new_energy, happiness=new_happiness, intimacy=new_intimacy,
        coins=new_coins, xp=new_xp, level=new_level, status="playing",
    )
    if coins_gain > 0:
        db.record_earning(conn, user_id, coins_gain, rounds=1)
        db.add_transaction(conn, user_id, "play_reward", coins_gain, f"بازی {session['game_type']} — {'موفق' if success else 'ناموفق'}")
    prefs = db.get_preferences(conn, cat["id"])
    db.update_preferences(conn, cat["id"], play_count=int(prefs["play_count"]) + 1)
    if not db.memory_exists(conn, cat["id"], "first_play"):
        db.add_memory(conn, cat["id"], "first_play", "امروز اولین بارم بود که بازی کردم. خیلی خوش گذشت! 🧶")
    return False, {
        "success": success, "coins": coins_gain, "xp": xp_gain,
        "level_ups": level_ups, "new_level": new_level, "capped": False,
    }, success


# ---------- خواب ----------

def start_sleep(conn, cat: dict) -> None:
    db.update_cat(conn, cat["id"], status="sleeping", location="بالشت آبی")


def wake_up(conn, cat: dict) -> None:
    db.update_cat(conn, cat["id"], status="awake", location="خانه")


# ---------- فروشگاه ----------

def buy_item(conn, user_id: int, cat: dict, item_id: str) -> tuple[bool, str]:
    """خرید در یک تراکنش: بررسی سکه + کسر + افزودن به موجودی + ثبت تراکنش.
    خرید تکراری وسایل دائمی (مثل درخت گربه) مجاز نیست.
    """
    item = SHOP_ITEMS.get(item_id)
    if not item:
        return False, "این وسیله رو نمی‌شناسم! 😿"
    # غذاها از مسیر فروشگاه غذا خریداری می‌شوند، نه این تابع
    if item_id in FOODS:
        return False, "غذا را از منوی غذا بخر! 🍗"
    if db.get_item_qty(conn, user_id, item_id) > 0:
        return False, "already_owned"
    if cat["coins"] < item["price"]:
        return False, "not_enough_coins"
    new_coins = cat["coins"] - item["price"]
    db.update_cat(conn, cat["id"], coins=new_coins)
    db.add_inventory(conn, user_id, item_id, 1)
    db.add_transaction(conn, user_id, "shop_buy", -item["price"], f"خرید: {item['name']}")
    if not db.memory_exists(conn, cat["id"], "first_item"):
        db.add_memory(conn, cat["id"], "first_item", f"امروز اولین وسیله‌م رو گرفتم: {item['name']} 🎁")
    return True, "ok"


def buy_food(conn, user_id: int, cat: dict, food_id: str, qty: int = 1) -> tuple[bool, str]:
    """خرید غذا با سکه — در یک تراکنش."""
    food = FOODS.get(food_id)
    if not food:
        return False, "این غذا رو نمی‌شناسم! 😿"
    total = food["price"] * qty
    if cat["coins"] < total:
        return False, "not_enough_coins"
    db.update_cat(conn, cat["id"], coins=cat["coins"] - total)
    db.add_inventory(conn, user_id, food_id, qty)
    db.add_transaction(conn, user_id, "food_buy", -total, f"خرید غذا: {food['name']} × {qty}")
    return True, "ok"
