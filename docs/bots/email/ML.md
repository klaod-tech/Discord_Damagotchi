# 이메일봇 — ML 계획

---

## 현재: 규칙 기반 스팸 필터

```
2단계: 제목 키워드 매칭
  → ["광고", "무료", "[홍보]", "이벤트", "쿠폰", "구독", "프로모션"]

3단계: 화이트리스트 확인
  → email_senders 테이블 기반
```

---

## 향후: ML 스팸 분류기

### 학습 데이터

```sql
-- email_log 테이블
is_spam BOOLEAN DEFAULT FALSE   -- 학습 레이블
subject TEXT                    -- 특성 1: 제목
sender_email TEXT               -- 특성 2: 발신자
```

### 분류 모델

- **알고리즘**: Naive Bayes (텍스트) + SVM (발신자 패턴)
- **특성**: 제목 TF-IDF + 발신자 이메일 도메인
- **유저별 개인화 모델** — 발신자 패턴이 유저마다 다름

### 피드백 흐름

```
유저: "/스팸신고" 슬래시 커맨드 (예정)
  → email_log.is_spam = True 업데이트
  → 모델 재학습 트리거

유저: 발신자 화이트리스트에 추가
  → 해당 발신자 메일은 항상 is_spam = False
```

### 구현 예정 커맨드

```python
"/스팸신고" → 최근 N개 이메일 중 스팸 선택 → is_spam = True → 재학습
"/스팸취소" → is_spam = False 복구
```

### 데이터 누적 기준

- 10건 미만: 규칙 기반만 사용
- 10건 이상: ML 분류기 + 규칙 기반 앙상블
- 50건 이상: ML 분류기 단독 사용

---

## 현재 GPT 요약

```python
# utils/mail.py
async def summarize_email(subject: str, body: str) -> str:
    """
    본문 200자 초과 시 GPT-4o로 요약
    200자 이하 → 원문 그대로 반환
    """
```
