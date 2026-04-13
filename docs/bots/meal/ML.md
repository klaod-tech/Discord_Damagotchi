# 식사봇 — ML 칼로리 보정 현황

---

## 현재: GPT-4o Vision + ML 보정 파이프라인

```
사진 업로드
    → GPT-4o Vision 분석 → gpt_calories (1차 추정)
    → get_corrected_calories(gpt_calories) → 최종 칼로리
                           ↑
                   utils/gpt_ml_bridge.py
                   utils/ml.py (Ridge/RandomForest)
```

---

## utils/ml.py — 칼로리 보정 모델

- **알고리즘**: Ridge Regression (기본) + RandomForest (데이터 충분 시)
- **특성**: food_name (TF-IDF), meal_type (one-hot), gpt_calories
- **타겟**: 실제 칼로리 (사용자 수정 값 — 현재는 GPT값을 Y로 사용, 향후 피드백 시스템 추가)
- **재학습**: 매주 일요일 03:00 (`_weekly_ml_retrain`)
- **모델 저장**: `models/calorie_model_{user_id}.pkl` (유저별 개인화)

---

## utils/gpt_ml_bridge.py

```python
from utils.gpt_ml_bridge import get_corrected_calories

calories = get_corrected_calories(
    user_id=user_id,
    food_name=food_name,
    meal_type=meal_type,
    gpt_calories=gpt_raw,
)
# 모델 없음 또는 데이터 부족(< 10건) → gpt_raw 그대로 반환
```

---

## 배지 `photo_10` 조건

```sql
SELECT COUNT(*) FROM meals
WHERE user_id = %s AND input_method = 'photo'
-- count >= 10 → photo_10 배지 획득
```

---

## 향후 개선 계획

### 1. 사용자 피드백 루프
- 유저가 칼로리를 직접 수정 → `meals.calories` 업데이트 → ML 재학습 데이터로 활용
- 슬래시 커맨드 `/칼로리수정 <meal_id> <calories>` 추가 예정

### 2. 음식량 표현 인식
- "반 공기", "크게", "조금" 등 양 표현 → 칼로리 배율 조정
- `gpt_ml_bridge`에서 파싱 후 보정 계수 적용

### 3. 식사 패턴 기반 보정
- `utils/pattern.py` 연동 — 특정 유저의 음식 선호도/양 패턴 반영

### 4. 과거 식사 입력 처리 (예정)
- `import time` 활용 — 현재 시간 기준으로 날짜/끼니 자동 판단
- 저녁에 아침 메뉴 입력 → 식사 과정 및 이미지 보내기 제외
- 전날 메뉴 입력 → Embed 갱신 없이 DB만 저장
