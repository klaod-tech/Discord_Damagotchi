import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from datetime import date, timedelta

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def get_conn():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id          TEXT PRIMARY KEY,
            tamagotchi_name  TEXT,
            city             TEXT,
            wake_time        TEXT,
            init_weight      REAL,
            goal_weight      REAL,
            daily_cal_target INTEGER,
            breakfast_time   TEXT,
            lunch_time       TEXT,
            dinner_time      TEXT,
            thread_id        TEXT,
            created_at       TIMESTAMP DEFAULT NOW()
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS tamagotchi (
            user_id          TEXT PRIMARY KEY REFERENCES users(user_id),
            hp               INTEGER DEFAULT 100,
            hunger           INTEGER DEFAULT 50,
            mood             INTEGER DEFAULT 50,
            current_image    TEXT DEFAULT 'normal.png',
            embed_message_id TEXT,
            last_fed_at      TIMESTAMP,
            updated_at       TIMESTAMP DEFAULT NOW()
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS meals (
            meal_id      SERIAL PRIMARY KEY,
            user_id      TEXT REFERENCES users(user_id),
            meal_type    TEXT,
            food_name    TEXT,
            calories     INTEGER,
            protein      REAL,
            carbs        REAL,
            fat          REAL,
            fiber        REAL,
            input_method TEXT,
            gpt_comment  TEXT,
            recorded_at  TIMESTAMP DEFAULT NOW()
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS weather_log (
            log_id         SERIAL PRIMARY KEY,
            user_id        TEXT REFERENCES users(user_id),
            weather        TEXT,
            temp           REAL,
            pm10           INTEGER,
            pm25           INTEGER,
            selected_image TEXT,
            gpt_comment    TEXT,
            recorded_at    TIMESTAMP DEFAULT NOW()
        )
    """)

    conn.commit()
    cur.close()
    conn.close()
    print("[DB] 테이블 초기화 완료")

# ===== Users CRUD =====
def create_user(user_id, data: dict):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO users (
            user_id, tamagotchi_name, city, wake_time,
            init_weight, goal_weight, daily_cal_target,
            breakfast_time, lunch_time, dinner_time, thread_id
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (user_id) DO NOTHING
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
        data.get("thread_id"),
    ))
    conn.commit()
    cur.close()
    conn.close()

def get_user(user_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row

def update_user(user_id, **kwargs):
    conn = get_conn()
    cur = conn.cursor()
    fields = ", ".join(f"{k} = %s" for k in kwargs)
    values = list(kwargs.values()) + [user_id]
    cur.execute(f"UPDATE users SET {fields} WHERE user_id = %s", values)
    conn.commit()
    cur.close()
    conn.close()

def set_thread_id(user_id, thread_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET thread_id = %s WHERE user_id = %s",
        (thread_id, user_id)
    )
    conn.commit()
    cur.close()
    conn.close()

def get_all_users():
    """스케줄러 등에서 전체 유저 조회"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

# ===== Tamagotchi CRUD =====
def create_tamagotchi(user_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO tamagotchi (user_id)
        VALUES (%s)
        ON CONFLICT (user_id) DO NOTHING
    """, (user_id,))
    conn.commit()
    cur.close()
    conn.close()

def get_tamagotchi(user_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM tamagotchi WHERE user_id = %s", (user_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row

def update_tamagotchi(user_id, data: dict = None, **kwargs):
    conn = get_conn()
    cur = conn.cursor()
    fields_data = data if data else kwargs
    fields = ", ".join(f"{k} = %s" for k in fields_data)
    values = list(fields_data.values()) + [user_id]
    cur.execute(
        f"UPDATE tamagotchi SET {fields}, updated_at = NOW() WHERE user_id = %s",
        values
    )
    conn.commit()
    cur.close()
    conn.close()

def set_embed_message_id(user_id, message_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE tamagotchi SET embed_message_id = %s WHERE user_id = %s",
        (message_id, user_id)
    )
    conn.commit()
    cur.close()
    conn.close()

# ===== Meals CRUD =====
def create_meal(user_id, meal_type, food_name, calories,
                protein, carbs, fat, fiber, input_method, gpt_comment,
                recorded_date: date = None):
    """
    recorded_date: 소급 입력 시 해당 날짜 지정 (None이면 오늘)
    """
    conn = get_conn()
    cur = conn.cursor()

    if recorded_date is None:
        cur.execute("""
            INSERT INTO meals (
                user_id, meal_type, food_name, calories,
                protein, carbs, fat, fiber, input_method, gpt_comment
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (user_id, meal_type, food_name, calories,
              protein, carbs, fat, fiber, input_method, gpt_comment))
    else:
        # 소급 입력: recorded_at을 해당 날짜 정오로 설정
        recorded_at = f"{recorded_date} 12:00:00"
        cur.execute("""
            INSERT INTO meals (
                user_id, meal_type, food_name, calories,
                protein, carbs, fat, fiber, input_method, gpt_comment, recorded_at
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (user_id, meal_type, food_name, calories,
              protein, carbs, fat, fiber, input_method, gpt_comment, recorded_at))

    conn.commit()
    cur.close()
    conn.close()

def get_meals_by_date(user_id, target_date: date):
    """특정 날짜의 식사 기록 조회"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM meals
        WHERE user_id = %s
        AND recorded_at::date = %s
        ORDER BY recorded_at ASC
    """, (user_id, target_date))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def get_today_meals(user_id):
    return get_meals_by_date(user_id, date.today())

def get_calories_by_date(user_id, target_date: date) -> int:
    """특정 날짜의 총 칼로리"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT COALESCE(SUM(calories), 0) as total
        FROM meals
        WHERE user_id = %s
        AND recorded_at::date = %s
    """, (user_id, target_date))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row["total"] if row else 0

def get_today_calories(user_id) -> int:
    return get_calories_by_date(user_id, date.today())

def has_meal_type_on_date(user_id, meal_type: str, target_date: date) -> bool:
    """특정 날짜에 해당 meal_type이 이미 입력됐는지 확인"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(*) as cnt FROM meals
        WHERE user_id = %s
        AND meal_type = %s
        AND recorded_at::date = %s
    """, (user_id, meal_type, target_date))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return (row["cnt"] or 0) > 0

def is_all_meals_done_on_date(user_id, target_date: date) -> bool:
    """특정 날짜에 아침/점심/저녁이 모두 입력됐는지 확인"""
    for meal_type in ["아침", "점심", "저녁"]:
        if not has_meal_type_on_date(user_id, meal_type, target_date):
            return False
    return True

# ===== Weather Log CRUD =====
def create_weather_log(user_id, weather, temp, pm10, pm25, selected_image, gpt_comment):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO weather_log (
            user_id, weather, temp, pm10, pm25, selected_image, gpt_comment
        ) VALUES (%s,%s,%s,%s,%s,%s,%s)
    """, (user_id, weather, temp, pm10, pm25, selected_image, gpt_comment))
    conn.commit()
    cur.close()
    conn.close()

def get_latest_weather(user_id):
    """가장 최근 날씨 기록 조회"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM weather_log
        WHERE user_id = %s
        ORDER BY recorded_at DESC
        LIMIT 1
    """, (user_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row
