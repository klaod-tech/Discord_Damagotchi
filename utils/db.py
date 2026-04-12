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
            gender           TEXT,
            age              INTEGER,
            height           REAL,
            created_at       TIMESTAMP DEFAULT NOW()
        )
    """)

    # 기존 users 테이블에 컬럼 누락 시 추가 (마이그레이션)
    for col, col_type in [("gender", "TEXT"), ("age", "INTEGER"), ("height", "REAL")]:
        cur.execute(f"""
            ALTER TABLE users ADD COLUMN IF NOT EXISTS {col} {col_type}
        """)

    # 스트릭 / 배지 컬럼 (v2.7 마이그레이션)
    for col, col_type, default in [
        ("streak",     "INTEGER", "0"),
        ("max_streak", "INTEGER", "0"),
        ("badges",     "TEXT",    "'[]'"),
    ]:
        cur.execute(
            f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {col} {col_type} DEFAULT {default}"
        )

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

    cur.execute("""
        CREATE TABLE IF NOT EXISTS weight_log (
            log_id      SERIAL PRIMARY KEY,
            user_id     TEXT REFERENCES users(user_id),
            weight      REAL,
            recorded_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # 이메일 컬럼 마이그레이션 (v3.0)
    for col, col_type in [
        ("naver_email",    "TEXT"),
        ("naver_app_pw",   "TEXT"),
        ("email_last_uid", "INTEGER"),
        ("mail_thread_id", "TEXT"),      # 메일 전용 쓰레드 ID
    ]:
        cur.execute(f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {col} {col_type}")

    # 알림 받을 발신자 목록
    cur.execute("""
        CREATE TABLE IF NOT EXISTS email_senders (
            sender_id    SERIAL PRIMARY KEY,
            user_id      TEXT REFERENCES users(user_id) ON DELETE CASCADE,
            sender_email TEXT NOT NULL,
            nickname     TEXT,
            created_at   TIMESTAMP DEFAULT NOW(),
            UNIQUE (user_id, sender_email)
        )
    """)

    # 수신 이메일 로그 (ML 학습 데이터)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS email_log (
            log_id       SERIAL PRIMARY KEY,
            user_id      TEXT REFERENCES users(user_id) ON DELETE CASCADE,
            sender_email TEXT,
            subject      TEXT,
            summary_gpt  TEXT,
            is_spam      BOOLEAN DEFAULT FALSE,
            received_at  TIMESTAMP DEFAULT NOW()
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
            breakfast_time, lunch_time, dinner_time, thread_id,
            gender, age, height
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (user_id) DO UPDATE SET
            tamagotchi_name  = EXCLUDED.tamagotchi_name,
            city             = EXCLUDED.city,
            wake_time        = EXCLUDED.wake_time,
            init_weight      = EXCLUDED.init_weight,
            goal_weight      = EXCLUDED.goal_weight,
            daily_cal_target = EXCLUDED.daily_cal_target,
            breakfast_time   = EXCLUDED.breakfast_time,
            lunch_time       = EXCLUDED.lunch_time,
            dinner_time      = EXCLUDED.dinner_time,
            thread_id        = EXCLUDED.thread_id,
            gender           = EXCLUDED.gender,
            age              = EXCLUDED.age,
            height           = EXCLUDED.height
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
        data.get("gender"),
        data.get("age"),
        data.get("height"),
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
        ON CONFLICT (user_id) DO UPDATE SET
            hp               = 100,
            hunger           = 50,
            mood             = 50,
            current_image    = 'normal.png',
            embed_message_id = NULL,
            last_fed_at      = NULL,
            updated_at       = NOW()
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
        AND (recorded_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Seoul')::date = %s
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
        AND (recorded_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Seoul')::date = %s
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
        AND (recorded_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Seoul')::date = %s
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


# ===== Streak / Badge CRUD =====

def update_streak(user_id: str, streak: int, max_streak: int):
    """연속 기록일 업데이트"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET streak = %s, max_streak = %s WHERE user_id = %s",
        (streak, max_streak, user_id),
    )
    conn.commit()
    cur.close()
    conn.close()


def add_badges(user_id: str, badge_ids: list):
    """기존 badges JSON 배열에 새 배지를 중복 없이 추가"""
    import json as _json
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT badges FROM users WHERE user_id = %s", (user_id,))
    row = cur.fetchone()
    existing = _json.loads(row["badges"] or "[]") if row else []
    merged = list(set(existing + badge_ids))
    cur.execute(
        "UPDATE users SET badges = %s WHERE user_id = %s",
        (_json.dumps(merged, ensure_ascii=False), user_id),
    )
    conn.commit()
    cur.close()
    conn.close()


# ===== Email CRUD =====

def set_mail_thread_id(user_id: str, thread_id: str):
    """메일 전용 쓰레드 ID 저장"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET mail_thread_id = %s WHERE user_id = %s",
        (thread_id, user_id),
    )
    conn.commit()
    cur.close()
    conn.close()

def set_email_credentials(user_id: str, naver_email: str, naver_app_pw: str, initial_uid: int = 0):
    """네이버 이메일 계정 정보 저장"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET naver_email = %s, naver_app_pw = %s, email_last_uid = %s WHERE user_id = %s",
        (naver_email, naver_app_pw, initial_uid, user_id),
    )
    conn.commit()
    cur.close()
    conn.close()

def get_email_users():
    """이메일 설정된 전체 유저 조회 (모니터링 스케줄러용)"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE naver_email IS NOT NULL AND naver_app_pw IS NOT NULL")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def update_email_last_uid(user_id: str, uid: int):
    """마지막으로 처리한 이메일 UID 갱신"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE users SET email_last_uid = %s WHERE user_id = %s", (uid, user_id))
    conn.commit()
    cur.close()
    conn.close()

def add_email_sender(user_id: str, sender_email: str, nickname: str) -> bool:
    """발신자 등록 (중복 시 False 반환)"""
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO email_senders (user_id, sender_email, nickname) VALUES (%s, %s, %s)",
            (user_id, sender_email.lower(), nickname),
        )
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        return False
    finally:
        cur.close()
        conn.close()

def remove_email_sender(user_id: str, sender_email: str) -> bool:
    """발신자 삭제 (존재하지 않으면 False 반환)"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM email_senders WHERE user_id = %s AND sender_email = %s RETURNING sender_id",
        (user_id, sender_email.lower()),
    )
    deleted = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return deleted is not None

def get_email_senders(user_id: str) -> list:
    """등록된 발신자 목록 조회"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM email_senders WHERE user_id = %s ORDER BY created_at ASC",
        (user_id,),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def save_email_log(user_id: str, sender_email: str, subject: str, summary_gpt: str, is_spam: bool = False):
    """이메일 수신 로그 저장 (ML 학습 데이터)"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO email_log (user_id, sender_email, subject, summary_gpt, is_spam)
           VALUES (%s, %s, %s, %s, %s)""",
        (user_id, sender_email, subject, summary_gpt, is_spam),
    )
    conn.commit()
    cur.close()
    conn.close()


def get_weekly_meal_stats(user_id: str, start_date) -> dict:
    """
    start_date 이후 7일간 식사 통계 반환.
    Returns:
      daily_calories : {날짜str: 총칼로리}
      meal_coverage  : {끼니: 기록일수}
      top_food       : 가장 많이 먹은 음식명 (없으면 None)
    """
    conn = get_conn()
    cur = conn.cursor()

    # 일별 칼로리
    cur.execute(
        """
        SELECT
            (recorded_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Seoul')::date AS day,
            SUM(calories) AS total
        FROM meals
        WHERE user_id = %s
          AND (recorded_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Seoul')::date >= %s
        GROUP BY day
        ORDER BY day
        """,
        (user_id, start_date),
    )
    daily_calories = {str(r["day"]): r["total"] for r in cur.fetchall()}

    # 끼니 유형별 기록일 수
    cur.execute(
        """
        SELECT
            meal_type,
            COUNT(DISTINCT (recorded_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Seoul')::date) AS days
        FROM meals
        WHERE user_id = %s
          AND (recorded_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Seoul')::date >= %s
        GROUP BY meal_type
        """,
        (user_id, start_date),
    )
    meal_coverage = {r["meal_type"]: r["days"] for r in cur.fetchall()}

    # 가장 많이 먹은 음식
    cur.execute(
        """
        SELECT food_name, COUNT(*) AS cnt
        FROM meals
        WHERE user_id = %s
          AND (recorded_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Seoul')::date >= %s
        GROUP BY food_name
        ORDER BY cnt DESC
        LIMIT 1
        """,
        (user_id, start_date),
    )
    top_row = cur.fetchone()

    cur.close()
    conn.close()
    return {
        "daily_calories": daily_calories,
        "meal_coverage":  meal_coverage,
        "top_food":       top_row["food_name"] if top_row else None,
    }
