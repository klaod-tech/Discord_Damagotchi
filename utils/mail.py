"""
utils/mail.py — 네이버 메일 IMAP 수신 모니터링 + SMTP 발송

IMAP 흐름:
  imap.naver.com:993 (SSL) → INBOX만 폴링
  → 스팸 키워드 필터 (한국 광고메일 법적 표기 기반)
  → 등록된 발신자 확인
  → 통과 시 반환 (email_monitor.py에서 GPT 요약 + Discord 알림 처리)

SMTP 흐름:
  smtp.naver.com:587 (TLS) → 주간 리포트 등 발송용
"""

import imaplib
import smtplib
import email
from email.header import decode_header
from email.utils import parsedate_to_datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta, timezone

NAVER_IMAP_HOST = "imap.naver.com"
NAVER_IMAP_PORT = 993
NAVER_SMTP_HOST = "smtp.naver.com"
NAVER_SMTP_PORT = 587

# 한국 정보통신망법 기반 광고 필수 표기 키워드
SPAM_KEYWORDS = [
    "[광고]", "[AD]", "[홍보]", "[이벤트]", "[공지]",
    "수신거부", "무료수신거부", "Unsubscribe", "UNSUBSCRIBE",
]


def _decode_str(value: str | bytes | None) -> str:
    """이메일 헤더 문자열 디코딩 (인코딩 혼합 처리)"""
    if value is None:
        return ""
    parts = decode_header(value)
    result = ""
    for part, enc in parts:
        if isinstance(part, bytes):
            result += part.decode(enc or "utf-8", errors="replace")
        else:
            result += str(part)
    return result.strip()


def _extract_body(msg: email.message.Message) -> str:
    """이메일 본문 추출 (multipart 대응, text/plain 우선)"""
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            cd = str(part.get("Content-Disposition", ""))
            if ct == "text/plain" and "attachment" not in cd:
                payload = part.get_payload(decode=True)
                charset = part.get_content_charset() or "utf-8"
                return payload.decode(charset, errors="replace")
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            return payload.decode(charset, errors="replace")
    return ""


def _extract_sender_email(from_header: str) -> str:
    """'홍길동 <hong@example.com>' 형태에서 이메일만 추출"""
    if "<" in from_header and ">" in from_header:
        return from_header.split("<")[1].split(">")[0].strip().lower()
    return from_header.strip().lower()


def _extract_sender_name(from_header: str) -> str:
    """'홍길동 <hong@example.com>' 형태에서 이름만 추출"""
    if "<" in from_header:
        return from_header.split("<")[0].strip().strip('"').strip("'")
    return from_header.strip()


def is_spam(subject: str) -> bool:
    """제목 기반 광고/스팸 판별"""
    return any(kw in subject for kw in SPAM_KEYWORDS)


def fetch_new_emails(
    naver_id: str,
    app_pw: str,
    registered_senders: list[str],
    last_uid: int = 0,
) -> tuple[list[dict], int]:
    """
    INBOX에서 last_uid 이후의 새 이메일을 가져와 필터링.

    Returns:
        (emails, max_uid)
        emails: 필터 통과한 이메일 목록
        max_uid: 이번 폴링에서 확인한 최대 UID (DB 갱신용)
    """
    results: list[dict] = []
    max_uid = last_uid

    try:
        mail = imaplib.IMAP4_SSL(NAVER_IMAP_HOST, NAVER_IMAP_PORT)
        mail.login(naver_id, app_pw)
        mail.select("INBOX")

        # 최근 1일 + last_uid 이후만 검색
        since_date = (datetime.now() - timedelta(days=1)).strftime("%d-%b-%Y")
        _, data = mail.uid("search", None, f'SINCE {since_date}')
        uids = data[0].split() if data and data[0] else []

        registered_lower = {s.lower() for s in registered_senders}

        for uid_bytes in uids:
            uid = int(uid_bytes)
            if uid <= last_uid:
                continue
            if uid > max_uid:
                max_uid = uid

            # 이메일 원문 fetch
            _, msg_data = mail.uid("fetch", uid_bytes, "(RFC822)")
            if not msg_data or not msg_data[0]:
                continue
            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)

            subject     = _decode_str(msg.get("Subject", ""))
            from_header = _decode_str(msg.get("From", ""))
            sender_email = _extract_sender_email(from_header)
            sender_name  = _extract_sender_name(from_header)

            # 발송 일시 파싱 (KST 변환)
            sent_at: datetime | None = None
            date_header = msg.get("Date", "")
            if date_header:
                try:
                    kst = timezone(timedelta(hours=9))
                    sent_at = parsedate_to_datetime(date_header).astimezone(kst)
                except Exception:
                    sent_at = None

            # 1단계: 스팸/광고 필터
            if is_spam(subject):
                print(f"[메일] 광고 필터 차단: '{subject}'")
                continue

            # 2단계: 등록된 발신자 확인
            if sender_email not in registered_lower:
                continue

            # 본문 추출 (최대 2000자)
            body = _extract_body(msg)[:2000]

            results.append({
                "uid":          uid,
                "sender_email": sender_email,
                "sender_name":  sender_name,
                "subject":      subject,
                "body":         body,
                "sent_at":      sent_at,
            })
            print(f"[메일] 새 메일 감지 — from: {sender_email} / 제목: {subject}")

        mail.logout()

    except imaplib.IMAP4.error as e:
        print(f"[IMAP 인증 오류] {e}")
    except Exception as e:
        print(f"[IMAP 오류] {e}")

    return results, max_uid


def send_email(
    to_email: str,
    subject: str,
    body_html: str,
    naver_id: str,
    app_pw: str,
):
    """
    Naver SMTP로 HTML 이메일 발송 (주간 리포트 등).
    naver_id: @naver.com 앞부분만 (예: 'klaod')
    """
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"{naver_id}@naver.com"
    msg["To"]      = to_email
    msg.attach(MIMEText(body_html, "html", "utf-8"))

    try:
        with smtplib.SMTP(NAVER_SMTP_HOST, NAVER_SMTP_PORT) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.login(naver_id, app_pw)
            smtp.send_message(msg)
        print(f"[SMTP] 발송 완료 → {to_email}")
    except Exception as e:
        print(f"[SMTP 오류] {e}")
