# 프로젝트 개요

> last_updated: 2026-04-13 | 현재 버전: v3.2

---

## 한 줄 소개

먹구름(mukgoorm) — 유저가 음식을 입력하면 나만의 캐릭터에게 밥을 주는 행위로 연결되며, 칼로리·날씨·체중·이메일 정보를 **수치 없이 캐릭터 이미지와 대사로 간접 전달**하는 디스코드 라이프스타일 관리 멀티봇.

---

## 핵심 원칙 (절대 변경 불가)

1. **hp/hunger/mood 수치는 사용자에게 절대 직접 노출 금지** — 이미지+대사로만 간접 표현
2. **날씨는 별도 알림 없음** — 기상 시간에 이미지 자동 교체로만 전달
3. **칼로리/영양소 수치는 오늘 요약 버튼 클릭 시 Ephemeral로만 확인 가능**
4. **파일명 소문자 고정** (eat.png O, Eat.PNG X)
5. **각 봇은 자신이 소유한 DB 테이블에만 INSERT/UPDATE**
6. **기존 유저 fallback**: 신규 전용 쓰레드 ID가 NULL이면 `thread_id`(메인)로 자동 fallback

---

## 기술 스택

| 항목 | 내용 |
|------|------|
| 언어 | Python 3.11+ |
| 디스코드 | discord.py 2.x (slash commands, View/Modal, Intents) |
| AI | OpenAI GPT-4o (자연어 파싱, Vision, 대사 생성, 칼로리 fallback) |
| 영양 DB | 식품의약품안전처 식품영양성분 DB API (칼로리/영양소 1순위) |
| 날씨 | 기상청 공공데이터 API (초단기실황조회) |
| 미세먼지 | 에어코리아 API (PM10, PM2.5) |
| 이메일 | 네이버 IMAP (imaplib) / SMTP (smtplib) |
| DB | Supabase (PostgreSQL) — psycopg2-binary, Session pooler |
| 스케줄러 | APScheduler (AsyncIOScheduler) |
| ML | scikit-learn (Ridge / RandomForest), pandas, numpy |
| 칼로리 공식 | Mifflin-St Jeor |
| 이미지 | NovelAI (NAI Diffusion Anime V3, 512×512) |

---

## 멀티봇 구조 (v3.2~)

하나의 봇에 모든 기능을 넣는 대신, **기능별로 독립된 봇 프로세스**로 분리.  
모든 봇은 **동일한 Supabase DB를 공유**하며 독립적인 이벤트 루프에서 동작.

```
Discord 서버 #먹구름 채널
│
├── bot.py          먹구름봇    온보딩·설정·식사텍스트·스케줄러·캐릭터
├── bot_mail.py     메일봇      IMAP 폴링·이메일 알림·발신자 관리
├── bot_meal.py     식사봇      사진 식사 감지·GPT Vision·칼로리 분석
├── bot_weather.py  날씨봇      기상청 API·미세먼지·wake_time 알림
├── bot_weight.py   체중관리봇  체중 기록·목표 달성·추이 (skeleton → 분리 예정)
├── bot_diary.py    일기봇      일기 작성·감정 분석 (미구현)
└── bot_schedule.py 일정봇      일정 등록·알림·반복 (미구현)
                                    ↓ 전체 공유
                              Supabase DB
```

### 봇 현황

| 봇 파일 | 상태 | 로드 Cog | 응답/Push 위치 |
|---------|------|----------|------------|
| `bot.py` | ✅ 운영 중 | onboarding, summary, settings, time_settings, scheduler, weight* | `personal_channel_id` (오케스트레이터) |
| `bot_mail.py` | ✅ 운영 중 | email_monitor | `mail_thread_id` (Push 전용) |
| `bot_meal.py` | ✅ 운영 중 | meal | `personal_channel_id` (직접 응답) |
| `bot_weather.py` | ✅ 운영 중 | weather | `info_thread_id` (Push 전용) |
| `bot_weight.py` | 🔄 skeleton | (weight Cog 이전 예정) | `personal_channel_id` (직접 응답) |
| `bot_diary.py` | 📋 미구현 | (diary Cog 예정) | `personal_channel_id` (직접 응답) |
| `bot_schedule.py` | 📋 미구현 | (schedule Cog 예정) | `personal_channel_id` (직접 응답) + `info_thread_id` (Push 알림) |

> *`cogs.weight`는 현재 bot.py에 임시 로드 중. bot_weight.py 활성화 시 이전 예정.

### 봇 간 상태 공유 방식

봇 프로세스가 분리되어 있어 in-memory 공유 불가 → **DB를 단일 진실 공급원**으로 사용.

```
예시 — 사진 식사 입력 대기 상태:
  [먹구름봇] 📸 버튼 클릭 → set_meal_waiting(user_id, 60초) → DB 기록
  [식사봇  ] on_message   → is_meal_waiting(user_id)         → DB 조회 → 사진 처리
```

---

## 디스코드 채널·쓰레드 구조

> **v4.0 목표 구조** — 유저별 전용 채널 + 기능봇별 쓰레드

```
서버
├── #먹구름-시작  (공용 — 온보딩 진입점)
│     [🐣 다마고치 시작하기] 버튼 고정
│
└── 📁 먹구름  (카테고리)
    │
    ├── #{이름}-채팅창  (유저A 전용 채널 — 메인봇 대화 공간)
    │     캐릭터 상태 Embed 고정, 자연어 대화 입력
    │   ├── 🍽️ {이름}의 식사기록  (쓰레드 — 식사봇 전용)
    │   ├── 🌤️ {이름}의 날씨      (쓰레드 — 날씨봇 전용)
    │   ├── ⚖️ {이름}의 체중관리  (쓰레드 — 체중관리봇 전용)
    │   ├── 📧 {이름}의 메일함    (쓰레드 — 메일봇 전용)
    │   ├── 📔 {이름}의 일기장    (쓰레드 — 일기봇 전용, v3.4~)
    │   └── 📅 {이름}의 일정표    (쓰레드 — 일정봇 전용, v3.5~)
    │
    └── #{이름}-채팅창  (유저B 전용 채널 — 동일 구조)
```

> **채널 권한**: 온보딩 시 해당 유저만 전용 채널을 볼 수 있도록 권한 자동 설정.  
> 다른 유저는 서로의 채널 접근 불가.

### v3.2 현재 구조 (기존 유저 호환용)

```
#다마고치 채널 (단일 채널)
└── 유저별 쓰레드 5개 (thread_id 기반 fallback 유지)
```

> 기존 2인 유저는 thread_id fallback으로 계속 동작. 신규 유저부터 전용 채널 방식 적용.

### 채널 구조 변경에 따른 DB 추가 컬럼

| 컬럼 | 설명 |
|------|------|
| `personal_channel_id` | 유저 전용 채널 ID (v4.0 온보딩 시 생성) |
| `address` | 동 단위 주소 — 음식 추천 전용 (n8n 연동 시 수집) |

---

## 유저 규모 및 설계 기준

| 항목 | 내용 |
|------|------|
| 현재 운영 | 2인 프라이빗 서버 |
| 목표 규모 | 최대 20인 소규모 서버 |
| 채널 예상 수 | 20명 × 6~7 쓰레드 ≈ 130개 (Discord 한도 500개, 여유 있음) |
| DB 연결 | 7개 봇 × 동시 연결 — Supabase 커넥션 풀 모니터링 필요 |
| API 비용 기준 | 20명 × GPT 호출 빈도 — 월 예산 계획 시 20인 기준 적용 |

---

## 환경변수 (.env)

```bash
# 봇 토큰 (봇마다 별도 Discord Application)
DISCORD_TOKEN           # 먹구름봇 (bot.py)
DISCORD_TOKEN_EMAIL     # 메일봇 (bot_mail.py)
DISCORD_TOKEN_MEAL      # 식사봇 (bot_meal.py)
DISCORD_TOKEN_WEATHER   # 날씨봇 (bot_weather.py)
DISCORD_TOKEN_WEIGHT    # 체중관리봇 (bot_weight.py) — 발급 필요
DISCORD_TOKEN_DIARY     # 일기봇 (bot_diary.py) — 미구현
DISCORD_TOKEN_SCHEDULE  # 일정봇 (bot_schedule.py) — 미구현

# API 키 (전 봇 공유)
OPENAI_API_KEY          # GPT-4o (자연어, Vision, 대사 생성)
WEATHER_API_KEY         # 기상청 공공데이터 포털 인증키
AIR_API_KEY             # 에어코리아 API 키
FOOD_API_KEY            # 식약처 식품영양성분 DB (data.go.kr)

# DB
DATABASE_URL            # Supabase Session pooler URL
                        # postgresql://postgres.{project_id}:{password}@...

# 채널 (v3.2 현재)
TAMAGOTCHI_CHANNEL_ID   # 온보딩 진입점 채널 ID (#먹구름-시작)

# 채널 (v4.0 채널 구조 전환 시 추가)
TAMAGOTCHI_CATEGORY_ID  # 유저 전용 채널이 생성될 카테고리 ID

# n8n (웹훅 URL 수령 후 등록)
N8N_FOOD_WEBHOOK_URL    # 음식 추천 웹훅 URL (n8n에서 발급)

# 이메일 발신 (미사용, Phase 3 예정)
NAVER_MAIL_ID           # 봇 발신용 네이버 아이디
NAVER_MAIL_PW           # 봇 발신용 네이버 앱 비밀번호
```

> **이메일 수신 계정**은 `.env`가 아닌 유저가 디스코드 설정 버튼으로 직접 입력  
> → Supabase `users.naver_email / naver_app_pw`에 유저별 저장

---

## 공유 유틸리티 (utils/)

| 모듈 | 역할 | 사용 봇 |
|------|------|---------|
| `utils/db.py` | Supabase CRUD 전체, 마이그레이션 | 모든 봇 |
| `utils/gpt.py` | GPT-4o 래퍼 (파싱·분석·대사·요약) | bot.py, bot_mail.py |
| `utils/embed.py` | 메인 Embed + View/Modal 빌더 | bot.py |
| `utils/image.py` | 11종 이미지 우선순위 선택 로직 | bot.py, bot_weather.py |
| `utils/ml.py` | 칼로리 보정 모델 (즉시 + 개인화) | bot_meal.py |
| `utils/pattern.py` | 식습관 패턴 5종 분석 | bot.py |
| `utils/gpt_ml_bridge.py` | ML 결과 → GPT 프롬프트 주입 | bot.py |
| `utils/badges.py` | 배지 7종 정의 + 달성 체크 | bot.py |
| `utils/nutrition.py` | 식약처 API 조회 + GPT fallback | bot_meal.py |
| `utils/mail.py` | 네이버 IMAP/SMTP 클라이언트 | bot_mail.py |
| `utils/email_ui.py` | EmailSetupModal, SenderAddModal 공통 모달 | bot.py, bot_mail.py |

---

## 버전 히스토리

| 버전 | 날짜 | 주요 변경사항 |
|------|------|--------------|
| v4.0 | 예정 | 유저별 전용 채널 구조, 메인봇 자연어 오케스트레이터 전환, ML 의도 분류 |
| v3.5 | 예정 | 일정봇 (bot_schedule.py) 구현 |
| v3.4 | 예정 | 일기봇 (bot_diary.py) 구현 |
| v3.3 | 예정 | 체중관리봇 분리, n8n 음식 추천 연동 |
| v1.0 | 2026-03-25 | 전체 설계, DB 구조, 기술스택 확정 |
| v1.1~v1.9 | 2026-03-28~04-02 | 온보딩, 식사 입력, 날씨, 스케줄러, 이미지 시스템 |
| v2.0 | 2026-04-02 | gender/age/height DB 저장, 칼로리 재계산 |
| v2.1 | 2026-04-02 | 프로젝트명 먹구름 확정, GPT 캐릭터 프롬프트 수정 |
| v2.2 | 2026-04-02 | 식사 알림 스케줄러 3단계, hourly hunger decay |
| v2.3 | 2026-04-03 | UTC→KST 타임존 버그 수정, Embed 이미지 크게 표시 |
| v2.4~v2.6 | 2026-04-03 | UI 개선, 시간 설정 10분 단위, ML 재학습 스케줄러 |
| v2.7 | 2026-04-04 | 스트릭 + 배지 7종, 주간 리포트 |
| v2.8 | 2026-04-07 | 식약처 API 연동, 중복 제출 방지 |
| v2.9 | 2026-04-11 | 버튼 5개 재편, 하루 정리 통합, 설정 하위 메뉴 |
| v3.0 | 2026-04-12 | 이메일 모니터링 (IMAP 폴링, 스팸 필터, 발신자 알림) |
| v3.1 | 2026-04-13 | **메일봇 분리** (bot_mail.py), 폴링 1분으로 단축, 발송 시각 표시 |
| v3.2 | 2026-04-13 | **식사봇·날씨봇·체중관리봇 분리** (bot_meal/weather/weight.py), 온보딩 쓰레드 5개, DB 기반 대기 상태 |

---

## GitHub

- Repo: https://github.com/klaod-tech/mukgoorm
- 메인 브랜치: `main`
- 개발 브랜치: `develop` ← **모든 개발은 여기서**
