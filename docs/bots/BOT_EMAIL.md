# 이메일봇 개발 가이드 — Claude 전용

> **이 파일만 읽으면 이메일봇을 완전히 구현/수정할 수 있습니다.**  
> 공통 참조: `01_ARCHITECTURE.md`, `02_SHARED_DB.md`, `03_SHARED_UTILS.md`

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
- IMAP(네이버) **1분 폴링** → 새 메일 감지
- 등록된 발신자 화이트리스트 기반 필터링
- 스팸 필터 3단계 적용
- 200자 이하 본문: 원문 표시 / 초과: GPT 요약
- 메일 전용 쓰레드에 Embed 알림 전송
- 슬래시 커맨드: `/이메일설정`, `/발신자추가`, `/발신자목록`, `/발신자삭제`

### 이 봇이 하지 않는 것
- 이메일 설정 UI의 메인 버튼 — 먹구름봇 `cogs/settings.py` `EmailSubView`
- 발신자 추가/삭제 모달 — `utils/email_ui.py` (공유 모달, 먹구름봇도 import)

---

## 3. 스팸 필터 3단계

```
1단계: INBOX 폴더만 처리 (Spam/Sent/Draft 제외)
2단계: 제목 키워드 필터
        → ["광고", "무료", "[홍보]", "이벤트", "쿠폰", "구독", "프로모션"] 포함 시 스팸
3단계: 화이트리스트 (email_senders 테이블)
        → 등록된 sender_email과 일치하는 발신자만 알림
```

---

## 4. 메일 폴링 흐름

```
APScheduler (1분 IntervalTrigger)
  └── _poll_emails()
        → get_email_users(): 이메일 설정된 유저 전체 조회
        → 유저별:
            1. fetch_new_emails(naver_email, naver_app_pw, last_uid)
            2. 새 메일 각각:
               a. 스팸 필터 1단계: INBOX 확인
               b. 스팸 필터 2단계: 제목 키워드
               c. get_email_senders(user_id): 화이트리스트 조회
               d. 발신자 일치하지 않으면 skip
               e. 본문 200자 이하 → 원문 / 초과 → GPT summarize_email()
               f. save_email_log() DB 저장
               g. mail_thread_id 쓰레드에 Embed 전송
               h. update_email_last_uid() 업데이트
```

---

## 5. Discord Embed 출력 형식

```
📬 새 메일 도착!

📋 제목: [제목]
👤 발신자: [발신자 이름 <이메일>]
📅 발송 일시: 2026-04-13 14:30 KST

💌 내용:
[원문 or GPT 요약]

───
[닉네임]이(가) 보낸 메일
```

---

## 6. DB 사용 목록

### 읽기 (Read)
```python
get_email_users()              # 이메일 설정된 유저 전체
get_email_senders(user_id)     # 발신자 화이트리스트
```

### 쓰기 (Write — 소유)
```python
set_email_credentials(user_id, naver_email, naver_app_pw, initial_uid=0)
update_email_last_uid(user_id, uid)
add_email_sender(user_id, sender_email, nickname) -> bool
remove_email_sender(user_id, sender_email) -> bool
save_email_log(user_id, sender_email, subject, summary_gpt, is_spam=False)
```

### 절대 건드리지 말 것
- `meals`, `weather_log`, `weight_log`, `diary_log`, `schedule_log` 금지

---

## 7. utils/mail.py 핵심 함수

```python
# IMAP 새 메일 조회
async def fetch_new_emails(
    naver_email: str,
    naver_app_pw: str,
    last_uid: int,
) -> list[dict]:
    """
    반환: [
        {
            "uid": int,
            "subject": str,
            "from": str,        # "발신자이름 <email>" 형식
            "body": str,        # 본문 (최대 1000자)
            "sent_at": datetime # KST 변환됨
        }
    ]
    IMAP: imap.naver.com:993 (SSL)
    """

# SMTP 발신
async def send_email(to_email: str, subject: str, body: str):
    """
    SMTP: smtp.naver.com:587 (STARTTLS)
    발신 계정: 먹구름봇 공용 계정 (NAVER_MAIL_ID, NAVER_MAIL_PW)
    """
```

---

## 8. utils/email_ui.py 공유 모달

```python
# 이메일 계정 설정 (먹구름봇 설정 메뉴 + 이메일봇 슬래시 커맨드 양쪽에서 사용)
class EmailSetupModal(discord.ui.Modal, title="📧 이메일 설정"):
    email_input = ...    # 네이버 이메일 주소
    pw_input    = ...    # 앱 비밀번호
    # on_submit: set_email_credentials() → 메일 전용 쓰레드 생성 (없으면)

# 발신자 추가
class SenderAddModal(discord.ui.Modal, title="📬 발신자 등록"):
    email_input    = ...  # 발신자 이메일
    nickname_input = ...  # 별명
    # on_submit: add_email_sender()
```

---

## 9. 슬래시 커맨드 목록

| 커맨드 | 설명 | 응답 |
|--------|------|------|
| `/이메일설정` | 네이버 계정 연동 | EmailSetupModal |
| `/발신자추가` | 알림 받을 발신자 등록 | SenderAddModal |
| `/발신자목록` | 등록된 발신자 확인 | Embed (ephemeral) |
| `/발신자삭제` | 등록 발신자 삭제 | Select Menu → 삭제 |

---

## 10. ML 계획

### 현재: 규칙 기반 스팸 필터
- 키워드 매칭 + 화이트리스트

### 향후: ML 스팸 분류기
- `email_log.is_spam` Boolean 컬럼이 학습 레이블
- 유저가 "스팸" 표시 → is_spam = True 업데이트
- Naive Bayes / SVM으로 제목+발신자 기반 분류
- 유저별 개인화 모델 (발신자 패턴이 유저마다 다름)

```python
# 향후 추가할 슬래시 커맨드
"/스팸신고" → email_log.is_spam = True → 모델 재학습 트리거
```

---

## 11. bot_mail.py 전체 코드

```python
"""
bot_mail.py — 이메일 전용 봇 진입점

역할: 네이버 IMAP 1분 폴링 → 발신자 필터 → Discord 메일함 쓰레드 알림
DB : 먹구름과 동일한 Supabase 공유
토큰: .env의 DISCORD_TOKEN_EMAIL 사용
"""
import os
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv
from utils.db import init_db

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN_EMAIL")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!mail_", intents=intents)
_bot_ready = False

@bot.event
async def on_ready():
    global _bot_ready
    if _bot_ready:
        print(f"[RECONNECT] {bot.user} 재연결됨 — 초기화 생략")
        return
    _bot_ready = True
    init_db()
    await bot.tree.sync()
    print(f"[메일봇] {bot.user} 로그인 완료")

@bot.event
async def on_error(event, *args, **kwargs):
    import traceback
    traceback.print_exc()

async def main():
    async with bot:
        await bot.load_extension("cogs.email_monitor")
        print("[메일봇] cogs.email_monitor 로드 완료")
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 12. 개발 시 주의사항

- IMAP 로그인 실패 시 try/except로 조용히 넘어감 (봇 크래시 방지)
- `fetch_new_emails()` 실패해도 다음 1분 폴링 때 재시도
- 이메일 UID는 항상 `email_last_uid`보다 큰 것만 처리 (중복 알림 방지)
- 앱 비밀번호는 네이버 계정 > 보안 > IMAP/SMTP 사용 설정 후 발급
- 네이버 IMAP: `imap.naver.com:993` (SSL)
- 네이버 SMTP: `smtp.naver.com:587` (STARTTLS)
