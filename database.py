"""لایه‌ی پایگاه داده — SQLite
همه‌ی عملیات اقتصادی (خرید، کسر موجودی، ثبت تراکنش) در یک تراکنش انجام می‌شوند.
زمان سرور مبنای محاسبات است.
"""
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Optional

from config import DB_PATH, INITIAL, INITIAL_INVENTORY


def get_conn(db_path: str = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init_db(db_path: str = DB_PATH) -> None:
    """ساخت همه‌ی جداول در صورت نبودن. برای تست هم قابل استفاده است."""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = get_conn(db_path)
    try:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            created_at INTEGER NOT NULL,
            state TEXT NOT NULL DEFAULT 'idle',
            notifications_enabled INTEGER NOT NULL DEFAULT 0,
            notify_hour INTEGER NOT NULL DEFAULT 10
        );
        CREATE TABLE IF NOT EXISTS cats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            name TEXT NOT NULL,
            intimacy INTEGER NOT NULL DEFAULT 10,
            hunger REAL NOT NULL DEFAULT 30,
            energy REAL NOT NULL DEFAULT 80,
            happiness REAL NOT NULL DEFAULT 65,
            coins INTEGER NOT NULL DEFAULT 100,
            xp INTEGER NOT NULL DEFAULT 0,
            level INTEGER NOT NULL DEFAULT 1,
            status TEXT NOT NULL DEFAULT 'awake',
            location TEXT NOT NULL DEFAULT 'خانه',
            last_updated INTEGER NOT NULL,
            last_pet_at INTEGER NOT NULL DEFAULT 0,
            created_at INTEGER NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(telegram_id)
        );
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            item_id TEXT NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 0,
            UNIQUE(user_id, item_id),
            FOREIGN KEY (user_id) REFERENCES users(telegram_id)
        );
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cat_id INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            description TEXT NOT NULL,
            created_at INTEGER NOT NULL,
            FOREIGN KEY (cat_id) REFERENCES cats(id)
        );
        CREATE TABLE IF NOT EXISTS preferences (
            cat_id INTEGER PRIMARY KEY,
            favorite_foods TEXT NOT NULL DEFAULT '',
            favorite_games TEXT NOT NULL DEFAULT '',
            favorite_sleep_spot TEXT NOT NULL DEFAULT 'بالشت آبی',
            play_count INTEGER NOT NULL DEFAULT 0,
            feed_count INTEGER NOT NULL DEFAULT 0,
            discovered_traits TEXT NOT NULL DEFAULT '',
            FOREIGN KEY (cat_id) REFERENCES cats(id)
        );
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            amount INTEGER NOT NULL,
            note TEXT NOT NULL DEFAULT '',
            created_at INTEGER NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(telegram_id)
        );
        CREATE TABLE IF NOT EXISTS game_sessions (
            id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            game_type TEXT NOT NULL,
            winning_choice TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at INTEGER NOT NULL,
            resolved_at INTEGER,
            FOREIGN KEY (user_id) REFERENCES users(telegram_id)
        );
        CREATE TABLE IF NOT EXISTS daily_earnings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount INTEGER NOT NULL,
            rounds INTEGER NOT NULL DEFAULT 1,
            created_at INTEGER NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(telegram_id)
        );
        CREATE TABLE IF NOT EXISTS quests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            quest_id TEXT NOT NULL,
            date TEXT NOT NULL,
            completed INTEGER NOT NULL DEFAULT 0,
            UNIQUE(user_id, quest_id, date),
            FOREIGN KEY (user_id) REFERENCES users(telegram_id)
        );
        """)
        conn.commit()
    finally:
        conn.close()


# ---------- کاربران و گربه ----------

def get_or_create_user(conn, telegram_id: int, username: str = "", first_name: str = "") -> sqlite3.Row:
    now = int(time.time())
    row = conn.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)).fetchone()
    if row:
        return row
    conn.execute(
        "INSERT INTO users (telegram_id, username, first_name, created_at) VALUES (?,?,?,?)",
        (telegram_id, username or "", first_name or "", now),
    )
    conn.commit()
    return conn.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)).fetchone()


def set_user_state(conn, telegram_id: int, state: str) -> None:
    conn.execute("UPDATE users SET state = ? WHERE telegram_id = ?", (state, telegram_id))
    conn.commit()


def get_user_state(conn, telegram_id: int) -> str:
    row = conn.execute("SELECT state FROM users WHERE telegram_id = ?", (telegram_id,)).fetchone()
    return row["state"] if row else "idle"


def get_cat(conn, user_id: int) -> Optional[sqlite3.Row]:
    return conn.execute("SELECT * FROM cats WHERE user_id = ?", (user_id,)).fetchone()


def create_cat(conn, user_id: int, name: str) -> sqlite3.Row:
    """ساخت گربه با مقادیر اولیه + موجودی اولیه + خاطره‌ی اولین ملاقات."""
    now = int(time.time())
    cur = conn.execute(
        """INSERT INTO cats (user_id, name, intimacy, hunger, energy, happiness,
                             coins, xp, level, status, location, last_updated, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (user_id, name, INITIAL["intimacy"], INITIAL["hunger"], INITIAL["energy"],
         INITIAL["happiness"], INITIAL["coins"], INITIAL["xp"], INITIAL["level"],
         "awake", "خانه", now, now),
    )
    cat_id = cur.lastrowid
    conn.execute("INSERT INTO preferences (cat_id) VALUES (?)", (cat_id,))
    for item_id, qty in INITIAL_INVENTORY.items():
        conn.execute(
            "INSERT INTO inventory (user_id, item_id, quantity) VALUES (?,?,?)",
            (user_id, item_id, qty),
        )
    conn.execute(
        "INSERT INTO memories (cat_id, event_type, description, created_at) VALUES (?,?,?,?)",
        (cat_id, "first_meet", f"امروز با یه انسان آشنا شدم. هنوز نمی‌دونم قابل اعتماده یا نه، ولی غذا داشت. 🐟", now),
    )
    conn.execute(
        "INSERT INTO transactions (user_id, type, amount, note, created_at) VALUES (?,?,?,?,?)",
        (user_id, "initial_coins", INITIAL["coins"], "سکه‌ی اولیه", now),
    )
    conn.commit()
    return get_cat(conn, user_id)


def update_cat(conn, cat_id: int, **fields) -> None:
    if not fields:
        return
    sets = ", ".join(f"{k} = ?" for k in fields)
    conn.execute(f"UPDATE cats SET {sets} WHERE id = ?", (*fields.values(), cat_id))
    conn.commit()


# ---------- موجودی ----------

def get_inventory(conn, user_id: int) -> dict[str, int]:
    rows = conn.execute("SELECT item_id, quantity FROM inventory WHERE user_id = ?", (user_id,)).fetchall()
    return {r["item_id"]: r["quantity"] for r in rows}


def get_item_qty(conn, user_id: int, item_id: str) -> int:
    row = conn.execute(
        "SELECT quantity FROM inventory WHERE user_id = ? AND item_id = ?", (user_id, item_id)
    ).fetchone()
    return row["quantity"] if row else 0


def add_inventory(conn, user_id: int, item_id: str, delta: int) -> int:
    """افزودن/کم کردن موجودی در تراکنش. مقدار منفی مجاز نیست — اگر کم شود به صفر می‌رسد."""
    cur_qty = get_item_qty(conn, user_id, item_id)
    new_qty = max(0, cur_qty + delta)
    conn.execute(
        """INSERT INTO inventory (user_id, item_id, quantity) VALUES (?,?,?)
           ON CONFLICT(user_id, item_id) DO UPDATE SET quantity = excluded.quantity""",
        (user_id, item_id, new_qty),
    )
    conn.commit()
    return new_qty


# ---------- خاطرات و ترجیحات ----------

def add_memory(conn, cat_id: int, event_type: str, description: str) -> None:
    conn.execute(
        "INSERT INTO memories (cat_id, event_type, description, created_at) VALUES (?,?,?,?)",
        (cat_id, event_type, description, int(time.time())),
    )
    conn.commit()


def get_memories(conn, cat_id: int, limit: int = 30) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM memories WHERE cat_id = ? ORDER BY created_at ASC LIMIT ?",
        (cat_id, limit),
    ).fetchall()


def memory_exists(conn, cat_id: int, event_type: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM memories WHERE cat_id = ? AND event_type = ? LIMIT 1", (cat_id, event_type)
    ).fetchone()
    return row is not None


def get_preferences(conn, cat_id: int) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM preferences WHERE cat_id = ?", (cat_id,)).fetchone()
    if not row:
        conn.execute("INSERT INTO preferences (cat_id) VALUES (?)", (cat_id,))
        conn.commit()
        row = conn.execute("SELECT * FROM preferences WHERE cat_id = ?", (cat_id,)).fetchone()
    return row


def update_preferences(conn, cat_id: int, **fields) -> None:
    if not fields:
        return
    sets = ", ".join(f"{k} = ?" for k in fields)
    conn.execute(f"UPDATE preferences SET {sets} WHERE cat_id = ?", (*fields.values(), cat_id))
    conn.commit()


# ---------- تراکنش و درآمد روزانه ----------

def add_transaction(conn, user_id: int, tx_type: str, amount: int, note: str = "") -> None:
    conn.execute(
        "INSERT INTO transactions (user_id, type, amount, note, created_at) VALUES (?,?,?,?,?)",
        (user_id, tx_type, amount, note, int(time.time())),
    )
    conn.commit()


def earnings_last_24h(conn, user_id: int, now: Optional[int] = None) -> tuple[int, int]:
    """مجموع سکه و دورهای پاداش‌دار در پنجره‌ی شناور ۲۴ ساعته‌ی گذشته."""
    now = now or int(time.time())
    row = conn.execute(
        "SELECT COALESCE(SUM(amount),0) AS coins, COALESCE(SUM(rounds),0) AS rounds "
        "FROM daily_earnings WHERE user_id = ? AND created_at > ?",
        (user_id, now - 24 * 3600),
    ).fetchone()
    return int(row["coins"]), int(row["rounds"])


def record_earning(conn, user_id: int, amount: int, rounds: int = 1) -> None:
    conn.execute(
        "INSERT INTO daily_earnings (user_id, amount, rounds, created_at) VALUES (?,?,?,?)",
        (user_id, amount, rounds, int(time.time())),
    )
    conn.commit()


# ---------- جلسات بازی (idempotency) ----------

def create_game_session(conn, user_id: int, game_type: str, winning_choice: str) -> str:
    session_id = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO game_sessions (id, user_id, game_type, winning_choice, created_at) VALUES (?,?,?,?,?)",
        (session_id, user_id, game_type, winning_choice, int(time.time())),
    )
    conn.commit()
    return session_id


def get_game_session(conn, session_id: str) -> Optional[sqlite3.Row]:
    return conn.execute("SELECT * FROM game_sessions WHERE id = ?", (session_id,)).fetchone()


def resolve_game_session(conn, session_id: str) -> bool:
    """علامت‌گذاری جلسه به‌عنوان حل‌شده. اگر قبلاً حل شده بود False برمی‌گرداند (کلیک تکراری)."""
    cur = conn.execute(
        "UPDATE game_sessions SET status = 'resolved', resolved_at = ? WHERE id = ? AND status = 'pending'",
        (int(time.time()), session_id),
    )
    conn.commit()
    return cur.rowcount == 1
