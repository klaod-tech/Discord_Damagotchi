import sqlite3
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.getenv("DATABASE_URL", "./tamagotchi.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS Users (
            user_id TEXT PRIMARY KEY,
            tamagotchi_name TEXT,
            city TEXT,
            wake_time TEXT,
            init_weight REAL,
            goal_weight REAL,
            daily_cal_target INTEGER,
            breakfast_time TEXT,
            lunch_time TEXT,
            dinner_time TEXT,
            thread_id TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS Tamagotchi (
            user_id TEXT PRIMARY KEY,
            hp INTEGER DEFAULT 70,
            hunger INTEGER DEFAULT 70,
            mood INTEGER DEFAULT 70,
            current_image TEXT DEFAULT 'normal.png',
            embed_message_id TEXT,
            last_fed_at DATETIME,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES Users(user_id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS Meals (
            meal_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            meal_type TEXT,
            food_name TEXT,
            calories INTEGER,
            protein REAL,
            carbs REAL,
            fat REAL,
            fiber REAL,
            input_method TEXT,
            gpt_comment TEXT,
            recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES Users(user_id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS Weather_Log (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            weather TEXT,
            temp REAL,
            pm10 INTEGER,
            pm25 INTEGER,
            selected_image TEXT,
            gpt_comment TEXT,
            recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES Users(user_id)
        )
    """)

    conn.commit()
    conn.close()


# ── Users ──────────────────────────────────────────────
def create_user(user_id: str, data: dict):
    conn = get_conn()
    conn.execute("""
        INSERT OR REPLACE INTO Users
        (user_id, tamagotchi_name, city, wake_time, init_weight, goal_weight,
         daily_cal_target, breakfast_time, lunch_time, dinner_time)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        data.get("tamagotchi_name"),
        data.get("city"),
        data.get("wake_time"),
        data.get("init_weight"),
        data.get("goal_weight"),
        data.get("daily_cal_target"),
        data.get("breakfast_time"),
        data.get("lunch_time"),
        data.get("dinner_time"),
    ))
    conn.commit()
    conn.close()


def get_user(user_id: str):
    conn = get_conn()
    row = conn.execute("SELECT * FROM Users WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_user(user_id: str, data: dict):
    conn = get_conn()
    fields = ", ".join(f"{k} = ?" for k in data)
    values = list(data.values()) + [user_id]
    conn.execute(f"UPDATE Users SET {fields} WHERE user_id = ?", values)
    conn.commit()
    conn.close()


def set_thread_id(user_id: str, thread_id: str):
    conn = get_conn()
    conn.execute("UPDATE Users SET thread_id = ? WHERE user_id = ?", (thread_id, user_id))
    conn.commit()
    conn.close()


# ── Tamagotchi ─────────────────────────────────────────
def create_tamagotchi(user_id: str):
    conn = get_conn()
    conn.execute("""
        INSERT OR IGNORE INTO Tamagotchi (user_id) VALUES (?)
    """, (user_id,))
    conn.commit()
    conn.close()


def get_tamagotchi(user_id: str):
    conn = get_conn()
    row = conn.execute("SELECT * FROM Tamagotchi WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_tamagotchi(user_id: str, data: dict):
    data["updated_at"] = datetime.now().isoformat()
    conn = get_conn()
    fields = ", ".join(f"{k} = ?" for k in data)
    values = list(data.values()) + [user_id]
    conn.execute(f"UPDATE Tamagotchi SET {fields} WHERE user_id = ?", values)
    conn.commit()
    conn.close()


def set_embed_message_id(user_id: str, message_id: str):
    conn = get_conn()
    conn.execute(
        "UPDATE Tamagotchi SET embed_message_id = ? WHERE user_id = ?",
        (message_id, user_id),
    )
    conn.commit()
    conn.close()


# ── Meals ──────────────────────────────────────────────
def add_meal(user_id: str, data: dict):
    conn = get_conn()
    conn.execute("""
        INSERT INTO Meals
        (user_id, meal_type, food_name, calories, protein, carbs, fat, fiber,
         input_method, gpt_comment)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        data.get("meal_type"),
        data.get("food_name"),
        data.get("calories"),
        data.get("protein"),
        data.get("carbs"),
        data.get("fat"),
        data.get("fiber"),
        data.get("input_method", "text"),
        data.get("gpt_comment"),
    ))
    conn.commit()
    conn.close()


def get_today_meals(user_id: str):
    conn = get_conn()
    rows = conn.execute("""
        SELECT * FROM Meals
        WHERE user_id = ?
          AND DATE(recorded_at) = DATE('now', 'localtime')
        ORDER BY recorded_at
    """, (user_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_today_calories(user_id: str) -> int:
    conn = get_conn()
    row = conn.execute("""
        SELECT COALESCE(SUM(calories), 0) AS total
        FROM Meals
        WHERE user_id = ?
          AND DATE(recorded_at) = DATE('now', 'localtime')
    """, (user_id,)).fetchone()
    conn.close()
    return row["total"] if row else 0


# ── Weather_Log ────────────────────────────────────────
def add_weather_log(user_id: str, data: dict):
    conn = get_conn()
    conn.execute("""
        INSERT INTO Weather_Log
        (user_id, weather, temp, pm10, pm25, selected_image, gpt_comment)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        data.get("weather"),
        data.get("temp"),
        data.get("pm10"),
        data.get("pm25"),
        data.get("selected_image"),
        data.get("gpt_comment"),
    ))
    conn.commit()
    conn.close()


def get_latest_weather(user_id: str):
    conn = get_conn()
    row = conn.execute("""
        SELECT * FROM Weather_Log
        WHERE user_id = ?
        ORDER BY recorded_at DESC LIMIT 1
    """, (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None
