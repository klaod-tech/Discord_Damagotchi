# 🌧️ 먹구름 (mukgoorm)

디스코드에서 동작하는 1인 1캐릭터 라이프스타일 관리 멀티봇.  
음식을 입력하면 나만의 캐릭터에게 밥을 주는 행위로 연결되고,  
**칼로리·날씨·체중·이메일 정보를 수치가 아닌 캐릭터 이미지와 대사로 간접 전달**합니다.

> 현재 버전: **v3.2** | 개발 브랜치: `develop`

---

## 🤖 멀티봇 구조

기능별로 독립된 봇 프로세스로 분리되어 있으며, 모든 봇이 하나의 Supabase DB를 공유합니다.  
봇 간 직접 HTTP 통신 없이 **DB를 단일 진실 공급원**으로 사용합니다.

```
bot.py          먹구름봇     오케스트레이터 · 온보딩 · 설정 · 식사(텍스트) · 스케줄러 · 캐릭터 관리
bot_mail.py     메일봇       IMAP 1분 폴링 · 이메일 알림 · 발신자 관리
bot_meal.py     식사봇       사진 식사 감지 · GPT-4o Vision · 칼로리 분석
bot_weather.py  날씨봇       기상청 API · 미세먼지 · 기상 시간 자동 알림
bot_weight.py   체중관리봇   체중 기록 · 목표 달성 · 추이 관리  [skeleton → 분리 예정]
bot_diary.py    일기봇       일기 작성 · 감정 분석              [미구현 — v3.4 예정]
bot_schedule.py 일정봇       일정 등록 · 알림 · 반복             [미구현 — v3.5 예정]
                                         ↓ 전체 공유
                                   Supabase DB
```

### 디스코드 채널 구조

**현재 (v3.2)** — 단일 채널 + 유저별 쓰레드

```
#다마고치 채널
└── 유저별 쓰레드 5개 (온보딩 시 자동 생성)
    ├── {이름}의 구름       ← 먹구름봇  (캐릭터 Embed, 버튼 5개)
    ├── 🍽️ {이름}의 식사   ← 식사봇    (사진 분석 결과)
    ├── 🌤️ {이름}의 날씨   ← 날씨봇    (기상 시 날씨 Embed)
    ├── ⚖️ {이름}의 체중   ← 체중관리봇 (체중 기록)
    └── 📧 {이름}의 메일함 ← 메일봇    (이메일 알림)
```

**목표 (v4.0)** — 유저별 전용 채널 + Push 전용 쓰레드 2개

```
📁 먹구름 (카테고리)
└── #{이름}-채팅창  (유저 전용 채널)
    캐릭터 Embed 고정 · 자연어 대화 · 서브봇 직접 응답
    ├── 🔔 {이름}의 알림   ← Push 전용: 날씨 기상 알림 + 일정 D-day
    └── 📧 {이름}의 메일함 ← Push 전용: 이메일 알림
```

> v4.0 핵심 변화: 서브봇은 `personal_channel_id`에 직접 응답. 메인봇으로 반환하지 않음.  
> task_queue DB 테이블을 통한 단방향 트리거. GPT/ML 의도 분류 → 전문봇 자동 트리거.

---

## 📁 프로젝트 구조

```
mukgoorm/
├── bot.py              먹구름봇 진입점
├── bot_mail.py         메일봇 진입점
├── bot_meal.py         식사봇 진입점
├── bot_weather.py      날씨봇 진입점
├── bot_weight.py       체중관리봇 진입점 (skeleton)
├── bot_diary.py        일기봇 진입점 (미구현)
├── bot_schedule.py     일정봇 진입점 (미구현)
│
├── cogs/
│   ├── onboarding.py       온보딩 Modal + 쓰레드/채널 자동 생성
│   ├── meal.py             사진 식사 감지 (bot_meal.py 전용)
│   ├── weather.py          날씨 연동 + wake_time 스케줄러 (bot_weather.py 전용)
│   ├── email_monitor.py    IMAP 폴링 + Discord 알림 (bot_mail.py 전용)
│   ├── weight.py           체중 기록 + 달성률 (bot.py 임시 → bot_weight.py 이전 예정)
│   ├── summary.py          오늘 요약 Ephemeral
│   ├── settings.py         설정 하위 메뉴 (내정보/위치/시간/이메일)
│   ├── time_settings.py    시간 설정 Select Menu (2단계)
│   └── scheduler.py        APScheduler (칼로리 판정 / 식사 알림 / 주간 리포트)
│
├── utils/
│   ├── db.py               Supabase CRUD 전체 (모든 봇 공유)
│   ├── gpt.py              GPT-4o 래퍼 (파싱 / Vision / 대사 / 이메일 요약)
│   ├── embed.py            메인 Embed UI + 버튼 + MealInputModal
│   ├── image.py            11종 이미지 우선순위 선택 로직
│   ├── badges.py           배지 7종 정의 + 달성 체크
│   ├── pattern.py          식습관 패턴 5종 분석
│   ├── ml.py               칼로리 보정 모델 (Ridge / RandomForest)
│   ├── gpt_ml_bridge.py    ML 결과 → GPT 프롬프트 브릿지
│   ├── nutrition.py        식약처 식품영양성분 DB API + GPT fallback
│   ├── mail.py             네이버 IMAP / SMTP 클라이언트
│   └── email_ui.py         이메일 공통 Modal (먹구름봇·메일봇 공유)
│
├── images/                 캐릭터 이미지 11종 (.png)
├── models/                 유저별 칼로리 보정 모델 (.pkl, 자동 생성)
├── docs/                   프로젝트 문서
├── .env
└── requirements.txt
```

---

## 🚀 실행 방법

### 1. 패키지 설치

```bash
pip install -r requirements.txt
```

### 2. 환경변수 설정

`.env` 파일을 프로젝트 루트에 배치 (아래 환경변수 섹션 참고)

### 3. 봇 실행 (터미널 4개)

```bash
# 터미널 1 — 먹구름봇 (온보딩 / 설정 / 식사텍스트 / 스케줄러)
python bot.py

# 터미널 2 — 메일봇 (IMAP 1분 폴링 / 이메일 알림)
python bot_mail.py

# 터미널 3 — 식사봇 (사진 식사 감지 / GPT Vision)
python bot_meal.py

# 터미널 4 — 날씨봇 (기상청 API / wake_time 알림)
python bot_weather.py
```

### 4. 디스코드 최초 설정

봇 실행 후 관리자 계정으로 `#먹구름` 채널에서:

```
!setup
```

→ 고정 메시지 + [🐣 다마고치 시작하기] 버튼 생성

---

## ⚙️ 환경변수 (.env)

| 변수명 | 설명 | 상태 |
|--------|------|------|
| `DISCORD_TOKEN` | 먹구름봇 토큰 | 필수 |
| `DISCORD_TOKEN_EMAIL` | 메일봇 토큰 | 필수 |
| `DISCORD_TOKEN_MEAL` | 식사봇 토큰 | 필수 |
| `DISCORD_TOKEN_WEATHER` | 날씨봇 토큰 | 필수 |
| `DISCORD_TOKEN_WEIGHT` | 체중관리봇 토큰 | 발급 필요 |
| `DISCORD_TOKEN_DIARY` | 일기봇 토큰 | 미구현 |
| `DISCORD_TOKEN_SCHEDULE` | 일정봇 토큰 | 미구현 |
| `OPENAI_API_KEY` | OpenAI API 키 | 필수 |
| `WEATHER_API_KEY` | 기상청 공공데이터 포털 인증키 | 필수 |
| `AIR_API_KEY` | 에어코리아 API 키 (미세먼지) | 필수 |
| `FOOD_API_KEY` | 식약처 식품영양성분 DB API 키 | 필수 |
| `DATABASE_URL` | Supabase Session pooler URL | 필수 |
| `TAMAGOTCHI_CHANNEL_ID` | 온보딩 진입점 채널 ID | 필수 |
| `TAMAGOTCHI_CATEGORY_ID` | 유저 전용 채널 카테고리 ID (v4.0~) | 전환 시 필요 |
| `N8N_FOOD_WEBHOOK_URL` | n8n 음식 추천 웹훅 URL | URL 수령 후 등록 |

> **이메일 수신 계정**은 `.env`가 아닌 유저가 디스코드 설정 버튼으로 직접 입력합니다.  
> → Supabase `users.naver_email / naver_app_pw`에 유저별 저장

---

## 🛠️ 기술 스택

| 분류 | 기술 |
|------|------|
| 언어 | Python 3.11+ |
| 디스코드 | discord.py 2.x (slash commands, View/Modal) |
| AI | OpenAI GPT-4o (자연어 파싱 · Vision · 대사 생성 · 이메일 요약) |
| 영양 DB | 식약처 식품영양성분 DB API (1순위) + GPT fallback |
| 날씨 | 기상청 공공데이터 API (초단기실황) |
| 미세먼지 | 에어코리아 API (PM10 · PM2.5) |
| 이메일 | 네이버 IMAP SSL / SMTP |
| DB | Supabase (PostgreSQL) + psycopg2-binary Session pooler |
| 스케줄러 | APScheduler AsyncIOScheduler |
| ML | scikit-learn (Ridge · RandomForest) · pandas · numpy |
| 칼로리 공식 | Mifflin-St Jeor |
| 음식 추천 | n8n 웹훅 연동 (URL 수령 후 활성화) |

---

## 🎮 메인 Embed (v3.2 현재 / v4.0 전환 전까지 유지)

```
[ 🍽️ 식사 입력 ]  [ 📋 하루 정리 ]  [ 🍜 뭐 먹고 싶어? ]
[ ⚙️ 설정 ]       [ ⚖️ 체중 기록 ]
```

| 버튼 | 처리 봇 | 동작 |
|------|---------|------|
| 🍽️ 식사 입력 | 먹구름봇 (텍스트) / 식사봇 (사진) | 텍스트 → GPT 파싱 + 식약처 API / 사진 → GPT Vision |
| 📋 하루 정리 | 먹구름봇 | 칼로리·탄단지·끼니·체중·날씨·GPT 코멘트 Ephemeral |
| 🍜 뭐 먹고 싶어? | 먹구름봇 | n8n 웹훅 POST → 음식 추천 |
| ⚙️ 설정 | 먹구름봇 | 하위 메뉴: 내정보 / 위치 / 시간 / 이메일 |
| ⚖️ 체중 기록 | 먹구름봇* | 체중 입력 → 달성률 + GPT 반응 |

> *체중 기록은 현재 먹구름봇에서 처리. bot_weight.py 분리 후 체중관리봇으로 이전 예정.

---

## 📊 칼로리 분석 우선순위

```
1순위: 식약처 식품영양성분 DB API  → 성공 시 공식 영양 수치
         ↓ 실패 시
2순위: OpenAI GPT-4o fallback     → 추정 칼로리/영양소
         ↓ 항상 적용
3순위: ML 보정 (get_corrected_calories)
         - 즉시: 양 표현 키워드 배율 (조금 ×0.7 / 많이 ×1.4 / 두 그릇 ×2.0 ...)
         - 30건+ 누적 시: Ridge / RandomForest 개인화 모델 추가 보정
```

---

## ⏱️ 스케줄러 동작 요약

| 시각 | 담당 봇 | 동작 |
|------|---------|------|
| 매 1분 | 메일봇 | IMAP 폴링 → 새 메일 Discord 알림 |
| 유저 wake_time | 날씨봇 | 기상청·에어코리아 API → `info_thread_id` 날씨 Embed |
| 식사시간 -30분 | 먹구름봇 | 배고픔 예고 메시지 |
| 식사시간 정각 | 먹구름봇 | 미입력 시 upset.png + GPT 대사 |
| 식사시간 +1시간 | 먹구름봇 | 미입력 시 추가 GPT 대사 |
| 매 시간 정각 | 먹구름봇 | 전체 유저 hunger -5 |
| 매일 22:00 | 먹구름봇 | 칼로리 판정 + 스트릭 갱신 + 배지 체크 |
| 매주 일요일 03:00 | 먹구름봇* | ML 칼로리 보정 모델 전체 재학습 |
| 매주 일요일 08:00 | 먹구름봇 | 주간 리포트 (칼로리·끼니·체중·스트릭·배지) |

> *ML 재학습 Job은 추후 식사봇(bot_meal.py)으로 이전 예정.

---

## 📧 이메일 모니터링

| 항목 | 내용 |
|------|------|
| 처리 봇 | 메일봇 (bot_mail.py) |
| 폴링 간격 | 1분 |
| 지원 메일 | 네이버 IMAP SSL (imap.naver.com:993) |
| 스팸 필터 | 1단계: INBOX 한정 / 2단계: 제목 키워드 / 3단계: 발신자 화이트리스트 |
| 본문 처리 | ≤200자 → 원문 그대로 / >200자 → GPT-4o 요약 |
| 알림 위치 | `mail_thread_id` (메일함 쓰레드, Push 전용) |
| 슬래시 커맨드 | `/이메일설정` `/발신자추가` `/발신자목록` `/발신자삭제` |

---

## 🖼️ 캐릭터 이미지 (11종, 우선순위 순)

| 이미지 | 표시 조건 | 우선순위 |
|--------|-----------|---------|
| `cheer.png` | 목표 달성 / 배지 획득 | 1 |
| `eat.png` | 식사 입력 직후 3분 | 2 |
| `upset.png` | 배고픔 (hunger < 40) | 3 |
| `wear_mask.png` | PM10 > 80 또는 PM2.5 > 35 | 4 |
| `rainy.png` | 비 / 소나기 | 4 |
| `snow.png` | 눈 | 4 |
| `hot.png` | 기온 ≥ 26°C | 4 |
| `warm.png` | 기온 ≤ 5°C | 4 |
| `tired.png` | hp < 40 또는 mood < 40 | 5 |
| `smile.png` | 상태 양호 (hp·hunger·mood ≥ 70) | 5 |
| `normal.png` | 기본값 | 5 |

> hp / hunger / mood 수치는 내부 전용 — 유저에게 직접 노출하지 않습니다.

---

## 🏅 도전과제 배지 (7종)

| 배지 ID | 이름 | 달성 조건 |
|---------|------|----------|
| `first_meal` | 🍽️ 첫 끼니 | 첫 번째 식사 기록 |
| `streak_3` | 🔥 3일 연속 | 3일 연속 식사 기록 |
| `streak_7` | 🌟 일주일 달인 | 7일 연속 |
| `streak_30` | 👑 한 달 챔피언 | 30일 연속 |
| `calorie_10` | 🎯 목표 달성 10회 | 목표 칼로리 ≥ 90% 달성일 10일 이상 |
| `photo_10` | 📸 사진 마스터 | 사진 입력 누적 10회 이상 |
| `morning_7` | 🌅 아침형 인간 | 아침 끼니 누적 기록 7회 이상 |

배지 달성 시 골드 Embed 전송 + 메인 Embed `cheer.png`로 갱신.

---

## 🗄️ DB 테이블 요약

| 테이블 | 소유 봇 | 주요 내용 |
|--------|---------|----------|
| `users` | 공통 | 유저 정보, 시간 설정, 채널/쓰레드 ID, 이메일 자격증명 |
| `tamagotchi` | 먹구름봇 | hp / hunger / mood / 현재 이미지 |
| `meals` | 먹구름봇(텍스트) + 식사봇(사진) | 식사 기록, 칼로리, 영양소 |
| `weather_log` | 날씨봇 | 날씨·기온·미세먼지 기록 |
| `weight_log` | 체중관리봇 | 체중 기록 |
| `email_senders` | 메일봇 | 발신자 화이트리스트 |
| `email_log` | 메일봇 | 수신 이메일 로그 |
| `diary_log` | 일기봇 (예정) | 일기 원문 + 감정 분석 |
| `schedules` | 일정봇 (예정) | 일정·반복·알림 상태 |
| `intent_log` | 먹구름봇 (v4.0 예정) | 자연어 의도 분류 ML 학습 데이터 |

> **타임존 주의**: Supabase는 UTC 저장. 날짜 비교는 반드시 UTC → KST 이중 변환 사용.

상세: [`docs/03_DATABASE.md`](docs/03_DATABASE.md)

---

## 🗺️ 개발 로드맵

| Phase | 버전 | 내용 |
|-------|------|------|
| ✅ 완료 | v1.0~v3.2 | 멀티봇 4개 운영 (먹구름·메일·식사·날씨), ML 칼로리 보정, 배지/스트릭 |
| 다음 | v3.3 | 체중관리봇 분리 + n8n 음식 추천 연동 |
| 예정 | v3.4 | 일기봇 (감정 분석) |
| 예정 | v3.5 | 일정봇 (일정 등록 + APScheduler 알림) |
| 장기 | v4.0 | 유저별 전용 채널 + 자연어 오케스트레이터 전환 |

상세: [`docs/PRODUCTION_ROADMAP.md`](docs/PRODUCTION_ROADMAP.md)

---

## 📖 상세 문서

| 문서 | 내용 |
|------|------|
| [`docs/01_OVERVIEW.md`](docs/01_OVERVIEW.md) | 개요 · 기술스택 · 멀티봇 구조 |
| [`docs/02_FLOWS.md`](docs/02_FLOWS.md) | 전체 기능 흐름 (봇별 처리 주체 명시) |
| [`docs/03_DATABASE.md`](docs/03_DATABASE.md) | DB 스키마 · 테이블 소유권 |
| [`docs/05_ML_MODULES.md`](docs/05_ML_MODULES.md) | ML 모듈 · 봇별 ML 로드맵 |
| [`docs/06_PROGRESS.md`](docs/06_PROGRESS.md) | 구현 현황 · 이전 예정 · 버그 목록 |
| [`docs/PRODUCTION_ROADMAP.md`](docs/PRODUCTION_ROADMAP.md) | 전체 Phase 제작 순서 |
| [`docs/TEAM_OVERVIEW.md`](docs/TEAM_OVERVIEW.md) | 팀 기술 개요서 (신규 팀원 온보딩 시작점) |
| [`docs/bots/00_INDEX.md`](docs/bots/00_INDEX.md) | 봇별 상세 문서 인덱스 |

---

현재 버전: **v3.2** (2026-04-14)
