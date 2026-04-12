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
thread_id        TEXT NOT NULL         -- 유저 전용 쓰레드 ID (다마고치/식사/날씨)
gender           TEXT                  -- 성별 (남/여) — 칼로리 재계산용
age              INTEGER               -- 나이 — 칼로리 재계산용
height           REAL                  -- 키 cm — 칼로리 재계산용
streak           INTEGER DEFAULT 0     -- 현재 연속 식사 기록일 (v2.7)
max_streak       INTEGER DEFAULT 0     -- 역대 최고 연속 기록일 (v2.7)
badges           TEXT    DEFAULT '[]'  -- 획득 배지 ID JSON 배열 (v2.7)
naver_email      TEXT                  -- 네이버 아이디 (이메일 모니터링용) (v3.0)
naver_app_pw     TEXT                  -- 네이버 앱 비밀번호 (v3.0)
email_last_uid   INTEGER               -- 마지막 처리한 IMAP UID (중복 방지) (v3.0)
mail_thread_id   TEXT                  -- 메일 알림 전용 스레드 ID (v3.0)
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
recorded_at   TIMESTAMP DEFAULT NOW()  -- UTC 저장 (Supabase 기본값)
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

## email_senders (v3.0)

```sql
sender_id    SERIAL PRIMARY KEY
user_id      TEXT REFERENCES users(user_id) ON DELETE CASCADE
sender_email TEXT NOT NULL                  -- 발신자 이메일 (소문자 정규화)
nickname     TEXT                           -- 디스코드 표시용 별명
created_at   TIMESTAMP DEFAULT NOW()
UNIQUE (user_id, sender_email)              -- 동일 발신자 중복 등록 방지
```

---

## email_log (v3.0)

```sql
log_id       SERIAL PRIMARY KEY
user_id      TEXT REFERENCES users(user_id) ON DELETE CASCADE
sender_email TEXT        -- 발신자 이메일
subject      TEXT        -- 메일 제목
summary_gpt  TEXT        -- GPT 3줄 요약 (ML 학습 레이블 역할)
is_spam      BOOLEAN DEFAULT FALSE
received_at  TIMESTAMP DEFAULT NOW()
```

> **ML 활용 계획**: `summary_gpt`가 누적되면 GPT → 경량 요약 모델(Extractive/Abstractive)로 대체 예정.  
> 칼로리 모델과 동일한 "GPT label → ML 학습 → 대체" 패턴.

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
| `has_meal_type_on_date(user_id, meal_type, date)` | 특정 날짜 끼니 기록 여부 |
| `create_weather_log(...)` | 날씨 기록 저장 |
| `get_latest_weather(user_id)` | 최신 날씨 조회 |
| `create_weight_log(user_id, weight)` | 체중 기록 저장 |
| `get_weight_logs(user_id, limit)` | 체중 기록 조회 |
| `update_streak(user_id, streak, max_streak)` | 연속 기록일 업데이트 (v2.7) |
| `add_badges(user_id, badge_ids)` | 배지 JSON 배열에 신규 배지 추가 (v2.7) |
| `get_weekly_meal_stats(user_id, start_date)` | 주간 식사 통계 (일별 칼로리/끼니 커버리지/최다 음식) (v2.7) |
| `set_mail_thread_id(user_id, thread_id)` | 메일 전용 스레드 ID 저장 (v3.0) |
| `set_email_credentials(user_id, naver_email, app_pw)` | 네이버 계정 연동 저장 + email_last_uid 초기화 (v3.0) |
| `get_email_users()` | naver_email/naver_app_pw 설정된 전체 유저 조회 (스케줄러용) (v3.0) |
| `update_email_last_uid(user_id, uid)` | 마지막 처리 IMAP UID 갱신 (v3.0) |
| `add_email_sender(user_id, sender_email, nickname)` | 발신자 등록 (중복 시 False 반환) (v3.0) |
| `remove_email_sender(user_id, sender_email)` | 발신자 삭제 (미존재 시 False 반환) (v3.0) |
| `get_email_senders(user_id)` | 등록된 발신자 목록 조회 (v3.0) |
| `save_email_log(user_id, sender_email, subject, summary_gpt)` | 수신 이메일 로그 저장 (v3.0) |

> **타임존 주의**: `recorded_at`은 UTC로 저장됨 (Supabase 기본값). 날짜 비교 쿼리는  
> `(recorded_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Seoul')::date = %s` 형태로  
> UTC → KST 이중 변환 후 비교. `AT TIME ZONE` 단일 사용 시 역방향 해석 버그 발생.
