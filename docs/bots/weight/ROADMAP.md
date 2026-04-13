# 체중관리봇 — 이전 절차 및 구현 로드맵

---

## 현재 상태

- `cogs/weight.py`: WeightCog + WeightInputModal + DB 함수 구현 완료
- `bot.py`: `cogs.weight` 로드 중 (먹구름봇에서 처리)
- `bot_weight.py`: skeleton (cogs.weight 로드 미활성화)
- 분리 브랜치: `feat/weight-migration`

---

## Phase 1: 봇 분리

### 1-1. bot_weight.py 활성화

```python
# bot_weight.py main() 수정
async def main():
    async with bot:
        await bot.load_extension("cogs.weight")
        await bot.start(TOKEN)
```

### 1-2. bot.py에서 weight cog 제거

```python
# bot.py COGS 목록에서 "cogs.weight" 제거
# 주의: WeightInputModal은 utils/embed.py의 weight_button에서 import
#       → bot.py에서도 WeightInputModal이 필요하므로 import만 유지
```

### 1-3. Cog 중복 방지

- `WeightCog`는 반드시 한 봇에서만 로드 (슬래시 커맨드 충돌 방지)
- 먹구름봇 `weight_button`은 `WeightInputModal`을 직접 import → Cog 없어도 동작

---

## Phase 2: 체중 전용 쓰레드 알림 추가

```python
# WeightInputModal.on_submit() 수정
# 현재: ephemeral=True (유저에게만 보임)
# 변경: weight_thread_id 쓰레드에 공개 Embed 전송

thread_id = user.get("weight_thread_id") or user.get("thread_id")
if thread_id:
    thread = guild.get_thread(int(thread_id))
    if thread:
        await thread.send(embed=weight_embed)
```

---

## Phase 3: 기능 확장

### 체중 추이 그래프
```python
# matplotlib으로 7일/30일 체중 추이 그래프 생성
# PNG 파일 → discord.File → thread.send(file=graph_file)
import matplotlib.pyplot as plt
import io

def generate_weight_graph(history: list[dict]) -> io.BytesIO:
    dates = [h["recorded_at"].strftime("%m/%d") for h in reversed(history)]
    weights = [h["weight"] for h in reversed(history)]
    plt.figure(figsize=(8, 4))
    plt.plot(dates, weights, marker='o', color='#5865F2')
    plt.axhline(goal_weight, color='red', linestyle='--', label='목표')
    plt.title("체중 변화")
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()
    return buf
```

### 주간 체중 알림 (APScheduler)
```python
# 매주 일요일 체중관리봇 전용 주간 요약
# 먹구름봇 _weekly_report()의 체중 섹션을 체중관리봇으로 이전
```

### 칼로리 목표 자동 재산출
```python
# 체중 기록 시 goal_weight와의 diff 계산
# diff > 2kg → daily_cal_target 재산출 제안
# update_user(daily_cal_target=new_cal) 자동 적용
```

---

## Phase 4: ML 연동

### 식사봇 ML과 연계
- `weight_log` 데이터를 `meals` 데이터와 결합
- 칼로리 섭취 vs 체중 변화 상관관계 학습
- 개인화 칼로리 권장량 자동 조정

### 강화학습 피드백
- 체중 감소 시 → 이전 기간 칼로리 조합이 "좋은" 선택
- 체중 증가 시 → "나쁜" 선택으로 ML 모델에 피드백

---

## 주의사항

- `get_weight_history()`와 `get_latest_weight_before()` 함수는  
  먹구름봇 `scheduler.py`와 `embed.py`에서도 import → 이전 후에도 이 함수들은 공개 유지
- DB 함수는 이전 시 `utils/db.py`로 이동 권장 (현재는 cogs/weight.py에 임시 위치)
