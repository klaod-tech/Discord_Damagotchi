# 먹구름(mukgoorm) — 팀 기술 개요서

> **현재 버전**: v3.2
> **GitHub**: https://github.com/klaod-tech/mukgoorm
> **작성일**: 2026-04-13

---

## 1. 프로젝트 소개

### 한 줄 요약
> 나만의 AI 캐릭터와 함께하는 **디스코드 기반 라이프스타일 관리 봇**.

### 상세 소개
먹구름은 단순한 칼로리 계산 앱이 아닙니다.
유저가 **음식, 체중, 감정, 일정**을 기록하면, 나만의 캐릭터가 그 데이터를 바탕으로
오늘의 상태를 이미지와 대사로 **간접적으로** 전달합니다.

숫자를 직접 보여주는 대신, 캐릭터의 표정과 한마디가 오늘 내 하루를 대신 말해줍니다.

**현재 구현된 기능:**
- 식사 기록 (텍스트 / 사진) → 칼로리·영양소 분석 → 캐릭터 반응
- 체중 기록 → 목표 체중까지의 변화 추적
- 날씨·미세먼지 실시간 반영 → 캐릭터 이미지 자동 교체
- ML 기반 개인화 칼로리 보정 (데이터 누적 시)
- 스트릭 + 도전과제 배지 시스템
- 네이버 이메일 모니터링 → 등록 발신자 메일 알림
- **멀티봇 아키텍처**: 식사봇 / 날씨봇 / 체중관리봇 / 메일봇 독립 분리 (v3.2)

**앞으로 추가될 기능:**
- 일기 (하루 감정/메모 기록 → 캐릭터 반응)
- 일정 (오늘 할 일 / 식사 계획 관리)
- 음식 추천 (위치 + 식사 이력 기반 — n8n 연동)
- 이메일 서비스 (주간 리포트 / 배지 알림 — Naver Mail)
- 총괄 AI 채널 (유저가 자연어로 캐릭터에게 모든 기능을 말로 요청)

### 핵심 철학
```
"기록은 습관이고, 습관은 캐릭터에 녹아든다."

유저가 꾸준히 기록할수록 캐릭터가 더 풍부하게 반응한다.
데이터가 쌓일수록 ML이 개인화되고, 추천과 피드백이 정교해진다.
```

---

## 2. 핵심 설계 원칙 (절대 변경 금지)

| # | 원칙 |
|---|------|
| 1 | `hp / hunger / mood` 수치는 사용자에게 **절대 직접 노출 금지** — 이미지+대사로만 표현 |
| 2 | 날씨는 별도 알림 없음 — 기상 시간에 이미지 자동 교체로만 전달 |
| 3 | 칼로리/영양소 수치는 "오늘 요약" 버튼 클릭 시 Ephemeral로만 확인 가능 |
| 4 | 이미지 파일명 소문자 고정 (`eat.png` O, `Eat.PNG` X) |

---

## 3. 기술 스택

| 분류 | 내용 |
|------|------|
| 언어 | Python 3.11+ |
| 디스코드 | discord.py 2.x (슬래시 커맨드 + View / Modal) |
| AI | OpenAI GPT-4o — 자연어 파싱, Vision(사진입력), 대사 생성, 칼로리 fallback |
| 영양 DB | 식품의약품안전처 식품영양성분 DB API — **칼로리 1순위 출처** |
| 날씨 | 기상청 공공데이터 API (초단기실황조회) |
| 미세먼지 | 에어코리아 API (PM10, PM2.5) |
| DB | Supabase (PostgreSQL) — psycopg2-binary, Session pooler |
| 스케줄러 | APScheduler (AsyncIOScheduler) |
| ML | scikit-learn (Ridge / RandomForest), pandas, numpy, Prophet |
| 칼로리 공식 | Mifflin-St Jeor BMR |
| 이미지 | NovelAI (NAI Diffusion Anime V3, 512×512) — 11종 고정 |
| 이메일 | Naver Mail IMAP (수신 모니터링) / SMTP (발신) |
| 음식 추천 (예정) | n8n 웹훅 연동 |

---

## 4. 환경변수 (.env)

```
# 먹구름봇 (오케스트레이터)
DISCORD_TOKEN              # 먹구름봇 토큰
TAMAGOTCHI_CHANNEL_ID      # #다마고치 채널 ID

# 전용 봇 토큰 (각 봇 프로세스에서 사용)
DISCORD_TOKEN_EMAIL        # 메일봇 토큰
DISCORD_TOKEN_MEAL         # 식사봇 토큰
DISCORD_TOKEN_WEATHER      # 날씨봇 토큰
DISCORD_TOKEN_WEIGHT       # 체중관리봇 토큰
DISCORD_TOKEN_DIARY        # 일기봇 토큰 (예정)
DISCORD_TOKEN_SCHEDULE     # 일정봇 토큰 (예정)

# API 키 (모든 봇 공유)
OPENAI_API_KEY             # OpenAI API 키
WEATHER_API_KEY            # 기상청 공공데이터 포털 인증키
AIR_API_KEY                # 에어코리아 API 키
FOOD_API_KEY               # 식약처 식품영양성분 DB API 키
DATABASE_URL               # Supabase Session pooler URL

# 추가 예정
N8N_FOOD_WEBHOOK_URL       # n8n 음식 추천 웹훅 URL
```

---

## 5. 봇 구조 (멀티봇 아키텍처 — v3.2~)

### 실행 봇 목록

| 봇 파일 | 역할 | 상태 | 토큰 |
|---------|------|------|------|
| `bot.py` | 먹구름봇 — 오케스트레이터 (자연어 GPT/ML 의도 분류, 설정, 온보딩) | ✅ 운영 | `DISCORD_TOKEN` |
| `bot_mail.py` | 메일봇 — IMAP 1분 폴링, 발신자 알림 | ✅ 운영 | `DISCORD_TOKEN_EMAIL` |
| `bot_meal.py` | 식사봇 — 사진 감지, 칼로리 분석 | ✅ 분리 완료 | `DISCORD_TOKEN_MEAL` |
| `bot_weather.py` | 날씨봇 — 기상청/에어코리아 스케줄 알림 | ✅ 분리 완료 | `DISCORD_TOKEN_WEATHER` |
| `bot_weight.py` | 체중관리봇 — 체중 기록, 목표 관리 (이후 점진적 기능 확장) | 🔄 skeleton | `DISCORD_TOKEN_WEIGHT` |
| `bot_diary.py` | 일기봇 — 감정 분석, 식사×감정 상관 데이터 | 📋 구상 단계 | `DISCORD_TOKEN_DIARY` |
| `bot_schedule.py` | 일정봇 — 일정 등록, 반복 패턴 학습 | 📋 구상 단계 | `DISCORD_TOKEN_SCHEDULE` |

> **모든 봇은 동일한 Supabase DB 공유** — 별도 IPC 없이 DB를 통해 상태 공유

### 봇 간 상태 공유 방식

```
식사 사진 대기 상태:
  [먹구름봇] 📸 버튼 클릭 → users.meal_waiting_until = NOW()+60s (DB 기록)
  [식사봇]   on_message → is_meal_waiting() DB 조회 → 사진 분석

날씨 알림:
  [날씨봇]   APScheduler → weather_thread_id or thread_id → 쓰레드에 embed 전송

체중 달성 알림:
  [먹구름봇] WeightInputModal → weight_thread_id or thread_id → embed 전송
```

---

## 6. 디스코드 채널 구조

### 현재 (v3.2)

```
서버
└── #다마고치 채널  (단일 공용 채널)
    ├── [고정 메시지] 시작하기 버튼
    │
    └── 쓰레드 (유저별, 온보딩 시 자동 생성, 모두 동일 채널에 혼재)
        ├── {캐릭터명}의 구름        — 메인 Embed + 버튼 5개
        ├── 🍽️ {이름}의 식사 기록   — 식사봇 전용
        ├── 🌤️ {이름}의 날씨        — 날씨봇 전용
        ├── ⚖️ {이름}의 체중관리    — 체중관리봇 전용
        └── 📧 {이름}의 메일함       — 메일봇 전용
```

### 목표 구조 (v4.0)

```
서버
├── #먹구름-시작  (공용 — 온보딩 진입점)
│
└── 📁 먹구름  (카테고리)
    ├── #유저A-채팅창  ← 유저A 전용 채널 (메인봇 자연어 대화)
    │   캐릭터 상태 Embed 고정 (버튼 없음)
    │   ├── 🍽️ A의-식사기록    — 식사봇
    │   ├── 🌤️ A의-날씨        — 날씨봇
    │   ├── ⚖️ A의-체중관리    — 체중관리봇
    │   ├── 📧 A의-메일함      — 메일봇
    │   ├── 📔 A의-일기장      — 일기봇 (v3.4~)
    │   └── 📅 A의-일정표      — 일정봇 (v3.5~)
    │
    └── #유저B-채팅창  (동일 구조)
```

> **변화 핵심**: 단일 채널+쓰레드 → 유저별 전용 채널+기능별 쓰레드  
> 메인봇 UX: 버튼 Embed → 자연어 대화, GPT/ML 의도 분류 → 전문봇 자동 트리거

---

## 7. 파일 구조

```
mukgoorm/
├── bot.py                  # 먹구름봇 (오케스트레이터) — Cog 로드, !setup, !소환
├── bot_mail.py             # 메일봇 — email_monitor 단독 로드
├── bot_meal.py             # 식사봇 — cogs.meal 단독 로드
├── bot_weather.py          # 날씨봇 — cogs.weather 단독 로드
├── bot_weight.py           # 체중관리봇 — 향후 cogs.weight 이전 예정
├── bot_diary.py            # 일기봇 — 구현 예정
├── bot_schedule.py         # 일정봇 — 구현 예정
│
├── cogs/                   # 기능 모듈 (Cog)
│   ├── onboarding.py       # 온보딩 — 전용 쓰레드 5개 자동 생성
│   ├── meal.py             # 식사봇용 — 사진 감지, DB 기반 대기 상태
│   ├── summary.py          # 하루 정리 — 먹구름봇에서 호출
│   ├── settings.py         # 설정 SubView (내정보/위치/시간/이메일)
│   ├── time_settings.py    # 시간 설정 Select Menu
│   ├── scheduler.py        # APScheduler — 식사 알림, 일일 판정, ML 재학습, 주간 리포트
│   ├── weather.py          # 날씨봇용 — 기상청/에어코리아, weather_thread_id 우선
│   ├── weight.py           # 체중 기록 Modal, weight_thread_id 우선
│   └── email_monitor.py    # 메일봇용 — IMAP 1분 폴링, 슬래시 커맨드 4종
│
├── utils/                  # 공통 유틸리티
│   ├── db.py               # PostgreSQL CRUD — 멀티봇 쓰레드 ID setter/getter 포함
│   ├── embed.py            # 메인 Embed + MainView — photo_btn DB 대기 상태 기록
│   ├── gpt.py              # OpenAI API 래퍼
│   ├── nutrition.py        # 식약처 API 래퍼
│   ├── image.py            # 이미지 선택 로직 (11종)
│   ├── ml.py               # 개인화 칼로리 보정 모델
│   ├── pattern.py          # 식습관 패턴 분석
│   ├── gpt_ml_bridge.py    # ML 결과 → GPT 브릿지
│   ├── badges.py           # 배지 7종 판정 로직
│   ├── mail.py             # IMAP 수신 / SMTP 발신 클라이언트
│   └── email_ui.py         # EmailSetupModal / SenderAddModal 공통 분리
│
├── docs/                   # 프로젝트 문서
│   ├── 01_OVERVIEW.md      # 개요, 기술스택, 버전 히스토리
│   ├── 02_FLOWS.md         # 기능별 흐름도
│   ├── 03_DATABASE.md      # DB 스키마
│   ├── 04_GAME_RULES.md    # 수치 변동 규칙
│   ├── 05_ML_MODULES.md    # ML 모듈 + 봇별 ML 로드맵
│   ├── 06_PROGRESS.md      # 진행 상황 / 버그 트래킹
│   ├── 07_NEXT_FEATURES.md # 다음 개발 계획
│   ├── 08_EMAIL.md         # 이메일 기능 상세
│   └── TEAM_OVERVIEW.md    # 이 문서
│
├── models/                 # ML 모델 저장소 (자동 생성)
│   └── calorie_model_{user_id}.pkl
│
├── requirements.txt
└── .env
```

---

## 8. DB 스키마 요약

### 현재 테이블

| 테이블 | 역할 |
|--------|------|
| `users` | 유저 설정, 신체정보, 목표, 스트릭, 배지, **전용 쓰레드 ID 6종**, `meal_waiting_until` |
| `tamagotchi` | 캐릭터 상태 (hp/hunger/mood, 현재 이미지, 마지막 식사 시각) |
| `meals` | 식사 기록 (음식명, 칼로리, 단백질, 탄수화물, 지방, 식이섬유) |
| `weight_log` | 체중 기록 (날짜별) |
| `weather_log` | 날씨 기록 (기온, 미세먼지, 선택 이미지) |
| `email_senders` | 유저별 등록 발신자 목록 (알림 필터) |
| `email_log` | 수신 이메일 로그 (ML 스팸 분류 학습 데이터) |

### users 테이블 주요 컬럼 (v3.2 기준)

| 컬럼 | 타입 | 역할 |
|------|------|------|
| `thread_id` | TEXT | 메인 쓰레드 ID (기존 fallback용) |
| `mail_thread_id` | TEXT | 메일봇 전용 쓰레드 |
| `meal_thread_id` | TEXT | 식사봇 전용 쓰레드 |
| `weather_thread_id` | TEXT | 날씨봇 전용 쓰레드 |
| `weight_thread_id` | TEXT | 체중관리봇 전용 쓰레드 |
| `meal_waiting_until` | TIMESTAMP | 사진 입력 대기 만료 시각 (봇 간 상태 공유) |

### 추가 예정 테이블

| 테이블 | 역할 | 시기 |
|--------|------|------|
| `diary_log` | 일기 기록 (내용, GPT 감정 태그, 강도) | 일기봇 구현 시 |
| `schedule_log` | 일정 기록 (제목, 날짜, 반복 여부) | 일정봇 구현 시 |

> **타임존 주의**: Supabase는 UTC 저장.
> 날짜 비교 쿼리는 `(recorded_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Seoul')::date = %s` 사용.

---

## 9. 주요 기능 흐름

### 9-1. 온보딩

```
!setup → #다마고치 채널에 [시작하기] 버튼 고정

[🐣 다마고치 시작하기] 클릭
  ├── 신규 유저 → OnboardingModal 표시
  └── 기존 유저
        ├── 쓰레드 살아있음 → 해당 쓰레드로 안내
        └── 쓰레드 없음 (삭제됨) → OnboardingModal 표시 (재등록, ML 데이터 보존)

OnboardingModal
  → Mifflin-St Jeor 공식으로 GPT가 일일 권장 칼로리 계산
  → users / tamagotchi UPSERT
  → 쓰레드 5개 자동 생성 (메인 / 식사 / 날씨 / 체중관리 / 메일함)
  → 메인 Embed 전송
```

### 9-2. 식사 입력

```
[🍽️ 식사 입력] 클릭 → 텍스트 / 사진 선택

텍스트 흐름 (먹구름봇):
  MealInputModal 제출
    → GPT: 날짜/끼니/음식명 자연어 파싱
    → 식약처 API: 칼로리/영양소 조회 (1순위)
    → 실패 시 GPT-4o: 칼로리/영양소 추정 (fallback)
    → ML 보정: 양 표현 패턴 + 개인화 모델
    → DB 저장 → 캐릭터 상태 갱신 → Embed 갱신

사진 흐름 (봇 간 협력):
  [사진으로 입력] 선택
    → 먹구름봇: users.meal_waiting_until = NOW()+60s (DB 기록)
    → 유저: 식사 전용 쓰레드에 사진 업로드
    → 식사봇: on_message → is_meal_waiting() DB 조회 → 감지
    → GPT-4o Vision: 음식 인식 + 칼로리 추정
    → 이후 텍스트와 동일
```

### 9-3. 스케줄러

| 시점 | 동작 |
|------|------|
| 기상 시간 (유저별) | 기상청+에어코리아 API → 날씨 이미지 교체 + 대사 생성 |
| 아침/점심/저녁 시간 (유저별) | 미입력 시 식사 알림 전송 |
| 매 1시간 | hunger 수치 자연 감소 |
| 매일 22:00 (유저별) | 오늘 칼로리 판정 → hp/mood 수치 조정 |
| 매주 일요일 03:00 | ML 모델 전체 유저 재학습 |
| 매주 일요일 08:00 | 주간 리포트 + 스트릭/배지 갱신 자동 발송 |

---

## 10. 캐릭터 이미지 시스템 (utils/image.py)

총 11종, 상태 수치 기반 자동 선택.

| 우선순위 | 조건 | 이미지 |
|---------|------|--------|
| 1 | 목표 체중 달성 | `cheer.png` |
| 2 | 식사 직후 3분 이내 | `eat.png` |
| 3 | hunger < 40 | `upset.png` |
| 4 | PM10>80 or PM2.5>35 | `wear mask.png` |
| 4 | 비/소나기 | `rainy.png` |
| 4 | 눈 | `snow.png` |
| 4 | 기온 ≥ 26°C | `hot.png` |
| 4 | 기온 ≤ 5°C | `warm.png` |
| 5 | hp<40 or mood<40 | `tired.png` |
| 5 | hp≥70, hunger≥70, mood≥70 | `smile.png` |
| 5 | 그 외 | `normal.png` |

---

## 11. ML 모듈 구조

```
utils/pattern.py     식습관 패턴 5종 분석
  └── 14일 데이터 → 요일별 과식 / 아침 결식 / 저녁 집중 / 주간 추이 / 연속 소식
  └── 결과를 GPT System Prompt에 자연어로 주입

utils/ml.py          개인화 칼로리 보정 모델
  ├── 즉시 보정 (항상 동작)
  │     "조금" ×0.7 / "반" ×0.5 / "많이" ×1.4 / "두 그릇" ×2.0 ...
  └── 개인화 모델 (30건+ 누적 시)
        Ridge vs RandomForest 교차검증 자동 선택
        → models/calorie_model_{user_id}.pkl
        → 매주 일요일 03:00 재학습

utils/gpt_ml_bridge.py   ML 결과 → GPT extra_context 브릿지
```

---

## 12. 배지 시스템 (v2.7~)

| 배지 ID | 이름 | 조건 |
|---------|------|------|
| `first_meal` | 첫 한 끼 | 첫 식사 기록 |
| `streak_3` | 3일 연속 | 3일 연속 3끼 기록 |
| `streak_7` | 일주일 기록왕 | 7일 연속 3끼 기록 |
| `streak_30` | 한 달 챔피언 | 30일 연속 3끼 기록 |
| `goal_achieved` | 목표 달성 | 목표 체중 도달 |
| `weight_loss_1` | 첫 감량 | 0.5kg 이상 감량 |
| `perfect_week` | 완벽한 한 주 | 7일간 목표 칼로리 ±10% 유지 |

---

## 13. 칼로리 분석 우선순위 (v2.8~)

```
1순위: 식약처 식품영양성분 DB API
  → 검색 성공 시 1회 제공량 기준 영양 수치 반환
  → 실패 시 None 반환 → 2순위로 넘어감

2순위: OpenAI GPT-4o (fallback)
  → 식약처 결과 없을 때만 호출

3순위: ML 보정 (항상 적용)
  → 양 표현 키워드 배율 적용
  → 30건+ 누적 시 개인화 모델 추가 보정
```

---

## 14. 전체 개발 로드맵

```
[완료] v1.0~v2.9
  온보딩, 식사 입력(텍스트/사진), 날씨/미세먼지, 체중 기록,
  ML 개인화, 스트릭/배지, 주간 리포트, 식약처 API 연동,
  UI 개편 (하루 정리 통합, 설정 하위 메뉴, 버튼 5개)

[완료] v3.0~v3.1 — 이메일 모니터링
  - 네이버 IMAP 1분 폴링 → 발신자 필터링 → Discord 알림
  - bot_mail.py 분리 (메일봇 독립)
  - 설정 내 EmailSubView (발신자 추가/목록/삭제/수정)

[완료] v3.2 — 멀티봇 분리 (현재)
  - bot_meal.py: cogs.meal 독립 — 사진 감지, DB 기반 대기 상태
  - bot_weather.py: cogs.weather 독립 — weather_thread_id 전용 알림
  - bot_weight.py: 향후 분리 준비 완료 (skeleton)
  - DB: meal/weather/weight_thread_id + meal_waiting_until 컬럼 추가
  - 온보딩: 전용 쓰레드 5개 자동 생성

[다음] v3.3 — 체중관리봇 분리 + n8n 음식 추천
  - bot_weight.py 완전 활성화 (cogs.weight 이전, 기능 추가 없이)
  - n8n 웹훅 URL 수령 후 음식 추천 연동

[다음] v3.4 — 일기봇 (bot_diary.py)
  - UX 흐름 구체화 후 구현
  - diary_log 테이블 생성
  - GPT 감정 분석 → DB 저장

[다음] v3.5 — 일정봇 (bot_schedule.py)
  - UX 흐름 구체화 후 구현
  - schedules 테이블 생성
  - APScheduler 알림

[장기] v4.0 — 채널 구조 전환 + 오케스트레이터
  - 유저별 전용 채널 + 기능봇 쓰레드 구조로 온보딩 전환
  - 버튼 Embed 폐기 → 자연어 대화 방식
  - GPT/ML 의도 분류 → 전문봇 자동 트리거
  - intent_log 데이터 축적 → ML 의도 분류기 점진적 전환 (비용 절감)
```

---

## 15. 현재 알려진 이슈 (P2 수준)

| # | 내용 | 비고 |
|---|------|------|
| 1 | 식사 여러 건 동시 입력 미지원 ("아침 시리얼, 점심 비빔밥" → 첫 번째만 인식) | Modal 1회 = 1건 구조 |
| 2 | 식약처에 없는 음식 (숫자/단위 포함) 검색 실패 → GPT fallback 처리 중 | 음식명 정제 로직 미구현 |
| 3 | ML 학습 레이블이 GPT 추정값 → 데이터 충분 시 실측 칼로리로 교체 필요 | GPT→ML 전환 시점 수정 예정 |
| 4 | `gpt_ml_bridge.generate_comment_with_pattern()` 시그니처 불일치 (데드코드) | 사용 전 수정 필요 |

---

## 16. 로컬 실행 방법

```bash
# 1. 의존성 설치
pip install -r requirements.txt

# 2. 환경변수 설정 (.env 작성)

# 3. 봇 실행 (각각 별도 터미널에서)
python bot.py          # 먹구름봇 (오케스트레이터)
python bot_mail.py     # 메일봇
python bot_meal.py     # 식사봇
python bot_weather.py  # 날씨봇

# 4. 디스코드 서버 초기 설정 (관리자 권한 필요, 최초 1회)
!setup
```

---

## 17. Git 브랜치 전략

```
main     ← 배포 브랜치 (안정 버전)
develop  ← 개발 브랜치 (모든 개발은 여기서)
```

기능 개발 → `develop` 커밋/푸시 → 검증 후 `main` 머지
