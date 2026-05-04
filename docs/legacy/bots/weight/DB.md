# 체중관리봇 — DB 담당 범위

---

## 1. 소유 테이블: `weight_log`

```sql
CREATE TABLE weight_log (
    log_id      SERIAL PRIMARY KEY,
    user_id     TEXT REFERENCES users(user_id),
    weight      REAL,                -- 체중 (kg)
    recorded_at TIMESTAMP DEFAULT NOW()
)
```

---

## 2. DB 함수 (cogs/weight.py에 정의)

> 현재 utils/db.py가 아닌 cogs/weight.py 내에 직접 정의됨.  
> 체중관리봇 분리 시 utils/db.py로 이전 예정.

```python
def save_weight_log(user_id: str, weight: float) -> None:
    """weight_log 테이블에 체중 기록 저장"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO weight_log (user_id, weight, recorded_at) VALUES (%s, %s, NOW())",
        (user_id, weight),
    )
    conn.commit(); cur.close(); conn.close()

def get_weight_history(user_id: str, limit: int = 7) -> list[dict]:
    """최근 체중 기록 조회 (최신순)
    Returns: [{"weight": float, "recorded_at": datetime}, ...]
    """

def get_latest_weight(user_id: str) -> float | None:
    """가장 최근 체중 반환"""

def get_latest_weight_before(user_id: str) -> float | None:
    """직전 체중 기록 반환 (현재 입력 전)
    get_weight_history(limit=2)[1]
    """
```

---

## 3. 다른 봇에서 읽는 함수

```python
# 먹구름봇 scheduler.py
from cogs.weight import get_weight_history
weight_history = get_weight_history(user_id, limit=7)

# 먹구름봇 embed.py (하루정리)
from cogs.weight import get_weight_history
current_weight = weight_history[0]["weight"] if weight_history else None
```

---

## 4. 절대 건드리지 말 것

체중관리봇은 아래 테이블에 INSERT/UPDATE 금지:

```
meals, weather_log, email_senders, email_log,
tamagotchi (읽기는 가능),
diary_log (추가 예정), schedule_log (추가 예정)
```
