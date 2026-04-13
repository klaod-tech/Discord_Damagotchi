# 체중관리봇 — 체중 기록 흐름

---

## 1. 현재 흐름 (먹구름봇에서 처리)

```
유저: "⚖️ 체중 기록" 클릭 (MainView 버튼)
  → weight_button() (utils/embed.py)
  → send_modal(WeightInputModal)

유저: 체중 입력 (예: "75.3")
  → WeightInputModal.on_submit()
  → 파싱: float("75.3") = 75.3
  → 유효성: 20.0 ≤ weight ≤ 300.0
  → save_weight_log(user_id, weight)
  → 비교 계산:
       goal_weight = user.goal_weight
       init_weight = user.init_weight
       prev_weight = get_latest_weight_before(user_id)  ← 직전 기록
       diff_from_goal = weight - goal_weight
       diff_from_prev = weight - prev_weight
  → 컨텍스트 결정:
       diff_from_goal <= 0 → "목표 달성!" (goal_achieved=True)
       diff_from_prev < 0  → "감소! 칭찬해줘!"
       diff_from_prev > 0  → "증가. 걱정하지만 응원해줘!"
       else                → "유지. 응원해줘!"
  → generate_comment(context)
  → 프로그레스 바:
       total_diff = |init_weight - goal_weight|
       done_diff  = |init_weight - weight|
       ratio = done_diff / total_diff (최대 1.0)
       bar = "█" * int(ratio*10) + "░" * (10 - int(ratio*10))
  → Embed 전송 (ephemeral=True):
       - 현재 체중 + 변화 (▲/▼/→)
       - 목표 체중 + 남은 몸무게
       - 달성률 바
       - 타마고치 한마디
  → goal_achieved=True 시:
       thread_id = weight_thread_id or thread_id
       create_or_update_embed(goal_achieved=True)  ← cheer.png
```

---

## 2. 프로그레스 바 계산 예시

```
init_weight = 76kg, goal_weight = 70kg, current = 73kg

total_diff = |76 - 70| = 6kg
done_diff  = |76 - 73| = 3kg
ratio = 3/6 = 0.5
filled = int(0.5 * 10) = 5
bar = "█████░░░░░" 50%
```

---

## 3. 체중 변화 텍스트

```python
diff_from_prev > 0 → "▲ {diff_from_prev}kg 증가"
diff_from_prev < 0 → "▼ {abs(diff_from_prev)}kg 감소"
else               → "→ 변화 없음"
```

---

## 4. 목표 달성 판정

```python
if diff_from_goal <= 0:  # weight <= goal_weight
    goal_achieved = True
    # → cheer.png 이미지
    # → weight_thread_id or thread_id 쓰레드에 Embed 갱신
```

---

## 5. 향후 체중관리봇 분리 계획

현재 `WeightCog`는 먹구름봇(bot.py)에 로드됨.  
Phase 1 이전 후:

```
bot_weight.py → cogs.weight 로드
bot.py → cogs.weight 제거

WeightCog에 추가:
  - 체중 전용 쓰레드(weight_thread_id)에 기록 알림
  - 체중 추이 그래프 (7일/30일)
  - 주간 체중 변화 요약 알림
```

→ `weight/ROADMAP.md` 참조
