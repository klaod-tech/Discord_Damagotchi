# 식사봇 — 사진 입력 흐름

---

## 경로 1: 사진 입력 대기 흐름 (먹구름봇 버튼에서 유도)

```
[먹구름봇] 유저가 "📸 사진으로 입력" 클릭
  → MealInputSelectView.photo_btn()  (utils/embed.py)
  → set_meal_waiting(user_id, seconds=60)  ← DB에 만료 시각 저장
  → meal_thread_id 있으면:
       edit_message("🍽️ {meal_thread.mention}에 음식 사진을 올려줘! (60초)")
  → 없으면:
       edit_message("📸 지금 이 채팅에 올려줘 (60초)")

[60초 내 유저가 식사 쓰레드에 사진 업로드]
  → MealPhotoCog.on_message() 트리거
  → 6가지 필터 통과 확인
  → is_meal_waiting(user_id) → True
  → clear_meal_waiting(user_id)  ← 즉시 해제
  → "📸 사진 분석 중... 잠깐만 기다려줘!" 임시 메시지 전송
  → analyze_food_image(image_url)  ← GPT-4o Vision
  → 임시 메시지 삭제
  → _build_analysis_embed(analysis) + MealPhotoConfirmView 전송

[유저: "✅ 기록하기" 클릭]
  → MealPhotoConfirmView.confirm()
  → get_corrected_calories() — ML 보정
  → generate_comment("사진으로 식사 기록! 반응해줘!")
  → create_meal(..., input_method="photo")
  → update_tamagotchi(hunger+, mood+, hp+, last_fed_at)
  → Ephemeral 결과 전송 (칼로리/영양소/총 칼로리)
  → create_or_update_embed(thread, just_ate=True)  ← 메인 Embed 갱신
  → 버튼 비활성화
```

---

## 경로 2: 자발적 사진 업로드 흐름 (대기 없이 쓰레드에 업로드)

```
[유저가 식사 전용 쓰레드에 사진 업로드]
  → MealPhotoCog.on_message() 트리거
  → is_meal_waiting(user_id) → False
  → "📸 음식 사진이에요?" + MealPhotoDetectView 전송

[유저: "✅ 분석하기" 클릭]
  → MealPhotoDetectView.analyze()
  → defer(thinking=True)
  → analyze_food_image(image_url)  ← GPT-4o Vision
  → 감지 버튼 비활성화
  → _build_analysis_embed(analysis) + MealPhotoConfirmView 전송

[이후는 경로 1의 "기록하기" 단계와 동일]
```

---

## GPT-4o Vision 분석 상세

```python
analyze_food_image(image_url: str) -> dict

# 반환:
{
    "food_name":   str,   # 음식명 (한국어)
    "meal_type":   str,   # "아침" | "점심" | "저녁" | "간식"
    "calories":    int,
    "protein":     float, # (g)
    "carbs":       float, # (g)
    "fat":         float, # (g)
    "fiber":       float, # (g)
    "description": str,   # 음식 한 줄 설명 (Embed용)
}

# 모델: gpt-4o, detail="low" (비용 절감)
# JSON만 반환, JSON 펜스 제거 처리 포함
```

---

## ML 칼로리 보정

```python
from utils.gpt_ml_bridge import get_corrected_calories

calories = get_corrected_calories(
    user_id=user_id,
    food_name=food_name,
    meal_type=meal_type,
    gpt_calories=analysis["calories"],  # GPT 분석값 → ML 보정
)
```

> ML 모델이 없거나 데이터 부족 시 GPT 원값 그대로 사용

---

## DB 저장

```python
create_meal(
    user_id      = user_id,
    meal_type    = analysis["meal_type"],
    food_name    = analysis["food_name"],
    calories     = corrected_calories,
    protein      = analysis["protein"],
    carbs        = analysis["carbs"],
    fat          = analysis["fat"],
    fiber        = analysis["fiber"],
    input_method = "photo",     # ← 사진 구분 (배지 photo_10 조건)
    gpt_comment  = comment,
    recorded_date= None,        # 항상 오늘 날짜 (사진 입력은 현재 시간)
)
```

---

## 타마고치 수치 갱신 공식

```python
_hunger_gain(calories):
    calories >= 800 → +50
    calories >= 400 → +35
    else            → +15

new_hunger = min(100, tama.hunger + hunger_gain)
new_mood   = min(100, tama.mood   + 5)
new_hp     = min(100, tama.hp     + 5)
last_fed_at = datetime.utcnow().isoformat()
```

---

## 봇 간 협력 관계

```
먹구름봇 embed.py           식사봇 meal.py
─────────────────           ──────────────────
set_meal_waiting()     →    is_meal_waiting()
(사진 입력 버튼 클릭)         clear_meal_waiting()
                             analyze_food_image()
                             create_meal()
                             update_tamagotchi()
                    ←       create_or_update_embed()
                             (메인 Embed 갱신)
```

**공유 상태: DB `users.meal_waiting_until` 컬럼** (IPC 없이 DB 단일 공급원)
