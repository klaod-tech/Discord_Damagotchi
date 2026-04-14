# 전체 아키텍처 — 멀티봇 설계

---

## 1. 봇 전체 목록 및 역할

| 봇 | 파일 | prefix | 토큰 | Cog | 상태 |
|----|------|--------|------|-----|------|
| **먹구름봇** | `bot.py` | `!` | `DISCORD_TOKEN` | onboarding, summary, settings, time_settings, scheduler, weight | ✅ 운영 |
| **메일봇** | `bot_mail.py` | `!mail_` | `DISCORD_TOKEN_EMAIL` | email_monitor | ✅ 운영 |
| **식사봇** | `bot_meal.py` | `!meal_` | `DISCORD_TOKEN_MEAL` | meal | ✅ 운영 |
| **날씨봇** | `bot_weather.py` | `!weather_` | `DISCORD_TOKEN_WEATHER` | weather | ✅ 운영 |
| **체중관리봇** | `bot_weight.py` | `!weight_` | `DISCORD_TOKEN_WEIGHT` | (weight 이전 예정) | 🔄 skeleton |
| **일기봇** | `bot_diary.py` | `!diary_` | `DISCORD_TOKEN_DIARY` | diary (신규) | 📋 예정 |
| **일정봇** | `bot_schedule.py` | `!schedule_` | `DISCORD_TOKEN_SCHEDULE` | schedule (신규) | 📋 예정 |

> **모든 봇은 동일한 Supabase DB 공유** — HTTP IPC 없이 DB를 단일 진실 공급원으로 사용

---

## 2. 환경변수 전체 목록

```env
# ── 봇 토큰 ──────────────────────────────────
DISCORD_TOKEN              # 먹구름봇 (오케스트레이터)
DISCORD_TOKEN_EMAIL        # 메일봇
DISCORD_TOKEN_MEAL         # 식사봇
DISCORD_TOKEN_WEATHER      # 날씨봇
DISCORD_TOKEN_WEIGHT       # 체중관리봇
DISCORD_TOKEN_DIARY        # 일기봇 (예정)
DISCORD_TOKEN_SCHEDULE     # 일정봇 (예정)

# ── 채널 / 서버 ───────────────────────────────
TAMAGOTCHI_CHANNEL_ID      # 온보딩 진입점 채널 ID (v3.2: 다마고치 채널)
TAMAGOTCHI_CATEGORY_ID     # 유저 전용 채널 생성 카테고리 ID (v4.0~)

# ── API 키 (모든 봇 공유) ─────────────────────
OPENAI_API_KEY             # GPT-4o (자연어 파싱, Vision, 대사 생성)
DATABASE_URL               # Supabase Session pooler (PostgreSQL)
WEATHER_API_KEY            # 기상청 공공데이터 포털
AIR_API_KEY                # 에어코리아 미세먼지
FOOD_API_KEY               # 식약처 식품영양성분 DB

# ── n8n (웹훅 URL 수령 후 등록) ───────────────
N8N_FOOD_WEBHOOK_URL       # n8n 음식 추천 웹훅 (이미 구성됨, URL만 등록)
```

---

## 3. 봇 진입점 공통 패턴

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
_bot_ready = False  # 재연결 시 on_ready 중복 실행 방지

@bot.event
async def on_ready():
    global _bot_ready
    if _bot_ready:
        print(f"[RECONNECT] {bot.user} 재연결됨 — 초기화 생략")
        return
    _bot_ready = True
    init_db()            # 공통 + 봇 고유 테이블 마이그레이션
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

## 4. 디스코드 채널·쓰레드 소유권

### v4.0 목표 구조 (유저별 전용 채널)

온보딩 시 유저 전용 채널 1개 + **Push 전용 쓰레드 2개**만 생성.

| 구분 | 이름 | DB 컬럼 | 용도 |
|------|------|---------|---------|
| **채널** | `#{이름}-채팅창` | `personal_channel_id` | 오케스트레이터 대화 + 서브봇 직접 응답 공간 |
| **쓰레드** | `🔔 {이름}의 알림` | `info_thread_id` | Push 전용: 날씨 기상 알림, 일정 D-day 알림, 주간 리포트 |
| **쓰레드** | `📧 {이름}의 메일함` | `mail_thread_id` | Push 전용: 이메일 수신 알림 |

> **설계 원칙**:
> - 유저가 요청한 것 (식사 기록, 체중, 일기 등) → 서브봇이 `personal_channel_id`에 직접 응답
> - 시스템이 자동 발송하는 Push → 쓰레드 (`info_thread_id` or `mail_thread_id`)
> - 서브봇은 메인봇으로 결과를 반환하지 않음. `personal_channel_id` 권한을 직접 보유.
>
> 캐릭터 상태 Embed는 채널에 **고정 메시지(pin)**로 표시. 채널 권한: 해당 유저만 읽기/쓰기 가능.

### v3.2 현재 구조 (단일 채널 + 쓰레드)

온보딩 시 `cogs/onboarding.py`가 #다마고치 채널 아래 쓰레드를 자동 생성.

| 쓰레드명 | DB 컬럼 | 담당 봇 |
|---------|---------|---------|
| `{이름}의 {캐릭터명}` | `thread_id` | 먹구름봇 (메인 Embed, **fallback 기준**) |
| `📧 {이름}의 메일함` | `mail_thread_id` | 메일봇 |
| `🍽️ {이름}의 식사 기록` | `meal_thread_id` | 식사봇 |
| `🌤️ {이름}의 날씨` | `weather_thread_id` | 날씨봇 |
| `⚖️ {이름}의 체중관리` | `weight_thread_id` | 체중관리봇 |

### Fallback 패턴 (기존 유저 호환 — 반드시 사용)

```python
# 유저 요청 응답: 전용 채널 없으면 메인 thread_id fallback
channel_id = user.get("personal_channel_id") or user.get("thread_id")

# Push 알림 (날씨/일정): info_thread_id 없으면 thread_id fallback
info_id = user.get("info_thread_id") or user.get("thread_id")

# 메일 알림: mail_thread_id 없으면 thread_id fallback
mail_id = user.get("mail_thread_id") or user.get("thread_id")
```

기존 유저(`personal_channel_id`, `info_thread_id` = NULL) → 메인 쓰레드(`thread_id`)로 자동 fallback.

---

## 5. DB 테이블 소유권

| 테이블 | 소유 봇 | 다른 봇 접근 허용 |
|--------|---------|-----------------|
| `users` | 먹구름봇 (온보딩) | **모든 봇 읽기 가능**, 자기 컬럼만 쓰기 |
| `tamagotchi` | 먹구름봇 | 식사봇 (hunger/mood/hp UPDATE) |
| `meals` | 식사봇 | 먹구름봇 읽기 (하루정리), 체중관리봇 읽기 (칼로리 조정) |
| `weather_log` | 날씨봇 | 먹구름봇 읽기 (하루정리 날씨 표시) |
| `weight_log` | 체중관리봇 | 먹구름봇 읽기 (하루정리 체중 표시) |
| `email_senders` | 메일봇 | 없음 |
| `email_log` | 메일봇 | ML 학습 시 읽기 |
| `diary_log` | 일기봇 | 먹구름봇 읽기, 식사봇 읽기 (식사×감정 상관) |
| `schedule_log` | 일정봇 | 먹구름봇 읽기 |

---

## 6. 봇 간 통신 — task_queue 패턴

> **핵심 원칙**: 봇 간 직접 HTTP 통신 없음. DB `task_queue` 테이블을 단일 통신 채널로 사용.  
> 서브봇은 처리 결과를 **메인봇으로 반환하지 않음** — `personal_channel_id`에 직접 응답.

```
[먹구름봇] on_message — 의도 분류 후:
    1. task_queue INSERT { bot_target: "meal", user_id: ..., payload: {...} }
    2. intent_log INSERT (ML 학습 데이터 축적)
    3. 먹구름봇 처리 종료 (서브봇 응답 대기 없음)

[서브봇] 폴링 루프 (5~30초 간격):
    1. task_queue SELECT WHERE bot_target = 'meal' AND status = 'pending'
    2. 처리 (GPT 파싱, DB 저장 등)
    3. personal_channel_id 채널에 직접 Embed 응답
    4. task_queue UPDATE status = 'done'
```

### 사진 입력 — v4.0 직접 업로드 방식

```
[식사봇] personal_channel_id 채널 on_message 이벤트
    → 이미지 첨부 감지 → "📸 음식 사진이에요? [✅] [❌]" 응답
    → Vision 분석 → Embed + [✅ 기록하기] [❌ 취소]
    ← meal_waiting DB 패턴 불필요 (채널에서 직접 처리)
```

### v3.2 하위 호환 — 사진 대기 상태 (기존 유저)

```
[먹구름봇] v3.2 버튼 경유:
    1. set_meal_waiting(user_id, seconds=60)  ← DB 만료 시각
    2. "식사 쓰레드에 사진을 올려줘!" 안내

[식사봇] meal_thread_id or thread_id on_message:
    → is_meal_waiting(user_id) → True
    → clear_meal_waiting(user_id)
    → GPT-4o Vision 분석 → Embed
```

---

## 7. 슬래시 커맨드 네임스페이스 (충돌 방지)

| 봇 | 등록 커맨드 |
|----|------------|
| 먹구름봇 | `/start` |
| 메일봇 | `/이메일설정`, `/발신자추가`, `/발신자목록`, `/발신자삭제` |
| 일기봇 | `/일기`, `/감정통계` |
| 일정봇 | `/일정등록`, `/일정목록`, `/일정삭제` |
| 식사봇 / 날씨봇 / 체중관리봇 | 슬래시 커맨드 없음 (버튼/스케줄러 기반) |

---

## 8. 개발 규칙 (충돌 방지)

1. **마이그레이션**: 새 컬럼 → `ALTER TABLE users ADD COLUMN IF NOT EXISTS`
2. **테이블 생성**: `CREATE TABLE IF NOT EXISTS`를 `init_db()` 내에 추가
3. **함수명 접두사**: 도메인 명확히 (`get_diary_*`, `save_schedule_*`)
4. **Cog 등록**: `async def setup(bot)` 반드시 정의
5. **DB 연결**: `get_conn()` 사용 후 `conn.close()`, `cur.close()` 필수
6. **중복 Cog**: 동일 Cog를 두 봇이 동시 로드하면 슬래시 커맨드 충돌 → 반드시 한 봇에서만 로드
7. **thread_id fallback**: 새 쓰레드 없는 기존 유저 → 반드시 `or user.get("thread_id")` 처리

---

## 9. 로컬 실행 (개발 시)

각 봇은 별도 터미널에서 독립 실행:

```bash
python bot.py           # 먹구름봇 (항상 실행)
python bot_mail.py      # 메일봇
python bot_meal.py      # 식사봇
python bot_weather.py   # 날씨봇
python bot_weight.py    # 체중관리봇 (skeleton)
python bot_diary.py     # 일기봇 (구현 후)
python bot_schedule.py  # 일정봇 (구현 후)
```

---

## 10. 브랜치 전략

```
main        ← 배포 (안정)
develop     ← 통합 (PR target)
feat/diary  ← 일기봇 개발
feat/schedule ← 일정봇 개발
feat/weight-migration ← 체중관리봇 이전
```
