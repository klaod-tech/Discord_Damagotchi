# 🐣 Discord AI 다마고치 봇

디스코드에서 동작하는 1인 1다마고치 봇.  
음식을 입력하면 다마고치에게 밥을 주는 행위로 연결되고,  
**칼로리 관리와 날씨 정보를 수치가 아닌 캐릭터 이미지와 대사로 간접 전달**합니다.

---

## 📁 프로젝트 구조

```
Discord_Damagotchi/
├── bot.py                  # 봇 메인 진입점
├── cogs/
│   ├── onboarding.py       # 온보딩 + 쓰레드 생성
│   ├── meal.py             # 식사 입력 (텍스트 + 사진)
│   ├── weather.py          # 날씨 연동 + 이미지 교체
│   ├── summary.py          # 오늘 요약
│   ├── settings.py         # 설정 변경
│   └── scheduler.py        # APScheduler 알림 관리
├── utils/
│   ├── gpt.py              # OpenAI API 래퍼
│   ├── db.py               # DB 연결 + 쿼리
│   ├── embed.py            # Embed UI 생성 + 수정
│   └── image.py            # 상태별 이미지 선택 로직
├── images/                 # 다마고치 이미지 (~25종)
├── database.py             # DB 초기화 + CRUD
├── .env.example            # 환경변수 템플릿
├── requirements.txt
└── README.md
```

---

## 🚀 실행 방법

### 1. 패키지 설치
```bash
pip install -r requirements.txt
```

### 2. 환경변수 설정
```bash
cp .env.example .env
# .env 파일을 열어 값 입력
```

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
| `DATABASE_URL` | DB 경로 (기본값: `./tamagotchi.db`) |
| `TAMAGOTCHI_CHANNEL_ID` | `#다마고치` 채널 ID |

---

## 🛠️ 기술 스택

- **Python 3.11+**
- **discord.py** — 디스코드 봇
- **OpenAI GPT-4o** — 칼로리 분석 / Vision / 대사 생성
- **SQLite** — 로컬 DB
- **APScheduler** — 식사 알림, 날씨 교체 자동화
- **기상청 공공데이터 API** — 날씨 정보

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