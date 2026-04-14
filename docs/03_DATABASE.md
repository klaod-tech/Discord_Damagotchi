# DB 스키마 — Supabase (PostgreSQL)

> last_updated: 2026-04-13 | 현재 버전: v3.2  
> **연결 방식**: psycopg2 + Session pooler URL  
> **연결 함수**: `utils/db.py` → `get_conn()`  
> **환경변수**: `DATABASE_URL=postgresql://postgres.{project_id}:{password}@...`

---

## 봇별 테이블 소유권

| 테이블 | 소유 봇 | 상태 |
|--------|---------|------|
| `users` | 먹구름봇 (공통 참조) | ✅ 운영 |
| `tamagotchi` | 먹구름봇 | ✅ 운영 |
| `meals` | 먹구름봇 (텍스트) + 식사봇 (사진) | ✅ 운영 |
| `weather_log` | 날씨봇 | ✅ 운영 |
| `weight_log` | 체중관리봇* | ✅ 운영 |
| `email_senders` | 메일봇 | ✅ 운영 |
| `email_log` | 메일봇 | ✅ 운영 |
| `diary_log` | 일기봇 | 📋 미생성 (v3.4 예정) |
| `schedules` | 일정봇 | 📋 미생성 (v3.5 예정) |

> *weight_log는 현재 먹구름봇의 cogs.weight에서 INSERT. bot_weight.py 분리 후 체중관리봇 소유로 전환.

---

## users

```sql
-- 기본 정보
user_id          TEXT PRIMARY KEY      -- 디스코드 유저 ID
tamagotchi_name  TEXT NOT NULL         -- 캐릭터 이름
city             TEXT NOT NULL         -- 거주 도시 (날씨 API용)
gender           TEXT                  -- 성별 (남/여) — Mifflin-St Jeor 재계산용
age              INTEGER               -- 나이
height           REAL                  -- 키 cm
init_weight      REAL NOT NULL         -- 시작 체중 kg
goal_weight      REAL NOT NULL         -- 목표 체중 kg
daily_cal_target INTEGER NOT NULL      -- GPT 계산 일일 칼로리 목표

-- 시간 설정
wake_time        TEXT NOT NULL         -- 기상 시간 HH:MM (날씨봇 알림 기준)
breakfast_time   TEXT NOT NULL         -- 아침 알림 HH:MM
lunch_time       TEXT NOT NULL         -- 점심 알림 HH:MM
dinner_time      TEXT NOT NULL         -- 저녁 알림 HH:MM

-- 채널 / 쓰레드 ID
personal_channel_id TEXT               -- 유저 전용 채널 ID (v4.0~, 오케스트레이터 대화 + 서브봇 응답)
thread_id        TEXT                  -- 메인 쓰레드 (fallback 기준, 기존 v3.2 유저 호환용)
info_thread_id   TEXT                  -- Push 알림 전용: 날씨 + 일정 알림 (v4.0~)
mail_thread_id   TEXT                  -- 메일봇 Push 전용 (v3.0~)
-- 제거: meal_thread_id, weather_thread_id, weight_thread_id, diary_thread_id, schedule_thread_id
--   → v4.0부터 서브봇 응답은 personal_channel_id에 직접, 별도 기능별 쓰레드 없음

-- 위치 정보
-- city: 기존 (날씨 API용, 시 단위)
address          TEXT                  -- 음식 추천용 주소 (v4.0, 구/동 단위, nullable)

-- 식사봇 cross-process 상태
meal_waiting_until TIMESTAMP           -- 사진 대기 만료 시각 (v3.2) — NULL이면 대기 중 아님

-- 이메일
naver_email      TEXT                  -- 유저 네이버 아이디 (이메일 모니터링용, v3.0)
naver_app_pw     TEXT                  -- 네이버 앱 비밀번호 (v3.0)
email_last_uid   INTEGER               -- 마지막 처리 IMAP UID (중복 방지, v3.0)

-- 게임성
streak           INTEGER DEFAULT 0     -- 현재 연속 식사 기록일 (v2.7)
max_streak       INTEGER DEFAULT 0     -- 역대 최고 연속 기록일 (v2.7)
badges           TEXT    DEFAULT '[]'  -- 획득 배지 ID JSON 배열 (v2.7)

created_at       TIMESTAMP DEFAULT NOW()
```

### 쓰레드/채널 ID Fallback 규칙

각 봇은 신규 ID가 NULL인 기존 v3.2 유저를 위해 반드시 fallback 적용:

```python
# 유저 요청 응답 (식사봇, 체중봇, 일기봇 등): 전용 채널 → fallback 메인 쓰레드
channel_id = user.get("personal_channel_id") or user.get("thread_id")

# Push 알림 (날씨봇, 일정봇): 알림 쓰레드 → fallback 메인 쓰레드
info_id = user.get("info_thread_id") or user.get("thread_id")

# Push 알림 (메일봇): 메일 쓰레드 → fallback 메인 쓰레드
mail_id = user.get("mail_thread_id") or user.get("thread_id")
```

---

## tamagotchi

```sql
user_id          TEXT PRIMARY KEY REFERENCES users(user_id)
hp               INTEGER DEFAULT 100   -- 체력 0~100 [내부전용 — 절대 수치 노출 금지]
hunger           INTEGER DEFAULT 100   -- 배부름 0~100 [내부전용]
mood             INTEGER DEFAULT 100   -- 기분 0~100 [내부전용]
current_image    TEXT                  -- 현재 표시 이미지 파일명 (소문자, .png)
embed_message_id TEXT                  -- Embed 수정용 메시지 ID
last_fed_at      TIMESTAMP             -- 마지막 식사 입력 시각 (eat.png 트리거용)
updated_at       TIMESTAMP             -- 마지막 수치 갱신 시각
```

### 이미지 11종

| 파일명 | 상황 |
|--------|------|
| `normal.png` | 기본 (맑은 날씨) |
| `smile.png` | 구름 많음 |
| `tired.png` | 흐림 |
| `eat.png` | 식사 직후 (3분 한시적) |
| `upset.png` | 배고픔 (식사 시간 지남) |
| `cheer.png` | 목표 달성 / 배지 획득 |
| `rainy.png` | 비 |
| `snow.png` | 눈 |
| `hot.png` | 더위 (≥26°C) |
| `warm.png` | 추위 (≤5°C) |
| `wear_mask.png` | 미세먼지 나쁨 |

---

## meals

```sql
meal_id       SERIAL PRIMARY KEY
user_id       TEXT REFERENCES users(user_id)
meal_type     TEXT        -- 아침 | 점심 | 저녁 | 간식 | 식사
food_name     TEXT        -- 입력/인식된 음식명
calories      INTEGER
protein       REAL        -- g
carbs         REAL        -- g
fat           REAL        -- g
fiber         REAL        -- g
input_method  TEXT        -- 'text' (먹구름봇) | 'photo' (식사봇)
gpt_comment   TEXT        -- GPT 대사 캐싱 (nullable, ML 학습 레이블 역할)
recorded_at   TIMESTAMP DEFAULT NOW()  -- UTC 저장
```

> **타임존 주의**: 날짜 비교 쿼리는 반드시 UTC→KST 변환 후 비교:
> ```sql
> (recorded_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Seoul')::date = %s
> ```
> `AT TIME ZONE` 단일 사용 시 역방향 해석 버그 발생.

---

## weather_log

```sql
log_id         SERIAL PRIMARY KEY
user_id        TEXT REFERENCES users(user_id)
weather        TEXT        -- 맑음 | 비 | 눈 | 흐림 등
temp           REAL        -- 기온 °C [내부전용 — 수치 노출 금지]
pm10           INTEGER     -- 미세먼지 μg/m³ [내부전용]
pm25           INTEGER     -- 초미세먼지 μg/m³ [내부전용]
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

## email_senders

```sql
sender_id    SERIAL PRIMARY KEY
user_id      TEXT REFERENCES users(user_id) ON DELETE CASCADE
sender_email TEXT NOT NULL                  -- 발신자 이메일 (소문자 정규화)
nickname     TEXT                           -- 디스코드 표시용 별명
created_at   TIMESTAMP DEFAULT NOW()
UNIQUE (user_id, sender_email)              -- 동일 발신자 중복 등록 방지
```

---

## email_log

```sql
log_id       SERIAL PRIMARY KEY
user_id      TEXT REFERENCES users(user_id) ON DELETE CASCADE
sender_email TEXT        -- 발신자 이메일
subject      TEXT        -- 메일 제목
summary_gpt  TEXT        -- GPT 요약 (≤200자 원문 / >200자 GPT 요약)
is_spam      BOOLEAN DEFAULT FALSE
received_at  TIMESTAMP DEFAULT NOW()
```

> **ML 활용 계획**: `summary_gpt`가 누적되면 GPT → 경량 요약 모델(Extractive)로 대체 예정.  
> 칼로리 모델과 동일한 "GPT label → ML 학습 → 대체" 패턴.

---

## diary_log (v3.4 예정 — 미생성)

```sql
log_id      SERIAL PRIMARY KEY
user_id     TEXT REFERENCES users(user_id)
content     TEXT NOT NULL               -- 일기 원문 (최대 500자)
emotion     TEXT                        -- '긍정' | '부정' | '중립'
intensity   INTEGER                     -- 감정 강도 1~5
keywords    TEXT                        -- 감정 키워드 JSON 배열
written_at  TIMESTAMP DEFAULT NOW()
```

---

## task_queue (v4.0 예정 — 미생성)

> 먹구름봇 → 서브봇 단방향 트리거 + 서브봇 → 메인봇 결과 반환 채널.  
> **식사(meal)는 task_queue 미사용** — 버튼 클릭 기반 기존 흐름 유지.

```sql
task_id      SERIAL PRIMARY KEY
bot_target   TEXT NOT NULL           -- 'weight' | 'diary' | 'schedule'
user_id      TEXT NOT NULL
payload      TEXT                    -- 유저 발화 원문 JSON (먹구름봇 → 서브봇)
result_json  TEXT                    -- 처리 결과 JSON (서브봇 → 먹구름봇)
             -- 체중봇: { "weight": 68.5, "achieved_goal": false, "progress_pct": 72 }
             -- 일기봇: { "emotion_tag": "슬픔", "comment": "오늘 많이 힘들었구나..." }
             -- 일정봇: { "title": "병원 예약", "scheduled_at": "2026-04-21T15:00" }
status       TEXT DEFAULT 'pending'  -- 'pending' | 'done' | 'archived'
created_at   TIMESTAMP DEFAULT NOW()
completed_at TIMESTAMP               -- 서브봇이 done 처리한 시각
```

> **status 흐름**: `pending` → (서브봇 처리) → `done` → (메인봇 수신) → `archived`

---

## intent_log (v4.0 예정 — 미생성)

> ML 의도 분류기 학습 데이터. 먹구름봇 on_message에서 GPT 분류 시마다 저장.

```sql
log_id         SERIAL PRIMARY KEY
user_id        TEXT NOT NULL
message        TEXT NOT NULL           -- 유저 발화 원문
intent         TEXT NOT NULL           -- 'meal' | 'diary' | 'schedule' | 'weight' | 'none'
entity_json    TEXT                    -- GPT 추출 엔티티 JSON (예: {"food": "비빔밥"})
classified_by  TEXT DEFAULT 'gpt'      -- 'gpt' | 'ml' (ML 전환 후 변경)
created_at     TIMESTAMP DEFAULT NOW()
```

> **활용**: 유저당 50건+ 누적 시 `utils/intent_classifier.py`로 개인화 ML 모델 학습.  
> 매주 일요일 03:30 재학습 (ML 재학습과 같은 주기).

---

## schedules (v3.5 예정 — 미생성)

```sql
schedule_id  SERIAL PRIMARY KEY
user_id      TEXT REFERENCES users(user_id)
title        TEXT NOT NULL
description  TEXT
scheduled_at TIMESTAMP NOT NULL          -- KST 기준 저장
repeat_type  TEXT DEFAULT 'none'         -- 'none' | 'daily' | 'weekly' | 'monthly'
notified     BOOLEAN DEFAULT FALSE
completed    BOOLEAN DEFAULT FALSE
created_at   TIMESTAMP DEFAULT NOW()
```

---

## DB 함수 전체 목록 (utils/db.py)

### 공통 / users

| 함수 | 설명 | 버전 |
|------|------|------|
| `init_db()` | 테이블 생성 + 마이그레이션 컬럼 추가 (봇 on_ready에서 호출) | v1 |
| `get_conn()` | Supabase Session pooler 연결 반환 | v1 |
| `create_user(user_id, data)` | 유저 생성 (UPSERT) | v1 |
| `get_user(user_id)` | 유저 조회 | v1 |
| `update_user(user_id, **kwargs)` | 유저 정보 수정 | v1 |
| `get_all_users()` | 전체 유저 조회 (스케줄러용) | v1 |
| `update_streak(user_id, streak, max_streak)` | 연속 기록일 업데이트 | v2.7 |
| `add_badges(user_id, badge_ids)` | 배지 JSON 배열에 추가 | v2.7 |

### 채널/쓰레드 ID Setter

| 함수 | 설명 | 버전 |
|------|------|------|
| `set_personal_channel_id(user_id, channel_id)` | 유저 전용 채널 ID 저장 | v4.0 예정 |
| `set_info_thread_id(user_id, thread_id)` | Push 알림 쓰레드 ID 저장 (날씨+일정) | v4.0 예정 |
| `set_mail_thread_id(user_id, thread_id)` | 메일봇 쓰레드 ID 저장 | v3.0 |
| ~~`set_meal_thread_id`~~ | v4.0에서 제거 (personal_channel 직접 응답) | — |
| ~~`set_weather_thread_id`~~ | v4.0에서 제거 (info_thread 통합) | — |
| ~~`set_weight_thread_id`~~ | v4.0에서 제거 (personal_channel 직접 응답) | — |

### 식사봇 대기 상태

| 함수 | 설명 | 버전 |
|------|------|------|
| `set_meal_waiting(user_id, seconds)` | 사진 대기 상태 설정 (meal_waiting_until = now + seconds) | v3.2 |
| `is_meal_waiting(user_id)` | 대기 상태 여부 확인 (만료 시 False) | v3.2 |
| `clear_meal_waiting(user_id)` | 대기 상태 해제 (NULL로 초기화) | v3.2 |

### tamagotchi

| 함수 | 설명 |
|------|------|
| `create_tamagotchi(user_id)` | 다마고치 생성 (hp/hunger/mood=100) |
| `get_tamagotchi(user_id)` | 다마고치 조회 |
| `update_tamagotchi(user_id, data)` | 수치 + last_fed_at 갱신 |
| `set_embed_message_id(user_id, msg_id)` | Embed 메시지 ID 저장 |

### meals

| 함수 | 설명 |
|------|------|
| `create_meal(user_id, meal_type, food_name, calories, ...)` | 식사 기록 저장 (소급 입력 지원) |
| `get_meals_by_date(user_id, date)` | 특정 날짜 식사 목록 |
| `get_calories_by_date(user_id, date)` | 특정 날짜 총 칼로리 |
| `has_meal_type_on_date(user_id, meal_type, date)` | 특정 날짜 끼니 기록 여부 |
| `get_weekly_meal_stats(user_id, start_date)` | 주간 식사 통계 (일별 칼로리/끼니/최다 음식) |

### weather_log

| 함수 | 설명 |
|------|------|
| `create_weather_log(user_id, weather, temp, pm10, pm25, image, comment)` | 날씨 기록 저장 |
| `get_latest_weather(user_id)` | 최신 날씨 조회 |

### weight_log

| 함수 | 설명 |
|------|------|
| `create_weight_log(user_id, weight)` | 체중 기록 저장 |
| `get_weight_history(user_id, limit)` | 체중 기록 조회 (최신순) |
| `get_latest_weight_before(user_id, date)` | 특정 날짜 이전 최신 체중 |

### email

| 함수 | 설명 | 버전 |
|------|------|------|
| `set_email_credentials(user_id, email, pw, initial_uid)` | 네이버 계정 + initial_uid 저장 | v3.0 |
| `get_email_users()` | 이메일 설정된 전체 유저 조회 | v3.0 |
| `update_email_last_uid(user_id, uid)` | 마지막 처리 UID 갱신 | v3.0 |
| `add_email_sender(user_id, sender_email, nickname)` | 발신자 등록 | v3.0 |
| `remove_email_sender(user_id, sender_email)` | 발신자 삭제 | v3.0 |
| `get_email_senders(user_id)` | 발신자 목록 조회 | v3.0 |
| `save_email_log(user_id, sender_email, subject, summary_gpt)` | 이메일 로그 저장 | v3.0 |
