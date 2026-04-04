# 📋 Claude 시작 프롬프트 (v2.7 기준 — 2026-04-04)

새 대화에서 이 파일을 붙여넣으면 맥락 없이도 바로 이어서 개발 가능해.
상세 문서는 `docs/` 폴더 참고. 인덱스: `docs/CONTEXT.md`

---

## 🐣 프로젝트 개요

**먹구름(mukgoorm)** — 디스코드에서 동작하는 1인 1캐릭터 식습관 관리 봇.
유저가 음식을 입력하면 캐릭터에게 밥을 주는 행위로 연결되고,
**칼로리/날씨 정보를 수치 없이 캐릭터 이미지와 대사로 간접 전달**하는 게 핵심.

### 핵심 원칙 (절대 변경 불가)
- hp/hunger/mood 수치는 사용자에게 절대 직접 노출 금지 → 이미지+대사로만
- 날씨는 별도 알림 없음 → 기상 시간에 이미지 자동 교체로만 전달
- 칼로리/영양소 수치는 `📊 오늘 요약` 버튼 Ephemeral로만 확인 가능
- 모든 개발은 `develop` 브랜치에서 → main은 배포용

---

## 🛠️ 기술 스택

- Python 3.11+, discord.py 2.x
- OpenAI GPT-4o (칼로리 분석, Vision, 자연어 파싱, 대사 생성)
- Supabase (PostgreSQL) — psycopg2 Session pooler
- APScheduler (AsyncIOScheduler)
- 기상청 공공데이터 API (초단기실황) + 에어코리아 API (PM10/PM2.5)
- scikit-learn / pandas / numpy (ML 칼로리 보정 + 패턴 분석)
- prophet (선택적 — 없어도 graceful fallback)

---

## 📁 파일 구조

```
Discord_Damagotchi/
├── bot.py                  # 진입점, 8개 cog 로드, !setup/!소환 커맨드
├── database.py             # init_db 수동 실행용
├── cogs/
│   ├── onboarding.py       # 4필드 Modal, 쓰레드 생성, 첫 Embed
│   ├── meal.py             # 사진 식사 입력 (GPT-4o Vision), on_message 감지
│   ├── weather.py          # 기상청+에어코리아, wake_time 기반 스케줄러
│   ├── summary.py          # 오늘 요약 Ephemeral
│   ├── settings.py         # 설정 변경 Modal (이름/도시/목표체중)
│   ├── time_settings.py    # 시간 설정 Select Menu 2단계
│   ├── scheduler.py        # 전체 스케줄 관리 (아래 표 참고)
│   └── weight.py           # 체중 기록 + 달성률
├── utils/
│   ├── gpt.py              # GPT-4o 래퍼 (칼로리계산/파싱/분석/대사)
│   ├── db.py               # Supabase CRUD + streak/badge 함수
│   ├── embed.py            # 메인 Embed UI + MainView (6버튼) + MealInputModal
│   ├── image.py            # 이미지 선택 로직 (11종, 우선순위 5단계)
│   ├── badges.py           # 도전과제 배지 7종 + check_new_badges()
│   ├── pattern.py          # 식습관 패턴 분석 (14일, 5가지 패턴)
│   ├── ml.py               # 칼로리 보정 모델 (Ridge/RF, models/ 저장)
│   └── gpt_ml_bridge.py    # ML → GPT extra_context 브릿지
├── images/                 # 이미지 11종 (소문자 고정)
│   cheer/eat/upset/tired/normal/smile/rainy/snow/hot/warm/wear mask.png
├── docs/                   # 상세 문서 (CONTEXT.md 인덱스)
└── requirements.txt
```

---

## 🗄️ DB 스키마 (Supabase PostgreSQL)

### users
```
user_id, tamagotchi_name, city, wake_time,
breakfast_time, lunch_time, dinner_time,
init_weight, goal_weight, daily_cal_target,
thread_id, gender, age, height,
streak(v2.7), max_streak(v2.7), badges TEXT '[]'(v2.7),
created_at
```

### tamagotchi
```
user_id(FK), hp(100), hunger(50), mood(50),
current_image, embed_message_id, last_fed_at, updated_at
```

### meals
```
meal_id(SERIAL), user_id(FK), meal_type, food_name,
calories, protein, carbs, fat, fiber,
input_method(text/photo), gpt_comment,
recorded_at(UTC — 조회 시 AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Seoul' 필수)
```

### weather_log
```
log_id(SERIAL), user_id(FK), weather, temp, pm10, pm25,
selected_image, gpt_comment, recorded_at
```

### weight_log
```
log_id(SERIAL), user_id(FK), weight, recorded_at
```

---

## ⏰ 스케줄러 동작 (cogs/scheduler.py)

| 시각 | 함수 | 동작 |
|------|------|------|
| 식사시간 -30분 | `_meal_reminder` | 쓰레드 배고픔 예고 |
| 식사시간 정각 | `_meal_upset` | 미입력 시 upset.png + 대사 |
| 식사시간 +1시간 | `_meal_late` | 미입력 시 추가 대사 |
| 매 시간 정각 | `_hourly_hunger_decay` | hunger -5 (전체 유저) |
| 매일 22:00 | `_nightly_analysis` | 칼로리 판정 + streak 업데이트 + 배지 체크 |
| 일요일 03:00 | `_weekly_ml_retrain` | ML 모델 재학습 |
| 일요일 08:00 | `_weekly_report` | 주간 리포트 Embed 전송 |

---

## 🎮 메인 Embed 버튼 (현재 6개, 2행)

```
Row 0: [🍽️ 식사 입력] [📊 오늘 요약] [📅 오늘 일정]
Row 1: [⚙️ 설정 변경] [⏰ 시간 설정] [⚖️ 체중 기록]
```

| 버튼 | custom_id | 동작 |
|------|-----------|------|
| 식사 입력 | btn_meal | MealInputSelectView (텍스트/사진 선택) |
| 오늘 요약 | btn_summary | send_summary() Ephemeral |
| 오늘 일정 | btn_today | 칼로리바/체중/날씨/ML코멘트 Ephemeral |
| 설정 변경 | btn_settings | SettingsModal (이름/도시/목표체중) |
| 시간 설정 | btn_time_settings | TimeStep1View → TimeStep2View |
| 체중 기록 | btn_weight | WeightInputModal |

> **v2.8 예정**: 버튼 5개로 개편 (하루 정리 통합, 설정 하위 메뉴, 뭐 먹고 싶어? 추가)
> 상세: `docs/07_NEXT_FEATURES.md`

---

## 🖼️ 이미지 선택 우선순위 (utils/image.py)

| 순위 | 조건 | 이미지 |
|------|------|--------|
| 1 | goal_achieved=True | cheer.png |
| 2 | just_ate=True OR last_fed_at 3분 이내 | eat.png |
| 3 | hunger < 40 | upset.png |
| 4 | 날씨 (PM10>80→마스크, 비, 눈, 더위, 추위) | wear mask/rainy/snow/hot/warm |
| 5 | hp<40 OR mood<40 | tired.png |
| 5 | hp≥70 AND hunger≥70 AND mood≥70 | smile.png |
| 5 | 기본값 | normal.png |

---

## 🏅 배지 시스템 (utils/badges.py — v2.7)

| 배지 | 조건 |
|------|------|
| first_meal | 첫 식사 기록 |
| streak_3 | 3일 연속 |
| streak_7 | 7일 연속 |
| streak_30 | 30일 연속 |
| calorie_10 | 목표 칼로리 90% 이상 달성일 10일 |
| photo_10 | 사진 입력 10회 |
| morning_7 | 아침 기록 7회 |

배지 달성 시: 골드 Embed + cheer.png 메인 Embed 갱신
streak은 매일 22:00 _nightly_analysis에서 업데이트 (식사 기록 있으면 +1, 없으면 0)

---

## 🔧 알려진 버그

| 우선순위 | 내용 | 위치 |
|---------|------|------|
| P2 | `generate_comment_with_pattern()` 파라미터 불일치 (데드코드라 크래시 없음) | gpt_ml_bridge.py:73 |

---

## ⚙️ 환경변수 (.env)

```
DISCORD_TOKEN=
OPENAI_API_KEY=
WEATHER_API_KEY=          # 기상청 공공데이터 포털
AIR_API_KEY=              # 에어코리아 (AIRKOREA_API_KEY 아님)
DATABASE_URL=postgresql://postgres.{프로젝트ID}:{비밀번호}@...
TAMAGOTCHI_CHANNEL_ID=
```

---

## 🌿 브랜치

- `main` — 배포용
- `develop` — 개발용 (현재 v2.7)

GitHub: https://github.com/klaod-tech/mukgoorm
