# 식사봇 — DB 담당 범위

---

## 1. 소유 테이블: `meals`

```sql
CREATE TABLE meals (
    meal_id      SERIAL PRIMARY KEY,
    user_id      TEXT REFERENCES users(user_id),
    meal_type    TEXT,               -- "아침" | "점심" | "저녁" | "간식" | "식사"
    food_name    TEXT,
    calories     INTEGER,
    protein      REAL,               -- (g)
    carbs        REAL,               -- (g)
    fat          REAL,               -- (g)
    fiber        REAL,               -- (g)
    input_method TEXT,               -- "text" | "photo"
    gpt_comment  TEXT,
    recorded_at  TIMESTAMP DEFAULT NOW()
)
```

---

## 2. 사용 함수 목록

### 쓰기 (소유)

```python
from utils.db import create_meal

create_meal(
    user_id, meal_type, food_name, calories,
    protein, carbs, fat, fiber,
    input_method,     # "photo"
    gpt_comment,
    recorded_date=None,  # None이면 오늘; 소급 입력 시 date 객체
)
```

### 읽기

```python
from utils.db import (
    get_user,
    get_tamagotchi,
    get_calories_by_date,
    is_meal_waiting,
    clear_meal_waiting,
)

# 사진 대기 상태 확인 및 해제
is_meal_waiting(user_id)    # bool
clear_meal_waiting(user_id) # None
```

### 쓰기 (meal.py 내 직접 사용)

```python
from utils.db import update_tamagotchi

update_tamagotchi(user_id, {
    "hunger":      new_hunger,
    "mood":        new_mood,
    "hp":          new_hp,
    "last_fed_at": datetime.utcnow().isoformat(),
})
```

---

## 3. 절대 건드리지 말 것

```python
# 식사봇은 아래 테이블에 INSERT/UPDATE 금지
weather_log, weight_log, email_senders, email_log,
diary_log (추가 예정), schedule_log (추가 예정)
```

---

## 4. KST 날짜 처리

recorded_at은 UTC 저장. 오늘 식사 조회 시:

```sql
(recorded_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Seoul')::date = CURRENT_DATE
```

Python에서는 `date.today()` 사용:

```python
from datetime import date
today = date.today()
get_calories_by_date(user_id, today)
```
