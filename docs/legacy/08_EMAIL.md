# 이메일 모니터링 (v3.1)

> 최초 구현: 2026-04-12 (v3.0)
> 봇 분리 + 기능 개선: 2026-04-13 (v3.1)
> 관련 파일: `bot_mail.py`, `cogs/email_monitor.py`, `utils/email_ui.py`, `utils/mail.py`, `cogs/settings.py`, `utils/db.py`

---

## 개요

유저가 본인의 네이버 계정을 연동하면, **메일 전용 봇(bot_mail.py)**이 1분마다 IMAP으로
받은 편지함을 폴링하여 등록된 발신자의 메일이 왔을 때 디스코드 전용 스레드에 알림을 보낸다.

먹구름 봇(bot.py)과 메일봇(bot_mail.py)은 **동일한 Supabase DB를 공유**하며,
각자 독립적인 이벤트 루프에서 동작한다.

---

## 봇 분리 구조 (v3.1)

```
[먹구름 봇 — bot.py]          [메일봇 — bot_mail.py]
  설정 UI / 식사 / 날씨           1분 IMAP 폴링
  ⚙️ 이메일 설정 버튼              스레드 알림 전송
          ↓                              ↓
         ┌────────────────────────────────┐
         │         Supabase DB           │
         │  naver_email / naver_app_pw   │
         │  email_last_uid / senders     │
         │  mail_thread_id               │
         └────────────────────────────────┘
```

### 실행
```bash
python bot.py        # 먹구름 봇 (식사/날씨/설정)
python bot_mail.py   # 메일봇 (IMAP 폴링)
```

### 환경변수 (.env)
| 변수명 | 설명 |
|--------|------|
| `DISCORD_TOKEN` | 먹구름 봇 토큰 |
| `DISCORD_TOKEN_EMAIL` | 메일봇 토큰 |

---

## 기능 목록

| 기능 | 설명 |
|------|------|
| 이메일 연동 | 네이버 아이디 + 앱 비밀번호 → IMAP 연결 테스트 후 DB 저장 |
| 메일 스레드 자동 생성 | 연동 시 `mail_thread_id` 없으면 `📧 {이름}의 메일함` 스레드 자동 생성 |
| **1분 폴링** | APScheduler `interval` — `email_last_uid` 이후의 메일만 조회 (v3.0: 5분 → v3.1: 1분) |
| 스팸 필터 3단계 | INBOX 한정 + 키워드 필터 + 발신자 화이트리스트 |
| 발신자 등록/목록/삭제 | 버튼 UI + 슬래시 커맨드 양쪽 지원 |
| **발송 일시 표시** | 메일 Date 헤더 파싱 → KST 변환 → embed에 `📅 발송 일시` 표시 (v3.1) |
| **200자 이하 본문 직접 출력** | 본문 ≤200자이면 GPT 요약 없이 원문 표시, 초과 시 GPT 요약 (v3.1) |
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

슬래시 커맨드 (메일봇에서 처리):
- `/이메일설정` — 계정 연동
- `/발신자추가` — 발신자 등록
- `/발신자목록` — 목록 확인
- `/발신자삭제 <email>` — 발신자 삭제

---

## Discord Embed 출력 형식

```
📧 새 메일 — {별명}
┌─────────────────────────────────────────┐
│ 보낸 사람              📅 발송 일시       │
│ 나 (klaolive15@gmail.com)  2026년 04월 12일 23:47 │
│                                         │
│ 제목                                    │
│ 안녕하세요                              │
│                                         │
│ 📝 요약                                 │
│ (본문 ≤200자: 원문 / >200자: GPT 요약)  │
│                                         │
│ 네이버 메일에서 전체 내용을 확인하세요.  │
└─────────────────────────────────────────┘
```

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

한국 정보통신망법상 광고성 메일 제목에 `[광고]` 표기 의무. 법적 필터.

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
    "uid":          int,
    "sender_email": str,
    "sender_name":  str,
    "subject":      str,
    "body":         str,      # plain text 우선 (최대 2000자)
    "sent_at":      datetime, # KST 변환된 발송 일시 (v3.1)
  }
```

- 연결: `imaplib.IMAP4_SSL("imap.naver.com", 993)`
- UID 기반 조회: `SEARCH SINCE` + UID 비교로 last_uid 이후 메일만 처리
- 인코딩 처리: `email.header.decode_header()` → UTF-8/EUC-KR 자동 디코딩
- 발송 일시: `email.utils.parsedate_to_datetime()` → `.astimezone(KST)` 변환

### 요약 분기 (`cogs/email_monitor.py`)

```python
if len(body.strip()) <= 200:
    summary = body.strip()   # 원문 그대로
else:
    summary = await summarize_email(subject, body)   # GPT 요약
```

### GPT 요약 (`utils/gpt.py → summarize_email()`)

```python
# 프롬프트 방향
"다음 이메일을 한국어로 3줄 이내로 요약해줘. 핵심 내용만 간결하게."
model=gpt-4o, max_tokens=150, temperature=0.3
```

요약 결과는 Discord Embed의 `📝 요약` 필드에 표시되고, `email_log.summary_gpt`에도 저장됨.

### 공유 모달 (`utils/email_ui.py`)

v3.1에서 모달 클래스를 공통 모듈로 분리.

| 클래스 | 사용처 |
|--------|--------|
| `EmailSetupModal` | `settings.py` (✏️ 이메일 수정 버튼), `email_monitor.py` (/이메일설정 커맨드) |
| `SenderAddModal` | `settings.py` (📬 발신자 추가 버튼), `email_monitor.py` (/발신자추가 커맨드) |

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

## v3.1 버그 수정 내역

| 항목 | 원인 | 수정 |
|------|------|------|
| 설정 후 기존 메일 재알림 | `set_email_credentials()`가 `initial_uid`를 무시하고 항상 0으로 저장 | 함수 시그니처에 `initial_uid: int = 0` 파라미터 추가, SQL을 `email_last_uid = %s`로 변경 |
| `/이메일설정` 스레드 내에서 실행 시 오류 | `interaction.channel`이 `Thread` 객체일 때 `create_thread()` 호출 불가 | `isinstance(ch, discord.Thread)` 체크 후 `ch.parent` 사용 |

---

## 기존 유저 마이그레이션

v3.0 이전에 온보딩한 유저는 `mail_thread_id`가 없음.
→ `✏️ 이메일 수정` 버튼으로 계정 연동 시 자동으로 메일 스레드 생성.

---

## ML 활용 계획

`email_log.summary_gpt`에 GPT 요약이 누적되면 경량 요약 모델(Extractive / Abstractive)로 대체 예정.
칼로리 모델과 동일한 "GPT label 누적 → ML 학습 → GPT 대체" 패턴.

현재 단계: 데이터 수집 중 (GPT label 누적)
