# 다음 작업 목록

> 기준: 2026-04-28 | exp 브랜치 커밋 이후 상태

---

## 즉시 실행 가능 — 버그 수정

### BUG-1. 식약처 검색어 전처리 (`utils/nutrition.py`)

**증상:** "샌드위치 2개", "라면 1인분" 처럼 숫자+단위가 붙은 검색어 → API 500 오류 → GPT fallback 강제 발생  
**위치:** `utils/nutrition.py:62` — `FOOD_NM_KOR` 파라미터에 전처리 없이 raw food_name 전달  

**수정 내용:**
```python
# utils/nutrition.py search_food_nutrition() 진입부에 추가

def _clean_food_name(name: str) -> str:
    """숫자+단위 제거: '샌드위치 2개' → '샌드위치'"""
    name = re.sub(r'\d+(\.\d+)?\s*(개|인분|그릇|접시|조각|장|캔|병|컵|잔|봉|팩)', '', name)
    return name.strip()

# search_food_nutrition() 내
food_name_clean = _clean_food_name(food_name)
params = {
    ...
    "FOOD_NM_KOR": food_name_clean,
}
```

---

### BUG-2. 사진 대기 만료 안내 메시지 없음 (`cogs/meal.py`)

**증상:** 60초 대기 만료 후 사진을 올려도 조용히 무시됨 (아무 반응 없음)  
**위치:** `cogs/meal.py` `on_message()` — `is_meal_waiting()` false 분기에 안내 없음  

**수정 내용:**
```python
# cogs/meal.py on_message() 내 이미지 감지 블록 수정

if image_attachments:
    image_url = image_attachments[0].url

    if is_meal_waiting(user_id):
        # 기존 로직 유지
        ...
        return

    # 만료 여부 확인 (meal_waiting_until이 과거 → 만료)
    waiting_until = user.get("meal_waiting_until")
    if waiting_until:
        from datetime import timezone
        now = datetime.now(timezone.utc)
        exp = waiting_until if waiting_until.tzinfo else waiting_until.replace(tzinfo=timezone.utc)
        if now > exp:
            await message.channel.send(
                f"<@{message.author.id}> 사진 입력 시간이 초과됐어요. 다시 📸 버튼을 눌러주세요!",
                delete_after=10,
            )
            return

    # 직접 업로드 경로 (기존 로직)
    detect_view = MealPhotoDetectView(...)
    ...
```

---

### BUG-3. `generate_comment_with_pattern()` 미연동 (`utils/gpt_ml_bridge.py`)

**증상:** ML 패턴 분석 결과가 다마고치 대사에 반영되지 않음. 함수는 구현됐지만 어디서도 호출되지 않는 데드코드  
**위치:** `utils/gpt_ml_bridge.py:34` — 함수 존재하나 `weather_info` 파라미터 누락으로 `generate_comment` 호출 불일치 가능성  

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

## 즉시 실행 가능 — 체중봇 분리

### WEIGHT-1. `bot_weight.py` 활성화 + `bot.py`에서 제거

**수정 내용 (2파일):**

```python
# bot_weight.py main() 수정
async def main():
    async with bot:
        await bot.load_extension("cogs.weight")   # 주석 해제
        await bot.start(TOKEN)
```

```python
# bot.py COGS 목록에서 제거
COGS = [
    "cogs.onboarding",
    "cogs.summary",
    "cogs.settings",
    "cogs.time_settings",
    "cogs.scheduler",
    # "cogs.weight",   ← 이 줄 삭제
]
```

**확인 순서:**
1. `python bot_weight.py` 실행 → `[체중관리봇] 로그인 완료` 출력 확인
2. `python bot.py` 실행 → `/체중기록` 슬래시 커맨드가 bot_weight.py에서만 등록되는지 확인

---

## 체중봇 기능 확장

### WEIGHT-2. 체중 기록 시 weight_thread에 공개 Embed 전송 (`cogs/weight.py`)

**현재:** `WeightInputModal.on_submit()` → ephemeral(본인만 보임)  
**목표:** `weight_thread_id` 쓰레드에 체중 기록 Embed 공개 전송

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
        await thread.send(embed=weight_embed)   # 기존 embed 재사용

await interaction.followup.send("✅ 체중이 기록됐어!", ephemeral=True)
```

---

### WEIGHT-3. 체중 추이 그래프 (`cogs/weight.py`)

**필요 패키지:** `pip install matplotlib`

```python
# cogs/weight.py 상단 추가
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

# on_submit() 내 사용
if len(history) >= 2:
    graph_buf  = generate_weight_graph(history, goal_weight)
    graph_file = discord.File(graph_buf, filename="weight_chart.png")
    embed.set_image(url="attachment://weight_chart.png")
    await thread.send(file=graph_file, embed=weight_embed)
```

---

### WEIGHT-4. 칼로리 목표 자동 조정 제안 (`cogs/weight.py`)

```python
# cogs/weight.py — on_submit() 내 체중 저장 후 실행

def _suggest_cal_adjustment(current_weight, goal_weight, history, current_target):
    if len(history) < 14:
        return None
    trend = history[0]["weight"] - history[-1]["weight"]  # 2주 변화량
    if goal_weight < current_weight:     # 감량 목표
        if trend > 0:                    # 오히려 증가
            return current_target - 150
        if trend < -2:                   # 너무 빠른 감량
            return current_target + 100
    elif goal_weight > current_weight:   # 증량 목표
        if trend < 0:
            return current_target + 150
    return None

# 사용
history    = get_weight_history(user_id, limit=14)
new_target = _suggest_cal_adjustment(current_weight, goal_weight, history, base_cal)
if new_target:
    # CalAdjustView 버튼으로 유저 확인 후 update_user(user_id, daily_cal_target=new_target)
    await thread.send(
        f"📊 최근 체중 추이를 보니 칼로리 목표를 **{base_cal}** → **{new_target} kcal**로 조정하면 어때요?",
        view=CalAdjustView(user_id, new_target),
    )
```

---

## 신규 봇 구현

### BOT-1. 일기봇 (`bot_diary.py`) — v3.4

**참고 문서:** `docs/bots/diary/`

**구현 순서:**
```
1. DB 마이그레이션
   ALTER TABLE users ADD COLUMN IF NOT EXISTS diary_thread_id TEXT;
   CREATE TABLE IF NOT EXISTS diary_log (
     log_id     SERIAL PRIMARY KEY,
     user_id    TEXT,
     content    TEXT,
     emotion    TEXT,        -- GPT 분석: 긍정/부정/중립
     keywords   TEXT,        -- JSON 배열
     written_at TIMESTAMP DEFAULT NOW()
   );

2. utils/db.py
   - set_diary_thread_id(user_id, thread_id)
   - create_diary_log(user_id, content, emotion, keywords)
   - get_diary_logs(user_id, limit=7)

3. cogs/diary.py
   - DiaryCog: on_message → 일기 쓰레드 텍스트 감지
   - DiaryInputModal: 제목 없는 자유 텍스트 입력
   - GPT 감정 분석 → diary_log 저장
   - 주간 감정 추이 Embed (/감정기록)

4. bot_diary.py
   - DISCORD_TOKEN_DIARY 환경변수 사용
   - thread_helper.join_assigned_threads(bot, "diary_thread_id")

5. cogs/onboarding.py
   - 온보딩 시 "📔 {이름}의 일기장" 쓰레드 추가 생성
   - set_diary_thread_id() 호출
```

**GPT 감정 분석 프롬프트 예시:**
```python
prompt = (
    f'다음 일기를 읽고 감정을 분석해줘.\n'
    f'일기: "{content}"\n\n'
    '{"emotion": "긍정/부정/중립 중 하나", "keywords": ["감정 키워드1", "키워드2"]}\n'
    'JSON으로만 답해줘.'
)
```

---

### BOT-2. 일정봇 (`bot_schedule.py`) — v3.5

**참고 문서:** `docs/bots/schedule/`

**구현 순서:**
```
1. DB 마이그레이션
   ALTER TABLE users ADD COLUMN IF NOT EXISTS schedule_thread_id TEXT;
   CREATE TABLE IF NOT EXISTS schedules (
     schedule_id  SERIAL PRIMARY KEY,
     user_id      TEXT,
     title        TEXT,
     scheduled_at TIMESTAMP,
     repeat_type  TEXT DEFAULT 'none',   -- none | daily | weekly
     notified     BOOLEAN DEFAULT FALSE,
     created_at   TIMESTAMP DEFAULT NOW()
   );

2. utils/db.py
   - set_schedule_thread_id(user_id, thread_id)
   - create_schedule(user_id, title, scheduled_at, repeat_type)
   - get_pending_schedules()      -- notified=false AND scheduled_at <= NOW()
   - mark_schedule_notified(schedule_id)

3. cogs/schedule.py
   - ScheduleCog: APScheduler 1분 폴링 → pending 알림 전송
   - ScheduleInputModal: 날짜+시간+내용 입력
   - /일정추가, /일정목록 슬래시 커맨드

4. bot_schedule.py
   - DISCORD_TOKEN_SCHEDULE 환경변수 사용
   - thread_helper.join_assigned_threads(bot, "schedule_thread_id")

5. cogs/onboarding.py
   - 온보딩 시 "📅 {이름}의 일정표" 쓰레드 추가 생성
```

---

## 작업 순서 권장

```
[즉시]
  1. BUG-1  식약처 검색어 전처리       utils/nutrition.py    ★ 5분
  2. BUG-2  사진 대기 만료 안내        cogs/meal.py          ★ 10분
  3. WEIGHT-1  체중봇 분리             bot_weight.py, bot.py ★ 5분

[다음]
  4. BUG-3  gpt_ml_bridge 연동 활성화 utils/gpt_ml_bridge.py
  5. WEIGHT-2  체중 쓰레드 공개 Embed  cogs/weight.py
  6. WEIGHT-3  체중 추이 그래프        cogs/weight.py

[이후]
  7. WEIGHT-4  칼로리 자동 조정
  8. BOT-1     일기봇
  9. BOT-2     일정봇
```
