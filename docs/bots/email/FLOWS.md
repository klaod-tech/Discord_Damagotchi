# 이메일봇 — IMAP 폴링 흐름 & 슬래시 커맨드 흐름

---

## 1. 메일 폴링 흐름 (1분 간격)

```
APScheduler IntervalTrigger(minutes=1)
  └── EmailMonitorCog._poll_emails()
        → get_email_users()  ← 이메일 설정된 전체 유저
        → 유저별 처리:
            1. fetch_new_emails(naver_email, naver_app_pw, last_uid)
               → IMAP4_SSL(imap.naver.com:993) 연결
               → email_last_uid 이후 UID만 조회
               → [{"uid", "subject", "from", "body", "sent_at"}, ...]

            2. 메일 각각 처리:
               a. 스팸 필터 1단계: INBOX 확인
               b. 스팸 필터 2단계: 제목 키워드
               c. get_email_senders(user_id) → 화이트리스트
               d. 발신자 불일치 → skip
               e. 본문 200자 이하 → 원문
                  초과 → summarize_email(subject, body)
               f. save_email_log(...)  ← DB 저장
               g. mail_thread_id 쓰레드에 Embed 전송
               h. update_email_last_uid(user_id, max_uid)

        오류 발생 시 → try/except로 조용히 넘어감 (봇 크래시 방지)
```

---

## 2. 이메일 설정 흐름

### 슬래시 커맨드 `/이메일설정`

```
유저: /이메일설정
  → send_modal(EmailSetupModal)  ← utils/email_ui.py

유저: 이메일/앱비밀번호 입력
  → EmailSetupModal.on_submit()
  → set_email_credentials(user_id, naver_email, naver_app_pw, initial_uid=0)
  → mail_thread_id 없으면 → 새 메일 전용 쓰레드 생성 + set_mail_thread_id()
  → "✅ 이메일 설정 완료!" 응답
```

### 먹구름봇 설정 메뉴에서도 동일

```
유저: ⚙️ 설정 → 이메일 설정
  → EmailSubView (cogs/settings.py)
  → "이메일 설정" 버튼 클릭
  → send_modal(EmailSetupModal)  ← 동일한 Modal 사용
```

---

## 3. 발신자 관리 흐름

### `/발신자추가`

```
유저: /발신자추가
  → send_modal(SenderAddModal)
  → 이메일/별명 입력
  → add_email_sender(user_id, sender_email.lower(), nickname) → bool
  → True: "✅ {nickname}({email}) 등록 완료!"
  → False: "이미 등록된 발신자야!"
```

### `/발신자목록`

```
유저: /발신자목록
  → get_email_senders(user_id)
  → Embed (ephemeral):
      발신자 목록:
      1. {nickname} ({email})
      2. ...
```

### `/발신자삭제`

```
유저: /발신자삭제
  → get_email_senders(user_id)
  → Select Menu: 삭제할 발신자 선택
  → remove_email_sender(user_id, selected_email)
  → "✅ 삭제 완료!"
```

---

## 4. 중복 알림 방지

```python
# 마지막 처리 UID 저장
update_email_last_uid(user_id, max_uid)

# 다음 폴링 시
fetch_new_emails(naver_email, naver_app_pw, last_uid=email_last_uid)
# → last_uid보다 큰 UID만 처리
```

---

## 5. IMAP 연결 오류 처리

```python
try:
    emails = await fetch_new_emails(...)
except Exception as e:
    print(f"[이메일 폴링 오류] {user_id}: {e}")
    continue  # 다음 유저로 → 봇 크래시 방지
```

IMAP 로그인 실패, 네트워크 오류 등 → 조용히 skip, 다음 1분 폴링 때 재시도
