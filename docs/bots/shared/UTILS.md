# 공통 유틸리티 가이드 (utils/)

---

## 1. utils/db.py

→ 상세 내용은 `shared/DB.md` 참조

핵심 사용 패턴:

```python
from utils.db import get_user, get_conn

# 단건 조회
user = get_user(user_id)  # dict | None

# 직접 쿼리가 필요한 경우
conn = get_conn()
cur  = conn.cursor()
cur.execute("SELECT ...", (param,))
row  = cur.fetchone()   # dict (RealDictCursor)
rows = cur.fetchall()   # list[dict]
conn.commit()
cur.close()
conn.close()
```

---

## 2. utils/gpt.py — OpenAI GPT-4o 래퍼

### 함수 목록

| 함수 | 반환 | 설명 |
|------|------|------|
| `calculate_daily_calories(gender, age, height, weight, goal_weight, activity="보통")` | `int` | Mifflin-St Jeor 기반 권장 칼로리 계산 |
| `parse_meal_input(raw_text)` | `dict` | 자연어 파싱: `{days_ago, meal_type, food_name}` |
| `analyze_meal_text(food_name)` | `dict` | 음식 영양소 분석: `{calories, protein, carbs, fat, fiber}` |
| `generate_comment(context, user, today_calories, recent_meals, weather_info, extra_context="")` | `str` | 타마고치 GPT 대사 생성 |
| `analyze_photo(image_bytes)` | `dict` | GPT-4o Vision 음식 분석: `{food_name, calories, ...}` |
| `summarize_email(subject, body)` | `str` | 이메일 본문 요약 (200자 이하면 원문 반환) |

### 사용 예시

```python
from utils.gpt import generate_comment, parse_meal_input

# 대사 생성
comment = await generate_comment(
    context="식사 후 반응해줘!",
    user=user,
    today_calories=1200,
    recent_meals="치킨",
    weather_info=None,
)

# 자연어 파싱
parsed = await parse_meal_input("어제 저녁에 삼겹살 먹었어")
# → {"days_ago": 1, "meal_type": "저녁", "food_name": "삼겹살"}
```

---

## 3. utils/image.py — 이미지 선택 로직

```python
from utils.image import select_image, IMAGE_DESCRIPTIONS

# 이미지 파일명 결정
filename = select_image(
    tama, user, weather_log,
    just_ate=False,
    overfed=False,
    underfed=False,
    goal_achieved=False,
)
```

### 이미지 선택 우선순위

| 순위 | 조건 | 이미지 |
|------|------|--------|
| 1 | `goal_achieved=True` | `cheer.png` |
| 2 | `just_ate=True` 또는 3분 이내 식사 | `eat.png` |
| 3 | `hunger < 40` | `upset.png` |
| 4 | 날씨 기반 (PM10>80 → 마스크, 비, 눈, 더위, 추위) | `wear mask.png`, `rainy.png`, `snow.png`, `hot.png`, `warm.png` |
| 5 | `hp < 40` 또는 `mood < 40` | `tired.png` |
| 6 | hp/hunger/mood 모두 ≥ 70 | `smile.png` |
| 기본 | 그 외 | `normal.png` |

### 이미지 파일 목록 (images/ 폴더)

```
cheer.png     — 목표 달성!
eat.png       — 냠냠 먹는 중
upset.png     — 배고파... (hungry + hungry_cry 통합)
wear mask.png — 미세먼지 많은 날
rainy.png     — 비 오는 날
snow.png      — 눈 오는 날
warm.png      — 추운 날 따뜻하게
hot.png       — 더운 날
tired.png     — 피곤하고 힘들어 (tired + sick 통합)
normal.png    — 오늘도 무난무난
smile.png     — 기분 최고!
```

> 파일명 소문자 고정 (`eat.png` O, `Eat.PNG` X)

---

## 4. utils/embed.py — 메인 Embed & 버튼 뷰

### 핵심 함수

```python
from utils.embed import create_or_update_embed, build_main_embed

# 메인 Embed 생성 또는 수정
await create_or_update_embed(
    thread,          # discord.Thread
    user,            # dict from get_user()
    tama,            # dict from get_tamagotchi()
    comment,         # str — GPT 대사
    weather=None,    # dict | None — 날씨 정보
    just_ate=False,
    overfed=False,
    underfed=False,
    goal_achieved=False,
)
```

### 버튼 View

| 클래스 | 설명 |
|--------|------|
| `MainView` | 메인 버튼 뷰 (timeout=None, Persistent) — Row0: 식사입력/하루정리/뭐먹고싶어, Row1: 설정/체중기록 |
| `MealInputSelectView` | 식사 입력 방식 선택 (텍스트/사진) |
| `MealInputModal` | 자연어 식사 입력 Modal (utils/embed.py에 위치!) |

> **주의**: `MealInputModal`은 `cogs/meal.py`가 아니라 `utils/embed.py`에 있음

### 내부 유틸 함수

```python
_build_weather_text(user, weather_log)  # 날씨 텍스트 포맷 (하루정리/날씨봇 공유)
_send_daily_analysis(thread, user, tama, meals, total_cal, target_cal, target_date)  # 일일 결산 Embed
_hunger_gain(calories)  # 칼로리 → hunger 회복량 계산
```

---

## 5. utils/badges.py — 배지 시스템

```python
from utils.badges import BADGES, check_new_badges, get_earned_badges

# 새 배지 체크 (scheduler._nightly_analysis 에서 호출)
new_badge_ids = check_new_badges(user_id, user, new_streak)

# 배지 목록 조회
earned = get_earned_badges(user)  # list[str] — badge_id 목록
```

### 배지 ID 전체 목록

| ID | 이름 | 조건 |
|----|------|------|
| `first_meal` | 🍽️ 첫 끼니 | meals 1건 이상 |
| `streak_3` | 🔥 3일 연속 | streak ≥ 3 |
| `streak_7` | 🌟 일주일 달인 | streak ≥ 7 |
| `streak_30` | 👑 한 달 챔피언 | streak ≥ 30 |
| `calorie_10` | 🎯 목표 달성 10회 | 목표 칼로리 90% 이상 달성 ≥ 10일 |
| `photo_10` | 📸 사진 마스터 | input_method='photo' ≥ 10회 |
| `morning_7` | 🌅 아침형 인간 | meal_type='아침' ≥ 7회 |

---

## 6. utils/ml.py — 칼로리 보정 ML

```python
from utils.ml import retrain_all_users

# 전체 유저 모델 재학습 (scheduler._weekly_ml_retrain 에서 호출)
retrain_all_users()
```

개별 예측은 `utils/gpt_ml_bridge.py` 통해 사용:

```python
from utils.gpt_ml_bridge import get_corrected_calories

calories = get_corrected_calories(
    user_id=user_id,
    food_name=food_name,
    meal_type=meal_type,
    gpt_calories=gpt_raw_calories,
)
```

---

## 7. utils/nutrition.py — 식약처 식품영양성분 DB

```python
from utils.nutrition import search_food_nutrition

result = await search_food_nutrition(food_name)
# 반환: {"calories": int, "protein": float, "carbs": float, "fat": float, "fiber": float}
# 없으면 None → GPT fallback
```

---

## 8. utils/pattern.py — 식사 패턴 분석

```python
from utils.pattern import analyze_eating_patterns

result = analyze_eating_patterns(user_id, target_cal)
# 반환: {"gpt_context": str, ...}
# 하루정리 버튼에서 GPT 컨텍스트로 주입됨
```

---

## 9. utils/mail.py — 이메일 IMAP/SMTP

```python
from utils.mail import fetch_new_emails, send_email

# IMAP 새 메일 조회 (네이버)
emails = await fetch_new_emails(naver_email, naver_app_pw, last_uid)
# 반환: [{"uid": int, "subject": str, "from": str, "body": str, "sent_at": datetime}]

# SMTP 발신 (먹구름봇 공용 계정)
await send_email(to_email, subject, body)
```

---

## 10. utils/email_ui.py — 이메일 공유 Modal

```python
# 두 봇 모두에서 import 가능
from utils.email_ui import EmailSetupModal, SenderAddModal
```

| 클래스 | 용도 |
|--------|------|
| `EmailSetupModal` | 네이버 계정 설정 (먹구름봇 설정메뉴 + 이메일봇 슬래시커맨드) |
| `SenderAddModal` | 발신자 등록 모달 |
