# 먹구름 전체 아키텍처 — 멀티봇 설계

---

## 1. 봇 전체 목록

| 봇 | 파일 | 역할 | 토큰 환경변수 | 상태 |
|----|------|------|--------------|------|
| **먹구름봇** | `bot.py` | 오케스트레이터 — GPT 자연어 파싱, 버튼 허브, 설정, 온보딩 | `DISCORD_TOKEN` | ✅ 운영 |
| **메일봇** | `bot_mail.py` | 이메일 IMAP 폴링, 발신자 알림 | `DISCORD_TOKEN_EMAIL` | ✅ 운영 |
| **식사봇** | `bot_meal.py` | 사진 감지, 음식 분석, 칼로리 기록 | `DISCORD_TOKEN_MEAL` | ✅ 운영 |
| **날씨봇** | `bot_weather.py` | 기상청/에어코리아 API 스케줄 알림 | `DISCORD_TOKEN_WEATHER` | ✅ 운영 |
| **체중관리봇** | `bot_weight.py` | 체중 추이, 목표 칼로리 조정 (예정) | `DISCORD_TOKEN_WEIGHT` | 🔄 skeleton |
| **일기봇** | `bot_diary.py` | 일기 입력, GPT 감정 분석 | `DISCORD_TOKEN_DIARY` | 📋 구현 예정 |
| **일정봇** | `bot_schedule.py` | 일정 등록, 알림, 반복 패턴 | `DISCORD_TOKEN_SCHEDULE` | 📋 구현 예정 |

---

## 2. 환경변수 전체 목록 (.env)

```env
# ── 봇 토큰 ──────────────────────────────
DISCORD_TOKEN              # 먹구름봇 (오케스트레이터)
DISCORD_TOKEN_EMAIL        # 메일봇
DISCORD_TOKEN_MEAL         # 식사봇
DISCORD_TOKEN_WEATHER      # 날씨봇
DISCORD_TOKEN_WEIGHT       # 체중관리봇
DISCORD_TOKEN_DIARY        # 일기봇
DISCORD_TOKEN_SCHEDULE     # 일정봇

# ── 채널 ─────────────────────────────────
TAMAGOTCHI_CHANNEL_ID      # 봇 전용 채널 ID (모든 봇이 쓰레드 조회에 사용)

# ── API 키 (모든 봇 공유) ────────────────
OPENAI_API_KEY             # GPT-4o
DATABASE_URL               # Supabase Session pooler (PostgreSQL)
WEATHER_API_KEY            # 기상청 공공데이터 포털
AIR_API_KEY                # 에어코리아 미세먼지
FOOD_API_KEY               # 식약처 식품영양성분 DB

# ── 추가 예정 ────────────────────────────
N8N_FOOD_WEBHOOK_URL       # n8n 음식 추천 웹훅
```

---

## 3. 봇 간 통신 방식

모든 봇은 **동일한 Supabase DB를 공유**합니다.  
HTTP IPC나 Discord 메시지 방식 대신 **DB를 단일 진실 공급원**으로 사용합니다.

### 3-1. 상태 공유 패턴

| 상황 | 생산자 (Writer) | 소비자 (Reader) | DB 컬럼 |
|------|----------------|----------------|---------|
| 사진 입력 대기 | 먹구름봇 | 식사봇 | `users.meal_waiting_until` |
| 날씨 쓰레드 조회 | 온보딩 (먹구름봇) | 날씨봇 | `users.weather_thread_id` |
| 체중 쓰레드 조회 | 온보딩 (먹구름봇) | 체중관리봇 | `users.weight_thread_id` |
| 일기 쓰레드 조회 | 온보딩 (먹구름봇) | 일기봇 | `users.diary_thread_id` |
| 일정 쓰레드 조회 | 온보딩 (먹구름봇) | 일정봇 | `users.schedule_thread_id` |

### 3-2. 사진 입력 예시 (봇 간 협력 흐름)

```
1. 유저 → 먹구름봇: [📸 사진으로 입력] 버튼 클릭
2. 먹구름봇 → DB: users.meal_waiting_until = NOW() + 60s
3. 유저 → Discord: 식사 전용 쓰레드에 사진 업로드
4. 식사봇: on_message 감지
5. 식사봇 → DB: is_meal_waiting(user_id) 조회 → True
6. 식사봇 → DB: clear_meal_waiting(user_id)
7. 식사봇 → GPT-4o Vision: 음식 분석
8. 식사봇 → Discord: 분석 결과 Embed 전송
```

---

## 4. 디스코드 쓰레드 소유권

온보딩 시 `cogs/onboarding.py`가 **쓰레드 7개**를 자동 생성합니다.

| 쓰레드 이름 | DB 컬럼 | 담당 봇 | 생성 시기 |
|------------|---------|---------|----------|
| `{이름}의 {캐릭터명}` | `thread_id` | 먹구름봇 | 온보딩 |
| `📧 {이름}의 메일함` | `mail_thread_id` | 메일봇 | 온보딩 |
| `🍽️ {이름}의 식사 기록` | `meal_thread_id` | 식사봇 | 온보딩 |
| `🌤️ {이름}의 날씨` | `weather_thread_id` | 날씨봇 | 온보딩 |
| `⚖️ {이름}의 체중관리` | `weight_thread_id` | 체중관리봇 | 온보딩 |
| `📔 {이름}의 일기` | `diary_thread_id` | 일기봇 | 온보딩 추가 예정 |
| `📅 {이름}의 일정` | `schedule_thread_id` | 일정봇 | 온보딩 추가 예정 |

### Fallback 패턴 (기존 유저 호환)

기존 유저는 새 전용 쓰레드가 없을 수 있음. 반드시 fallback 사용:

```python
thread_id = user.get("weather_thread_id") or user.get("thread_id")
```

---

## 5. DB 테이블 소유권

| 테이블 | 소유 봇 | 다른 봇 접근 |
|--------|---------|-------------|
| `users` | 먹구름봇 (온보딩) | 모든 봇 읽기 가능, 자기 컬럼만 쓰기 |
| `tamagotchi` | 먹구름봇 | 식사봇 (hunger/mood/hp 갱신) |
| `meals` | 식사봇 | 먹구름봇 읽기 (하루 정리), 체중관리봇 읽기 (칼로리 조정) |
| `weather_log` | 날씨봇 | 먹구름봇 읽기 (하루 정리 날씨 표시) |
| `weight_log` | 체중관리봇 | 먹구름봇 읽기 (하루 정리 체중 표시) |
| `email_senders` | 메일봇 | 없음 |
| `email_log` | 메일봇 | ML 학습 시 읽기 |
| `diary_log` | 일기봇 | 먹구름봇 읽기, 식사봇 읽기 (식사×감정 상관) |
| `schedule_log` | 일정봇 | 먹구름봇 읽기 |

---

## 6. Cog 이름 / 슬래시 커맨드 네임스페이스

충돌 방지를 위해 각 봇의 Cog와 명령어 네임스페이스를 분리합니다.

| 봇 | Cog 클래스명 | prefix | 슬래시 커맨드 예시 |
|----|-------------|--------|-----------------|
| 먹구름봇 | OnboardingCog, SchedulerCog 등 | `!` | `/start`, `/sync` |
| 메일봇 | EmailMonitorCog | `!mail_` | `/이메일설정`, `/발신자추가` |
| 식사봇 | MealPhotoCog | `!meal_` | (버튼 기반, 슬래시 없음) |
| 날씨봇 | WeatherCog | `!weather_` | (스케줄러 기반) |
| 체중관리봇 | WeightCog | `!weight_` | (버튼 기반) |
| 일기봇 | DiaryCog | `!diary_` | `/일기`, `/감정통계` |
| 일정봇 | ScheduleCog | `!schedule_` | `/일정등록`, `/일정목록` |

---

## 7. 봇 진입점 공통 구조

모든 봇 파일은 아래 패턴을 따릅니다:

```python
import os, asyncio, discord
from discord.ext import commands
from dotenv import load_dotenv
from utils.db import init_db

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN_XXX")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!xxx_", intents=intents)
_bot_ready = False

@bot.event
async def on_ready():
    global _bot_ready
    if _bot_ready:
        print(f"[RECONNECT] {bot.user} 재연결됨 — 초기화 생략")
        return
    _bot_ready = True
    init_db()          # 공통 테이블 마이그레이션
    await bot.tree.sync()
    print(f"[XXX봇] {bot.user} 로그인 완료")

@bot.event
async def on_error(event, *args, **kwargs):
    import traceback; traceback.print_exc()

async def main():
    async with bot:
        await bot.load_extension("cogs.xxx")
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 8. 개발 규칙 (충돌 방지)

1. **마이그레이션**: 새 컬럼 추가 시 반드시 `ALTER TABLE users ADD COLUMN IF NOT EXISTS`
2. **테이블 생성**: 자신이 소유한 테이블은 `CREATE TABLE IF NOT EXISTS`로 `init_db()` 내에 추가
3. **함수명**: `utils/db.py`에 함수 추가 시 자신의 도메인 접두사 사용 (e.g. `get_diary_*`, `save_diary_*`)
4. **Cog 등록**: `setup(bot)` 함수 반드시 정의
5. **봇 재시작 안전**: 모든 View는 `timeout=None` 또는 충분한 timeout. 영구 View는 `bot.add_view()` 등록
6. **DB 연결**: `get_conn()` 사용 후 반드시 `conn.close()` (컨텍스트 매니저 없이 수동 관리)

---

## 9. 로컬 실행 (개발 시)

각 봇은 별도 터미널에서 독립 실행:

```bash
python bot.py           # 먹구름봇 (오케스트레이터) — 항상 실행
python bot_mail.py      # 메일봇
python bot_meal.py      # 식사봇
python bot_weather.py   # 날씨봇
python bot_weight.py    # 체중관리봇
python bot_diary.py     # 일기봇 (구현 후)
python bot_schedule.py  # 일정봇 (구현 후)
```

---

## 10. 브랜치 전략

```
main        ← 배포 브랜치 (안정)
develop     ← 통합 브랜치 (PR target)
feat/meal   ← 식사봇 개발
feat/weather← 날씨봇 개발
feat/weight ← 체중관리봇 개발
feat/diary  ← 일기봇 개발
feat/schedule← 일정봇 개발
```

각 봇 개발 완료 → `develop`에 PR → 충돌 해결 → 검증 후 `main` 머지
