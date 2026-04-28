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
    goal_weight: float,
    activity: str = "보통",
) -> int:
    """
    Mifflin-St Jeor 공식 기반으로 목표 체중 달성을 위한
    일일 권장 칼로리를 계산.

    - 체중 감량 목표: TDEE에서 300~500kcal 감소
    - 체중 증량 목표: TDEE에서 300~500kcal 증가
    - 유지 목표: TDEE 그대로
    - 최소 칼로리: 여성 1200kcal / 남성 1500kcal (건강 하한선)
    """
    prompt = (
        f"다음 사용자의 하루 권장 섭취 칼로리를 계산해줘.\n\n"
        f"[사용자 정보]\n"
        f"- 성별: {gender}\n"
        f"- 나이: {age}세\n"
        f"- 키: {height}cm\n"
        f"- 현재 체중: {weight}kg\n"
        f"- 목표 체중: {goal_weight}kg\n"
        f"- 활동량: {activity}\n\n"
        f"[계산 규칙]\n"
        f"1. Mifflin-St Jeor 공식으로 기초대사량(BMR) 계산\n"
        f"   - 남성: BMR = 10×체중 + 6.25×키 - 5×나이 + 5\n"
        f"   - 여성: BMR = 10×체중 + 6.25×키 - 5×나이 - 161\n"
        f"2. 활동량 계수 적용 → TDEE 계산\n"
        f"   - 거의 없음: ×1.2 / 가벼운 활동: ×1.375 / 보통: ×1.55 / 활동적: ×1.725\n"
        f"3. 목표에 따른 칼로리 조정\n"
        f"   - 현재 체중 > 목표 체중 (감량): TDEE - 400kcal\n"
        f"   - 현재 체중 < 목표 체중 (증량): TDEE + 300kcal\n"
        f"   - 현재 체중 = 목표 체중 (유지): TDEE 그대로\n"
        f"4. 최소 칼로리 보장\n"
        f"   - 남성: 최소 1500kcal\n"
        f"   - 여성: 최소 1200kcal\n\n"
        f"최종 권장 칼로리를 정수로만 답해줘. 단위 없이 숫자만."
    )
    resp = await _client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=10,
        temperature=0,
    )
    text = resp.choices[0].message.content.strip().replace(",", "")
    try:
        cal = int(text)
        # 안전 범위 보정 (GPT가 이상한 값을 반환할 경우 대비)
        min_cal = 1500 if gender in ("남", "남성", "male") else 1200
        max_cal = 3500
        return max(min_cal, min(cal, max_cal))
    except ValueError:
        return 1800


# ── 자연어 식사 입력 파싱 ─────────────────────────────
async def parse_meal_input(raw_text: str) -> list[dict]:
    """
    유저의 자연어 입력에서 날짜 / 식사 종류 / 음식명을 추출.
    끼니가 여러 개이면 각각 추출하여 리스트로 반환.

    입력 예시:
      "어제 저녁에 치킨 먹었어"
      "오늘 아침 치킨 먹었어. 오늘 점심은 샌드위치 2개 먹었어"
      "아침 시리얼\\n점심 짜장면"

    Returns:
      [{"days_ago": 0|1|2, "meal_type": "아침"|"점심"|"저녁"|"간식"|"식사", "food_name": "..."}]
    """
    prompt = (
        "다음 문장에서 날짜, 식사 종류, 음식명을 추출해줘.\n"
        "끼니가 여러 개이면 각각 추출해줘.\n\n"
        f"입력: \"{raw_text}\"\n\n"
        "규칙:\n"
        "- days_ago: 오늘=0, 어제/1일전=1, 그저께/그제/2일전=2 (언급 없으면 0)\n"
        "- meal_type: 아침/점심/저녁/간식 중 하나 (언급 없으면 '식사')\n"
        "- food_name: 음식명과 수량을 함께 추출 (조사/어미만 제거, 수량은 유지)\n\n"
        "JSON으로만 답해줘 (다른 텍스트 없이):\n"
        '{"meals": [{"days_ago": 숫자, "meal_type": "문자열", "food_name": "문자열"}, ...]}'
    )
    resp = await _client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=300,
        temperature=0,
        response_format={"type": "json_object"},
    )
    data = json.loads(resp.choices[0].message.content)
    meals = data.get("meals", [])
    if isinstance(meals, dict):
        meals = [meals]
    if not meals:
        meals = [data]
    result = [
        {
            "days_ago":  int(m.get("days_ago", 0)),
            "meal_type": str(m.get("meal_type", "식사")),
            "food_name": str(m.get("food_name", "")),
        }
        for m in meals
        if m.get("food_name")
    ]
    return result or [{"days_ago": 0, "meal_type": "식사", "food_name": raw_text}]


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


# ── 캐릭터 대사 생성 ──────────────────────────────────
_SYSTEM_TEMPLATE = """
너는 '{tamagotchi_name}'이라는 이름의 귀여운 캐릭터야.
주인이 잘 먹고 건강하게 지내도록 곁에서 지켜보는 존재야.
주인을 진심으로 아끼고, 함께하는 친한 친구 같은 느낌이야.

[말투 규칙]
- 항상 반말로, 친근하고 귀엽게 말해줘
- 1~2문장으로 짧게 말해줘
- 이모지를 1~2개 자연스럽게 써줘
- 수치(kg, kcal)는 절대 직접 언급하지 말고 느낌으로 표현해줘
  예) 칼로리가 높아 (X) → 오늘 좀 많이 먹은 것 같은데? (O)
  예) 0.3kg 줄었어 (X) → 살이 조금씩 빠지고 있어! (O)
- 체중이 늘었을 땐 걱정하되 절대 비난하지 말고 부드럽게
- 체중이 줄었을 땐 신나게 칭찬해줘
- 잘 먹었을 땐 기뻐하고, 못 먹었을 땐 걱정해줘

[사용자 현황]
- 시작 체중: {init_weight}kg → 목표: {goal_weight}kg
- 오늘 먹은 양: {today_calories} / {daily_cal_target} kcal
- 최근 식사: {recent_meals}
- 오늘 날씨: {weather}, {temp}°C
""".strip()


async def generate_comment(
    context: str,
    user: dict,
    today_calories: int,
    recent_meals: str,
    weather_info: dict | None = None,
    extra_context: str = "",
) -> str:
    weather_text = weather_info.get("weather", "알 수 없음") if weather_info else "알 수 없음"
    temp_text    = weather_info.get("temp", "?") if weather_info else "?"

    system = _SYSTEM_TEMPLATE.format(
        tamagotchi_name  = user.get("tamagotchi_name", "타마"),
        init_weight      = user.get("init_weight", "?"),
        goal_weight      = user.get("goal_weight", "?"),
        daily_cal_target = user.get("daily_cal_target", 2000),
        today_calories   = today_calories,
        recent_meals     = recent_meals or "없음",
        weather          = weather_text,
        temp             = temp_text,
    )

    # ✅ ML 패턴 + 체중 변화 컨텍스트 주입
    if extra_context:
        system += f"\n\n[식습관 & 체중 패턴 참고]\n{extra_context}"

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


# ── 이메일 요약 ────────────────────────────────────────
async def summarize_email(subject: str, body: str) -> str:
    """
    수신 이메일을 3줄 이내로 요약.
    ML 학습 레이블로 저장되어 추후 자체 모델로 교체 예정.
    """
    prompt = (
        f"다음 이메일을 한국어로 3줄 이내로 핵심만 요약해줘.\n\n"
        f"제목: {subject}\n\n"
        f"본문:\n{body[:1500]}\n\n"
        f"요약 (3줄 이내, 번호 없이 자연스럽게):"
    )
    resp = await _client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=150,
        temperature=0.3,
    )
    return resp.choices[0].message.content.strip()
