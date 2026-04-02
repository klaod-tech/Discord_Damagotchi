# 🐣 Discord AI 다마고치 봇

디스코드에서 동작하는 1인 1다마고치 봇.  
음식을 입력하면 다마고치에게 밥을 주는 행위로 연결되고,  
**칼로리 관리와 날씨 정보를 수치가 아닌 캐릭터 이미지와 대사로 간접 전달**합니다.

---

## 📁 프로젝트 구조

```
Discord_Damagotchi/
├── bot.py                      # 봇 메인 진입점 (8개 cog 로드)
├── cogs/
│   ├── onboarding.py           # 온보딩 Modal + 쓰레드 생성
│   ├── meal.py                 # 식사 입력 (사진 — GPT-4o Vision)
│   ├── weather.py              # 날씨 연동 + wake_time 기반 이미지 교체
│   ├── summary.py              # 오늘 요약 (Ephemeral)
│   ├── settings.py             # 설정 변경 (이름/도시/목표체중)
│   ├── time_settings.py        # 시간 설정 Select Menu (2단계)
│   ├── scheduler.py            # APScheduler (오후 10시 칼로리 자동 판정)
│   └── weight.py               # 체중 기록 + 달성률
├── utils/
│   ├── gpt.py                  # OpenAI GPT-4o 래퍼
│   ├── db.py                   # Supabase CRUD (5개 테이블)
│   ├── embed.py                # 메인 Embed UI + 6개 버튼 + MealInputModal
│   ├── image.py                # 상태별 이미지 선택 로직 (11종)
│   ├── pattern.py              # 식습관 패턴 분석 (ML)
│   ├── ml.py                   # 칼로리 보정 모델 (ML)
│   └── gpt_ml_bridge.py        # ML → GPT 브릿지
├── images/                     # 다마고치 이미지 11종
├── docs/                       # 프로젝트 문서
│   ├── CONTEXT.md              # 문서 인덱스 (협업자 시작점)
│   ├── 01_OVERVIEW.md          # 개요, 기술스택, 버전 히스토리
│   ├── 02_FLOWS.md             # 전체 기능 흐름
│   ├── 03_DATABASE.md          # DB 스키마 + CRUD 함수
│   ├── 04_GAME_RULES.md        # 수치 변화 + 이미지 규칙
│   ├── 05_ML_MODULES.md        # ML 모듈 설명
│   └── 06_PROGRESS.md          # 진행 상황 + 남은 작업
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
팀원에게 `.env` 파일을 받아 프로젝트 루트에 배치하세요.

### 3. 봇 실행
```bash
python bot.py
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
| `DISCORD_TOKEN` | 디스코드 봇 토큰 |
| `OPENAI_API_KEY` | OpenAI API 키 |
| `WEATHER_API_KEY` | 기상청 공공데이터 포털 인증키 |
| `AIR_API_KEY` | 에어코리아 API 키 (미세먼지) |
| `DATABASE_URL` | Supabase Session pooler URL (`postgresql://...`) |
| `TAMAGOTCHI_CHANNEL_ID` | `#다마고치` 채널 ID |

---

## 🛠️ 기술 스택

- **Python 3.11+**
- **discord.py 2.x** — 디스코드 봇
- **OpenAI GPT-4o** — 칼로리 분석 / Vision / 대사 생성
- **Supabase (PostgreSQL)** — 클라우드 DB (psycopg2-binary)
- **APScheduler** — 날씨 교체, 칼로리 자동 판정
- **기상청 공공데이터 API** — 날씨 정보
- **에어코리아 API** — 미세먼지 정보
- **scikit-learn / pandas** — ML 칼로리 보정 + 식습관 패턴 분석

---

## 🎮 메인 Embed 버튼 (6개, 2행)

| Row | 버튼 | 동작 |
|-----|------|------|
| 1 | 🍽️ 식사 입력 | 텍스트 자연어 입력 → GPT 분석 → DB 저장 |
| 1 | 📊 오늘 요약 | 칼로리/탄단지/끼니별 내역 Ephemeral |
| 1 | 📅 오늘 일정 | 목표칼로리/체중현황/식사시간/날씨 Ephemeral |
| 2 | ⚙️ 설정 변경 | 이름/도시/목표체중 수정 |
| 2 | ⏰ 시간 설정 | 기상/식사 알림 시간 Select Menu |
| 2 | ⚖️ 체중 기록 | 체중 입력 → 달성률 + GPT 반응 |

---

## 🖼️ 다마고치 이미지 목록 (11종)

| 이미지 | 표시 조건 | 우선순위 |
|--------|-----------|---------|
| `cheer.png` | 목표 체중 달성 | 1 |
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

## 📖 상세 문서

프로젝트 상세 문서는 [`docs/CONTEXT.md`](docs/CONTEXT.md)를 참고하세요.  
현재 진행 상황과 남은 작업은 [`docs/06_PROGRESS.md`](docs/06_PROGRESS.md)를 확인하세요.
