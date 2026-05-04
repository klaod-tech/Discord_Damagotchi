# 이메일봇 — 오버뷰

> **이 파일 + FLOWS.md + DB.md** 를 읽으면 이메일봇을 완전히 이해/수정할 수 있습니다.

---

## 1. 봇 기본 정보

| 항목 | 내용 |
|------|------|
| 봇 파일 | `bot_mail.py` |
| 토큰 환경변수 | `DISCORD_TOKEN_EMAIL` |
| 커맨드 prefix | `!mail_` |
| 담당 Cog | `cogs/email_monitor.py` → `EmailMonitorCog` |
| 담당 쓰레드 | `users.mail_thread_id` |
| 담당 DB 테이블 | `email_senders` (소유), `email_log` (소유) |
| 담당 유틸 | `utils/mail.py`, `utils/email_ui.py` |
| 현재 상태 | ✅ 완전 구현 (v3.1) |

---

## 2. 역할 및 범위

### 이 봇이 하는 것
- 네이버 IMAP 1분 폴링 → 새 메일 감지
- 화이트리스트 발신자 필터링 (3단계 스팸 필터)
- 200자 이하 본문: 원문 / 초과: GPT 요약
- 메일 전용 쓰레드에 Embed 알림 전송
- 슬래시 커맨드: `/이메일설정`, `/발신자추가`, `/발신자목록`, `/발신자삭제`

### 이 봇이 하지 않는 것
- 설정 메뉴의 이메일 진입점 버튼 → 먹구름봇 `cogs/settings.py` `EmailSubView`
- 발신자 등록 Modal → `utils/email_ui.py` (공유 Modal, 두 봇 모두 사용)

---

## 3. 스팸 필터 3단계

```
1단계: INBOX 폴더만 처리 (Spam/Sent/Draft 제외)

2단계: 제목 키워드 필터
  → ["광고", "무료", "[홍보]", "이벤트", "쿠폰", "구독", "프로모션"] 포함 시 스킵

3단계: 화이트리스트 (email_senders 테이블)
  → 등록된 sender_email과 발신자 이메일 일치 시만 알림
```

---

## 4. 슬래시 커맨드 목록

| 커맨드 | 설명 | 응답 |
|--------|------|------|
| `/이메일설정` | 네이버 계정 연동 | EmailSetupModal |
| `/발신자추가` | 알림 받을 발신자 등록 | SenderAddModal |
| `/발신자목록` | 등록된 발신자 확인 | Embed (ephemeral) |
| `/발신자삭제` | 등록 발신자 삭제 | Select Menu → 삭제 |

---

## 5. 파일 구조

```
bot_mail.py               ← 봇 진입점
cogs/email_monitor.py     ← EmailMonitorCog (폴링, 슬래시커맨드)
utils/mail.py             ← IMAP/SMTP 래퍼
utils/email_ui.py         ← EmailSetupModal, SenderAddModal (먹구름봇 공유)
utils/db.py               ← email_senders/email_log DB 함수
```

---

## 6. 네이버 IMAP/SMTP 설정

| 항목 | 값 |
|------|-----|
| IMAP 호스트 | `imap.naver.com:993` (SSL) |
| SMTP 호스트 | `smtp.naver.com:587` (STARTTLS) |
| 앱 비밀번호 | 네이버 계정 > 보안 > IMAP/SMTP 사용 설정 후 발급 |

---

## 7. Discord Embed 출력 형식

```
📬 새 메일 도착!

📋 제목: [제목]
👤 발신자: [발신자 이름 <이메일>]
📅 발송 일시: 2026-04-13 14:30 KST

💌 내용:
[원문(200자 이하) or GPT 요약]

───
[닉네임]이(가) 보낸 메일
```
