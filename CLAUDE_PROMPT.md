# 📋 Claude Code 시작 프롬프트 (최초 1회 붙여넣기)

---

## 🐣 프로젝트 개요

디스코드에서 동작하는 **1인 1다마고치 봇**이야.
유저가 음식을 입력하면 다마고치에게 밥을 주는 행위로 연결되고,
**칼로리 관리와 날씨 정보를 수치가 아닌 캐릭터 이미지와 대사로 간접 전달**하는 게 핵심이야.

---

## 🛠️ 기술 스택

- Python 3.11+, discord.py
- OpenAI GPT-4o (칼로리 분석, Vision, 대사 생성)
- SQLite (tamagotchi.db)
- APScheduler (식사 알림, 날씨 교체 자동화)
- 기상청 공공데이터 API (날씨)

---

## 📁 목표 파일 구조

```
tamagotchi-bot/
├── bot.py
├── cogs/
│   ├── onboarding.py     # 온보딩 + 쓰레드 생성 ← 현재 여기까지 구현됨
│   ├── meal.py           # 식사 입력 (텍스트 + 사진)
│   ├── weather.py        # 날씨 연동 + 이미지 교체
│   ├── summary.py        # 오늘 요약
│   ├── settings.py       # 설정 변경
│   └── scheduler.py      # APScheduler 알림 관리
├── utils/
│   ├── gpt.py            # OpenAI API 래퍼
│   ├── db.py             # DB 연결 + 쿼리
│   ├── embed.py          # Embed UI 생성 + 수정
│   └── image.py          # 상태별 이미지 선택 로직
├── images/               # 다마고치 이미지 (~25종)
├── .env
└── requirements.txt
```

---

## 🗄️ DB 테이블 구조

### Users
| 컬럼 | 타입 | 설명 |
|------|------|------|
| user_id | TEXT PK | 디스코드 유저 ID |
| tamagotchi_name | TEXT | 다마고치 이름 |
| city | TEXT | 거주 도시 (날씨 기준) |
| wake_time | TEXT HH:MM | 기상 시간 |
| init_weight | REAL | 초기 체중 kg |
| goal_weight | REAL | 목표 체중 kg |
| daily_cal_target | INTEGER | GPT 산출 권장 칼로리 |
| breakfast_time | TEXT HH:MM | 아침 알림 시간 |
| lunch_time | TEXT HH:MM | 점심 알림 시간 |
| dinner_time | TEXT HH:MM | 저녁 알림 시간 |
| thread_id | TEXT | 유저 전용 쓰레드 ID |
| created_at | DATETIME | 생성 시각 |

### Tamagotchi
| 컬럼 | 타입 | 설명 |
|------|------|------|
| user_id | TEXT PK | FK → Users |
| hp | INTEGER 0~100 | 건강 수치 (내부 전용, 사용자 비노출) |
| hunger | INTEGER 0~100 | 배부름 수치 (내부 전용, 사용자 비노출) |
| mood | INTEGER 0~100 | 기분 수치 (내부 전용, 사용자 비노출) |
| current_image | TEXT | 현재 표시 이미지 파일명 |
| embed_message_id | TEXT | 쓰레드 내 Embed 메시지 ID |
| last_fed_at | DATETIME | 마지막 식사 입력 시각 |
| updated_at | DATETIME | 마지막 수치 업데이트 시각 |

### Meals
| 컬럼 | 타입 | 설명 |
|------|------|------|
| meal_id | INTEGER PK | auto increment |
| user_id | TEXT | FK → Users |
| meal_type | TEXT | breakfast / lunch / dinner / snack |
| food_name | TEXT | 음식명 (콤마 구분) |
| calories | INTEGER | 총 칼로리 kcal |
| protein | REAL | 단백질 g |
| carbs | REAL | 탄수화물 g |
| fat | REAL | 지방 g |
| fiber | REAL | 식이섬유 g |
| input_method | TEXT | text / photo |
| gpt_comment | TEXT | GPT 다마고치 한마디 (캐싱) |
| recorded_at | DATETIME | 입력 시각 |

### Weather_Log
| 컬럼 | 타입 | 설명 |
|------|------|------|
| log_id | INTEGER PK | auto increment |
| user_id | TEXT | FK → Users |
| weather | TEXT | 맑음/비/눈/흐림 등 |
| temp | REAL | 기온 °C |
| pm10 | INTEGER | 미세먼지 μg/m³ |
| pm25 | INTEGER | 초미세먼지 μg/m³ |
| selected_image | TEXT | 선택된 이미지 파일명 |
| gpt_comment | TEXT | GPT 날씨 기반 대사 (캐싱) |
| recorded_at | DATETIME | 수집 시각 |

---

## ⚙️ 수치 변화 규칙

### hunger
- 적정 식사 입력: +30~40
- 과식: +50 이상
- 소식: +10~15
- 시간 경과: -5/시간
- hunger = 0 이어도 다마고치 사망 없음

### hp
- 적정 식사: +5
- 과식 3일 연속: -10
- 소식 3일 연속: -10

### mood
- 식사 입력: +5
- 오늘 요약 버튼 클릭: +3
- hunger < 30: -10

---

## 🖼️ 이미지 선택 우선순위

```
1순위: 특별 이벤트 (goal_achieved.png, birthday.png)
2순위: 식사 상태 (overfed.png, underfed.png, eating.png)
3순위: 배고픔 (hungry_cry.png, hungry.png)
4순위: 날씨 (sunny/hot/cold/rainy/snowy/cloudy/dusty.png)
5순위: 기본 감정 (happy/normal/tired/sick.png)
```

### 이미지별 트리거 조건
| 이미지 | 조건 |
|--------|------|
| goal_achieved.png | 목표 체중 달성 |
| overfed.png | 오후 10시 총 칼로리 > 권장 |
| underfed.png | 오후 10시 총 칼로리 < 권장×0.67 |
| eating.png | 식사 입력 직후 3분 |
| hungry_cry.png | hunger < 20 AND 알림 1시간 경과 |
| hungry.png | hunger < 40 AND 알림 정각 경과 |
| dusty.png | PM10 > 80 OR PM2.5 > 35 |
| rainy.png | 날씨 = 비/소나기 |
| snowy.png | 날씨 = 눈 |
| hot.png | 기온 ≥ 26°C |
| cold.png | 기온 ≤ 5°C |
| sunny.png | 맑음 + 15~25°C |
| cloudy.png | 흐림 |
| sick.png | hp < 40 |
| tired.png | mood < 40 |
| normal.png | 모든 수치 40~69 |
| happy.png | hp ≥ 70, hunger ≥ 70, mood ≥ 70 |

---

## 💬 GPT System Prompt (범용)

```
너는 '{tamagotchi_name}'이라는 이름의 AI 다마고치야.
성격은 밝고 긍정적이야. 짧고 친근하게 말해줘.

[사용자 정보]
- 시작 체중: {init_weight}kg, 목표 체중: {goal_weight}kg
- 권장 칼로리: {daily_cal_target} kcal
- 오늘 섭취 칼로리: {today_calories} / {daily_cal_target} kcal
- 최근 식사: {recent_meals}
- 오늘 날씨: {weather}, {temp}°C

건강 조언은 부드럽게, 수치는 직접 언급하지 말고 느낌으로 표현해줘.
```

---

## ✅ 현재 구현 완료

- `database.py` — DB 초기화 + Users/Tamagotchi/Meals/Weather_Log CRUD
- `onboarding.py` — 2단계 Modal, 쓰레드 생성, GPT 칼로리 계산, 메인 Embed 버튼
- `bot.py` — 봇 진입점, `/setup` 명령어로 고정 메시지 전송

## 🔜 다음 구현할 것

**우선순위 2번: 메인 Embed UI — 이미지 + 이미지 선택 로직**
- `utils/image.py` — 상태 수치 기반 이미지 선택 함수
- `utils/embed.py` — Embed 생성 및 수정 함수
- `utils/gpt.py` — OpenAI API 래퍼 (대사 생성)

---

## 환경변수 (.env)

```
DISCORD_TOKEN=
OPENAI_API_KEY=
WEATHER_API_KEY=
DATABASE_URL=./tamagotchi.db
TAMAGOTCHI_CHANNEL_ID=
```

---

위 내용이 이 프로젝트의 전체 설계야. 이걸 기반으로 개발을 이어서 진행해줘.
