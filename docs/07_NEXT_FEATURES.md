# 개발 로드맵 및 멀티봇 아키텍처

> last_updated: 2026-04-13 | 현재 버전: v3.2

---

## 핵심 설계 원칙 — 봇 × 스레드 1:1 구조

기능이 늘어날수록 하나의 봇에 모든 기능을 넣으면:
- 봇 재시작 시 전체 기능 영향
- 코드 결합도 증가 → 유지보수 어려움
- Discord API Rate Limit 집중

**해결책**: 기능별로 봇과 스레드를 1:1로 분리.  
모든 봇은 **동일한 Supabase DB를 공유**하며 독립적인 이벤트 루프에서 동작.

---

## 현재 구조 (v3.2)

```
Discord 서버
├── #다마고치 채널 (단일 공용 채널)
│   └── 쓰레드 (유저별, 모두 동일 채널에 혼재)
│       ├── {이름}의 구름       ← bot.py (먹구름봇) — 버튼 Embed 허브, 설정, 온보딩
│       ├── 🍽️ {이름}의 식사   ← bot_meal.py (식사봇) — 사진 감지, 칼로리 분석
│       ├── 🌤️ {이름}의 날씨   ← bot_weather.py (날씨봇) — 기상청/에어코리아
│       ├── ⚖️ {이름}의 체중   ← bot_weight.py (skeleton)
│       └── 📧 {이름}의 메일함 ← bot_mail.py (메일봇) — IMAP 폴링
│
└── Supabase DB (공유)
```

### 실행

```bash
python bot.py         # 먹구름봇 — 온보딩/설정/하루정리/체중
python bot_mail.py    # 메일봇   — IMAP 폴링/이메일 알림
python bot_meal.py    # 식사봇   — 사진 감지/칼로리 분석
python bot_weather.py # 날씨봇   — 기상청/에어코리아 스케줄
```

### 환경변수

| 변수명 | 봇 | 설명 |
|--------|-----|------|
| `DISCORD_TOKEN` | bot.py | 먹구름봇 토큰 |
| `DISCORD_TOKEN_EMAIL` | bot_mail.py | 메일봇 토큰 |
| `DISCORD_TOKEN_MEAL` | bot_meal.py | 식사봇 토큰 |
| `DISCORD_TOKEN_WEATHER` | bot_weather.py | 날씨봇 토큰 |
| `DISCORD_TOKEN_WEIGHT` | bot_weight.py | 체중관리봇 토큰 |

---

## 오케스트레이터 아키텍처 (목표 설계)

먹구름봇(bot.py)은 #먹구름 채널에서 유저 메시지를 수신하고,
GPT로 의도를 파악한 뒤 관련 전문봇들에게 작업을 위임하는 **오케스트레이터** 역할을 담당한다.

### 흐름

```
유저: "나 오늘 광교산 가서 샌드위치 먹었어"
  ↓
먹구름봇 (오케스트레이터)
  → GPT 의도 분석
      - 식사 언급 → 식사봇 트리거
      - 일상 기록 → 일기봇 트리거
      - 칼로리 관련 → 체중관리봇 트리거
  ↓
  ├── bot_meal.py  → 식사 스레드에 "샌드위치" 분석 결과 알림
  ├── bot_diary.py → 일기 스레드에 오늘 기록 저장 유도
  └── bot_weight.py → 체중관리 스레드에 칼로리 반영
```

```
유저: "나 내일 제주도 가서 해수욕장 갔다 올거야"
  ↓
먹구름봇 (오케스트레이터)
  → GPT 의도 분석
      - 미래 일정 → 일정봇 트리거
      - 지역 언급 → 날씨봇 트리거
  ↓
  ├── bot_schedule.py → 일정 스레드에 "제주도 해수욕장" 일정 등록 유도
  └── bot_weather.py  → 날씨 스레드에 제주도 내일 날씨 미리 조회
```

### 봇 간 통신 방식 (설계 예정)

전문봇들은 독립적인 프로세스라 직접 함수 호출 불가.
아래 방식 중 하나로 구현 예정:

| 방식 | 설명 | 장단점 |
|------|------|--------|
| **Supabase DB 태스크 큐** | 오케스트레이터가 `task_queue` 테이블에 작업 삽입 → 전문봇이 주기적으로 폴링 | 단순/안정적, 실시간성 낮음 |
| **Discord 메시지 신호** | 오케스트레이터가 봇 전용 채널에 신호 메시지 → 전문봇이 `on_message` 감지 | 실시간, Discord 의존적 |
| **내부 HTTP API** | 각 봇이 로컬 HTTP 서버 노출 → 오케스트레이터가 POST 호출 | 빠름, 배포 시 포트 관리 필요 |

> 현재 권장: **Supabase DB 태스크 큐** — 봇이 늘어나도 통신 구조가 단순하게 유지됨.

---

## 목표 구조 (v4.0+)

```
Discord 서버
├── #먹구름-시작  (공용 — 온보딩 진입점)
│
└── 📁 먹구름  (카테고리)
    │
    ├── #유저A-채팅창  ← 유저A 전용 채널 (메인봇 자연어 대화 공간)
    │   │  캐릭터 상태 Embed 고정
    │   │
    │   │  유저A: "나 오늘 광교산에서 샌드위치 먹었어"
    │   │    ↓ GPT/ML 의도 분류
    │   │  먹구름봇 → 식사봇 + 일기봇 동시 트리거 (task_queue)
    │   │
    │   ├── 🍽️ A의-식사기록   ← bot_meal.py — 식사 입력/칼로리 분석
    │   ├── 🌤️ A의-날씨       ← bot_weather.py — 날씨/미세먼지 알림
    │   ├── ⚖️ A의-체중관리   ← bot_weight.py — 체중 기록/목표/추이
    │   ├── 📧 A의-메일함     ← bot_mail.py — 이메일 알림
    │   ├── 📔 A의-일기장     ← bot_diary.py — 일기/감정 분석 (v3.4~)
    │   └── 📅 A의-일정표     ← bot_schedule.py — 일정/알림 (v3.5~)
    │
    └── #유저B-채팅창  ← 유저B 전용 채널 (동일 구조)

└── Supabase DB (전체 공유)
```

> **먹구름봇 역할**: 버튼 허브 → **자연어 오케스트레이터**로 전환.  
> GPT(초기) → ML(50건+ 누적 후) 의도 분류로 전문봇 자동 트리거.  
> intent_log 테이블에 학습 데이터 축적 → ML 개인화로 점진적 GPT 비용 절감.

---

## 기능별 구현 현황

| 기능 | 봇 | 스레드 | 상태 |
|------|-----|--------|------|
| 온보딩 / 설정 / 전체 조율 | bot.py | — | ✅ 운영 중 |
| 식사 입력 / 칼로리 분석 | bot_meal.py | 식사 기록 | ✅ v3.2 분리 완료 |
| 날씨 / 미세먼지 알림 | bot_weather.py | 날씨 | ✅ v3.2 분리 완료 |
| 체중 기록 + 목표 관리 | bot_weight.py | 체중관리 | 🔄 skeleton (분리 예정) |
| 스트릭 / 배지 / 주간 리포트 | bot.py | — | ✅ 구현 완료 |
| 이메일 모니터링 | bot_mail.py | 메일함 | ✅ v3.1 완료 |
| 음식 추천 (n8n) | bot.py | — | 🔧 준비 중 (n8n 연동 대기) |
| 일기 / 감정 분석 | bot_diary.py | 일기장 | 📋 설계 완료, 구현 예정 |
| 일정 / 캘린더 / 알림 | bot_schedule.py | 일정표 | 📋 설계 완료, 구현 예정 |

---

## Phase 3 — 음식 추천 (n8n 연동)

> 현재: 버튼 표시 ("준비 중"), n8n 연동 대기 중

### 구조

```
[🍜 뭐 먹고 싶어?] 클릭
  → bot.py → POST n8n 웹훅 URL
    payload: 위치 + 오늘 식사 + 이번 주 식사 + 남은 칼로리
  → n8n 워크플로우 (팀원 담당)
    → 외부 음식/식당 API
    → 추천 결과 생성
  → Discord Embed (Ephemeral)
```

### 웹훅 페이로드

```json
{
  "user_id": "123456789",
  "location": { "city": "서울", "address": "마포구 합정동" },
  "remaining_calories": 620,
  "today_calories": 1380,
  "daily_cal_target": 2000,
  "today_meals": ["비빔밥", "아메리카노"],
  "weekly_meals": ["비빔밥", "삼겹살", "라면", "치킨", "된장찌개"]
}
```

### n8n 응답 포맷 (미정 — 팀원 확정 후 구현)

```
[ ] 응답 Content-Type: application/json
[ ] 추천 결과 JSON 구조
[ ] 추천 개수 (1개? 3개?)
[ ] 실패 시 에러 응답 형식
```

### 환경변수 추가 필요

```
N8N_FOOD_WEBHOOK_URL   # n8n 음식 추천 웹훅 URL
```

### 위치 정보 상세화 (미결)

현재 `users.city`는 시 단위 ("서울"). 추천 정확도를 위해 구/동 단위 필요.

**권장 옵션 B: `address` 필드 별도 추가**
- `city` — 날씨 API 전용 (기존 유지)
- `address` — 음식 추천 전용 (신규, nullable)
- 날씨 코드 무변경, 기존 유저 영향 없음

---

## Phase 4 — 일기봇 (bot_diary.py)

> 상태: 설계 완료, 구현 예정  
> 상세 문서: [`docs/bots/diary/`](bots/diary/) — OVERVIEW / FLOWS / DB / IMPLEMENTATION / ML

### 개요

유저가 하루 일기를 작성하면 GPT가 감정을 분석하고, ML이 패턴을 학습하여
장기 감정 추이를 트래킹한다.

### 예상 기능

| 기능 | 설명 |
|------|------|
| 일기 작성 | 텍스트 입력 Modal → `diary_log` 저장 |
| 감정 분석 | GPT → 긍정/부정/중립 + 핵심 감정 키워드 |
| 감정 추이 | 주간/월간 감정 변화 Embed |
| ML 연동 | 감정 패턴 → 식사 패턴과 교차 분석 (장기 목표) |

### 필요 DB

```sql
diary_log (
  log_id      SERIAL PRIMARY KEY,
  user_id     TEXT,
  content     TEXT,       -- 일기 원문
  emotion     TEXT,       -- GPT 분석 감정 (긍정/부정/중립)
  keywords    TEXT,       -- 감정 키워드 JSON
  written_at  TIMESTAMP
)
```

### 스레드

```
{이름}의 일기장 — bot_diary.py 전용
  이미지: 📓 일기장 아이콘
  자동 archive: 10080분 (7일)
```

---

## Phase 5 — 일정봇 (bot_schedule.py)

> 상태: 설계 완료, 구현 예정  
> 상세 문서: [`docs/bots/schedule/`](bots/schedule/) — OVERVIEW / FLOWS / DB / IMPLEMENTATION / ML

### 개요

유저가 할일/일정을 등록하면 지정 시간에 디스코드 알림을 보낸다.

### 예상 기능

| 기능 | 설명 |
|------|------|
| 일정 등록 | 날짜 + 시간 + 내용 Modal |
| 알림 | APScheduler → 지정 시간에 스레드 알림 |
| 일정 목록 | 오늘/이번 주 일정 조회 |
| 반복 일정 | 매일/매주 반복 옵션 |

### 필요 DB

```sql
schedules (
  schedule_id   SERIAL PRIMARY KEY,
  user_id       TEXT,
  title         TEXT,
  scheduled_at  TIMESTAMP,
  repeat_type   TEXT,   -- none | daily | weekly
  notified      BOOLEAN DEFAULT FALSE,
  created_at    TIMESTAMP
)
```

---

## 공유 모듈 전략

봇이 늘어날수록 공통 코드는 `utils/`에 집중화.

| 모듈 | 역할 | 사용 봇 |
|------|------|---------|
| `utils/db.py` | DB CRUD 전체 | 모든 봇 |
| `utils/gpt.py` | GPT 래퍼 | bot.py, bot_mail.py, bot_diary.py |
| `utils/email_ui.py` | 이메일 Modal 공유 | bot.py, bot_mail.py |
| `utils/mail.py` | IMAP/SMTP | bot_mail.py |
| `utils/badges.py` | 배지 로직 | bot.py |

---

## 미결 사항

```
n8n 연동 (Phase 3)
[ ] n8n 응답 포맷 확정 (팀원)
[ ] 위치 필드 address 컬럼 추가 결정
[ ] N8N_FOOD_WEBHOOK_URL 환경변수 등록

다음 봇 구현
[ ] bot_weight.py — cogs.weight 이전 + 체중 목표 동적 조정 통합
[ ] bot_diary.py  — 구현 코드: docs/bots/diary/IMPLEMENTATION.md
[ ] bot_schedule.py — 구현 코드: docs/bots/schedule/IMPLEMENTATION.md

배포
[ ] 호스팅 방식 결정 (Railway / Render / VPS — 4개 봇 프로세스 동시 배포)
[ ] .env → 플랫폼 시크릿 이전
```
