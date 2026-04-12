# 이메일 모니터링 (v3.0)

> 구현 완료: 2026-04-12  
> 관련 파일: `cogs/email_monitor.py`, `utils/mail.py`, `cogs/settings.py`, `utils/db.py`

---

## 개요

유저가 본인의 네이버 계정을 연동하면, 봇이 5분마다 IMAP으로 받은 편지함을 폴링하여
등록된 발신자의 메일이 왔을 때 디스코드 전용 스레드에 알림을 보낸다.
메일 요약은 GPT를 통해 생성되며, 향후 ML 요약 모델 학습 레이블로 활용 예정.

---

## 기능 목록

| 기능 | 설명 |
|------|------|
| 이메일 연동 | 네이버 아이디 + 앱 비밀번호 → IMAP 연결 테스트 후 DB 저장 |
| 메일 스레드 자동 생성 | 연동 시 `mail_thread_id` 없으면 `📧 {이름}의 메일함` 스레드 자동 생성 |
| 5분 폴링 | APScheduler `interval` — email_last_uid 이후의 메일만 조회 |
| 스팸 필터 3단계 | INBOX 한정 + 키워드 필터 + 발신자 화이트리스트 |
| 발신자 등록/목록/삭제 | 버튼 UI로 전부 처리 (슬래시 커맨드 불필요) |
| GPT 3줄 요약 | `summarize_email()` — max_tokens=150, temp=0.3 |
| 이메일 로그 저장 | `email_log` 테이블에 원문 제목 + GPT 요약 저장 (ML 학습 데이터) |

---

## UI 접근 경로

```
⚙️ 설정 → 📧 이메일 설정 → EmailSubView
  ├── [📬 발신자 추가]  →  SenderAddModal (이메일 + 별명)
  ├── [📋 발신자 목록]  →  Ephemeral Embed
  ├── [🗑️ 발신자 삭제]  →  SenderDeleteView (Select 드롭다운)
  └── [✏️ 이메일 수정]  →  EmailSetupModal (네이버 계정 재연동)
```

슬래시 커맨드도 병행 제공:
- `/이메일설정` — 계정 연동
- `/발신자추가` — 발신자 등록
- `/발신자목록` — 목록 확인
- `/발신자삭제 <email>` — 발신자 삭제

---

## 스팸 필터 상세

### 1단계 — INBOX 한정
IMAP 조회 시 `INBOX`만 대상으로 함. 네이버가 이미 스팸함으로 분류한 메일은 도달하지 않음.

### 2단계 — 제목 키워드 필터 (`utils/mail.py → is_spam()`)

```python
SPAM_KEYWORDS = [
    "[광고]", "[AD]", "[홍보]", "[이벤트]", "[공지]",
    "수신거부", "무료수신거부", "Unsubscribe",
]
```

한국 정보통신망법상 광고성 메일에는 제목에 `[광고]` 표기가 의무. 법적 필터.

### 3단계 — 발신자 화이트리스트
`email_senders` 테이블에 등록된 발신자 이메일과 정확히 일치해야 알림 발송.
등록되지 않은 발신자의 메일은 조용히 무시.

---

## 기술 구현

### IMAP 수신 (`utils/mail.py`)

```python
fetch_new_emails(naver_id, app_pw, registered_senders, last_uid)
  → (list[dict], max_uid)

dict 형식:
  {
    "uid": int,
    "sender_email": str,
    "sender_name": str,
    "subject": str,
    "body": str,   # plain text 우선, 없으면 HTML 태그 제거
  }
```

- 연결: `imaplib.IMAP4_SSL("imap.naver.com", 993)`
- UID 기반 조회: `SEARCH SINCE` + UID 비교로 last_uid 이후 메일만 처리
- 인코딩 처리: `email.header.decode_header()` → UTF-8/EUC-KR 자동 디코딩

### GPT 요약 (`utils/gpt.py → summarize_email()`)

```python
# 프롬프트 방향
"다음 이메일을 한국어로 3줄 이내로 요약해줘. 핵심 내용만 간결하게."
model=gpt-4o, max_tokens=150, temperature=0.3
```

요약 결과는 Discord Embed의 `📝 요약` 필드에 표시되고, `email_log.summary_gpt`에도 저장됨.

### 네이버 IMAP/SMTP 설정 요건

| 항목 | 설정 |
|------|------|
| IMAP 서버 | imap.naver.com:993 (SSL) |
| SMTP 서버 | smtp.naver.com:587 (TLS) |
| 인증 방식 | 앱 비밀번호 (일반 로그인 비밀번호 불가) |
| 앱 비밀번호 발급 | 네이버 보안설정 → 2단계 인증 → 앱 비밀번호 |
| IMAP 활성화 | 네이버 메일 → 환경설정 → POP3/IMAP 설정 → **IMAP/SMTP 설정** 탭 → 사용함 |

> ⚠️ **IMAP 탭과 POP3 탭은 별개**. POP3/SMTP 사용함으로 설정해도 IMAP은 별도로 활성화 필요.

---

## 기존 유저 마이그레이션

v3.0 이전에 온보딩한 유저는 `mail_thread_id`가 없음.
→ `✏️ 이메일 수정` 버튼으로 계정 연동 시 자동으로 메일 스레드 생성.

```python
# EmailSetupModal.on_submit() 내부
if not user_data.get("mail_thread_id"):
    mail_thread = await parent_channel.create_thread(...)
    set_mail_thread_id(user_id, str(mail_thread.id))
```

---

## ML 활용 계획

`email_log.summary_gpt`에 GPT 요약이 누적되면 경량 요약 모델(Extractive / Abstractive)로 대체 예정.
칼로리 모델과 동일한 "GPT label 누적 → ML 학습 → GPT 대체" 패턴.

현재 단계: 데이터 수집 중 (GPT label 누적)
