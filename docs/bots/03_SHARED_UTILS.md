# 공유 유틸리티 가이드

> `utils/` 디렉터리의 공통 모듈 사용법.  
> 각 봇은 이 모듈들을 import해서 사용하며, 수정 시 다른 봇에 영향을 줄 수 있으니 주의.

---

## 1. utils/gpt.py — OpenAI API 래퍼

### 주요 함수

```python
# 칼로리 계산 (온보딩 시 1회)
async def calculate_daily_calories(gender, age, height, weight, goal_weight, activity) -> int

# 자연어 식사 파싱
async def parse_meal_input(text: str) -> dict
# 반환: {"days_ago": int, "meal_type": str, "food_name": str}

# 영양소 분석 (식약처 fallback용)
async def analyze_meal_text(food_name: str) -> dict
# 반환: {"calories": int, "protein": float, "carbs": float, "fat": float, "fiber": float}

# 다마고치 대사 생성
async def generate_comment(context, user, today_calories, recent_meals, weather_info, extra_context="") -> str

# 이메일 요약
async def summarize_email(subject: str, body: str) -> str
```

### generate_comment 사용 예시

```python
from utils.gpt import generate_comment

comment = await generate_comment(
    context="방금 치킨을 먹었어. 반응해줘!",
    user=user,              # DB에서 가져온 users row
    today_calories=1200,
    recent_meals="치킨",
    weather_info=None,      # 또는 {"weather": "맑음", "temp": 25.0}
)
```

---

## 2. utils/embed.py — 메인 Embed & MainView

> **주의**: 이 파일은 먹구름봇이 소유합니다. 다른 봇은 읽기만 하세요.

### 주요 컴포넌트

```python
# 메인 Embed 생성/수정 (먹구름봇 전용 쓰레드에 전송)
async def create_or_update_embed(
    thread, user, tama, comment,
    weather=None,
    *,
    just_ate=False,
    overfed=False,
    underfed=False,
    goal_achieved=False,
) -> str  # embed_message_id 반환

# Embed 색상 결정 (hp/hunger/mood 평균 기반)
def _embed_color(tama: dict) -> int

# 칼로리 → 포만감 증가량
def _hunger_gain(calories: int) -> int  # 15 / 35 / 50

# MainView — 5개 버튼 (먹구름봇 메인 쓰레드 Embed에 붙음)
class MainView(discord.ui.View)

# 식사 입력 모달 (텍스트)
class MealInputModal(discord.ui.Modal)

# 식사 입력 방식 선택 (텍스트 / 사진)
class MealInputSelectView(discord.ui.View)
```

### 날씨 텍스트 생성 (독립 함수 — 재사용 가능)

```python
from utils.embed import _build_weather_text

weather_text = _build_weather_text(user, weather_log)
```

---

## 3. utils/image.py — 이미지 선택 로직

```python
from utils.image import select_image, IMAGE_DESCRIPTIONS

# 이미지 파일명 선택 (우선순위 적용)
filename = select_image(
    tama, user, weather,
    just_ate=False,
    overfed=False,
    underfed=False,
    goal_achieved=False,
)
# 반환: "normal.png" / "eat.png" / "rainy.png" 등 11종
```

### 이미지 우선순위

| 우선순위 | 조건 | 파일명 |
|---------|------|-------|
| 1 | 목표 체중 달성 | `cheer.png` |
| 2 | 식사 직후 3분 | `eat.png` |
| 3 | hunger < 40 | `upset.png` |
| 4 | PM10>80 or PM2.5>35 | `wear mask.png` |
| 4 | 비/소나기 | `rainy.png` |
| 4 | 눈 | `snow.png` |
| 4 | 기온 ≥ 26°C | `hot.png` |
| 4 | 기온 ≤ 5°C | `warm.png` |
| 5 | hp<40 or mood<40 | `tired.png` |
| 5 | hp≥70, hunger≥70, mood≥70 | `smile.png` |
| 5 | 그 외 | `normal.png` |

---

## 4. utils/ml.py — 칼로리 보정 모델

```python
from utils.ml import correct_calories_immediate, load_user_model, retrain_all_users

# 즉시 보정 (양 표현 키워드 배율 적용 — 항상 동작)
corrected = correct_calories_immediate(food_name: str, gpt_calories: int) -> int
# "조금" ×0.7 / "반" ×0.5 / "많이" ×1.4 / "두 그릇" ×2.0 등

# 개인화 모델 로드 (30건+ 누적 시)
model = load_user_model(user_id: str)  # None이면 아직 학습 불가

# 전체 유저 모델 재학습 (스케줄러에서 주 1회 호출)
retrain_all_users()
```

---

## 5. utils/gpt_ml_bridge.py — ML→GPT 브릿지

```python
from utils.gpt_ml_bridge import get_corrected_calories

# ML 보정된 칼로리 반환 (즉시 보정 + 개인화 모델 통합)
calories = get_corrected_calories(
    user_id="12345",
    food_name="치킨",
    meal_type="저녁",
    gpt_calories=800,
) -> int
```

---

## 6. utils/nutrition.py — 식약처 API

```python
from utils.nutrition import search_food_nutrition

# 식약처 식품영양성분 DB 검색 (1순위)
result = await search_food_nutrition(food_name: str) -> dict | None
# 반환: {"calories": int, "protein": float, "carbs": float, "fat": float, "fiber": float}
# 없으면 None → gpt.analyze_meal_text()로 fallback
```

---

## 7. utils/pattern.py — 식습관 패턴 분석

```python
from utils.pattern import analyze_eating_patterns

result = analyze_eating_patterns(user_id: str, target_cal: int) -> dict
# 반환: {"gpt_context": str}  ← generate_comment()의 extra_context에 주입
```

분석 패턴 5종: 요일별 과식 / 아침 결식 / 저녁 집중 / 주간 추이 / 연속 소식

---

## 8. utils/badges.py — 배지 시스템

```python
from utils.badges import check_new_badges, BADGE_DEFINITIONS

# 신규 배지 체크 (스케줄러 nightly에서 호출)
new_badges = check_new_badges(user_id: str, streak: int) -> list[str]
# 반환: 새로 획득한 badge_id 리스트

# 배지 정의
BADGE_DEFINITIONS = {
    "first_meal": {"name": "첫 한 끼", "emoji": "🍽️"},
    "streak_3":   {"name": "3일 연속", "emoji": "🔥"},
    "streak_7":   {"name": "일주일 기록왕", "emoji": "⭐"},
    "streak_30":  {"name": "한 달 챔피언", "emoji": "🏆"},
    "goal_achieved": {"name": "목표 달성", "emoji": "🎯"},
    "weight_loss_1": {"name": "첫 감량", "emoji": "📉"},
    "perfect_week":  {"name": "완벽한 한 주", "emoji": "💎"},
}
```

---

## 9. utils/mail.py — 이메일 클라이언트 (메일봇 전용)

```python
from utils.mail import fetch_new_emails, send_email

# IMAP 수신 (새 메일 목록)
emails = await fetch_new_emails(naver_email, naver_app_pw, last_uid) -> list[dict]
# 각 dict: {"uid": int, "subject": str, "from": str, "body": str, "sent_at": datetime}

# SMTP 발신
await send_email(to_email, subject, body)
```

---

## 10. utils/email_ui.py — 이메일 UI 모달 (메일봇/먹구름봇 공유)

```python
from utils.email_ui import EmailSetupModal, SenderAddModal

# 이메일 계정 설정 모달
class EmailSetupModal(discord.ui.Modal)

# 발신자 추가 모달
class SenderAddModal(discord.ui.Modal)
```

---

## 11. 새 유틸리티 추가 시 규칙

1. `utils/` 아래 새 파일 생성 (e.g. `utils/diary_analyzer.py`)
2. 파일명은 도메인 명확히 표시
3. 다른 봇의 유틸을 수정하지 않음 — 필요하면 자신의 파일 신규 생성
4. `utils/db.py`에 함수 추가 시 봇 도메인 접두사 사용:
   - 일기봇: `get_diary_*`, `save_diary_*`
   - 일정봇: `get_schedule_*`, `save_schedule_*`
