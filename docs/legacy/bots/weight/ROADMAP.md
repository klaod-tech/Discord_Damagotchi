# 체중관리봇 (bot_weight.py) 제작 로드맵

> last_updated: 2026-04-13 | 현재 버전: skeleton 🔄

---

## 현재 상태

| 파일 | 상태 |
|------|------|
| `cogs/weight.py` | ✅ WeightCog + WeightInputModal + DB 함수 구현 완료 |
| `bot.py` | ✅ `cogs.weight` 로드 중 (임시) |
| `bot_weight.py` | 🔄 skeleton — cogs.weight 미활성화 |
| `utils/db.py` | ✅ `weight_thread_id` 컬럼, `set_weight_thread_id()`, `get_weight_history()` 구현 |

---

## Phase 1 — 봇 분리 (v3.3 최우선)

### 1-1. bot_weight.py 활성화

```python
# bot_weight.py 현재 (skeleton)
async def main():
    async with bot:
        # await bot.load_extension("cogs.weight")  ← 주석 해제
        await bot.start(TOKEN)

# → 수정 후
async def main():
    async with bot:
        await bot.load_extension("cogs.weight")
        await bot.start(TOKEN)
```

### 1-2. bot.py에서 weight Cog 제거

```python
# bot.py COGS 목록
COGS = [
    "cogs.onboarding",
    "cogs.summary",
    "cogs.settings",
    "cogs.time_settings",
    "cogs.scheduler",
    # "cogs.weight",  ← 이 줄 제거
]
```

### 1-3. WeightInputModal import 경로 확인

`utils/embed.py`의 `weight_button` 콜백은 `WeightInputModal`을 직접 import.  
Cog를 언로드해도 Modal은 동작 → **import 경로는 건드리지 않음**.

```python
# utils/embed.py — 변경 없이 유지
from cogs.weight import WeightInputModal
```

### 1-4. 배포 순서

```
1. bot_weight.py 활성화 (주석 해제)
2. bot.py에서 cogs.weight 제거
3. 두 봇 동시 실행 테스트:
   python bot.py
   python bot_weight.py
4. /체중기록 슬래시 커맨드가 bot_weight.py에서 등록되는지 확인
5. bot.py에서 /체중기록 더 이상 보이지 않는지 확인
```

---

## Phase 2 — 체중 전용 쓰레드 알림 (v3.3)

현재 `WeightInputModal.on_submit()` → ephemeral(유저만 보임)  
→ `weight_thread_id` 쓰레드에 공개 Embed로 전환

```python
# cogs/weight.py WeightInputModal.on_submit() 수정

async def on_submit(self, interaction: discord.Interaction):
    # 기존 로직 (체중 저장, 목표 달성 판정) 유지
    user = get_user(str(interaction.user.id))
    
    # 체중 전용 쓰레드에 공개 전송
    thread_id = user.get("weight_thread_id") or user.get("thread_id")
    if thread_id:
        guild = interaction.guild
        thread = guild.get_thread(int(thread_id))
        if thread:
            await thread.send(embed=weight_embed)
    
    # ephemeral 확인 메시지는 제거 or 간략화
    await interaction.response.send_message("체중이 기록됐어요!", ephemeral=True)
```

---

## Phase 3 — 기능 확장 (v3.4)

### 3-1. 체중 추이 그래프

```python
# cogs/weight.py — 그래프 생성 함수 추가
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import io

def generate_weight_graph(history: list[dict], goal_weight: float) -> io.BytesIO:
    # KST 기준 날짜 포맷
    dates = [h["recorded_at"].strftime("%m/%d") for h in reversed(history[-14:])]
    weights = [h["weight"] for h in reversed(history[-14:])]

    plt.figure(figsize=(8, 4))
    plt.plot(dates, weights, marker='o', color='#5865F2', linewidth=2)
    plt.axhline(y=goal_weight, color='#ED4245', linestyle='--', alpha=0.7, label=f'목표 {goal_weight}kg')
    plt.xticks(rotation=45, fontsize=8)
    plt.ylabel("체중 (kg)")
    plt.title("최근 체중 변화", pad=12)
    plt.legend()
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100)
    buf.seek(0)
    plt.close()
    return buf
```

사용:
```python
graph_buf = generate_weight_graph(history, goal_weight)
graph_file = discord.File(graph_buf, filename="weight_chart.png")
await thread.send(file=graph_file, embed=weight_embed)
```

### 3-2. 달성률 시각화 (진행 바)

현재 달성률 계산 로직은 있으나 텍스트 진행 바 형태.  
→ 그래프 추가로 시각적 보완.

```python
def build_progress_bar(current: float, start: float, goal: float) -> str:
    # 감량 목표: start > goal
    total = abs(start - goal)
    done  = abs(start - current)
    pct   = min(done / total, 1.0) if total > 0 else 1.0
    
    filled = int(pct * 10)
    bar = "█" * filled + "░" * (10 - filled)
    return f"{bar} {pct*100:.0f}%"
```

### 3-3. 주간 체중 요약 (APScheduler)

먹구름봇 `_weekly_report()`의 체중 섹션을 체중관리봇으로 이전.

```python
# cogs/weight.py — WeightCog에 추가
@scheduler.scheduled_job('cron', day_of_week='sun', hour=8, minute=30, timezone='Asia/Seoul')
async def weekly_weight_report():
    users = get_all_users()
    for user in users:
        history = get_weight_history(user["user_id"], limit=7)
        if not history: continue

        first = history[-1]["weight"]
        last  = history[0]["weight"]
        diff  = last - first  # 음수 = 감량

        trend = f"이번 주 {'감량' if diff < 0 else '증가'} {abs(diff):.1f}kg"
        # thread에 주간 체중 Embed 전송
```

---

## Phase 4 — 칼로리 목표 자동 재산출 (v3.4)

> 체중 변화에 따라 `daily_cal_target` 자동 조정

### 4-1. 로직

```python
# cogs/weight.py WeightInputModal.on_submit() 내 추가

def suggest_cal_adjustment(current_weight, goal_weight, recent_history, current_target):
    """
    최근 2주간 체중 변화 추이로 칼로리 조정 제안
    """
    if len(recent_history) < 14:
        return None  # 데이터 부족

    trend = recent_history[0]["weight"] - recent_history[-1]["weight"]  # 2주 변화량

    if goal_weight < current_weight:  # 감량 목표
        if trend > 0:  # 체중이 오히려 증가
            return current_target - 150  # 150kcal 감소
        if trend < -2:  # 너무 빠른 감량 (주 1kg+ 이상)
            return current_target + 100  # 100kcal 증가 (근손실 방지)
    elif goal_weight > current_weight:  # 증량 목표
        if trend < 0:
            return current_target + 150

    return None  # 조정 불필요
```

### 4-2. 유저 확인 후 적용

```python
new_target = suggest_cal_adjustment(...)
if new_target:
    await thread.send(
        embed=discord.Embed(
            description=f"칼로리 목표를 {current_target} → {new_target} kcal로 조정하면 어때요?",
            color=0x57F287
        ).add_field(name="적용하기", value="아래 버튼을 눌러주세요"),
        view=CalAdjustView(user_id, new_target)
    )
```

---

## Phase 5 — ML 연동 (v4.0)

### 5-1. 식사봇 ML과 연계

```python
# 체중 변화 vs 칼로리 섭취 상관관계
# utils/ml.py WeightCorrelationModel 추가

# 입력 피처
features = [
    "avg_daily_calories_7d",   # 7일 평균 칼로리
    "protein_ratio",           # 단백질 비율
    "carb_ratio",              # 탄수화물 비율
    "meal_regularity_score",   # 규칙적 식사 점수
]
# 레이블: 주간 체중 변화량 (kg)
```

### 5-2. 강화학습 피드백 루프

```
체중 감소 → 이전 주 식사 패턴 "긍정" 강화
체중 증가 → "부정" 피드백
→ ML이 개인화 칼로리 권장량 자동 학습
```

---

## 주요 파일 위치

| 파일 | 역할 |
|------|------|
| `bot_weight.py` | 봇 진입점 (현재 skeleton) |
| `cogs/weight.py` | WeightCog, WeightInputModal, DB 함수 |
| `utils/db.py` | `get_weight_history()`, `create_weight_log()`, `set_weight_thread_id()` |

---

## DB 테이블 소유

```sql
weight_log (
  log_id      SERIAL PRIMARY KEY,
  user_id     TEXT REFERENCES users,
  weight      REAL NOT NULL,
  recorded_at TIMESTAMP DEFAULT NOW()
)

-- users 테이블 관련 컬럼
users.init_weight    REAL    -- 시작 체중
users.goal_weight    REAL    -- 목표 체중
users.weight_thread_id TEXT  -- 체중관리봇 전용 쓰레드
```

---

## 환경변수

| 변수명 | 상태 | 설명 |
|--------|------|------|
| `DISCORD_TOKEN_WEIGHT` | 📋 발급 필요 | 체중관리봇 토큰 |

---

## 제작 순서 요약

```
Step 1 (즉시) — bot_weight.py 주석 해제, bot.py cogs.weight 제거
Step 2         — weight_thread_id 쓰레드 공개 Embed 전환
Step 3 (v3.4)  — 체중 추이 그래프 (matplotlib)
Step 4 (v3.4)  — 주간 체중 요약 APScheduler
Step 5 (v3.4)  — 칼로리 목표 자동 조정 로직
Step 6 (v4.0)  — 식사 ML 연동, 강화학습 피드백
```
