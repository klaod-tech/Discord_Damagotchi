# 메일봇 (bot_mail.py) 제작 로드맵

> last_updated: 2026-04-13 | 현재 버전: v3.1 ✅ 운영 중

---

## 현재 상태 요약

### 구현 완료

- `bot_mail.py`: `cogs.email_monitor` 단독 로드, `DISCORD_TOKEN_EMAIL` 사용
- `cogs/email_monitor.py`: 1분 IMAP 폴링, GPT 요약, Discord 알림
- 3단계 스팸 필터: 키워드 → 발신자 검증 → 본문 내용 체크
- `/이메일설정`, `/발신자추가`, `/발신자목록`, `/발신자삭제` 슬래시 커맨드
- `utils/mail.py`: 네이버 IMAP/SMTP, 헤더 디코딩, KST 발송 시각 변환
- `utils/email_ui.py`: `EmailSetupModal`, `SenderAddModal` 공통 모달 (먹구름봇과 공유)

### 처리 흐름

```
[메일봇] 1분 주기 폴링
  → IMAP LOGIN (users.naver_email + naver_app_pw)
  → 마지막 UID 이후 신규 메일 조회 (email_last_uid)
  → 발신자 검증 (email_senders 테이블)
  → 스팸 필터 3단계
  → 본문 길이 판단:
      ≤200자 → 원문 그대로 Embed
      >200자  → GPT 요약 후 Embed
  → mail_thread_id 에 Discord 알림
  → email_last_uid 업데이트
```

### Embed 구성 (현재)

```
📬 새 메일이 도착했어요!
─────────────────────
✉️ 발신자: {이름} <{email}>
📅 발송 일시: 2026-04-13 오후 3:24 (KST)
📝 내용:
{원문 or GPT 요약}
```

---

## Phase 1 — 안정화 작업 (v3.1.x)

### 1-1. IMAP 연결 실패 재시도

네이버 IMAP은 일시적으로 타임아웃 발생 가능.  
현재는 예외 발생 시 해당 사이클 조용히 스킵.  
→ 로그 + 3회 재시도 추가.

```python
# utils/mail.py fetch_new_emails() 수정
for attempt in range(3):
    try:
        mail = imaplib.IMAP4_SSL("imap.naver.com", 993)
        mail.login(email, app_pw)
        break
    except Exception as e:
        if attempt == 2:
            raise  # 3회 실패 시 예외 전파
        await asyncio.sleep(10)
```

### 1-2. 앱 비밀번호 검증

`/이메일설정` 완료 후 즉시 IMAP 로그인 테스트.  
잘못된 비밀번호로 설정 시 "연결에 실패했어요" 즉시 안내.

```python
# utils/email_ui.py EmailSetupModal.on_submit() 에 추가
try:
    test_connection(naver_email, naver_app_pw)
    # 성공: 자격증명 저장
    set_email_credentials(user_id, naver_email, naver_app_pw, initial_uid)
    await interaction.response.send_message("이메일 설정 완료!", ephemeral=True)
except Exception:
    await interaction.response.send_message(
        "이메일 로그인에 실패했어요.\n네이버 앱 비밀번호를 다시 확인해주세요.",
        ephemeral=True
    )
```

### 1-3. 메일 본문 줄바꿈 처리

현재 HTML 태그가 포함된 메일이 원문 표시될 경우 Embed가 지저분.  
→ 간단한 HTML strip 추가.

```python
# utils/mail.py 본문 추출 후
import re
body = re.sub(r'<[^>]+>', '', body)   # HTML 태그 제거
body = re.sub(r'\s+', ' ', body).strip()  # 공백 정리
```

---

## Phase 2 — 기능 개선 (v3.2~v3.3)

### 2-1. 수신 카테고리 분류

현재 모든 메일을 동일하게 알림.  
→ GPT로 카테고리 분류 후 Embed 아이콘 변경.

```python
CATEGORIES = {
    "결제/금융": "💳",
    "배송/쇼핑": "📦",
    "업무/공지": "📋",
    "뉴스레터": "📰",
    "기타": "📬",
}

category = await classify_email(subject, body)
icon = CATEGORIES.get(category, "📬")
```

### 2-2. 중요 메일 강조

발신자가 `email_senders`에 `priority = 'high'`로 등록된 경우  
→ Embed 색상 빨간색 + `@here` 멘션 (옵션).

```sql
-- email_senders 테이블 컬럼 추가
ALTER TABLE email_senders ADD COLUMN IF NOT EXISTS priority TEXT DEFAULT 'normal';
-- 값: 'normal' | 'high'
```

### 2-3. 일일 메일 요약

하루 받은 메일을 저녁 21:00에 요약 Embed 전송.

```python
# cogs/email_monitor.py APScheduler 추가
@scheduler.scheduled_job('cron', hour=21, minute=0, timezone='Asia/Seoul')
async def daily_email_summary():
    for user in get_users_with_email():
        today_mails = get_email_log_today(user['user_id'])
        if not today_mails: continue

        summary = f"오늘 {len(today_mails)}통의 메일을 받았어요.\n"
        for mail in today_mails[:5]:
            summary += f"• {mail['sender_name']}: {mail['subject'][:30]}\n"

        thread = guild.get_thread(int(user['mail_thread_id'] or user['thread_id']))
        await thread.send(embed=build_summary_embed(summary))
```

---

## Phase 3 — SMTP 발신 (v3.4)

> 유저 네이버 메일로 주간 리포트 발송

### 3-1. 주간 리포트 이메일 발송

현재 주간 리포트는 Discord 쓰레드로만 전송.  
→ `utils/mail.py send_email()`으로 네이버 이메일에도 동일 내용 발송.

```python
# cogs/scheduler.py _weekly_report() 수정
if user.get("naver_email"):
    await send_email(
        from_email=NAVER_MAIL_ID,
        from_pw=NAVER_MAIL_PW,
        to_email=user["naver_email"],
        subject=f"[먹구름] {user['tamagotchi_name']}의 주간 리포트",
        body=report_text
    )
```

### 3-2. 이메일 서식 HTML 템플릿

```html
<!-- templates/weekly_report.html -->
<h2>이번 주 {name}의 먹구름 리포트</h2>
<table>
  <tr><td>평균 칼로리</td><td>{avg_cal} kcal</td></tr>
  <tr><td>현재 체중</td><td>{weight} kg</td></tr>
  <tr><td>스트릭</td><td>{streak}일 연속</td></tr>
</table>
```

---

## Phase 4 — ML 스팸 분류 (v4.0)

### 4-1. 스팸 ML 모델

현재 3단계 키워드 기반 스팸 필터를 ML로 업그레이드.

```python
# utils/ml.py — SpamClassifier 추가
from sklearn.linear_model import LogisticRegression
from sklearn.feature_extraction.text import TfidfVectorizer

class SpamClassifier:
    def train(self, labeled_emails):
        X = self.vectorizer.fit_transform([e['subject'] + ' ' + e['body'] for e in labeled_emails])
        y = [e['is_spam'] for e in labeled_emails]
        self.model.fit(X, y)

    def predict(self, subject: str, body: str) -> bool:
        X = self.vectorizer.transform([subject + ' ' + body])
        return bool(self.model.predict(X)[0])
```

학습 데이터: `email_log.is_spam` 컬럼 활용 (유저가 "스팸으로 처리" 버튼 클릭 시 레이블 추가).

---

## 주요 파일 위치

| 파일 | 역할 |
|------|------|
| `bot_mail.py` | 봇 진입점, `cogs.email_monitor` 로드 |
| `cogs/email_monitor.py` | 1분 폴링, Embed 생성, 슬래시 커맨드 |
| `utils/mail.py` | IMAP/SMTP 클라이언트, 헤더 디코딩 |
| `utils/email_ui.py` | `EmailSetupModal`, `SenderAddModal` 공통 모달 |
| `utils/gpt.py` | `summarize_email()` |
| `utils/db.py` | `email_senders` CRUD, `email_log` CRUD, `set_email_credentials()` |

---

## DB 테이블 소유

```sql
email_senders (
  id          SERIAL PRIMARY KEY,
  user_id     TEXT REFERENCES users,
  email       TEXT,
  name        TEXT,
  priority    TEXT DEFAULT 'normal',   -- Phase 2 추가
  created_at  TIMESTAMP
)

email_log (
  log_id      SERIAL PRIMARY KEY,
  user_id     TEXT REFERENCES users,
  sender      TEXT,
  subject     TEXT,
  summary     TEXT,
  is_spam     BOOLEAN DEFAULT FALSE,   -- Phase 4 추가
  received_at TIMESTAMP
)
```

---

## 환경변수

| 변수명 | 설명 |
|--------|------|
| `DISCORD_TOKEN_EMAIL` | 메일봇 토큰 |
| (향후) `NAVER_MAIL_ID` | 봇 발신 이메일 (Phase 3) |
| (향후) `NAVER_MAIL_PW` | 봇 발신 앱 비밀번호 (Phase 3) |

---

## 설계 원칙 (변경 금지)

1. 이메일 자격증명(`naver_email`, `naver_app_pw`)은 DB 암호화 없이 저장 — 향후 암호화 고려
2. `email_last_uid` 업데이트는 메일 처리 성공 후에만 — 실패 시 다음 사이클 재시도
3. `initial_uid` 설정: 이메일 연결 시 기존 메일 재알림 방지를 위해 현재 최대 UID 기록
4. 스팸 필터 통과한 메일만 Discord 알림 — 필터 탈락 시 `email_log`에 기록만
