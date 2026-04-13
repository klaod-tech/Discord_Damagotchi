# 일기봇 — DB 담당 범위

---

## 1. 신규 생성 테이블: `diary_log`

`utils/db.py`의 `init_db()` 내에 추가:

```python
# diary_thread_id 컬럼 추가
cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS diary_thread_id TEXT")

# diary_log 테이블 생성
cur.execute("""
    CREATE TABLE IF NOT EXISTS diary_log (
        diary_id      SERIAL PRIMARY KEY,
        user_id       TEXT REFERENCES users(user_id) ON DELETE CASCADE,
        content       TEXT NOT NULL,
        emotion_tag   TEXT,          -- 기쁨/슬픔/화남/평온/불안/설렘
        emotion_score REAL,          -- 0.0 ~ 1.0
        gpt_comment   TEXT,
        recorded_at   TIMESTAMP DEFAULT NOW()
    )
""")
```

---

## 2. 신규 DB 함수 (`utils/db.py`에 추가)

```python
def set_diary_thread_id(user_id: str, thread_id: str):
    """일기 전용 쓰레드 ID 저장"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET diary_thread_id = %s WHERE user_id = %s",
        (thread_id, user_id),
    )
    conn.commit(); cur.close(); conn.close()


def save_diary(user_id: str, content: str, emotion_tag: str, emotion_score: float, gpt_comment: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO diary_log (user_id, content, emotion_tag, emotion_score, gpt_comment)
        VALUES (%s, %s, %s, %s, %s)
    """, (user_id, content, emotion_tag, emotion_score, gpt_comment))
    conn.commit(); cur.close(); conn.close()


def get_diaries_by_date(user_id: str, target_date) -> list:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM diary_log
        WHERE user_id = %s
        AND (recorded_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Seoul')::date = %s
        ORDER BY recorded_at ASC
    """, (user_id, target_date))
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows


def get_recent_diaries(user_id: str, limit: int = 7) -> list:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM diary_log
        WHERE user_id = %s
        ORDER BY recorded_at DESC
        LIMIT %s
    """, (user_id, limit))
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows


def get_emotion_stats(user_id: str, days: int = 7) -> dict:
    """최근 N일 감정 태그 분포 → {emotion_tag: count, ...}"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT emotion_tag, COUNT(*) as cnt
        FROM diary_log
        WHERE user_id = %s
          AND recorded_at >= NOW() - INTERVAL '%s days'
        GROUP BY emotion_tag
        ORDER BY cnt DESC
    """, (user_id, days))
    rows = cur.fetchall()
    cur.close(); conn.close()
    return {r["emotion_tag"]: r["cnt"] for r in rows if r["emotion_tag"]}
```

---

## 3. 온보딩 추가 (`cogs/onboarding.py`)

```python
# import 추가
from utils.db import (..., set_diary_thread_id)

# OnboardingModal.on_submit() 내 체중 쓰레드 생성 이후에 추가:
diary_thread = await channel.create_thread(
    name=f"📔 {interaction.user.display_name}의 일기",
    auto_archive_duration=10080,
    invitable=False,
)
set_diary_thread_id(user_id, str(diary_thread.id))
await diary_thread.send(
    f"📔 안녕, {interaction.user.mention}!\n"
    f"여기는 **일기 전용** 쓰레드야.\n"
    f"오늘 하루 어땠어? 자유롭게 적어줘!\n"
    f"`/일기` 명령어로 일기를 쓸 수 있어."
)
```

---

## 4. 절대 건드리지 말 것

```python
meals, weather_log, weight_log, email_senders, email_log,
schedule_log (추가 예정)
```
