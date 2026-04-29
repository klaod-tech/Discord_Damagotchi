# 다음 작업 목록

> 기준: 2026-04-29

---

## 즉시 실행 가능 — 버그 수정

### BUG-3. `generate_comment_with_pattern()` 미연동 (`utils/gpt_ml_bridge.py`)

**증상:** ML 패턴 분석 결과가 다마고치 대사에 반영되지 않음. 함수는 구현됐지만 어디서도 호출되지 않는 데드코드  
**위치:** `utils/gpt_ml_bridge.py:34` — `weather_info` 파라미터 누락으로 `generate_comment` 호출 불일치

**수정 내용:**
```python
# utils/gpt_ml_bridge.py generate_comment_with_pattern() 내
comment = await generate_comment(
    context=...,
    user=user,
    today_calories=today_calories,
    recent_meals=meal_summary,
    weather_info=None,        # ← 누락된 파라미터 추가
    extra_context=full_context,
)
```

**연동 위치 (수정 후 교체):**
```python
# cogs/scheduler.py _nightly_analysis() 내
# 기존: generate_comment(...)
# 변경: generate_comment_with_pattern(user_id=..., user=..., daily_cal_target=..., ...)
```

---

### MAIL-1. 메일봇 `on_thread_create` 미추가 (`bot_mail.py`)

**증상:** 메일 스레드(`📧 {이름}의 메일함`) 생성 시 메일봇이 자동 참여하지 않음  
**수정:** `bot_mail.py`에 아래 이벤트 추가

```python
@bot.event
async def on_thread_create(thread: discord.Thread):
    if "메일" in thread.name:
        try:
            await thread.join()
        except Exception:
            pass
```

---

## 체중봇 기능 확장

### WEIGHT-2. 체중 기록 시 weight_thread에 공개 Embed 전송 (`cogs/weight.py`)

**현재:** `WeightInputModal.on_submit()` → ephemeral(본인만 보임)  
**목표:** `weight_thread_id` 스레드에 체중 기록 Embed 공개 전송

```python
# cogs/weight.py WeightInputModal.on_submit() 하단 추가

thread_id = user.get("weight_thread_id") or user.get("thread_id")
if thread_id and interaction.guild:
    thread = interaction.guild.get_thread(int(thread_id))
    if thread is None:
        try:
            ch = await interaction.guild.fetch_channel(int(thread_id))
            if isinstance(ch, discord.Thread):
                thread = ch
        except Exception:
            thread = None
    if thread:
        await thread.send(embed=weight_embed)

await interaction.followup.send("✅ 체중이 기록됐어!", ephemeral=True)
```

---

### WEIGHT-3. 체중 추이 그래프 (`cogs/weight.py`)

**필요 패키지:** `pip install matplotlib`

```python
import io
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

def generate_weight_graph(history: list[dict], goal_weight: float) -> io.BytesIO:
    dates   = [h["recorded_at"].strftime("%m/%d") for h in reversed(history[-14:])]
    weights = [h["weight"] for h in reversed(history[-14:])]

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(dates, weights, marker='o', color='#5865F2', linewidth=2)
    ax.axhline(y=goal_weight, color='#ED4245', linestyle='--', alpha=0.7, label=f'목표 {goal_weight}kg')
    ax.set_ylabel("체중 (kg)")
    ax.set_title("최근 체중 변화")
    ax.legend()
    plt.xticks(rotation=45, fontsize=8)
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100)
    buf.seek(0)
    plt.close()
    return buf
```

---

### WEIGHT-4. 칼로리 목표 자동 조정 제안 (`cogs/weight.py`)

```python
def _suggest_cal_adjustment(current_weight, goal_weight, history, current_target):
    if len(history) < 14:
        return None
    trend = history[0]["weight"] - history[-1]["weight"]
    if goal_weight < current_weight:
        if trend > 0:
            return current_target - 150
        if trend < -2:
            return current_target + 100
    elif goal_weight > current_weight:
        if trend < 0:
            return current_target + 150
    return None
```

---

## 신규 봇 구현

### BOT-1. 일기봇 cog (`cogs/diary.py`) — v3.4

**참고 문서:** `docs/bots/diary/`

**구현 순서:**
```
1. DB 마이그레이션 (init_db 내)
   CREATE TABLE IF NOT EXISTS diary_log (
     log_id     SERIAL PRIMARY KEY,
     user_id    TEXT,
     content    TEXT,
     emotion    TEXT,
     keywords   TEXT,
     written_at TIMESTAMP DEFAULT NOW()
   );

2. utils/db.py
   - create_diary_log(user_id, content, emotion, keywords)
   - get_diary_logs(user_id, limit=7)

3. cogs/diary.py
   - DiaryCog: on_message → diary_thread_id 감지
   - GPT 감정 분석 → diary_log 저장
   - 주간 감정 추이 Embed (/감정기록)

4. bot_diary.py
   - await bot.load_extension("cogs.diary") 주석 해제
```

---

### BOT-2. 일정봇 cog (`cogs/schedule.py`) — v3.5

**참고 문서:** `docs/bots/schedule/`

**구현 순서:**
```
1. DB 마이그레이션 (init_db 내)
   CREATE TABLE IF NOT EXISTS schedules (
     schedule_id  SERIAL PRIMARY KEY,
     user_id      TEXT,
     title        TEXT,
     scheduled_at TIMESTAMP,
     repeat_type  TEXT DEFAULT 'none',
     notified     BOOLEAN DEFAULT FALSE,
     created_at   TIMESTAMP DEFAULT NOW()
   );

2. utils/db.py
   - create_schedule / get_pending_schedules / mark_schedule_notified

3. cogs/schedule.py
   - APScheduler 1분 폴링 → pending 알림 전송
   - /일정추가, /일정목록 슬래시 커맨드

4. bot_schedule.py
   - await bot.load_extension("cogs.schedule") 주석 해제
```

---

## n8n 연동 — 음식 추천

### N8N-1. 음식 추천 스레드 생성 + n8n 웹훅 연동

**전제:** `.env`에 `N8N_FOOD_WEBHOOK_URL` 이미 등록됨

#### 1단계 — 온보딩 시 음식 추천 스레드 추가 (`cogs/onboarding.py`)

```python
# 기존 스레드 생성 블록 이후에 추가
food_thread = await personal_channel.create_thread(
    name=f"🍱 {name}의 음식 추천",
    type=discord.ChannelType.public_thread,
)
set_food_rec_thread_id(user_id, str(food_thread.id))
```

**DB:** `users` 테이블에 컬럼 추가
```sql
ALTER TABLE users ADD COLUMN IF NOT EXISTS food_rec_thread_id TEXT;
```

#### 2단계 — n8n 웹훅 호출 함수 (`utils/n8n.py`)

```python
import os, aiohttp

N8N_FOOD_URL = os.getenv("N8N_FOOD_WEBHOOK_URL")

async def request_food_recommendation(user_id: str, address: str, cal_remaining: int, mood: str = "") -> dict:
    """n8n 음식 추천 웹훅 호출 → 결과 dict 반환"""
    payload = {
        "user_id": user_id,
        "address": address,
        "cal_remaining": cal_remaining,
        "mood": mood,
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(N8N_FOOD_URL, json=payload, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            return await resp.json()
```

#### 3단계 — 음식 추천 버튼/트리거

**트리거 방식 (택1, 결정 필요):**
- A. 식사 기록 후 "🍽️ 오늘 저녁 뭐 먹을까?" 버튼 자동 표시 (잔여 칼로리 기반)
- B. 먹구름봇 메인 채널에서 "음식 추천" 키워드 감지 → 버튼 표시
- C. `/음식추천` 슬래시 커맨드

**응답 흐름:**
```
유저 트리거
  → bot.py or cogs/meal.py: request_food_recommendation() 호출
  → n8n: 주소 기반 주변 식당 검색 / GPT 음식 제안 / 잔여 칼로리 고려
  → n8n → HTTP Response (동기) 또는 Discord 웹훅 직접 전송
  → food_rec_thread_id 스레드에 추천 Embed 전송
```

**n8n → Discord 직접 전송 방식 (비동기 추천):**
n8n 워크플로우 안에서 Discord 웹훅 또는 봇 API로 직접 스레드에 메시지를 보내면
봇이 응답을 기다릴 필요 없음 → 타임아웃 위험 없음.

```python
# n8n이 직접 전송하는 경우 봇 쪽 코드는 단순히 요청만 보냄
await request_food_recommendation(user_id, address, cal_remaining)
# "음식 추천 중... 🍱 스레드를 확인해줘!" ephemeral 안내
```

#### 4단계 — `bot_meal.py` / `bot.py` on_thread_create 추가

```python
@bot.event
async def on_thread_create(thread: discord.Thread):
    if "음식" in thread.name or "추천" in thread.name:
        try:
            await thread.join()
        except Exception:
            pass
```

---

## 작업 순서 권장

```
[즉시]
  1. MAIL-1   bot_mail.py on_thread_create 추가
  2. BUG-3    gpt_ml_bridge 연동 활성화   utils/gpt_ml_bridge.py + cogs/scheduler.py

[다음]
  3. WEIGHT-2  체중 스레드 공개 Embed     cogs/weight.py
  4. WEIGHT-3  체중 추이 그래프           cogs/weight.py
  5. N8N-1     음식 추천 스레드 + n8n 연동 (트리거 방식 결정 후)

[이후]
  6. WEIGHT-4  칼로리 자동 조정
  7. BOT-1     일기봇 cog
  8. BOT-2     일정봇 cog
```
