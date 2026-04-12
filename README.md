# 🌧️ 먹구름 (mukgoorm)

디스코드에서 동작하는 1인 1캐릭터 식습관 관리 봇.
음식을 입력하면 나만의 캐릭터에게 밥을 주는 행위로 연결되고,
**칼로리 관리와 날씨 정보를 수치가 아닌 캐릭터 이미지와 대사로 간접 전달**합니다.

---

## 📁 프로젝트 구조

```
mukgoorm/
├── bot.py                      # 먹구름 봇 진입점 (식사/날씨/설정)
├── bot_mail.py                 # 메일봇 진입점 (IMAP 1분 폴링 전용)
├── database.py                 # init_db 수동 실행용
├── cogs/
│   ├── onboarding.py           # 온보딩 Modal + 스레드 생성
│   ├── meal.py                 # 식사 입력 (텍스트 / GPT-4o Vision 사진)
│   ├── weather.py              # 날씨 연동 + wake_time 기반 이미지 교체
│   ├── summary.py              # 오늘 요약 (Ephemeral)
│   ├── settings.py             # 설정 변경 (이름/도시/목표체중/이메일)
│   ├── time_settings.py        # 시간 설정 Select Menu (2단계)
│   ├── scheduler.py            # APScheduler (칼로리 판정 / 식사 알림 / 스트릭·배지 / 주간 리포트)
│   ├── weight.py               # 체중 기록 + 달성률
│   └── email_monitor.py        # 메일봇 전용 — IMAP 폴링 + Discord 알림
├── utils/
│   ├── gpt.py                  # OpenAI GPT-4o 래퍼
│   ├── db.py                   # Supabase CRUD (7개 테이블)
│   ├── embed.py                # 메인 Embed UI + 버튼 + MealInputModal
│   ├── image.py                # 상태별 이미지 선택 로직 (11종)
│   ├── badges.py               # 도전과제 배지 7종 정의 + 달성 체크
│   ├── pattern.py              # 식습관 패턴 분석 (ML)
│   ├── ml.py                   # 칼로리 보정 모델 (ML)
│   ├── gpt_ml_bridge.py        # ML → GPT 브릿지
│   ├── email_ui.py             # 이메일 공통 Modal (EmailSetupModal, SenderAddModal)
│   ├── mail.py                 # 네이버 IMAP/SMTP 클라이언트
│   └── nutrition.py            # 식약처 식품영양성분 DB API
├── images/                     # 다마고치 이미지 11종
├── docs/
│   ├── CONTEXT.md              # 문서 인덱스
│   ├── 01_OVERVIEW.md          # 개요, 기술스택, 버전 히스토리
│   ├── 02_FLOWS.md             # 전체 기능 흐름
│   ├── 03_DATABASE.md          # DB 스키마 + CRUD 함수
│   ├── 04_GAME_RULES.md        # 수치 변화 + 이미지 규칙 + 스트릭/배지 규칙
│   ├── 05_ML_MODULES.md        # ML 모듈 설명
│   ├── 06_PROGRESS.md          # 진행 상황 + 버전 변경 내역
│   ├── 07_NEXT_FEATURES.md     # 다음 개발 계획
│   └── 08_EMAIL.md             # 이메일 모니터링 상세
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
`.env` 파일을 프로젝트 루트에 배치하세요.

### 3. 봇 실행 (터미널 2개)
```bash
# 터미널 1 — 먹구름 봇 (식사/날씨/설정)
python bot.py

# 터미널 2 — 메일봇 (이메일 1분 폴링)
python bot_mail.py
```

### 4. 디스코드 최초 설정
봇이 켜진 후, 관리자 계정으로 `#다마고치` 채널에서:
```
!setup
```
명령어 실행 → 고정 메시지 + 시작하기 버튼 생성

---

## ⚙️ 환경변수 (.env)

| 변수명 | 설명 |
|--------|------|
| `DISCORD_TOKEN` | 먹구름 봇 토큰 |
| `DISCORD_TOKEN_EMAIL` | 메일봇 토큰 |
| `OPENAI_API_KEY` | OpenAI API 키 |
| `WEATHER_API_KEY` | 기상청 공공데이터 포털 인증키 |
| `AIR_API_KEY` | 에어코리아 API 키 (미세먼지) |
| `FOOD_API_KEY` | 식약처 식품영양성분 DB API 키 |
| `DATABASE_URL` | Supabase Session pooler URL (`postgresql://...`) |
| `TAMAGOTCHI_CHANNEL_ID` | `#다마고치` 채널 ID |

---

## 🛠️ 기술 스택

- **Python 3.11+**
- **discord.py 2.x** — 디스코드 봇
- **OpenAI GPT-4o** — 칼로리 분석 / Vision / 대사 생성 / 이메일 요약
- **Supabase (PostgreSQL)** — 클라우드 DB (psycopg2-binary)
- **APScheduler** — 날씨 교체 / 칼로리 자동 판정 / 식사 알림 / 이메일 폴링 / 주간 리포트
- **기상청 공공데이터 API** — 날씨 정보
- **에어코리아 API** — 미세먼지 정보
- **식약처 식품영양성분 DB API** — 공식 영양 정보
- **네이버 IMAP/SMTP** — 이메일 모니터링
- **scikit-learn / pandas** — ML 칼로리 보정 + 식습관 패턴 분석

---

## 🤖 멀티봇 구조

```
[먹구름 봇]              [메일봇]
식사 / 날씨 / 설정        IMAP 1분 폴링
이메일 설정 UI            Discord 스레드 알림
       ↓                        ↓
      ┌──────────────────────────┐
      │      Supabase DB (공유)  │
      └──────────────────────────┘
```

---

## 🎮 메인 Embed 버튼

| Row | 버튼 | 동작 |
|-----|------|------|
| 0 | 🍽️ 식사 입력 | 텍스트/사진 선택 → GPT 분석 + ML 칼로리 보정 |
| 0 | 📊 오늘 요약 | 칼로리/탄단지/끼니별 내역 Ephemeral |
| 0 | 📅 오늘 일정 | 목표칼로리/체중현황/식사시간/날씨 Ephemeral |
| 1 | ⚙️ 설정 변경 | 이름/도시/목표체중/이메일 하위 메뉴 |
| 1 | ⏰ 시간 설정 | 기상/식사 알림 시간 Select Menu (2단계) |
| 1 | ⚖️ 체중 기록 | 체중 입력 → 달성률 + GPT 반응 |

---

## 📧 이메일 모니터링

| 항목 | 내용 |
|------|------|
| 폴링 간격 | 1분 (메일봇 전용 이벤트 루프) |
| 지원 메일 | 네이버 메일 (IMAP SSL) |
| 알림 조건 | 등록된 발신자 + 스팸 키워드 미포함 |
| 요약 방식 | 본문 ≤200자 → 원문 그대로 / >200자 → GPT 요약 |
| 표시 정보 | 보낸 사람, 📅 발송 일시, 제목, 요약 |

상세: [`docs/08_EMAIL.md`](docs/08_EMAIL.md)

---

## 🏅 스케줄러 동작 요약

| 시각 | 담당 | 동작 |
|------|------|------|
| 매 1분 | 메일봇 | IMAP 폴링 → 새 메일 Discord 알림 |
| 매일 식사시간 -30분 | 먹구름 | 스레드에 배고픔 예고 메시지 |
| 매일 식사시간 정각 | 먹구름 | 미입력 시 upset.png + GPT 대사 |
| 매일 식사시간 +1시간 | 먹구름 | 미입력 시 추가 대사 |
| 매 시간 정각 | 먹구름 | hunger -5 (전체 유저) |
| 매일 22:00 | 먹구름 | 하루 칼로리 판정 + 스트릭 + 배지 체크 |
| 매주 일요일 03:00 | 먹구름 | ML 칼로리 보정 모델 재학습 |
| 매주 일요일 08:00 | 먹구름 | 주간 리포트 |

---

## 🏅 도전과제 배지 (7종)

| 배지 | 조건 |
|------|------|
| 🍽️ 첫 끼니 | 첫 번째 식사 기록 |
| 🔥 3일 연속 | 3일 연속 식사 기록 |
| 🌟 일주일 달인 | 7일 연속 |
| 👑 한 달 챔피언 | 30일 연속 |
| 🎯 목표 달성 10회 | 목표 칼로리 90% 이상 달성일 10일 |
| 📸 사진 마스터 | 사진 입력 10회 |
| 🌅 아침형 인간 | 아침 기록 7회 |

배지 달성 시 골드 Embed 전송 + 메인 이미지 `cheer.png` 갱신.

---

## 🖼️ 다마고치 이미지 목록 (11종)

| 이미지 | 표시 조건 | 우선순위 |
|--------|-----------|---------|
| `cheer.png` | 목표 체중 달성 / 배지 획득 | 1 |
| `eat.png` | 식사 입력 직후 3분 이내 | 2 |
| `upset.png` | hunger < 40 (배고픔) | 3 |
| `wear mask.png` | PM10 > 80 또는 PM2.5 > 35 | 4 |
| `rainy.png` | 비/소나기 | 4 |
| `snow.png` | 눈 | 4 |
| `hot.png` | 기온 ≥ 26°C | 4 |
| `warm.png` | 기온 ≤ 5°C | 4 |
| `tired.png` | hp < 40 또는 mood < 40 | 5 |
| `smile.png` | hp ≥ 70, hunger ≥ 70, mood ≥ 70 | 5 |
| `normal.png` | 기본값 | 5 |

---

## 📋 버전

현재 버전: **v3.1** (2026-04-13)
전체 변경 이력: [`docs/06_PROGRESS.md`](docs/06_PROGRESS.md)
이메일 기능 상세: [`docs/08_EMAIL.md`](docs/08_EMAIL.md)
다음 개발 계획: [`docs/07_NEXT_FEATURES.md`](docs/07_NEXT_FEATURES.md)

---

## 📖 상세 문서

프로젝트 상세 문서는 [`docs/CONTEXT.md`](docs/CONTEXT.md)를 참고하세요.
