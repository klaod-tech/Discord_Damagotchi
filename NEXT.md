# 다음 작업 목록

> 기준: 2026-04-29 | 이번 세션 작업 이후 상태

---

## ✅ 완료된 항목 (이번 세션)

| 항목 | 내용 |
|------|------|
| BUG-1 | `utils/nutrition.py` 수량 파싱 (`_parse_food_and_quantity`) + API 결과 이름 검증 |
| BUG-2 | `cogs/meal.py` 사진 대기 만료 안내 메시지 추가 |
| BUG-3 (일부) | 카테고리 재질문 기능 (`MEAL_CATEGORIES` 감지 → clarification 재요청) |
| WEIGHT-1 | `bot_weight.py` 분리 활성화, `bot.py`에서 `cogs.weight` 제거 |
| 인프라 | `all_bots.py` — 7개 봇 한 번에 실행 |
| 인프라 | `/리셋` 슬래시 커맨드 구현 (채널 삭제 + DB 초기화) |
| 인프라 | 시간 설정 1단계 안내 문구 추가 (`onboarding.py`) |
| **아키텍처** | **유저 전용 비공개 채널 방식으로 전환** (스레드 join 문제 근본 해결) |

### 아키텍처 변경 상세 (Private Channel)
- **이전:** 공유 채널(`#먹구름`)에 비공개 스레드 → 서브봇 join 불가
- **현재:** 시작하기 클릭 시 `{이름}의 먹구름` 비공개 채널 생성
  - `@everyone` 차단, 유저 + 모든 봇 권한 부여
  - 채널 내 공개 스레드 5개 (메인/메일/식사/날씨/체중)
  - 봇들이 채널 권한으로 자동 접근 → 별도 join 불필요
- **DB:** `user_channel_id` 컬럼 추가
- **서브봇:** `on_thread_create` / `join_assigned_threads` 제거 (bot_meal/weather/weight/mail)
- **리셋:** 채널 하나 삭제로 단순화 (스레드 자동 삭제)

> ⚠️ **테스트 필요:** 봇 재시작 후 시작하기 → 채널 생성 + 스레드 참여 확인

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
     emotion    TEXT,
     keywords   TEXT,
     written_at TIMESTAMP DEFAULT NOW()
   );

2. utils/db.py
   - set_diary_thread_id(user_id, thread_id)
   - create_diary_log(user_id, content, emotion, keywords)
   - get_diary_logs(user_id, limit=7)

3. cogs/diary.py
   - DiaryCog: on_message → 일기 스레드 텍스트 감지
   - GPT 감정 분석 → diary_log 저장
   - 주간 감정 추이 Embed (/감정기록)

4. bot_diary.py
   - DISCORD_TOKEN_DIARY 환경변수 사용
   - on_ready: init_db() 만 (thread_helper 불필요 — 채널 권한으로 자동 접근)

5. cogs/onboarding.py
   - 온보딩 시 "📔 {이름}의 일기장" 스레드 추가 생성 (user_channel 내부)
   - set_diary_thread_id() 호출
   - BOT_CLIENT_IDS에 DIARY bot ID 이미 포함됨
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
     repeat_type  TEXT DEFAULT 'none',
     notified     BOOLEAN DEFAULT FALSE,
     created_at   TIMESTAMP DEFAULT NOW()
   );

2. utils/db.py
   - set_schedule_thread_id(user_id, thread_id)
   - create_schedule / get_pending_schedules / mark_schedule_notified

3. cogs/schedule.py
   - APScheduler 1분 폴링 → pending 알림 전송
   - /일정추가, /일정목록 슬래시 커맨드

4. bot_schedule.py
   - DISCORD_TOKEN_SCHEDULE 환경변수 사용
   - on_ready: init_db() 만 (thread_helper 불필요)

5. cogs/onboarding.py
   - "📅 {이름}의 일정표" 스레드 추가 생성 (user_channel 내부)
```

---

## 작업 순서 권장

```
[즉시 — 테스트]
  0. 봇 재시작 후 시작하기 클릭 → 비공개 채널 + 스레드 생성 확인 ⚠️

[다음]
  1. BUG-3  gpt_ml_bridge 연동 활성화   utils/gpt_ml_bridge.py + cogs/scheduler.py
  2. WEIGHT-2  체중 스레드 공개 Embed   cogs/weight.py
  3. WEIGHT-3  체중 추이 그래프         cogs/weight.py

[이후]
  4. WEIGHT-4  칼로리 자동 조정
  5. BOT-1     일기봇
  6. BOT-2     일정봇
```
