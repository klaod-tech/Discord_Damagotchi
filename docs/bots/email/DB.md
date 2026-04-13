# 이메일봇 — DB 담당 범위

---

## 1. 소유 테이블: `email_senders`

```sql
CREATE TABLE email_senders (
    sender_id    SERIAL PRIMARY KEY,
    user_id      TEXT REFERENCES users(user_id) ON DELETE CASCADE,
    sender_email TEXT NOT NULL,
    nickname     TEXT,
    created_at   TIMESTAMP DEFAULT NOW(),
    UNIQUE (user_id, sender_email)
)
```

---

## 2. 소유 테이블: `email_log`

```sql
CREATE TABLE email_log (
    log_id       SERIAL PRIMARY KEY,
    user_id      TEXT REFERENCES users(user_id) ON DELETE CASCADE,
    sender_email TEXT,
    subject      TEXT,
    summary_gpt  TEXT,
    is_spam      BOOLEAN DEFAULT FALSE,    -- ML 학습 레이블
    received_at  TIMESTAMP DEFAULT NOW()
)
```

---

## 3. 사용 함수 목록

### 읽기

```python
from utils.db import get_email_users, get_email_senders

get_email_users()               # 이메일 설정된 전체 유저 (폴링용)
get_email_senders(user_id)      # 발신자 화이트리스트 조회
```

### 쓰기 (소유)

```python
from utils.db import (
    set_email_credentials,
    update_email_last_uid,
    add_email_sender,
    remove_email_sender,
    save_email_log,
    set_mail_thread_id,
)

set_email_credentials(user_id, naver_email, naver_app_pw, initial_uid=0)
update_email_last_uid(user_id, uid)
add_email_sender(user_id, sender_email, nickname) -> bool  # 중복 시 False
remove_email_sender(user_id, sender_email) -> bool         # 없으면 False
save_email_log(user_id, sender_email, subject, summary_gpt, is_spam=False)
set_mail_thread_id(user_id, thread_id)
```

---

## 4. users 테이블의 이메일 관련 컬럼

```sql
-- 이메일봇이 쓰기 가능한 컬럼 (users 테이블)
naver_email    TEXT      -- 네이버 이메일 주소
naver_app_pw   TEXT      -- 앱 비밀번호 (평문 저장 — 추후 암호화 고려)
email_last_uid INTEGER   -- 마지막으로 처리한 이메일 UID
mail_thread_id TEXT      -- 메일 전용 쓰레드 ID
```

---

## 5. 절대 건드리지 말 것

```python
meals, weather_log, weight_log, tamagotchi,
diary_log (추가 예정), schedule_log (추가 예정)
```
