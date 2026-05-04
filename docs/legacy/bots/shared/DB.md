# 공통 DB 가이드 — 전체 테이블 스키마 & 함수 목록

---

## 1. 연결 방법

```python
from utils.db import get_conn

conn = get_conn()   # psycopg2 RealDictCursor (딕셔너리로 반환)
cur  = conn.cursor()
# ... 쿼리 ...
conn.commit()
cur.close()
conn.close()
```

> **DATABASE_URL** = Supabase Session pooler (PostgreSQL)  
> 반환 결과는 항상 `dict` 타입 → `row["column_name"]` 으로 접근

---

## 2. 테이블 전체 스키마

### 2-1. `users` — 모든 봇 공유 (읽기), 소유 봇만 쓰기

```sql
CREATE TABLE users (
    user_id          TEXT PRIMARY KEY,           -- Discord user.id
    tamagotchi_name  TEXT,                       -- 캐릭터명
    city             TEXT,                       -- 도시 (날씨 API용)
    wake_time        TEXT,                       -- 기상 시간 "HH:MM"
    init_weight      REAL,                       -- 온보딩 시 초기 체중
    goal_weight      REAL,                       -- 목표 체중
    daily_cal_target INTEGER,                    -- 하루 목표 칼로리
    breakfast_time   TEXT,                       -- 아침 알림 "HH:MM"
    lunch_time       TEXT,                       -- 점심 알림 "HH:MM"
    dinner_time      TEXT,                       -- 저녁 알림 "HH:MM"
    thread_id        TEXT,                       -- 메인 쓰레드 ID
    gender           TEXT,                       -- 성별 (BMR 계산용)
    age              INTEGER,                    -- 나이 (BMR 계산용)
    height           REAL,                       -- 키 cm (BMR 계산용)
    created_at       TIMESTAMP DEFAULT NOW(),

    -- v2.7 마이그레이션 (스트릭/배지)
    streak           INTEGER DEFAULT 0,          -- 현재 연속 기록일
    max_streak       INTEGER DEFAULT 0,          -- 최대 연속 기록일
    badges           TEXT DEFAULT '[]',          -- JSON 배열 ["first_meal", ...]

    -- v3.0 마이그레이션 (이메일봇)
    naver_email      TEXT,                       -- 네이버 이메일 주소
    naver_app_pw     TEXT,                       -- 네이버 앱 비밀번호
    email_last_uid   INTEGER,                    -- 마지막 처리 이메일 UID
    mail_thread_id   TEXT,                       -- 메일 전용 쓰레드 ID

    -- v3.2 마이그레이션 (멀티봇 분리) — v4.0에서 아래 thread ID들 사용 중단
    meal_thread_id     TEXT,                     -- [v3.2 호환용, v4.0~폐기] 식사 전용 쓰레드
    weather_thread_id  TEXT,                     -- [v3.2 호환용, v4.0~폐기] 날씨 전용 쓰레드
    weight_thread_id   TEXT,                     -- [v3.2 호환용, v4.0~폐기] 체중관리 전용 쓰레드
    meal_waiting_until TIMESTAMP,                -- 사진 입력 대기 만료 시각 (v3.2 호환)

    -- v4.0 마이그레이션 (전용 채널 + Push 전용 쓰레드)
    personal_channel_id TEXT,                    -- 유저 전용 채널 (오케스트레이터 대화 + 서브봇 응답)
    info_thread_id      TEXT,                    -- Push 전용: 날씨 기상 알림 + 일정 D-day 알림
    address             TEXT,                    -- 음식 추천용 주소 (구/동 단위, nullable)
    diary_thread_id     TEXT,                    -- 일기봇 전용 쓰레드 ID
    schedule_thread_id  TEXT                     -- 일정봇 전용 쓰레드 ID
)
```

**컬럼별 쓰기 소유권:**

| 컬럼 | 소유 봇 |
|------|---------|
| tamagotchi_name, city, wake_time, init_weight, goal_weight, daily_cal_target, breakfast_time, lunch_time, dinner_time, thread_id, gender, age, height, address | 먹구름봇 (온보딩) |
| personal_channel_id, info_thread_id | 먹구름봇 (v4.0 온보딩) |
| streak, max_streak, badges | 먹구름봇 (scheduler) |
| naver_email, naver_app_pw, email_last_uid, mail_thread_id | 메일봇 |
| meal_waiting_until | 먹구름봇 (embed.py v3.2), 식사봇 (clear) |
| ~~meal_thread_id, weather_thread_id, weight_thread_id~~ | [v3.2 호환용만 유지, v4.0~신규 봇은 미사용] |

---

### 2-2. `tamagotchi` — 먹구름봇 소유, 식사봇 hunger/mood/hp 갱신 허용

```sql
CREATE TABLE tamagotchi (
    user_id          TEXT PRIMARY KEY REFERENCES users(user_id),
    hp               INTEGER DEFAULT 100,        -- 체력 (0~100)
    hunger           INTEGER DEFAULT 50,         -- 포만감 (0~100)
    mood             INTEGER DEFAULT 50,         -- 기분 (0~100)
    current_image    TEXT DEFAULT 'normal.png',  -- 현재 표시 이미지 파일명
    embed_message_id TEXT,                       -- 메인 Embed 메시지 ID
    last_fed_at      TIMESTAMP,                  -- 마지막 식사 시각
    updated_at       TIMESTAMP DEFAULT NOW()
)
```

> hp / hunger / mood 는 유저에게 **절대 직접 노출 금지** — 내부 로직용만

---

### 2-3. `meals` — 식사봇 소유

```sql
CREATE TABLE meals (
    meal_id      SERIAL PRIMARY KEY,
    user_id      TEXT REFERENCES users(user_id),
    meal_type    TEXT,               -- "아침" | "점심" | "저녁" | "간식" | "식사"
    food_name    TEXT,
    calories     INTEGER,
    protein      REAL,               -- 단백질 (g)
    carbs        REAL,               -- 탄수화물 (g)
    fat          REAL,               -- 지방 (g)
    fiber        REAL,               -- 식이섬유 (g)
    input_method TEXT,               -- "text" | "photo"
    gpt_comment  TEXT,
    recorded_at  TIMESTAMP DEFAULT NOW()
)
```

---

### 2-4. `weather_log` — 날씨봇 소유

```sql
CREATE TABLE weather_log (
    log_id         SERIAL PRIMARY KEY,
    user_id        TEXT REFERENCES users(user_id),
    weather        TEXT,             -- "맑음" | "흐림" | "비" | "눈"
    temp           REAL,             -- 기온 (°C)
    pm10           INTEGER,          -- 미세먼지 (μg/m³)
    pm25           INTEGER,          -- 초미세먼지 (μg/m³)
    selected_image TEXT,             -- 선택된 이미지 파일명
    gpt_comment    TEXT,
    recorded_at    TIMESTAMP DEFAULT NOW()
)
```

---

### 2-5. `weight_log` — 체중관리봇 소유

```sql
CREATE TABLE weight_log (
    log_id      SERIAL PRIMARY KEY,
    user_id     TEXT REFERENCES users(user_id),
    weight      REAL,                -- 체중 (kg)
    recorded_at TIMESTAMP DEFAULT NOW()
)
```

---

### 2-6. `email_senders` — 메일봇 소유

```sql
CREATE TABLE email_senders (
    sender_id    SERIAL PRIMARY KEY,
    user_id      TEXT REFERENCES users(user_id) ON DELETE CASCADE,
    sender_email TEXT NOT NULL,
    nickname     TEXT,
    created_at   TIMESTAMP DEFAULT NOW(),
    UNIQUE (user_id, sender_email)
)
```

---

### 2-7. `email_log` — 메일봇 소유

```sql
CREATE TABLE email_log (
    log_id       SERIAL PRIMARY KEY,
    user_id      TEXT REFERENCES users(user_id) ON DELETE CASCADE,
    sender_email TEXT,
    subject      TEXT,
    summary_gpt  TEXT,
    is_spam      BOOLEAN DEFAULT FALSE,  -- ML 학습 레이블
    received_at  TIMESTAMP DEFAULT NOW()
)
```

---

### 2-8. `diary_log` — 일기봇 소유 (신규 추가 예정)

```sql
CREATE TABLE diary_log (
    diary_id   SERIAL PRIMARY KEY,
    user_id    TEXT REFERENCES users(user_id) ON DELETE CASCADE,
    content    TEXT NOT NULL,            -- 일기 본문
    emotion    TEXT,                     -- GPT 분석 감정 (기쁨/슬픔/분노/불안/평온/설렘)
    emotion_score REAL,                  -- 감정 강도 0.0~1.0
    gpt_reply  TEXT,                     -- 타마고치 공감 답변
    recorded_at TIMESTAMP DEFAULT NOW()
);
```

---

### 2-9. `schedule_log` — 일정봇 소유 (신규 추가 예정)

```sql
CREATE TABLE schedule_log (
    schedule_id  SERIAL PRIMARY KEY,
    user_id      TEXT REFERENCES users(user_id) ON DELETE CASCADE,
    title        TEXT NOT NULL,
    description  TEXT,
    scheduled_at TIMESTAMP NOT NULL,     -- 일정 시각
    repeat_type  TEXT DEFAULT 'none',    -- 'none'|'daily'|'weekly'|'monthly'
    remind_min   INTEGER DEFAULT 30,     -- 몇 분 전 알림
    is_done      BOOLEAN DEFAULT FALSE,
    created_at   TIMESTAMP DEFAULT NOW()
);
```

---

## 3. DB 함수 전체 목록 (utils/db.py)

### Users 조회/생성

| 함수 | 반환 | 설명 |
|------|------|------|
| `get_conn()` | psycopg2 Connection | DB 연결 (RealDictCursor) |
| `create_user(user_id, data: dict)` | None | 유저 생성 또는 업데이트 (UPSERT) |
| `get_user(user_id)` | dict \| None | 단일 유저 조회 |
| `update_user(user_id, **kwargs)` | None | 유저 필드 동적 UPDATE |
| `set_thread_id(user_id, thread_id)` | None | 메인 쓰레드 ID 저장 |
| `get_all_users()` | list[dict] | 전체 유저 조회 (스케줄러용) |

### 타마고치

| 함수 | 반환 | 설명 |
|------|------|------|
| `create_tamagotchi(user_id)` | None | 타마고치 초기화 (UPSERT) |
| `get_tamagotchi(user_id)` | dict \| None | 타마고치 상태 조회 |
| `update_tamagotchi(user_id, data: dict \| **kwargs)` | None | 상태 업데이트 (updated_at 자동 갱신) |
| `set_embed_message_id(user_id, message_id)` | None | 메인 Embed 메시지 ID 저장 |

### 식사

| 함수 | 반환 | 설명 |
|------|------|------|
| `create_meal(user_id, meal_type, food_name, calories, protein, carbs, fat, fiber, input_method, gpt_comment, recorded_date=None)` | None | 식사 기록 생성 (recorded_date 지정 시 소급 입력) |
| `get_meals_by_date(user_id, target_date: date)` | list[dict] | 특정 날짜 식사 목록 |
| `get_today_meals(user_id)` | list[dict] | 오늘 식사 목록 |
| `get_calories_by_date(user_id, target_date: date)` | int | 특정 날짜 총 칼로리 |
| `get_today_calories(user_id)` | int | 오늘 총 칼로리 |
| `has_meal_type_on_date(user_id, meal_type, target_date)` | bool | 특정 날짜 해당 끼니 입력 여부 |
| `is_all_meals_done_on_date(user_id, target_date)` | bool | 아침/점심/저녁 모두 입력됐는지 |
| `get_weekly_meal_stats(user_id, start_date)` | dict | 주간 식사 통계 (daily_calories, meal_coverage, top_food) |

### 날씨

| 함수 | 반환 | 설명 |
|------|------|------|
| `create_weather_log(user_id, weather, temp, pm10, pm25, selected_image, gpt_comment)` | None | 날씨 기록 저장 |
| `get_latest_weather(user_id)` | dict \| None | 가장 최근 날씨 기록 |

### 스트릭 / 배지

| 함수 | 반환 | 설명 |
|------|------|------|
| `update_streak(user_id, streak, max_streak)` | None | 연속 기록일 업데이트 |
| `add_badges(user_id, badge_ids: list)` | None | 배지 추가 (중복 없이 JSON 배열에 병합) |

### 이메일

| 함수 | 반환 | 설명 |
|------|------|------|
| `set_mail_thread_id(user_id, thread_id)` | None | 메일 전용 쓰레드 ID 저장 |
| `set_email_credentials(user_id, naver_email, naver_app_pw, initial_uid=0)` | None | 네이버 계정 저장 |
| `get_email_users()` | list[dict] | 이메일 설정된 전체 유저 |
| `update_email_last_uid(user_id, uid)` | None | 마지막 처리 UID 갱신 |
| `add_email_sender(user_id, sender_email, nickname)` | bool | 발신자 등록 (중복 시 False) |
| `remove_email_sender(user_id, sender_email)` | bool | 발신자 삭제 |
| `get_email_senders(user_id)` | list[dict] | 발신자 목록 조회 |
| `save_email_log(user_id, sender_email, subject, summary_gpt, is_spam=False)` | None | 수신 로그 저장 |

### 채널·쓰레드 ID Setters (v4.0)

| 함수 | 반환 | 설명 |
|------|------|------|
| `set_personal_channel_id(user_id, channel_id)` | None | 유저 전용 채널 ID (v4.0 온보딩) |
| `set_info_thread_id(user_id, thread_id)` | None | Push 알림 쓰레드 ID (날씨+일정 통합) |
| `set_mail_thread_id(user_id, thread_id)` | None | 메일봇 Push 쓰레드 ID |
| `set_diary_thread_id(user_id, thread_id)` | None | 일기봇 전용 쓰레드 ID |
| `set_schedule_thread_id(user_id, thread_id)` | None | 일정봇 전용 쓰레드 ID |
| `set_meal_waiting(user_id, seconds=60)` | None | 사진 대기 만료 시각 설정 (v3.2 호환) |
| `clear_meal_waiting(user_id)` | None | 사진 대기 해제 (v3.2 호환) |
| `is_meal_waiting(user_id)` | bool | 사진 대기 중인지 확인 (v3.2 호환) |

> ~~`set_meal_thread_id`, `set_weather_thread_id`, `set_weight_thread_id`~~ — v4.0~신규 봇에서 미사용.

---

## 4. 마이그레이션 규칙

```python
# 새 컬럼 추가 시 — init_db() 안에 추가
cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS new_col TEXT")

# 새 테이블 추가 시
cur.execute("CREATE TABLE IF NOT EXISTS new_table (...)")
```

**절대 하지 말 것:**
- `DROP TABLE`, `DROP COLUMN` (데이터 손실)
- 기존 컬럼 타입 변경 (psycopg2 오류 유발)
- `init_db()` 외부에서 DDL 실행

---

## 5. Fallback 패턴 (기존 v3.2 유저 호환)

v4.0 신규 컬럼이 NULL인 기존 유저를 위해 **반드시** 적용:

```python
# 유저 요청 응답 (식사봇, 체중봇, 일기봇 등)
channel_id = user.get("personal_channel_id") or user.get("thread_id")

# Push 알림 (날씨봇, 일정봇)
info_id = user.get("info_thread_id") or user.get("thread_id")

# 메일 알림 (메일봇)
mail_id = user.get("mail_thread_id") or user.get("thread_id")
```

> v3.2 기존 유저는 `personal_channel_id`, `info_thread_id` = NULL → `thread_id` fallback 동작.  
> v3.2 개별 thread ID (meal/weather/weight)는 기존 코드에서 계속 동작하되, 신규 봇 개발 시 사용하지 않음.

---

## 6. KST 시간대 처리

DB는 UTC 저장. 쿼리 시 항상 KST 변환:

```sql
(recorded_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Seoul')::date = %s
```

Python에서 오늘 날짜: `from datetime import date; date.today()`
