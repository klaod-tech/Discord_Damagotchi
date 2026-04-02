# ML 모듈 설명

## 구성 파일

| 파일 | 역할 | 활성화 조건 |
|------|------|------------|
| `utils/pattern.py` | 식습관 패턴 분석 → GPT 대사에 주입 | 7일 이상 식사 데이터 |
| `utils/ml.py` | GPT 칼로리 보정 (양 표현 + 개인화 모델) | 즉시 (양 표현), 30건+ (모델) |
| `utils/gpt_ml_bridge.py` | ML 결과 → GPT System Prompt 브릿지 | 항상 |

---

## pattern.py — 식습관 패턴 분석 (ML 1순위)

**역할**: DB Meals에서 최근 14일 데이터 분석 → 패턴 탐지 → GPT System Prompt에 자연어로 주입

**탐지하는 5가지 패턴**:
1. **요일별 과식**: 특정 요일에 목표 110% 초과가 50% 이상 반복
2. **아침 결식**: 14일 중 7일 이상 아침 기록 없음
3. **저녁 집중 섭취**: 저녁 칼로리가 하루 평균 50% 이상
4. **주간 추이**: 이번 주 평균 vs 지난 주 평균 100kcal 이상 차이
5. **연속 소식**: 3일 연속으로 목표의 67% 미만 섭취

**사용 위치**: `utils/embed.py` → 📅 오늘 일정 버튼의 GPT 대사 생성 시

---

## ml.py — 칼로리 보정 모델 (ML 3순위)

**역할**: GPT-4o 추정 칼로리를 양 표현 패턴 + 개인화 모델로 보정

**즉시 보정 (모델 없이 동작)**:
| 표현 | 배율 |
|------|------|
| 조금/약간/살짝/적게 | ×0.7 |
| 반/절반 | ×0.5 |
| 한 그릇/보통 | ×1.0 |
| 많이/가득 | ×1.4 |
| 두 그릇 | ×2.0 |
| 엄청/대식 | ×1.8 |

**개인화 모델**: Ridge Regression vs Random Forest (교차검증으로 자동 선택)
- 저장 위치: `models/calorie_model_{user_id}.pkl`
- 활성화: 30개 이상 식사 기록 누적 시
- 재학습: 매주 일요일 03:00 (APScheduler — `cogs/scheduler.py` `_weekly_ml_retrain()`)

**사용 위치**: `utils/gpt_ml_bridge.py` → `get_corrected_calories()`

---

## gpt_ml_bridge.py — ML→GPT 브릿지

**역할**: ML 결과를 GPT `extra_context` 파라미터로 주입

**주요 함수**:
- `get_corrected_calories(user_id, food_name, meal_type, gpt_calories)` — 보정된 칼로리 반환 (int)
- `generate_comment_with_pattern(...)` — 패턴 분석 결과가 포함된 GPT 대사 생성

**사용 위치**: `cogs/meal.py`, `utils/embed.py` → MealInputModal, MealPhotoConfirmView

---

## 향후 ML 로드맵

| 순위 | 내용 | 시기 |
|------|------|------|
| ML 2순위 | 권장 칼로리 동적 조정 (체중 변화 기반, Q-Learning) | 4주+ 데이터 후 |
| ML 4순위 | 한식 CNN 음식 인식 (MobileNetV3, AI Hub) | 사진 데이터 충분 시 |
