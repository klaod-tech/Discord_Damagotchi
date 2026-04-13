# 식사봇 개발 가이드 — Claude 전용

> **이 파일만 읽으면 식사봇을 완전히 구현/수정할 수 있습니다.**  
> 공통 참조: `01_ARCHITECTURE.md`, `02_SHARED_DB.md`, `03_SHARED_UTILS.md`

---

## 1. 봇 기본 정보

| 항목 | 내용 |
|------|------|
| 봇 파일 | `bot_meal.py` |
| 토큰 환경변수 | `DISCORD_TOKEN_MEAL` |
| 커맨드 prefix | `!meal_` |
| 담당 Cog | `cogs/meal.py` → `MealPhotoCog` |
| 담당 쓰레드 | `users.meal_thread_id` (없으면 `thread_id` fallback) |
| 담당 DB 테이블 | `meals` (소유), `tamagotchi` (hunger/mood/hp 갱신) |

---

## 2. 역할 및 범위

### 이 봇이 하는 것
- 유저의 식사 전용 쓰레드에서 **사진 첨부 감지**
- 사진 → GPT-4o Vision → 음식 인식 + 칼로리 분석
- 분석 결과 Embed 전송 → 유저 확인 → DB 저장

### 이 봇이 하지 않는 것 (먹구름봇 담당)
- 텍스트 식사 입력 (`MealInputModal`) — `utils/embed.py`에 있음
- 식사 알림 스케줄러 — `cogs/scheduler.py`에 있음
- 하루 정리 — `utils/embed.py` `daily_button`에 있음

---

## 3. 현재 구현 상태

`cogs/meal.py` **구현 완료**. 이미 동작 중인 코드 기준.

```
bot_meal.py
  └── cogs/meal.py
        ├── MealPhotoCog (Cog)
        │   └── on_message: 사진 감지 → is_meal_waiting() → 분석 흐름
        ├── MealPhotoDetectView (View)
        │   └── [✅ 분석하기] / [❌ 아니야]
        ├── MealPhotoConfirmView (View)
        │   └── [✅ 기록하기] / [❌ 취소]
        └── analyze_food_image(image_url) → dict
```

---

## 4. 사진 입력 흐름

```
[먹구름봇] 유저가 [📸 사진으로 입력] 클릭
    → utils/embed.py photo_btn:
        set_meal_waiting(user_id, 60)  ← DB에 만료 시각 기록
        "식사 전용 쓰레드에 사진을 올려줘!" 안내

[식사봇] on_message 이벤트
    1. 봇 메시지 무시
    2. 첨부파일 없으면 무시
    3. 이미지 첨부 확인
    4. Thread인지 확인
    5. get_user(user_id) 조회
    6. meal_thread_id or thread_id 와 message.channel.id 비교
    7-A. is_meal_waiting(user_id) == True:
           clear_meal_waiting(user_id)
           GPT-4o Vision 분석 → MealPhotoConfirmView 전송
    7-B. is_meal_waiting(user_id) == False:
           "📸 음식 사진이에요?" + MealPhotoDetectView 전송

[MealPhotoDetectView] [✅ 분석하기]
    → GPT-4o Vision 분석 → MealPhotoConfirmView 전송

[MealPhotoConfirmView] [✅ 기록하기]
    → ML 칼로리 보정
    → create_meal() DB 저장
    → tamagotchi hunger/mood/hp 갱신
    → create_or_update_embed() 메인 Embed 갱신 (메인 쓰레드)
```

---

## 5. DB 사용 목록

### 읽기 (Read)
```python
get_user(user_id)          # users 테이블 — 쓰레드 ID, 목표 칼로리 등
get_tamagotchi(user_id)    # tamagotchi 테이블
get_calories_by_date(user_id, date)  # meals 테이블
is_meal_waiting(user_id)   # users.meal_waiting_until
```

### 쓰기 (Write — 소유)
```python
create_meal(user_id, meal_type, food_name, calories, protein, carbs, fat, fiber, input_method, gpt_comment)
update_tamagotchi(user_id, {"hunger": ..., "mood": ..., "hp": ..., "last_fed_at": ...})
clear_meal_waiting(user_id)   # users.meal_waiting_until = NULL
```

### 절대 건드리지 말 것
- `users` 테이블 구조 변경 금지
- `weather_log`, `weight_log`, `diary_log`, `schedule_log` — 읽기/쓰기 금지

---

## 6. 핵심 함수: analyze_food_image

```python
async def analyze_food_image(image_url: str) -> dict:
    """
    GPT-4o Vision으로 음식 분석.
    반환: {
        "food_name": str,
        "meal_type": str,   # 아침/점심/저녁/간식
        "calories": int,
        "protein": float,
        "carbs": float,
        "fat": float,
        "fiber": float,
        "description": str,
    }
    """
```

---

## 7. ML 계획 (현재 → 미래)

### 현재 적용
- `utils/gpt_ml_bridge.get_corrected_calories()` — 양 표현 즉시 보정 + Ridge/RF 개인화

### 향후 계획 (데이터 누적 후)
- 사진 입력의 경우 `input_method="photo"` 로 meals에 저장됨
- 사진 입력 vs 텍스트 입력 칼로리 차이 분석 → 개인화 보정 강화
- 음식 카테고리별 보정 모델 분리

---

## 8. 타마고치 수치 변화 규칙

| 칼로리 | hunger 증가 |
|--------|-----------|
| ≥ 800 kcal | +50 |
| ≥ 400 kcal | +35 |
| < 400 kcal | +15 |

- mood: +5 (항상)
- hp: +5 (항상)
- last_fed_at: UTC 현재 시각

---

## 9. 향후 기능 추가 예정

### 과거 식사 입력 시 흐름 제외
- 현재 시간 파악 → 저녁에 아침 메뉴 입력 or 전날 메뉴 입력 시
- 사진 분석 진행 + DB 저장은 동일
- **단**: 타마고치 수치 갱신 / Embed 업데이트 제외
- `is_past` 플래그 또는 시간 비교 로직으로 처리
- `time` 모듈 이미 import 되어 있음 (유지)

### 식사 전용 쓰레드 내 텍스트 입력도 처리
- 현재: 텍스트 입력은 먹구름봇 버튼에서만 가능
- 향후: 식사봇이 텍스트 메시지도 파싱하도록 확장 가능

---

## 10. bot_meal.py 전체 코드

```python
"""
bot_meal.py — 식사 전용 봇 진입점

역할: 사진 식사 입력 감지 / 칼로리 분석 / 영양소 / ML 보정
DB : 먹구름과 동일한 Supabase 공유
토큰: .env의 DISCORD_TOKEN_MEAL 사용
"""
import os
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv
from utils.db import init_db

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN_MEAL")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!meal_", intents=intents)
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
    print(f"[식사봇] {bot.user} 로그인 완료")

@bot.event
async def on_error(event, *args, **kwargs):
    import traceback
    traceback.print_exc()

async def main():
    async with bot:
        await bot.load_extension("cogs.meal")
        print("[식사봇] cogs.meal 로드 완료")
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 11. 개발 시 주의사항

- `on_message`는 모든 메시지에서 호출됨 → 빠른 필터링 우선 (봇 무시, 첨부파일 없음 무시)
- `is_meal_waiting()` DB 조회는 매 메시지마다 실행됨 → 쿼리 경량화 유지
- `MealPhotoConfirmView`의 `timeout=180` (3분) — 분석 후 유저가 기록 안 하면 자동 만료
- 이미지 분석 실패 시 `except` 처리로 에러 메시지 전송 (봇 크래시 방지)
