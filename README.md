# 🐣 Discord AI 다마고치 봇

디스코드에서 동작하는 1인 1다마고치 봇.  
음식을 입력하면 다마고치에게 밥을 주는 행위로 연결되고,  
**칼로리 관리와 날씨 정보를 수치가 아닌 캐릭터 이미지와 대사로 간접 전달**합니다.

---

## 📁 프로젝트 구조

```
Discord_Damagotchi/
├── bot.py                      # 봇 메인 진입점
├── cogs/
│   ├── onboarding.py           # 온보딩 + 쓰레드 생성
│   ├── meal.py                 # 식사 입력 (사진 — GPT Vision)
│   ├── weather.py              # 날씨 연동 + 이미지 교체
│   ├── summary.py              # 오늘 요약
│   ├── settings.py             # 설정 변경
│   ├── scheduler.py            # APScheduler (오후 10시 칼로리 판정)
│   └── weight.py               # 체중 기록
├── utils/
│   ├── gpt.py                  # OpenAI API 래퍼
│   ├── db.py                   # Supabase CRUD
│   ├── embed.py                # Embed UI + 식사 입력 Modal
│   ├── image.py                # 상태별 이미지 선택 로직
│   ├── pattern.py              # 식습관 패턴 분석 (ML)
│   ├── ml.py                   # 칼로리 보정 모델 (ML)
│   └── gpt_ml_bridge.py        # ML → GPT 브릿지
├── images/                     # 다마고치 이미지 (17종)
├── docs/                       # 프로젝트 문서
│   ├── CONTEXT.md              # 문서 인덱스 (협업자 시작점)
│   ├── 01_OVERVIEW.md
│   ├── 02_FLOWS.md
│   ├── 03_DATABASE.md
│   ├── 04_GAME_RULES.md
│   ├── 05_ML_MODULES.md
│   └── 06_PROGRESS.md
├── .env
└── requirements.txt
```

---

## 🚀 실행 방법

### 1. 패키지 설치
```bash
pip install -r requirements.txt
pip install psycopg2-binary
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
| `DATABASE_URL` | Supabase Session pooler URL |
| `TAMAGOTCHI_CHANNEL_ID` | `#다마고치` 채널 ID |

---

## 🛠️ 기술 스택

- **Python 3.11+**
- **discord.py 2.x** — 디스코드 봇
- **OpenAI GPT-4o** — 칼로리 분석 / Vision / 대사 생성
- **Supabase (PostgreSQL)** — 클라우드 DB (psycopg2)
- **APScheduler** — 날씨 교체, 칼로리 자동 판정
- **기상청 공공데이터 API** — 날씨 정보
- **에어코리아 API** — 미세먼지 정보
- **scikit-learn / pandas** — ML 칼로리 보정 + 식습관 패턴 분석

---

## 🖼️ 다마고치 이미지 목록

| 이미지 | 표시 조건 |
|--------|-----------|
| `happy.png` | hp ≥ 70, hunger ≥ 70, mood ≥ 70 |
| `normal.png` | 모든 수치 40~69 (기본) |
| `hungry.png` | 식사 알림 정각 이후 미입력 |
| `hungry_cry.png` | 식사 알림 1시간 후 미입력 |
| `eating.png` | 식사 입력 직후 3분 |
| `overfed.png` | 오후 10시 칼로리 > 권장 |
| `underfed.png` | 오후 10시 칼로리 < 권장×0.67 |
| `sunny.png` | 맑음 + 15~25°C |
| `hot.png` | 기온 ≥ 26°C |
| `cold.png` | 기온 ≤ 5°C |
| `rainy.png` | 비/소나기 |
| `snowy.png` | 눈 |
| `cloudy.png` | 흐림 |
| `dusty.png` | PM10 > 80 또는 PM2.5 > 35 |
| `sick.png` | hp < 40 |
| `tired.png` | mood < 40 |
| `goal_achieved.png` | 목표 체중 달성 |

---

## 📖 상세 문서

프로젝트 상세 문서는 [`docs/CONTEXT.md`](docs/CONTEXT.md)를 참고하세요.
