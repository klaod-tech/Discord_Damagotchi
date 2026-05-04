# 일정봇 — 일정 등록/알림/완료 흐름

---

## 1. `/일정등록` 흐름

```
유저: /일정등록
  → send_modal(ScheduleInputModal)

유저: 일정 입력 ("내일 오전 10시 병원 예약")
  → ScheduleInputModal.on_submit()
  → defer(ephemeral=True, thinking=True)
  → parse_schedule_input(text)
      → GPT-4o: {title, scheduled_at, is_repeat, repeat_rule}
  → datetime.fromisoformat(scheduled_at)
  → create_schedule(user_id, title, dt, is_repeat, repeat_rule) → schedule_id
  → Embed 구성:
       📌 일정: {title}
       📆 날짜/시간: YYYY년 MM월 DD일 HH:MM
       🔁 반복: {repeat_str} (반복 일정만)
       footer: "일정 ID: {schedule_id}"
  → thread_id = schedule_thread_id or thread_id
  → thread.send(embed=embed)  ← 일정 전용 쓰레드에 공개 전송
  → followup.send("✅ 일정이 등록됐어!", ephemeral=True)
```

---

## 2. `/일정목록` 흐름

```
유저: /일정목록
  → get_upcoming_schedules(user_id, days=7)
  → Embed 구성:
       📅 향후 7일 일정
       1. [MM/DD HH:MM] {title} {반복여부}
       2. ...
  → 각 일정 "✅ 완료" 버튼 포함 (ScheduleListView)
  → send(embed + view, ephemeral=True)
```

---

## 3. `/일정삭제` 흐름

```
유저: /일정삭제
  → get_upcoming_schedules(user_id, days=30)
  → Select Menu: 삭제할 일정 선택
  → delete_schedule(user_id, schedule_id) → bool
  → "✅ {title} 일정이 삭제됐어!"
```

---

## 4. 알림 스케줄러 (5분 간격)

```
APScheduler IntervalTrigger(minutes=5)
  → ScheduleCog._check_schedules()
      → get_all_pending_schedules()
      → 각 일정:
          thread_id = schedule_thread_id or thread_id
          thread.send(f"⏰ {title} 일정 알림!")
          mark_schedule_notified(schedule_id)
          if is_repeat:
              다음 scheduled_at 계산 → new_schedule 생성
              mark_schedule_done(old_schedule_id)
          else:
              mark_schedule_done(schedule_id)
```

---

## 5. GPT 날짜/시간 파싱

```python
parse_schedule_input(text: str) -> dict
# 입력: "내일 오전 10시 병원 예약"
# 출력: {
#     "title": "병원 예약",
#     "scheduled_at": "2026-04-14T10:00:00",
#     "is_repeat": False,
#     "repeat_rule": None
# }

# 입력: "매주 월요일 운동"
# 출력: {
#     "title": "운동",
#     "scheduled_at": "2026-04-14T00:00:00",  # 다음 월요일
#     "is_repeat": True,
#     "repeat_rule": "weekly"
# }

# 시스템 프롬프트에 오늘 날짜/시간(KST) 주입
# 모델: gpt-4o, max_tokens=200
```

---

## 6. 반복 일정 다음 실행 시각 계산

```python
from datetime import timedelta

def _next_scheduled_at(current: datetime, repeat_rule: str) -> datetime:
    if repeat_rule == "daily":
        return current + timedelta(days=1)
    elif repeat_rule == "weekly":
        return current + timedelta(weeks=1)
    elif repeat_rule == "monthly":
        # 다음달 같은 날
        month = current.month % 12 + 1
        year = current.year + (1 if month == 1 else 0)
        return current.replace(year=year, month=month)
    elif repeat_rule == "weekday":
        # 다음 평일 (월~금)
        next_dt = current + timedelta(days=1)
        while next_dt.weekday() >= 5:  # 토=5, 일=6
            next_dt += timedelta(days=1)
        return next_dt
    return None
```
