# 날씨봇 개발 가이드 — Claude 전용

> **이 파일만 읽으면 날씨봇을 완전히 구현/수정할 수 있습니다.**  
> 공통 참조: `01_ARCHITECTURE.md`, `02_SHARED_DB.md`, `03_SHARED_UTILS.md`

---

## 1. 봇 기본 정보

| 항목 | 내용 |
|------|------|
| 봇 파일 | `bot_weather.py` |
| 토큰 환경변수 | `DISCORD_TOKEN_WEATHER` |
| 커맨드 prefix | `!weather_` |
| 담당 Cog | `cogs/weather.py` → `WeatherCog` |
| 담당 쓰레드 | `users.weather_thread_id` (없으면 `thread_id` fallback) |
| 담당 DB 테이블 | `weather_log` (소유) |
| 외부 API | 기상청 공공데이터, 에어코리아 |

---

## 2. 역할 및 범위

### 이 봇이 하는 것
- 유저 기상 시간(`wake_time`)에 맞춰 날씨 + 미세먼지 조회
- 날씨 전용 쓰레드에 날씨 Embed 전송
- 먹구름봇의 메인 Embed 이미지 자동 교체 (날씨 반영)
- 매 10분마다 새 유저 스케줄러 자동 등록

### 이 봇이 하지 않는 것
- 날씨 설정 변경 — 먹구름봇 `cogs/settings.py`
- 기상 시간 설정 — 먹구름봇 `cogs/time_settings.py`

---

## 3. 현재 구현 상태

`cogs/weather.py` **구현 완료**. 이미 동작 중인 코드 기준.

```
bot_weather.py
  └── cogs/weather.py
        ├── WeatherCog (Cog)
        │   ├── APScheduler (AsyncIOScheduler)
        │   ├── _setup_jobs(): 봇 시작 시 전체 유저 wake_time Job 등록
        │   ├── _check_new_users(): 10분마다 새 유저 자동 등록
        │   ├── _run_weather_update(hour, minute): 해당 wake_time 유저 업데이트
        │   └── force_weather (관리자 명령어): 즉시 전체 업데이트
        ├── update_weather_for_user(bot, user): 유저 1명 날씨 전송
        ├── fetch_weather(nx, ny): 기상청 초단기실황 API
        └── fetch_air(city): 에어코리아 API
```

---

## 4. 날씨 알림 흐름

```
봇 시작
  └── _setup_jobs()
        → get_all_users() 조회
        → 각 유저의 wake_time 기준 CronJob 등록
        → job_id = "weather_HHMM" (중복 방지)

매 10분
  └── _check_new_users()
        → 신규 유저 wake_time 감지 → Job 추가 등록

매일 wake_time (유저별)
  └── _run_weather_update(hour, minute)
        → 해당 시각인 유저 필터링
        → update_weather_for_user(bot, user) 호출

update_weather_for_user(bot, user)
  1. weather_thread_id or thread_id 로 쓰레드 조회
  2. fetch_weather(nx, ny): 날씨/기온
  3. fetch_air(city): PM10/PM25
  4. generate_comment(): GPT 한마디
  5. create_weather_log(): DB 저장
  6. thread.send(embed=weather_embed): 날씨 전용 쓰레드에 전송
  7. create_or_update_embed(): 메인 Embed 이미지 교체 (메인 쓰레드)
```

---

## 5. DB 사용 목록

### 읽기 (Read)
```python
get_all_users()            # 전체 유저 wake_time 조회
get_tamagotchi(user_id)    # Embed 갱신용
```

### 쓰기 (Write — 소유)
```python
create_weather_log(user_id, weather, temp, pm10, pm25, selected_image, gpt_comment)
```

### 절대 건드리지 말 것
- `meals`, `weight_log`, `email_*`, `diary_log`, `schedule_log` — 읽기/쓰기 금지
- `users` 컬럼 추가/수정 금지

---

## 6. 외부 API

### 기상청 초단기실황 (초단기실황조회)
```
URL: http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtNcst
KEY: WEATHER_API_KEY
파라미터: serviceKey, numOfRows, pageNo, dataType, base_date, base_time, nx, ny
반환: PTY(강수형태), T1H(기온), SKY(하늘상태)
```

### 에어코리아 (시도별 실시간 측정정보)
```
URL: http://apis.data.go.kr/B552584/ArpltnInforInqireSvc/getCtprvnRltmMesureDnsty
KEY: AIR_API_KEY
파라미터: serviceKey, returnType, numOfRows, sidoName, ver
반환: pm10Value, pm25Value
```

---

## 7. 도시 → 격자 좌표 매핑

`CITY_GRID` 딕셔너리로 관리. 현재 50개 도시 지원.

```python
CITY_GRID: dict[str, tuple[int, int]] = {
    "서울": (60, 127), "부산": (98, 76), ...
}

def _find_grid(city: str) -> tuple[int, int]:
    # 완전 일치 우선, 없으면 부분 일치 (가장 긴 키)
    # 최종 fallback: 서울
```

---

## 8. 날씨 판별 로직

```python
pty  = int(result.get("PTY", 0))   # 강수형태
sky  = int(result.get("SKY", 1))   # 하늘상태
temp = float(result.get("T1H", 15)) # 기온

if pty in (1, 5):    weather = "비"
elif pty in (2, 6):  weather = "비/눈"
elif pty in (3, 7):  weather = "눈"
elif sky == 4:       weather = "흐림"
elif sky == 3:       weather = "구름많음"
else:                weather = "맑음"
```

---

## 9. 미세먼지 등급

```python
def _pm_grade(pm10, pm25) -> str:
    if pm10 > 150 or pm25 > 75: return "매우나쁨 😷"
    if pm10 > 80  or pm25 > 35: return "나쁨 😷"
    if pm10 > 30  or pm25 > 15: return "보통 😐"
    return "좋음 😊"
```

---

## 10. 향후 기능 추가 계획

### 날씨 기반 식사 추천 연계
- 날씨 API 결과 → 먹구름봇이 "오늘 같은 날씨엔 이런 음식 어때?" 연계 가능
- `weather_log` 최신 데이터를 `get_latest_weather(user_id)`로 먹구름봇에서 읽기

### 날씨 알림 커스터마이징
- 현재: 기상 시간에만 알림
- 향후: "비가 올 때만 알림", "미세먼지 나쁨일 때만 알림" 설정 추가 가능
- `users` 테이블에 `weather_notify_cond TEXT` 컬럼 추가 예정

### ML 활용
- `weather_log` × `meals` × `diary_log` 조인 → "날씨에 따른 식습관 패턴" 분석
- 비 오는 날 식사량 증가 패턴, 더운 날 가벼운 식사 패턴 등

---

## 11. bot_weather.py 전체 코드

```python
"""
bot_weather.py — 날씨 전용 봇 진입점

역할: 기상청 / 에어코리아 API 폴링 → 날씨 스레드 알림
DB : 먹구름과 동일한 Supabase 공유
토큰: .env의 DISCORD_TOKEN_WEATHER 사용
"""
import os
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv
from utils.db import init_db

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN_WEATHER")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!weather_", intents=intents)
_bot_ready = False

@bot.event
async def on_ready():
    global _bot_ready
    if _bot_ready:
        print(f"[RECONNECT] {bot.user} 재연결됨 — 초기화 생략")
        return
    _bot_ready = True
    init_db()
    await bot.tree.sync()
    print(f"[날씨봇] {bot.user} 로그인 완료")

@bot.event
async def on_error(event, *args, **kwargs):
    import traceback
    traceback.print_exc()

async def main():
    async with bot:
        await bot.load_extension("cogs.weather")
        print("[날씨봇] cogs.weather 로드 완료")
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 12. 개발 시 주의사항

- `create_or_update_embed()` 호출 시 메인 쓰레드(`thread_id`)를 사용해야 함 — Embed는 메인 쓰레드에 있음
- 날씨 전용 쓰레드엔 날씨 알림 Embed만 전송
- APScheduler Job은 `job_id` 중복 방지 (`replace_existing=True`)
- 기상청 API 응답 실패 시 `{"weather": "알 수 없음", "temp": 15.0}` 기본값 반환
- 에어코리아 API 응답 실패 시 `{"pm10": 0, "pm25": 0}` 기본값 반환
