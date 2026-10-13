"""تست منطق Pocket Cat — زمان، سطح، سقف روزانه، غذا، نوازش، idempotency.
بدون نیاز به تلگرام یا توکن اجرا می‌شود. با pytest یا مستقیم با python3.
"""
import os
import sys
import tempfile
import time

# اجرای مستقل: مسیر پروژه را به sys.path اضافه کن
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
import database as db
import game_logic


def fresh_db():
    """دیتابیس موقت تازه برای هر تست."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    db.init_db(tmp.name)
    return tmp.name


def make_cat(db_path, user_id=1, **overrides):
    conn = db.get_conn(db_path)
    try:
        db.get_or_create_user(conn, user_id, "test", "Test")
        cat = db.create_cat(conn, user_id, "موچی")
        cat = dict(cat)
        if overrides:
            db.update_cat(conn, cat["id"], **overrides)
            cat.update(overrides)
        return cat
    finally:
        conn.close()


# ---------- زمان ----------

def test_time_decay_awake():
    cat = {"hunger": 30, "energy": 80, "happiness": 65, "status": "awake", "last_updated": 1000000, "location": "خانه"}
    out = game_logic.apply_time_decay(cat, now=1000000 + 2 * 3600)
    assert out["hunger"] == 38, out  # +4*2
    assert out["energy"] == 76, out  # -2*2
    assert out["happiness"] == 63, out  # -1*2
    print("✓ test_time_decay_awake")


def test_time_decay_sleeping():
    cat = {"hunger": 30, "energy": 50, "happiness": 65, "status": "sleeping", "last_updated": 1000000, "location": "بالشت"}
    out = game_logic.apply_time_decay(cat, now=1000000 + 2 * 3600)
    assert out["energy"] == 74, out  # +12*2
    assert out["happiness"] == 65, out  # در خواب کم نمی‌شود
    assert out["hunger"] == 38, out
    print("✓ test_time_decay_sleeping")


def test_time_decay_resting():
    cat = {"hunger": 10, "energy": 50, "happiness": 50, "status": "resting", "last_updated": 1000000, "location": "خانه"}
    out = game_logic.apply_time_decay(cat, now=1000000 + 3600)
    assert out["energy"] == 55, out
    print("✓ test_time_decay_resting")


def test_clamp():
    cat = {"hunger": 98, "energy": 1, "happiness": 1, "status": "awake", "last_updated": 1000000, "location": "خانه"}
    out = game_logic.apply_time_decay(cat, now=1000000 + 5 * 3600)
    assert out["hunger"] == 100
    assert out["energy"] == 0
    assert out["happiness"] == 0
    print("✓ test_clamp")


# ---------- سطح ----------

def test_xp_formula():
    assert config.xp_needed_for_next_level(1) == 20
    assert config.xp_needed_for_next_level(2) == 30
    assert config.xp_needed_for_next_level(5) == 60
    print("✓ test_xp_formula")


def test_level_up_multiple():
    db_path = fresh_db()
    cat = make_cat(db_path, xp=18, level=1, coins=100, energy=90, happiness=50, intimacy=10)
    conn = db.get_conn(db_path)
    try:
        # ساخت جلسه با برنده‌ی مشخص و حل آن
        sid = db.create_game_session(conn, 1, "thread", "left")
        # برای کنترل نتیجه، مستقیم resolve را با picked=winning صدا می‌زنیم
        already, result, success = game_logic.resolve_play(conn, 1, cat, sid, "left")
        assert not already and success
        # 18 + 3 = 21 → سطح ۲، XP باقی‌مانده ۱، +۱۰ سکه سطح + ۵ سکه بازی = 115
        row = db.get_cat(conn, 1)
        assert row["level"] == 2, dict(row)
        assert row["xp"] == 1, dict(row)
        assert row["coins"] == 115, dict(row)
    finally:
        conn.close()
        os.unlink(db_path)
    print("✓ test_level_up_multiple")


# ---------- سقف روزانه ----------

def test_daily_cap():
    db_path = fresh_db()
    cat = make_cat(db_path, coins=100, energy=100, happiness=50)
    conn = db.get_conn(db_path)
    try:
        # ۱۰ دور موفق = ۵۰ سکه — دقیقاً سقف
        for _ in range(10):
            sid = db.create_game_session(conn, 1, "thread", "left")
            fresh = dict(db.get_cat(conn, 1))
            already, result, success = game_logic.resolve_play(conn, 1, fresh, sid, "left")
            assert not already
        row = db.get_cat(conn, 1)
        # ۱۰ دور موفق = ۵۰ سکه بازی + ۱ ارتقا (۱۰ سکه سطح) = ۱۶۰
        # XP: ۱۰×۳=۳۰ → بعد از ۷ دور سطح ۲ (۲۰ XP مصرف، ۱ باقی) + ۳ دور دیگر = ۱۰ XP
        assert row["coins"] == 160, dict(row)
        assert row["level"] == 2 and row["xp"] == 10, dict(row)
        # دور یازدهم باید capped شود (پاداش سکه ندهد)
        sid = db.create_game_session(conn, 1, "thread", "left")
        fresh = dict(db.get_cat(conn, 1))
        already, result, success = game_logic.resolve_play(conn, 1, fresh, sid, "left")
        assert result.get("capped") is True, result
    finally:
        conn.close()
        os.unlink(db_path)
    print("✓ test_daily_cap")


# ---------- غذا ----------

def test_feed_no_stock():
    db_path = fresh_db()
    cat = make_cat(db_path, hunger=50)
    conn = db.get_conn(db_path)
    try:
        ok, msg, _ = game_logic.feed_cat(conn, 1, cat, "fish")  # موجودی اولیه ماهی = ۰
        assert not ok and msg == "no_stock", (ok, msg)
    finally:
        conn.close()
        os.unlink(db_path)
    print("✓ test_feed_no_stock")


def test_feed_normal_clamps():
    db_path = fresh_db()
    cat = make_cat(db_path, hunger=20)
    conn = db.get_conn(db_path)
    try:
        # غذای معمولی داریم: ۳ عدد
        ok, msg, new_hunger = game_logic.feed_cat(conn, 1, cat, "food_normal")  # -25 → 0
        assert ok and new_hunger == 0, (ok, msg, new_hunger)
        assert db.get_item_qty(conn, 1, "food_normal") == 2
    finally:
        conn.close()
        os.unlink(db_path)
    print("✓ test_feed_normal_clamps")


def test_feed_full():
    db_path = fresh_db()
    cat = make_cat(db_path, hunger=3)
    conn = db.get_conn(db_path)
    try:
        ok, msg, _ = game_logic.feed_cat(conn, 1, cat, "food_normal")
        assert not ok and msg == "full"
    finally:
        conn.close()
        os.unlink(db_path)
    print("✓ test_feed_full")


# ---------- نوازش ----------

def test_pet_cooldown():
    db_path = fresh_db()
    cat = make_cat(db_path, happiness=50, intimacy=10, last_pet_at=int(time.time()))
    conn = db.get_conn(db_path)
    try:
        mood, rewarded, sleeping = game_logic.pet_cat(conn, 1, cat)
        assert not rewarded, "نوازش دوم در ۶۰ ثانیه نباید پاداش بدهد"
    finally:
        conn.close()
        os.unlink(db_path)
    print("✓ test_pet_cooldown")


def test_pet_sleeping_no_wake():
    db_path = fresh_db()
    cat = make_cat(db_path, status="sleeping", happiness=50, intimacy=10)
    conn = db.get_conn(db_path)
    try:
        mood, rewarded, sleeping = game_logic.pet_cat(conn, 1, cat)
        assert sleeping and not rewarded
        row = db.get_cat(conn, 1)
        assert row["status"] == "sleeping", "نوازش در خواب نباید بیدار کند"
    finally:
        conn.close()
        os.unlink(db_path)
    print("✓ test_pet_sleeping_no_wake")


# ---------- بازی: idempotency ----------

def test_play_idempotency():
    db_path = fresh_db()
    cat = make_cat(db_path, energy=90, happiness=50, coins=100)
    conn = db.get_conn(db_path)
    try:
        sid = db.create_game_session(conn, 1, "thread", "left")
        fresh = dict(db.get_cat(conn, 1))
        already1, r1, s1 = game_logic.resolve_play(conn, 1, fresh, sid, "left")
        assert not already1
        coins_after_first = db.get_cat(conn, 1)["coins"]
        # کلیک تکراری
        fresh2 = dict(db.get_cat(conn, 1))
        already2, r2, s2 = game_logic.resolve_play(conn, 1, fresh2, sid, "left")
        assert already2, "کلیک تکراری باید already باشد"
        assert db.get_cat(conn, 1)["coins"] == coins_after_first, "کلیک تکراری نباید سکه بدهد"
    finally:
        conn.close()
        os.unlink(db_path)
    print("✓ test_play_idempotency")


def test_play_blocked_low_energy():
    cat = {"energy": 5, "hunger": 30}
    ok, reason = game_logic.can_start_play(cat)
    assert not ok and reason == "low_energy"
    print("✓ test_play_blocked_low_energy")


def test_play_blocked_hungry():
    cat = {"energy": 80, "hunger": 95}
    ok, reason = game_logic.can_start_play(cat)
    assert not ok and reason == "too_hungry"
    print("✓ test_play_blocked_hungry")


# ---------- خرید ----------

def test_buy_not_enough():
    db_path = fresh_db()
    cat = make_cat(db_path, coins=10)
    conn = db.get_conn(db_path)
    try:
        ok, msg = game_logic.buy_item(conn, 1, cat, "cat_tree")  # ۸۰ سکه
        assert not ok and msg == "not_enough_coins"
    finally:
        conn.close()
        os.unlink(db_path)
    print("✓ test_buy_not_enough")


def test_buy_duplicate():
    db_path = fresh_db()
    cat = make_cat(db_path, coins=500)
    conn = db.get_conn(db_path)
    try:
        ok1, _ = game_logic.buy_item(conn, 1, cat, "color_ball")
        assert ok1
        cat2 = dict(db.get_cat(conn, 1))
        ok2, msg2 = game_logic.buy_item(conn, 1, cat2, "color_ball")
        assert not ok2 and msg2 == "already_owned"
    finally:
        conn.close()
        os.unlink(db_path)
    print("✓ test_buy_duplicate")


def test_start_twice_no_reset():
    """‎/start تکراری نباید ریست کند — با بررسی create_cat تکراری."""
    db_path = fresh_db()
    conn = db.get_conn(db_path)
    try:
        db.get_or_create_user(conn, 1)
        c1 = db.create_cat(conn, 1, "موچی")
        # تلاش دوم برای ساخت گربه — در منطق واقعی هندلر، اگر گربه وجود داشته باشد create صدا زده نمی‌شود.
        # اینجا فقط بررسی می‌کنیم که گربه‌ی موجود قابل خواندن است و مقدارش حفظ شده.
        c2 = db.get_cat(conn, 1)
        assert c2["name"] == "موچی" and c2["coins"] == 100
    finally:
        conn.close()
        os.unlink(db_path)
    print("✓ test_start_twice_no_reset")


ALL = [
    test_time_decay_awake, test_time_decay_sleeping, test_time_decay_resting, test_clamp,
    test_xp_formula, test_level_up_multiple, test_daily_cap,
    test_feed_no_stock, test_feed_normal_clamps, test_feed_full,
    test_pet_cooldown, test_pet_sleeping_no_wake,
    test_play_idempotency, test_play_blocked_low_energy, test_play_blocked_hungry,
    test_buy_not_enough, test_buy_duplicate, test_start_twice_no_reset,
]


if __name__ == "__main__":
    passed = 0
    failed = 0
    for fn in ALL:
        try:
            fn()
            passed += 1
        except AssertionError as e:
            print(f"✗ {fn.__name__} FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {fn.__name__} ERROR: {type(e).__name__}: {e}")
            failed += 1
    print(f"\nنتیجه: {passed} موفق، {failed} ناموفق از {len(ALL)} تست")
    sys.exit(1 if failed else 0)
