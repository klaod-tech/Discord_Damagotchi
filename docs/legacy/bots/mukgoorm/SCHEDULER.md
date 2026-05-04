# 먹구름봇 스케줄러 — APScheduler Job 전체 목록

> `cogs/scheduler.py` — `SchedulerCog` (AsyncIOScheduler)

---

## 1. 고정 Job (모든 유저 공통)

| Job ID | 시간 | 함수 | 설명 |
|--------|------|------|------|
| `nightly_analysis` | 매일 22:00 | `_nightly_analysis()` | 당일 칼로리 판정 + 스트릭 + 배지 |
| `hourly_hunger_decay` | 매 시간 정각 | `_hourly_hunger_decay()` | 전체 유저 hunger -5 |
| `weekly_ml_retrain` | 매주 일요일 03:00 | `_weekly_ml_retrain()` | ML 칼로리 모델 재학습 |
| `weekly_report` | 매주 일요일 08:00 | `_weekly_report()` | 주간 리포트 Embed 전송 |

---

## 2. 유저별 식사 알림 Job (동적 등록)

유저 1명당 3끼 × 3 Job = 최대 9개 등록. `register_meal_jobs(user_id)` 호출 시점:
- 온보딩 완료 시 (`on_submit`)
- 시간 설정 변경 시 (`TimeStep4View` 완료)

| Job ID 패턴 | 시간 | 함수 | 설명 |
|------------|------|------|------|
| `meal_pre_{user_id}_{끼니}` | 식사시간 -30분 | `_meal_reminder()` | 배고픔 예고 메시지 |
| `meal_upset_{user_id}_{끼니}` | 식사시간 정각 | `_meal_upset()` | 미입력 시 upset.png 교체 + 대사 |
| `meal_late_{user_id}_{끼니}` | 식사시간 +1시간 | `_meal_late()` | 미입력 시 추가 대사 |

---

## 3. 각 Job 상세

### `_nightly_analysis()` — 매일 22:00

```
1. get_all_users() → 전체 유저 순회
2. 오늘 식사 기록 없음 → 스트릭 초기화 + 경고 메시지
3. 식사 있음 → _send_daily_analysis() 호출 (일일 결산 Embed)
4. 스트릭 계산: prev + 1 → update_streak()
5. 배지 체크: check_new_badges() → 새 배지 있으면 add_badges() + Embed 알림
6. 배지 달성 시 create_or_update_embed(goal_achieved=True) — cheer.png
```

### `_hourly_hunger_decay()` — 매 시간 정각

```
get_all_users() → 유저별:
    tama.hunger = max(0, current - 5)
    update_tamagotchi(uid, {"hunger": new_hunger})
```

### `_weekly_ml_retrain()` — 매주 일요일 03:00

```
retrain_all_users()  # utils/ml.py
```

### `_weekly_report()` — 매주 일요일 08:00

```
get_all_users() → 유저별:
    get_weekly_meal_stats(user_id, start=오늘-6일)
    get_weight_history(user_id, limit=7)  # cogs/weight.py
    get_earned_badges(user)
    generate_comment(주간 요약 컨텍스트)
    Embed 구성:
      - 칼로리: 평균/목표/기록일/달성일
      - 끼니 커버리지: 아침/점심/저녁 × 7일
      - 이번 주 최다 음식
      - 체중 변화 (첫→마지막)
      - 연속 기록 스트릭 바
      - 보유 배지 (최근 3개)
      - 타마고치 한마디
    thread.send(embed)
```

### `_meal_reminder(user_id, meal_label)` — 식사시간 -30분

```
thread.send("🍽️ {name}이(가) 슬슬 배가 고파지고 있어!")
```

### `_meal_upset(user_id, meal_label)` — 식사시간 정각

```
if has_meal_type_on_date(user_id, meal_label, today): return  # 이미 먹었으면 패스
generate_comment("식사 시간인데 밥을 안 줬어. 배고파서 짧게 말해줘!")
create_or_update_embed(thread, user, tama, comment)  # upset.png 계열
```

### `_meal_late(user_id, meal_label)` — 식사시간 +1시간

```
if has_meal_type_on_date(...): return
generate_comment("1시간 넘게 지났는데 아직 밥을 못 먹었어. 슬프고 걱정돼서 짧게 말해줘.")
thread.send(f"😢 *{comment}*")
```

---

## 4. `_get_thread()` 헬퍼

```python
async def _get_thread(self, user_id: str) -> discord.Thread | None:
    user = get_user(user_id)
    # 현재 메인 쓰레드(thread_id)만 사용
    # ⚠️ 향후: meal/weather/weight 알림은 각 봇 스케줄러로 이전 예정
    thread_id = int(user["thread_id"])
    for guild in self.bot.guilds:
        thread = guild.get_thread(thread_id)
        if thread: return thread
    return None
```

---

## 5. 식사 알림 Job 등록 시점

```
온보딩 완료 (OnboardingModal.on_submit)
    → scheduler_cog.register_meal_jobs(user_id)
    → 기본 시간 (08:00/12:00/18:00) 기준 Job 등록

시간 설정 완료 (TimeStep4View)
    → scheduler_cog.register_meal_jobs(user_id)
    → 새 시간으로 Job 재등록 (replace_existing=True)

봇 시작 (on_ready)
    → register_all_users()
    → 전체 유저 식사 알림 일괄 등록
```
