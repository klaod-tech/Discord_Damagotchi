# 일기봇 — ML 계획

---

## 현재: GPT-4o 감정 분류

- emotion_tag: 기쁨/슬픔/화남/평온/불안/설렘 6종
- emotion_score: 0.0~1.0 강도

---

## 식사 × 감정 상관관계 (ML 데이터)

```sql
-- 감정별 평균 칼로리 (식사봇 데이터 + 일기봇 데이터 조인)
SELECT d.emotion_tag, AVG(m.calories) as avg_cal
FROM diary_log d
JOIN meals m ON d.user_id = m.user_id
  AND DATE(d.recorded_at) = DATE(m.recorded_at)
GROUP BY d.emotion_tag;
```

활용 예시:
- 슬픔 날 과식 → 먹구름봇 "오늘 힘들어 보이는데 조금만 먹어도 괜찮아"
- 기쁨 날 균형 식사 → "오늘 기분도 좋고 식사도 완벽해!"
- 불안 날 식사 불규칙 → "규칙적인 식사가 도움이 될 거야"

---

## 향후: KoBERT 감정 분류기

- diary_log 데이터 500건 이상 누적 후 KoBERT fine-tuning
- GPT 레이블 → KoBERT 학습 데이터로 활용
- 한국어 감정 분류 정확도 향상

## 노이즈 필터링

- `len(content) < 10` → "더 자세히 적어줘" 안내 (이미 구현)
- 향후: "ㅇ", "ㅋㅋ", "없음" 등 무의미 입력 추가 필터
