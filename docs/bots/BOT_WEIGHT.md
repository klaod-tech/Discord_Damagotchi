# 체중관리봇 개발 가이드 — Claude 전용

> **이 파일만 읽으면 체중관리봇을 완전히 구현/수정할 수 있습니다.**  
> 공통 참조: `01_ARCHITECTURE.md`, `02_SHARED_DB.md`, `03_SHARED_UTILS.md`

---

## 1. 봇 기본 정보

| 항목 | 내용 |
|------|------|
| 봇 파일 | `bot_weight.py` |
| 토큰 환경변수 | `DISCORD_TOKEN_WEIGHT` |
| 커맨드 prefix | `!weight_` |
| 담당 Cog | `cogs/weight.py` → `WeightCog` |
| 담당 쓰레드 | `users.weight_thread_id` (없으면 `thread_id` fallback) |
| 담당 DB 테이블 | `weight_log` (소유) |
| 현재 상태 | 🔄 버튼은 먹구름봇에 있음, 이전 준비 완료 |

---

## 2. 역할 및 범위

### 이 봇이 하는 것 (목표)
- 체중 기록 입력 수신 → DB 저장
- 목표 달성 Embed를 체중관리 전용 쓰레드에 전송
- 체중 추이 그래프 (향후)
- 목표 체중 기반 일일 칼로리 동적 조정 스케줄러 (향후)

### 현재 상태 (v3.2)
- `WeightInputModal` 버튼은 먹구름봇의 `MainView`에 있음 (`utils/embed.py`)
- `WeightInputModal.on_submit()` 처리는 `cogs/weight.py`에 있고 bot.py에 로드됨
- 목표 달성 시 `weight_thread_id or thread_id` 쓰레드에 Embed 전송 ✅
- `bot_weight.py`는 현재 skeleton (cog 미로드)

### 이 봇으로 이전할 항목
- `cogs/weight.py`를 `bot.py`에서 제거하고 `bot_weight.py`에서 로드
- 단, `WeightInputModal` 버튼은 먹구름봇 `MainView`에 유지 (버튼 → 모달만 다른 봇에서 처리)

---

## 3. 현재 cogs/weight.py 구조

```
cogs/weight.py
  ├── save_weight_log(user_id, weight)             # weight_log INSERT
  ├── get_weight_history(user_id, limit=7) -> list # 최근 체중 기록
  ├── get_latest_weight(user_id) -> float | None
  ├── get_latest_weight_before(user_id) -> float | None  # 직전 체중 (변화량 계산용)
  ├── WeightInputModal (Modal)
  │   └── on_submit: 체중 파싱 → 저장 → Embed → goal_achieved 시 create_or_update_embed
  └── WeightCog (Cog)
```

---

## 4. 체중 기록 흐름

```
[먹구름봇] 유저가 [⚖️ 체중 기록] 클릭 → WeightInputModal 표시

WeightInputModal.on_submit():
  1. 체중 파싱 (float, 20~300 범위 검증)
  2. save_weight_log(user_id, weight)  ← weight_log INSERT
  3. 이전 체중과 비교 (get_latest_weight_before)
  4. 목표 체중과 비교 (goal_weight)
  5. GPT 한마디 생성 (generate_comment)
  6. 달성률 프로그레스 바 계산
  7. 체중 기록 Embed 전송 (ephemeral)
  8. goal_achieved == True:
       → weight_thread_id or thread_id 조회
       → create_or_update_embed(goal_achieved=True)
```

---

## 5. DB 사용 목록

### 읽기 (Read)
```python
get_user(user_id)          # goal_weight, init_weight 조회
get_tamagotchi(user_id)    # Embed 갱신용
```

### 쓰기 (Write — 소유)
```python
save_weight_log(user_id, weight)   # weight_log INSERT
```

내부 함수 (weight.py에 정의, db.py에 없음):
```python
def save_weight_log(user_id, weight):
    # utils/db.get_conn() 사용
    # weight_log 테이블에 INSERT

def get_weight_history(user_id, limit=7) -> list[dict]:
    # [{"weight": float, "recorded_at": datetime}, ...]

def get_latest_weight(user_id) -> float | None:
    # get_weight_history(limit=1) 래퍼

def get_latest_weight_before(user_id) -> float | None:
    # get_weight_history(limit=2)[1] — 직전 기록
```

### 절대 건드리지 말 것
- `meals`, `weather_log`, `email_*`, `diary_log`, `schedule_log` 금지

---

## 6. 달성률 프로그레스 바 계산

```python
total_diff = abs(init_weight - goal_weight)  # 초기 → 목표 차이
done_diff  = abs(init_weight - weight)        # 초기 → 현재 차이
ratio      = min(done_diff / total_diff, 1.0) if total_diff > 0 else 0
filled     = int(ratio * 10)
bar        = "█" * filled + "░" * (10 - filled)
percent    = int(ratio * 100)
```

---

## 7. 향후 기능 추가 계획

### Phase 1 — bot_weight.py로 완전 이전
```python
# bot.py의 COGS에서 "cogs.weight" 제거
# bot_weight.py에 추가:
await bot.load_extension("cogs.weight")
```

**주의**: `WeightInputModal`은 `utils/embed.py`의 `weight_button`에서 호출됨.  
버튼은 먹구름봇이 관리하지만, 모달 처리는 어느 봇이든 Cog가 로드된 봇에서 실행됨.  
→ bot_weight.py가 cogs.weight를 로드하면 모달 처리도 이 봇에서 담당.

### Phase 2 — 체중 추이 스케줄러
```python
# 매일 특정 시간에 체중 입력 유도 알림
# APScheduler로 체중 전용 쓰레드에 알림 전송

# 예시:
class WeightCog(commands.Cog):
    def __init__(self, bot):
        self.scheduler = AsyncIOScheduler()
        self.scheduler.add_job(
            self._daily_weight_reminder,
            CronTrigger(hour=21, minute=0),  # 매일 9시
        )
        self.scheduler.start()
```

### Phase 3 — 체중 추이 그래프
- 최근 30일 weight_log → matplotlib 그래프 생성
- PNG 파일로 Discord 전송
- 목표 달성 예상 날짜 Prophet ML 예측

### Phase 4 — 목표 칼로리 동적 조정 연계
- 현재 `utils/embed.py daily_button`에서 체중 변화 기반 칼로리 조정 있음
- 이 로직을 체중관리봇이 매일 스케줄러로 자동 처리하도록 이전
- 변경된 목표 칼로리를 `users.daily_cal_target` 업데이트

### ML 계획
- weight_log 추이 → Prophet 시계열 예측 → 목표 달성 날짜 예측
- 체중 변화 패턴 × 식사 기록 상관관계 분석

---

## 8. bot_weight.py 전체 코드 (현재 skeleton)

```python
"""
bot_weight.py — 체중관리 전용 봇 진입점

역할: 체중 기록 / 칼로리 목표 동적 조정 / 체중 추이 예측
DB : 먹구름과 동일한 Supabase 공유
토큰: .env의 DISCORD_TOKEN_WEIGHT 사용
"""
import os
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv
from utils.db import init_db

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN_WEIGHT")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!weight_", intents=intents)
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
    print(f"[체중관리봇] {bot.user} 로그인 완료")

@bot.event
async def on_error(event, *args, **kwargs):
    import traceback
    traceback.print_exc()

async def main():
    async with bot:
        # Phase 1 이전 시 아래 주석 해제 + bot.py에서 "cogs.weight" 제거
        # await bot.load_extension("cogs.weight")
        print("[체중관리봇] 준비 완료 (Phase 1 이전 전)")
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 9. 개발 시 주의사항

- `WeightInputModal`이 `utils/embed.py`에 위치하므로 먹구름봇과 체중관리봇 동시에 `cogs.weight` 로드하지 말 것 (Cog 중복 등록 오류)
- Phase 1 이전 시: `bot.py` COGS에서 `"cogs.weight"` 제거 후 `bot_weight.py`에 추가
- 체중 입력은 `float` 파싱 + `20.0 ≤ weight ≤ 300.0` 범위 검증 유지
- 체중 전용 쓰레드 없는 기존 유저는 반드시 `weight_thread_id or thread_id` fallback
