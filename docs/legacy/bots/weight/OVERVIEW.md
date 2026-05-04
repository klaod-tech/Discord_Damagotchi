# 체중관리봇 — 오버뷰

---

## 1. 봇 기본 정보

| 항목 | 내용 |
|------|------|
| 봇 파일 | `bot_weight.py` |
| 토큰 환경변수 | `DISCORD_TOKEN_WEIGHT` |
| 커맨드 prefix | `!weight_` |
| 담당 Cog | `cogs/weight.py` → `WeightCog` |
| 응답 위치 | `users.personal_channel_id` (v4.0~, 직접 응답), fallback: `thread_id` |
| 담당 DB 테이블 | `weight_log` (소유) |
| 현재 상태 | 🔄 skeleton (WeightCog 구현됨, bot_weight.py는 아직 미활성화) |

---

## 2. 현재 상태

### 구현된 것 (cogs/weight.py)
- `WeightInputModal`: 체중 입력 Modal (숫자 파싱, 유효성 검증 20~300kg)
- `WeightCog`: Cog 클래스 (현재 먹구름봇 bot.py에서 로드)
- DB 함수 (cogs/weight.py 내 정의):
  - `save_weight_log(user_id, weight)`
  - `get_weight_history(user_id, limit=7)` → `[{weight, recorded_at}]`
  - `get_latest_weight(user_id)` → `float | None`
  - `get_latest_weight_before(user_id)` → 직전 체중

### 미구현 / 예정
- `bot_weight.py`에 cogs.weight 로드 활성화 (현재 skeleton)
- 체중 전용 쓰레드에 알림 전송 (현재 먹구름봇 메인 쓰레드에 전송)
- 체중 추이 그래프 (matplotlib 예정)
- 체중 기반 칼로리 목표 자동 재산출

---

## 3. WeightInputModal 동작 (현재 먹구름봇에서 처리)

1. 유저: "⚖️ 체중 기록" 클릭 (먹구름봇 메인 버튼)
2. `WeightInputModal` 팝업
3. 체중 입력 (kg) → 파싱
4. `save_weight_log(user_id, weight)`
5. 목표 달성 여부 판정:
   - `weight <= goal_weight` → goal_achieved = True → cheer.png
   - 전날 대비 감소 → 칭찬
   - 전날 대비 증가 → 부드러운 걱정
   - 유지 → 응원
6. 프로그레스 바 계산: `(init_weight → weight) / (init_weight → goal_weight)`
7. Embed 전송 (ephemeral=True)
8. 목표 달성 시: `personal_channel_id or thread_id` 채널에 `create_or_update_embed(goal_achieved=True)`

---

## 4. 주간 리포트에서 체중 데이터 사용

먹구름봇 `_weekly_report()`에서:

```python
from cogs.weight import get_weight_history

weight_history = get_weight_history(user_id, limit=7)
# w_start = 7일 전 / w_end = 최근
# weight_text = f"{w_start}kg → {w_end}kg ({sign}{w_diff}kg)"
```

---

## 5. 하루 정리에서 체중 데이터 사용

먹구름봇 `daily_button()`에서:

```python
weight_history = get_weight_history(user_id, limit=7)
current_weight = weight_history[0]["weight"]
# 체중 변화에 따라 target_cal 조율:
# 체중 증가(>0.3kg) → base_cal * 0.95
# 체중 감소(<-0.3kg, 목표>2kg) → base_cal * 1.05
```
