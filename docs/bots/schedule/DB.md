# 일정봇 — DB 담당 범위

---

## 1. 신규 생성 테이블: `schedule_log`

`utils/db.py`의 `init_db()` 내에 추가:

```python
# schedule_thread_id 컬럼 추가
cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS schedule_thread_id TEXT")

# schedule_log 테이블 생성
cur.execute("""
    CREATE TABLE IF NOT EXISTS schedule_log (
        schedule_id  SERIAL PRIMARY KEY,
        user_id      TEXT REFERENCES users(user_id) ON DELETE CASCADE,
        title        TEXT NOT NULL,
        scheduled_at TIMESTAMP NOT NULL,
        is_repeat    BOOLEAN DEFAULT FALSE,
        repeat_rule  TEXT,          -- 'daily'/'weekly'/'monthly'/'weekday'/null
        is_done      BOOLEAN DEFAULT FALSE,
        notified     BOOLEAN DEFAULT FALSE,  -- 알림 발송 완료 여부
        created_at   TIMESTAMP DEFAULT NOW()
    )
""")
```

---

## 2. 신규 DB 함수 (`utils/db.py`에 추가)

```python
def set_schedule_thread_id(user_id: str, thread_id: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET schedule_thread_id = %s WHERE user_id = %s",
        (thread_id, user_id),
    )
    conn.commit(); cur.close(); conn.close()


def create_schedule(user_id: str, title: str, scheduled_at, is_repeat: bool = False, repeat_rule: str = None) -> int:
    """일정 등록. 생성된 schedule_id 반환."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO schedule_log (user_id, title, scheduled_at, is_repeat, repeat_rule)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING schedule_id
    """, (user_id, title, scheduled_at, is_repeat, repeat_rule))
    row = cur.fetchone()
    conn.commit(); cur.close(); conn.close()
    return row["schedule_id"]


def get_upcoming_schedules(user_id: str, days: int = 7) -> list:
    """향후 N일 내 미완료 일정 조회"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM schedule_log
        WHERE user_id = %s
          AND is_done = FALSE
          AND scheduled_at BETWEEN NOW() AND NOW() + INTERVAL '%s days'
        ORDER BY scheduled_at ASC
    """, (user_id, days))
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows


def get_all_pending_schedules() -> list:
    """알림 보내야 할 전체 유저 일정 (스케줄러용)
    scheduled_at이 10분 이내이고 아직 알림 미발송인 일정
    """
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT s.*, u.schedule_thread_id, u.thread_id
        FROM schedule_log s
        JOIN users u ON s.user_id = u.user_id
        WHERE s.is_done = FALSE
          AND s.notified = FALSE
          AND s.scheduled_at <= NOW() + INTERVAL '10 minutes'
    """)
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows


def mark_schedule_done(schedule_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE schedule_log SET is_done = TRUE WHERE schedule_id = %s", (schedule_id,))
    conn.commit(); cur.close(); conn.close()


def mark_schedule_notified(schedule_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE schedule_log SET notified = TRUE WHERE schedule_id = %s", (schedule_id,))
    conn.commit(); cur.close(); conn.close()


def delete_schedule(user_id: str, schedule_id: int) -> bool:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM schedule_log WHERE schedule_id = %s AND user_id = %s RETURNING schedule_id",
        (schedule_id, user_id),
    )
    deleted = cur.fetchone()
    conn.commit(); cur.close(); conn.close()
    return deleted is not None
```

---

## 3. 온보딩 추가 (`cogs/onboarding.py`)

```python
from utils.db import (..., set_schedule_thread_id)

# 일기 쓰레드 이후에 추가:
schedule_thread = await channel.create_thread(
    name=f"📅 {interaction.user.display_name}의 일정",
    auto_archive_duration=10080,
    invitable=False,
)
set_schedule_thread_id(user_id, str(schedule_thread.id))
await schedule_thread.send(
    f"📅 안녕, {interaction.user.mention}!\n"
    f"여기는 **일정 전용** 쓰레드야.\n"
    f"`/일정등록` 명령어로 일정을 추가하면 알림을 보내줄게!\n"
    f"`/일정목록` 으로 등록된 일정을 확인할 수 있어."
)
```

---

## 4. 절대 건드리지 말 것

```python
meals, weather_log, weight_log, email_senders, email_log, diary_log, tamagotchi
```
