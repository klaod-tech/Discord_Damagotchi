# 공유 DB 스키마 & 함수 가이드

> 모든 봇이 공유하는 `utils/db.py` 기준 문서.  
> 각 봇은 자신이 소유한 테이블/함수만 수정합니다.

---

## 1. DB 연결

```python
# utils/db.py
import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.getenv("DATABASE_URL")  # Supabase Session pooler URL

def get_conn():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
```

**주의**: 모든 쿼리 후 반드시 `conn.close()`, `cur.close()` 호출.  
결과는 `RealDictRow` 형태 → `row["column_name"]`으로 접근.

---

## 2. 타임존 규칙

- Supabase(PostgreSQL)는 **UTC로 저장**
- 날짜 비교 시 반드시 KST 변환:

```sql
(recorded_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Seoul')::date = %s
```

- `date.today()`는 로컬 시간 기준 → 서버가 KST가 아니면 위 변환 필수

---

## 3. 전체 테이블 스키마

### 3-1. users (공유 — 모든 봇 읽기, 소유 컬럼만 쓰기)

```sql
CREATE TABLE IF NOT EXISTS users (
    user_id              TEXT PRIMARY KEY,
    tamagotchi_name      TEXT,
    city                 TEXT,
    wake_time            TEXT,
    init_weight          REAL,
    goal_weight          REAL,
    daily_cal_target     INTEGER,
    breakfast_time       TEXT,
    lunch_time           TEXT,
    dinner_time          TEXT,
    thread_id            TEXT,      -- 메인 쓰레드 (먹구름봇)
    gender               TEXT,
    age                  INTEGER,
    height               REAL,
    created_at           TIMESTAMP DEFAULT NOW(),
    streak               INTEGER DEFAULT 0,
    max_streak           INTEGER DEFAULT 0,
    badges               TEXT DEFAULT '[]',
    -- v3.0 이메일
    naver_email          TEXT,
    naver_app_pw         TEXT,
    email_last_uid       INTEGER,
    mail_thread_id       TEXT,      -- 메일봇 전용 쓰레드
    -- v3.2 멀티봇
    meal_thread_id       TEXT,      -- 식사봇 전용 쓰레드
    weather_thread_id    TEXT,      -- 날씨봇 전용 쓰레드
    weight_thread_id     TEXT,      -- 체중관리봇 전용 쓰레드
    meal_waiting_until   TIMESTAMP, -- 식사봇 사진 대기 상태
    -- v3.3 예정
    diary_thread_id      TEXT,      -- 일기봇 전용 쓰레드
    -- v3.4 예정
    schedule_thread_id   TEXT       -- 일정봇 전용 쓰레드
);
```

### 3-2. tamagotchi (먹구름봇 소유, 식사봇 수치 갱신)

```sql
CREATE TABLE IF NOT EXISTS tamagotchi (
    user_id          TEXT PRIMARY KEY REFERENCES users(user_id),
    hp               INTEGER DEFAULT 100,
    hunger           INTEGER DEFAULT 50,
    mood             INTEGER DEFAULT 50,
    current_image    TEXT DEFAULT 'normal.png',
    embed_message_id TEXT,
    last_fed_at      TIMESTAMP,
    updated_at       TIMESTAMP DEFAULT NOW()
);
```

### 3-3. meals (식사봇 소유)

```sql
CREATE TABLE IF NOT EXISTS meals (
    meal_id      SERIAL PRIMARY KEY,
    user_id      TEXT REFERENCES users(user_id),
    meal_type    TEXT,      -- 아침/점심/저녁/간식/식사
    food_name    TEXT,
    calories     INTEGER,
    protein      REAL,
    carbs        REAL,
    fat          REAL,
    fiber        REAL,
    input_method TEXT,      -- text / photo
    gpt_comment  TEXT,
    recorded_at  TIMESTAMP DEFAULT NOW()
);
```

### 3-4. weather_log (날씨봇 소유)

```sql
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
);
```

### 3-5. weight_log (체중관리봇 소유)

```sql
CREATE TABLE IF NOT EXISTS weight_log (
    log_id      SERIAL PRIMARY KEY,
    user_id     TEXT REFERENCES users(user_id),
    weight      REAL,
    recorded_at TIMESTAMP DEFAULT NOW()
);
```

### 3-6. email_senders (메일봇 소유)

```sql
CREATE TABLE IF NOT EXISTS email_senders (
    sender_id    SERIAL PRIMARY KEY,
    user_id      TEXT REFERENCES users(user_id) ON DELETE CASCADE,
    sender_email TEXT NOT NULL,
    nickname     TEXT,
    created_at   TIMESTAMP DEFAULT NOW(),
    UNIQUE (user_id, sender_email)
);
```

### 3-7. email_log (메일봇 소유)

```sql
CREATE TABLE IF NOT EXISTS email_log (
    log_id       SERIAL PRIMARY KEY,
    user_id      TEXT REFERENCES users(user_id) ON DELETE CASCADE,
    sender_email TEXT,
    subject      TEXT,
    summary_gpt  TEXT,
    is_spam      BOOLEAN DEFAULT FALSE,
    received_at  TIMESTAMP DEFAULT NOW()
);
```

### 3-8. diary_log (일기봇 소유) — 신규 구현 필요

```sql
CREATE TABLE IF NOT EXISTS diary_log (
    diary_id     SERIAL PRIMARY KEY,
    user_id      TEXT REFERENCES users(user_id) ON DELETE CASCADE,
    content      TEXT NOT NULL,       -- 일기 원문
    emotion_tag  TEXT,                -- GPT 감정 분류 (기쁨/슬픔/화남/평온/불안/설렘)
    emotion_score REAL,               -- 감정 강도 0.0~1.0
    gpt_comment  TEXT,                -- GPT 반응 대사
    recorded_at  TIMESTAMP DEFAULT NOW()
);
```

### 3-9. schedule_log (일정봇 소유) — 신규 구현 필요

```sql
CREATE TABLE IF NOT EXISTS schedule_log (
    schedule_id   SERIAL PRIMARY KEY,
    user_id       TEXT REFERENCES users(user_id) ON DELETE CASCADE,
    title         TEXT NOT NULL,
    scheduled_at  TIMESTAMP NOT NULL,  -- 일정 날짜+시간
    is_repeat     BOOLEAN DEFAULT FALSE,
    repeat_rule   TEXT,                -- 'daily'/'weekly'/'monthly' 등
    is_done       BOOLEAN DEFAULT FALSE,
    notified      BOOLEAN DEFAULT FALSE,
    created_at    TIMESTAMP DEFAULT NOW()
);
```

---

## 4. 공통 함수 (모든 봇에서 사용 가능)

### 4-1. 기본 CRUD

```python
def get_user(user_id: str) -> dict | None
def get_all_users() -> list[dict]
def update_user(user_id: str, **kwargs)
def create_user(user_id: str, data: dict)
```

### 4-2. Tamagotchi

```python
def get_tamagotchi(user_id: str) -> dict | None
def update_tamagotchi(user_id: str, data: dict = None, **kwargs)
def set_embed_message_id(user_id: str, message_id: str)
```

### 4-3. 쓰레드 ID Setter (봇별 소유)

| 함수 | 소유 봇 | 컬럼 |
|------|---------|------|
| `set_thread_id(user_id, thread_id)` | 먹구름봇 | `thread_id` |
| `set_mail_thread_id(user_id, thread_id)` | 메일봇 | `mail_thread_id` |
| `set_meal_thread_id(user_id, thread_id)` | 식사봇 | `meal_thread_id` |
| `set_weather_thread_id(user_id, thread_id)` | 날씨봇 | `weather_thread_id` |
| `set_weight_thread_id(user_id, thread_id)` | 체중관리봇 | `weight_thread_id` |
| `set_diary_thread_id(user_id, thread_id)` | 일기봇 | `diary_thread_id` (추가 필요) |
| `set_schedule_thread_id(user_id, thread_id)` | 일정봇 | `schedule_thread_id` (추가 필요) |

### 4-4. 사진 대기 상태 (식사봇 ↔ 먹구름봇)

```python
def set_meal_waiting(user_id: str, seconds: int = 60)  # 먹구름봇이 호출
def clear_meal_waiting(user_id: str)                    # 식사봇이 호출
def is_meal_waiting(user_id: str) -> bool               # 식사봇이 조회
```

### 4-5. 이메일 관련

```python
def set_email_credentials(user_id, naver_email, naver_app_pw, initial_uid=0)
def get_email_users() -> list[dict]
def update_email_last_uid(user_id, uid)
def add_email_sender(user_id, sender_email, nickname) -> bool
def remove_email_sender(user_id, sender_email) -> bool
def get_email_senders(user_id) -> list
def save_email_log(user_id, sender_email, subject, summary_gpt, is_spam=False)
```

### 4-6. 식사 관련

```python
def create_meal(user_id, meal_type, food_name, calories, protein, carbs, fat, fiber, input_method, gpt_comment, recorded_date=None)
def get_meals_by_date(user_id, target_date) -> list
def get_today_meals(user_id) -> list
def get_calories_by_date(user_id, target_date) -> int
def get_today_calories(user_id) -> int
def has_meal_type_on_date(user_id, meal_type, target_date) -> bool
def is_all_meals_done_on_date(user_id, target_date) -> bool
def get_weekly_meal_stats(user_id, start_date) -> dict
```

### 4-7. 날씨 관련

```python
def create_weather_log(user_id, weather, temp, pm10, pm25, selected_image, gpt_comment)
def get_latest_weather(user_id) -> dict | None
```

### 4-8. 스트릭 / 배지

```python
def update_streak(user_id, streak, max_streak)
def add_badges(user_id, badge_ids: list)
```

---

## 5. 마이그레이션 규칙

새 컬럼 추가 시 `init_db()` 내에 다음 패턴 사용:

```python
# 컬럼 하나 추가
cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS diary_thread_id TEXT")

# 여러 컬럼 추가
for col, col_type in [
    ("diary_thread_id",    "TEXT"),
    ("schedule_thread_id", "TEXT"),
]:
    cur.execute(f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {col} {col_type}")
```

새 테이블 추가 시:

```python
cur.execute("""
    CREATE TABLE IF NOT EXISTS diary_log (
        ...
    )
""")
```

**규칙**: `IF NOT EXISTS` 필수 — 이미 존재하는 경우 에러 없이 통과.

---

## 6. 쿼리 패턴 예시

### 단일 행 조회
```python
def get_user(user_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row  # dict 또는 None
```

### INSERT
```python
def save_diary(user_id, content, emotion_tag, emotion_score, gpt_comment):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO diary_log (user_id, content, emotion_tag, emotion_score, gpt_comment)
        VALUES (%s, %s, %s, %s, %s)
    """, (user_id, content, emotion_tag, emotion_score, gpt_comment))
    conn.commit()
    cur.close()
    conn.close()
```

### UPDATE (동적 컬럼)
```python
def update_user(user_id, **kwargs):
    conn = get_conn()
    cur = conn.cursor()
    fields = ", ".join(f"{k} = %s" for k in kwargs)
    values = list(kwargs.values()) + [user_id]
    cur.execute(f"UPDATE users SET {fields} WHERE user_id = %s", values)
    conn.commit()
    cur.close()
    conn.close()
```
