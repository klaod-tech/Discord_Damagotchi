# 🌧️ 먹구름 (mukgoorm)

디스코드에서 동작하는 1인 1캐릭터 라이프스타일 관리 봇.  
음식을 입력하면 나만의 캐릭터에게 밥을 주는 행위로 연결되고,  
**칼로리·날씨·감정 정보를 수치가 아닌 캐릭터 이미지와 대사로 간접 전달**합니다.

> 현재 버전: **v3.2** | 개발 브랜치: `develop`

---

## 🤖 멀티봇 구조 (v3.2)

기능별로 봇과 스레드를 1:1로 분리. 모든 봇은 **동일한 Supabase DB를 공유**하며 독립 이벤트 루프에서 동작합니다.

```
Discord 서버
└── #다마고치 채널
    └── 쓰레드 (유저별, 온보딩 시 5개 자동 생성)
        ├── {이름}의 구름       ← bot.py         오케스트레이터 (버튼 허브, 설정, 온보딩)
        ├── 🍽️ {이름}의 식사   ← bot_meal.py    사진 감지, 칼로리 분석
        ├── 🌤️ {이름}의 날씨   ← bot_weather.py 기상청/에어코리아 스케줄 알림
        ├── ⚖️ {이름}의 체중   ← bot_weight.py  체중 기록 (skeleton)
        └── 📧 {이름}의 메일함 ← bot_mail.py    IMAP 1분 폴링, 발신자 알림

Supabase DB (전체 공유 — HTTP IPC 없이 DB가 단일 진실 공급원)
```

---

## 📁 프로젝트 구조

```
mukgoorm/
├── bot.py                  # 먹구름봇 — 오케스트레이터 (Cog 6개 로드)
├── bot_mail.py             # 메일봇 — email_monitor 단독 로드
├── bot_meal.py             # 식사봇 — cogs.meal 단독 로드
├── bot_weather.py          # 날씨봇 — cogs.weather 단독 로드
├── bot_weight.py           # 체중관리봇 — skeleton (향후 cogs.weight 이전)
│
├── cogs/
│   ├── onboarding.py       # 온보딩 Modal + 전용 쓰레드 5개 자동 생성
│   ├── meal.py             # 식사봇용 — 사진 감지, DB 기반 대기 상태
│   ├── summary.py          # 하루 정리 (칼로리/탄단지/끼니/GPT 코멘트)
│   ├── settings.py         # SettingsSubView (내 정보/위치/시간/이메일)
│   ├── time_settings.py    # 시간 설정 Select Menu 2단계
│   ├── scheduler.py        # APScheduler — 식사 알림, 일일 판정, ML 재학습, 주간 리포트
│   ├── weather.py          # 날씨봇용 — 기상청/에어코리아, weather_thread_id 우선
│   ├── weight.py           # 체중 기록 Modal, weight_thread_id 우선
│   └── email_monitor.py    # 메일봇용 — IMAP 1분 폴링, 슬래시 커맨드 4종
│
├── utils/
│   ├── db.py               # Supabase CRUD (7개 테이블, 멀티봇 thread setter/getter)
│   ├── embed.py            # 메인 Embed + MainView (5개 버튼) + MealInputModal
│   ├── gpt.py              # OpenAI GPT-4o 래퍼
│   ├── nutrition.py        # 식약처 식품영양성분 DB API (칼로리 1순위)
│   ├── image.py            # 이미지 선택 로직 (11종, 우선순위 5단계)
│   ├── ml.py               # 개인화 칼로리 보정 (양 표현 즉시 + Ridge/RF 모델)
│   ├── pattern.py          # 식습관 패턴 분석 (5가지 패턴 탐지)
│   ├── gpt_ml_bridge.py    # ML 결과 → GPT System Prompt 브릿지
│   ├── badges.py           # 배지 7종 정의 + check_new_badges()
│   ├── mail.py             # 네이버 IMAP/SMTP 클라이언트
│   └── email_ui.py         # EmailSetupModal / SenderAddModal 공통 분리
│
├── images/                 # 캐릭터 이미지 11종
├── models/                 # ML 모델 저장소 (자동 생성, calorie_model_{user_id}.pkl)
├── docs/                   # 프로젝트 문서 (docs/CONTEXT.md 참고)
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
프로젝트 루트에 `.env` 파일 작성 (아래 환경변수 섹션 참고)

### 3. 봇 실행 (터미널 4개)
```bash
python bot.py          # 먹구름봇 — 온보딩, 설정, 하루 정리, 체중
python bot_mail.py     # 메일봇   — IMAP 1분 폴링, 이메일 알림
python bot_meal.py     # 식사봇   — 사진 감지, 칼로리 분석
python bot_weather.py  # 날씨봇   — 기상청/에어코리아 스케줄 알림
```

### 4. 디스코드 최초 설정
봇이 켜진 후, 관리자 계정으로 `#다마고치` 채널에서:
```
!setup
```
→ 고정 메시지 + `🐣 다마고치 시작하기` 버튼 생성

---

## ⚙️ 환경변수 (.env)

| 변수명 | 설명 |
|--------|------|
| `DISCORD_TOKEN` | 먹구름봇 토큰 |
| `DISCORD_TOKEN_EMAIL` | 메일봇 토큰 |
| `DISCORD_TOKEN_MEAL` | 식사봇 토큰 |
| `DISCORD_TOKEN_WEATHER` | 날씨봇 토큰 |
| `DISCORD_TOKEN_WEIGHT` | 체중관리봇 토큰 |
| `OPENAI_API_KEY` | OpenAI API 키 |
| `WEATHER_API_KEY` | 기상청 공공데이터 포털 인증키 |
| `AIR_API_KEY` | 에어코리아 API 키 (미세먼지) |
| `FOOD_API_KEY` | 식약처 식품영양성분 DB API 키 |
| `DATABASE_URL` | Supabase Session pooler URL (`postgresql://...`) |
| `TAMAGOTCHI_CHANNEL_ID` | `#다마고치` 채널 ID |

> 이메일 수신용 네이버 계정(`naver_email` / `naver_app_pw`)은 .env가 아닌  
> 유저가 디스코드 버튼(✏️ 이메일 수정)으로 직접 입력 → Supabase `users` 테이블에 per-user 저장.

---

## 🛠️ 기술 스택

| 분류 | 내용 |
|------|------|
| 언어 | Python 3.11+ |
| 디스코드 | discord.py 2.x (슬래시 커맨드 + View / Modal) |
| AI | OpenAI GPT-4o — 자연어 파싱, Vision(사진 입력), 대사 생성, fallback |
| 영양 DB | 식품의약품안전처 식품영양성분 DB API — **칼로리 1순위** |
| 날씨 | 기상청 공공데이터 API (초단기실황조회) |
| 미세먼지 | 에어코리아 API (PM10, PM2.5) |
| DB | Supabase (PostgreSQL) — psycopg2-binary, Session pooler |
| 스케줄러 | APScheduler (AsyncIOScheduler) |
| ML | scikit-learn (Ridge / RandomForest), pandas, numpy |
| 칼로리 공식 | Mifflin-St Jeor BMR |
| 이미지 | NovelAI (NAI Diffusion Anime V3, 512×512) — 11종 고정 |
| 이메일 | 네이버 IMAP (수신 모니터링) / SMTP (발신 예정) |
| 음식 추천 | n8n 웹훅 연동 (준비 중) |

---

## 🎮 메인 Embed 버튼 (v2.9~)

```
[다마고치 이미지 — 파일 첨부로 크게 표시]
──────────────────────────────────────────
[Embed] {tamagotchi_name}의 하루 · "GPT 대사"

Row 0: [ 🍽️ 식사 입력 ] [ 📋 하루 정리 ] [ 🍜 뭐 먹고 싶어? ]
Row 1: [ ⚙️ 설정 ]      [ ⚖️ 체중 기록 ]
```

| 버튼 | 동작 |
|------|------|
| 🍽️ 식사 입력 | 텍스트 / 사진 선택 → GPT 분석 + 식약처 API + ML 칼로리 보정 |
| 📋 하루 정리 | 칼로리 현황·탄단지·끼니별·체중·날씨·식사 알림 시간·GPT 한마디 통합 Ephemeral |
| 🍜 뭐 먹고 싶어? | "준비 중" (n8n 웹훅 연동 예정) |
| ⚙️ 설정 | 하위 메뉴: 내 정보 / 위치 설정 / 시간 설정 / 이메일 설정 |
| ⚖️ 체중 기록 | 체중 입력 → 달성률 바 + 목표 달성 판정 → Embed 갱신 |

---

## 📊 칼로리 분석 우선순위

```
1순위: 식약처 식품영양성분 DB API  → 성공 시 공식 영양 수치 반환
         ↓ 실패 시
2순위: OpenAI GPT-4o fallback     → 추정 칼로리/영양소 반환
         ↓ 항상 적용
3순위: ML 보정 (get_corrected_calories)
         - 즉시: 양 표현 키워드 배율 적용 (조금 ×0.7 / 많이 ×1.4 / 두 그릇 ×2.0 ...)
         - 30건+ 누적 시: Ridge / RandomForest 개인화 모델 추가 보정
```

---

## 🖼️ 캐릭터 이미지 (11종, 우선순위 순)

| 파일명 | 트리거 조건 | 우선순위 |
|--------|-----------|---------|
| `cheer.png` | 목표 체중 달성 / 배지 획득 | 1 |
| `eat.png` | 식사 입력 직후 3분 이내 | 2 |
| `upset.png` | hunger < 40 (배고픔) | 3 |
| `wear mask.png` | PM10 > 80 OR PM2.5 > 35 | 4 |
| `rainy.png` | 비 / 소나기 | 4 |
| `snow.png` | 눈 | 4 |
| `hot.png` | 기온 ≥ 26°C | 4 |
| `warm.png` | 기온 ≤ 5°C | 4 |
| `tired.png` | hp < 40 OR mood < 40 | 5 |
| `smile.png` | hp ≥ 70, hunger ≥ 70, mood ≥ 70 | 5 |
| `normal.png` | 기본값 | 5 |

> hp / hunger / mood 수치는 사용자에게 **절대 직접 노출 금지** — 이미지+대사로만 전달.

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

## ⏰ 스케줄러 동작 요약

| 시각 | 담당 봇 | 동작 |
|------|--------|------|
| 매 1분 | bot_mail.py | IMAP 폴링 → 새 메일 Discord 스레드 알림 |
| 식사시간 -30분 | bot.py | 배고픔 예고 메시지 |
| 식사시간 정각 | bot.py | 미입력 시 upset.png + GPT 대사 |
| 식사시간 +1시간 | bot.py | 미입력 시 추가 GPT 대사 |
| 매 시간 정각 | bot.py | hunger -5 (전체 유저) |
| 매일 22:00 | bot.py | 칼로리 판정 + 스트릭 + 배지 체크 |
| 매주 일요일 03:00 | bot.py | ML 칼로리 보정 모델 전체 재학습 |
| 매주 일요일 08:00 | bot.py | 주간 리포트 (칼로리 평균/스트릭/배지 요약) |

---

## 📧 이메일 모니터링 (v3.1)

| 항목 | 내용 |
|------|------|
| 폴링 간격 | 1분 (bot_mail.py 독립 이벤트 루프) |
| 지원 메일 | 네이버 IMAP SSL (imap.naver.com:993) |
| 스팸 필터 | 1단계: INBOX 한정 / 2단계: 제목 키워드 / 3단계: 발신자 화이트리스트 |
| 본문 처리 | ≤200자 → 원문 그대로 / >200자 → GPT-4o 3줄 요약 |
| 표시 정보 | 보낸 사람(별명), 📅 발송 일시(KST), 제목, 요약 |

**UI 접근 경로**: `⚙️ 설정 → 📧 이메일 설정`  
**슬래시 커맨드** (메일봇): `/이메일설정` `/발신자추가` `/발신자목록` `/발신자삭제`

상세: [`docs/08_EMAIL.md`](docs/08_EMAIL.md)

---

## 🗄️ DB 테이블 요약

| 테이블 | 역할 |
|--------|------|
| `users` | 유저 설정, 신체정보, 목표, 스트릭, 배지, 전용 스레드 ID 4종, `meal_waiting_until` |
| `tamagotchi` | 캐릭터 상태 (hp/hunger/mood, 현재 이미지, 마지막 식사 시각) |
| `meals` | 식사 기록 (음식명, 칼로리, 탄단지, 식이섬유, 입력 방식) |
| `weight_log` | 체중 기록 (날짜별) |
| `weather_log` | 날씨 기록 (기온, 미세먼지, 선택 이미지) |
| `email_senders` | 유저별 등록 발신자 목록 |
| `email_log` | 수신 이메일 로그 (ML 스팸 분류 학습 데이터) |

> **타임존 주의**: Supabase는 UTC 저장. 날짜 비교는 반드시 UTC → KST 이중 변환 사용.

---

## 🔮 개발 로드맵

| 버전 | 상태 | 내용 |
|------|------|------|
| v1.0~v2.9 | ✅ 완료 | 온보딩, 식사 입력(텍스트/사진), 날씨, 체중, ML, 스트릭/배지, 주간 리포트, 식약처 API |
| v3.0~v3.1 | ✅ 완료 | 이메일 모니터링 (bot_mail.py 분리) |
| v3.2 | ✅ 완료 (현재) | 멀티봇 분리 (식사봇 / 날씨봇 / 체중관리봇), 온보딩 시 전용 스레드 5개 자동 생성 |
| v3.3 | 📋 예정 | 일기봇 (bot_diary.py) — 감정 분석, 식사×감정 데이터 누적 |
| v3.4 | 📋 예정 | 일정봇 (bot_schedule.py) — 일정 등록, 알림, 반복 패턴 ML |
| v4.0 | 🔭 장기 | 오케스트레이터 고도화 — 자연어 발화 → 관련 봇 자동 트리거 |

---

## 📖 상세 문서

| 문서 | 내용 |
|------|------|
| [`docs/CONTEXT.md`](docs/CONTEXT.md) | 전체 문서 인덱스 |
| [`docs/TEAM_OVERVIEW.md`](docs/TEAM_OVERVIEW.md) | 팀 기술 개요서 (신규 팀원 온보딩 시작점) |
| [`docs/06_PROGRESS.md`](docs/06_PROGRESS.md) | 구현 현황 + 버그 + 버전 변경 내역 |
| [`docs/07_NEXT_FEATURES.md`](docs/07_NEXT_FEATURES.md) | 멀티봇 로드맵 + n8n 음식 추천 설계 |
| [`docs/bots/00_INDEX.md`](docs/bots/00_INDEX.md) | 봇별 개발 문서 인덱스 (Claude 세션 시작 가이드) |
