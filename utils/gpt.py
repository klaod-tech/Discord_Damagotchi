"""
utils/gpt.py — OpenAI API 래퍼

담당 기능:
  - 온보딩: 권장 칼로리 계산
  - 식사 입력: 음식 칼로리/영양소 분석 (텍스트)
  - 식사 입력: 사진 분석 (Vision)
  - 다마고치 대사 생성
"""

import os
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL = "gpt-4o"


# ── 권장 칼로리 계산 (온보딩) ──────────────────────────
async def calculate_daily_calories(
    gender: str,
    age: int,
    height: float,
    weight: float,
    activity: str,
    goal: str,
) -> int:
    """
    Returns daily calorie target (kcal, int).
    """
    prompt = (
        f"사용자 정보: 성별={gender}, 나이={age}세, 키={height}cm, "
        f"체중={weight}kg, 활동량={activity}, 목표={goal}.\n"
        "이 사람의 하루 권장 섭취 칼로리를 정수로만 답해줘. 단위 없이 숫자만."
    )
    resp = await _client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=10,
        temperature=0,
    )
    text = resp.choices[0].message.content.strip().replace(",", "")
    try:
        return int(text)
    except ValueError:
        return 2000  # fallback


# ── 텍스트 식사 분석 ───────────────────────────────────
async def analyze_meal_text(food_name: str) -> dict:
    """
    Returns {calories, protein, carbs, fat, fiber} as numeric values.
    food_name: 쉼표 구분 음식명 (예: "삼겹살 200g, 쌈채소")
    """
    prompt = (
        f"다음 식사의 영양 정보를 추정해줘: {food_name}\n"
        "JSON 형식으로만 답해줘 (다른 텍스트 없이):\n"
        '{"calories": 정수, "protein": 소수, "carbs": 소수, "fat": 소수, "fiber": 소수}'
    )
    resp = await _client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=80,
        temperature=0,
        response_format={"type": "json_object"},
    )
    import json
    data = json.loads(resp.choices[0].message.content)
    return {
        "calories": int(data.get("calories", 0)),
        "protein": float(data.get("protein", 0)),
        "carbs": float(data.get("carbs", 0)),
        "fat": float(data.get("fat", 0)),
        "fiber": float(data.get("fiber", 0)),
    }


# ── 사진 식사 분석 (Vision) ────────────────────────────
async def analyze_meal_image(image_url: str) -> dict:
    """
    image_url: Discord CDN URL 또는 base64 data URL
    Returns {food_name, calories, protein, carbs, fat, fiber}
    """
    resp = await _client.chat.completions.create(
        model=MODEL,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": (
                        "이 음식 사진의 영양 정보를 추정해줘.\n"
                        "JSON 형식으로만 답해줘 (다른 텍스트 없이):\n"
                        '{"food_name": "음식명", "calories": 정수, '
                        '"protein": 소수, "carbs": 소수, "fat": 소수, "fiber": 소수}'
                    ),
                },
                {"type": "image_url", "image_url": {"url": image_url}},
            ],
        }],
        max_tokens=120,
        temperature=0,
        response_format={"type": "json_object"},
    )
    import json
    data = json.loads(resp.choices[0].message.content)
    return {
        "food_name": data.get("food_name", "알 수 없는 음식"),
        "calories": int(data.get("calories", 0)),
        "protein": float(data.get("protein", 0)),
        "carbs": float(data.get("carbs", 0)),
        "fat": float(data.get("fat", 0)),
        "fiber": float(data.get("fiber", 0)),
    }


# ── 다마고치 대사 생성 ─────────────────────────────────
_SYSTEM_TEMPLATE = """
너는 '{tamagotchi_name}'이라는 이름의 AI 다마고치야.
성격은 밝고 긍정적이야. 짧고 친근하게 말해줘.

[사용자 정보]
- 시작 체중: {init_weight}kg, 목표 체중: {goal_weight}kg
- 권장 칼로리: {daily_cal_target} kcal
- 오늘 섭취 칼로리: {today_calories} / {daily_cal_target} kcal
- 최근 식사: {recent_meals}
- 오늘 날씨: {weather}, {temp}°C

건강 조언은 부드럽게, 수치는 직접 언급하지 말고 느낌으로 표현해줘.
""".strip()


async def generate_comment(
    context: str,
    user: dict,
    today_calories: int,
    recent_meals: str,
    weather_info: dict | None = None,
) -> str:
    """
    context: 대사 맥락 (예: "식사 후", "날씨 반응", "오늘 요약")
    Returns: 다마고치 한마디 (1~2문장)
    """
    weather_text = weather_info.get("weather", "알 수 없음") if weather_info else "알 수 없음"
    temp_text = weather_info.get("temp", "?") if weather_info else "?"

    system = _SYSTEM_TEMPLATE.format(
        tamagotchi_name=user.get("tamagotchi_name", "타마"),
        init_weight=user.get("init_weight", "?"),
        goal_weight=user.get("goal_weight", "?"),
        daily_cal_target=user.get("daily_cal_target", 2000),
        today_calories=today_calories,
        recent_meals=recent_meals or "없음",
        weather=weather_text,
        temp=temp_text,
    )

    resp = await _client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": context},
        ],
        max_tokens=80,
        temperature=0.8,
    )
    return resp.choices[0].message.content.strip()
