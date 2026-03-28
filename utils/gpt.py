"""
utils/gpt.py — OpenAI API 래퍼
담당 기능:
  - 온보딩: 권장 칼로리 계산
  - 식사 입력: 자연어 파싱 (날짜 + 식사 종류 + 음식명 추출)
  - 식사 입력: 음식 칼로리/영양소 분석 (텍스트)
  - 다마고치 대사 생성
"""
import os
import json
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
        return 2000


# ── 자연어 식사 입력 파싱 ─────────────────────────────
async def parse_meal_input(raw_text: str) -> dict:
    """
    유저의 자연어 입력에서 날짜 / 식사 종류 / 음식명을 추출.

    입력 예시:
      "어제 저녁에 치킨 먹었어"
      "오늘 점심 삼겹살이랑 된장찌개"
      "그저께 아침에 시리얼"
      "라면 한 그릇" (날짜/종류 생략 시 오늘/식사로 처리)

    Returns:
      {
        "days_ago": 0 | 1 | 2,       # 0=오늘, 1=어제, 2=그저께
        "meal_type": "아침"|"점심"|"저녁"|"간식",
        "food_name": "음식명 문자열"
      }
    """
    prompt = (
        "다음 문장에서 날짜, 식사 종류, 음식명을 추출해줘.\n\n"
        f"입력: \"{raw_text}\"\n\n"
        "규칙:\n"
        "- days_ago: 오늘=0, 어제/1일전=1, 그저께/그제/2일전=2 (언급 없으면 0)\n"
        "- meal_type: 아침/점심/저녁/간식 중 하나 (언급 없으면 '식사')\n"
        "- food_name: 음식명만 깔끔하게 추출 (조사/어미 제거)\n\n"
        "JSON으로만 답해줘 (다른 텍스트 없이):\n"
        '{"days_ago": 숫자, "meal_type": "문자열", "food_name": "문자열"}'
    )
    resp = await _client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=60,
        temperature=0,
        response_format={"type": "json_object"},
    )
    data = json.loads(resp.choices[0].message.content)
    return {
        "days_ago": int(data.get("days_ago", 0)),
        "meal_type": str(data.get("meal_type", "식사")),
        "food_name": str(data.get("food_name", raw_text)),
    }


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
    data = json.loads(resp.choices[0].message.content)
    return {
        "calories": int(data.get("calories", 0)),
        "protein":  float(data.get("protein", 0)),
        "carbs":    float(data.get("carbs", 0)),
        "fat":      float(data.get("fat", 0)),
        "fiber":    float(data.get("fiber", 0)),
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
    weather_text = weather_info.get("weather", "알 수 없음") if weather_info else "알 수 없음"
    temp_text    = weather_info.get("temp", "?") if weather_info else "?"

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
            {"role": "user",   "content": context},
        ],
        max_tokens=80,
        temperature=0.8,
    )
    return resp.choices[0].message.content.strip()
