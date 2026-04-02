# DB 스키마 — Supabase (PostgreSQL)

> **연결 방식**: psycopg2 + Session pooler URL  
> **연결 함수**: `utils/db.py` → `get_conn()`  
> **환경변수**: `DATABASE_URL=postgresql://postgres.{project_id}:{password}@...`

---

## users

```sql
user_id          TEXT PRIMARY KEY      -- 디스코드 유저 ID
tamagotchi_name  TEXT NOT NULL         -- 다마고치 이름
city             TEXT NOT NULL         -- 거주 도시 (날씨 API용)
wake_time        TEXT NOT NULL         -- 기상 시간 HH:MM (날씨 이미지 교체 기준)
breakfast_time   TEXT NOT NULL         -- 아침 알림 HH:MM
lunch_time       TEXT NOT NULL         -- 점심 알림 HH:MM
dinner_time      TEXT NOT NULL         -- 저녁 알림 HH:MM
init_weight      REAL NOT NULL         -- 초기 체중 kg
goal_weight      REAL NOT NULL         -- 목표 체중 kg
daily_cal_target INTEGER NOT NULL      -- Mifflin-St Jeor 공식으로 GPT 계산
thread_id        TEXT NOT NULL         -- 유저 전용 쓰레드 ID
gender           TEXT                  -- 성별 (남/여) — 칼로리 재계산용
age              INTEGER               -- 나이 — 칼로리 재계산용
height           REAL                  -- 키 cm — 칼로리 재계산용
created_at       TIMESTAMP DEFAULT NOW()
```

---

## tamagotchi

```sql
user_id          TEXT PRIMARY KEY REFERENCES users(user_id)
hp               INTEGER DEFAULT 100   -- 체력 0~100 [내부전용, 사용자 미노출]
hunger           INTEGER DEFAULT 100   -- 배부름 0~100 [내부전용, 사용자 미노출]
mood             INTEGER DEFAULT 100   -- 기분 0~100 [내부전용, 사용자 미노출]
current_image    TEXT                  -- 현재 표시 이미지 파일명
embed_message_id TEXT                  -- Embed 수정용 메시지 ID
last_fed_at      TIMESTAMP             -- 마지막 식사 입력 시각
updated_at       TIMESTAMP             -- 마지막 수치 갱신 시각
```

---

## meals

```sql
meal_id       SERIAL PRIMARY KEY
user_id       TEXT REFERENCES users(user_id)
meal_type     TEXT        -- 아침 | 점심 | 저녁 | 간식 | 식사
food_name     TEXT        -- 입력/인식된 음식명 (콤마 구분)
calories      INTEGER
protein       REAL        -- g
carbs         REAL        -- g
fat           REAL        -- g
fiber         REAL        -- g
input_method  TEXT        -- text | photo
gpt_comment   TEXT        -- GPT 대사 캐싱 (nullable)
recorded_at   TIMESTAMP DEFAULT NOW()
recorded_date DATE        -- 소급 입력용 날짜 (어제/그저께 지원)
```

---

## weather_log

```sql
log_id         SERIAL PRIMARY KEY
user_id        TEXT REFERENCES users(user_id)
weather        TEXT        -- 맑음 | 비 | 눈 | 흐림 등
temp           REAL        -- 기온 °C
pm10           INTEGER     -- 미세먼지 μg/m³
pm25           INTEGER     -- 초미세먼지 μg/m³
selected_image TEXT        -- 선택된 이미지 파일명
gpt_comment    TEXT        -- 날씨 기반 대사 캐싱 (nullable)
recorded_at    TIMESTAMP DEFAULT NOW()
```

---

## weight_log

```sql
log_id      SERIAL PRIMARY KEY
user_id     TEXT REFERENCES users(user_id)
weight      REAL        -- 체중 kg
recorded_at TIMESTAMP DEFAULT NOW()
```

---

## 주요 DB 함수 (utils/db.py)

| 함수 | 설명 |
|------|------|
| `init_db()` | 테이블 생성 (bot.py on_ready에서 호출) |
| `create_user(user_id, data)` | 유저 생성 |
| `get_user(user_id)` | 유저 조회 |
| `update_user(user_id, **kwargs)` | 유저 정보 수정 |
| `get_all_users()` | 전체 유저 조회 (스케줄러용) |
| `create_tamagotchi(user_id)` | 다마고치 생성 (hp/hunger/mood=100) |
| `get_tamagotchi(user_id)` | 다마고치 조회 |
| `update_tamagotchi(user_id, data)` | 수치 갱신 |
| `set_embed_message_id(user_id, msg_id)` | Embed 메시지 ID 저장 |
| `create_meal(...)` | 식사 기록 저장 (소급 입력 지원) |
| `get_today_meals(user_id)` | 오늘 식사 목록 |
| `get_meals_by_date(user_id, date)` | 특정 날짜 식사 목록 |
| `get_today_calories(user_id)` | 오늘 총 칼로리 |
| `get_calories_by_date(user_id, date)` | 특정 날짜 총 칼로리 |
| `create_weather_log(...)` | 날씨 기록 저장 |
| `get_latest_weather(user_id)` | 최신 날씨 조회 |
