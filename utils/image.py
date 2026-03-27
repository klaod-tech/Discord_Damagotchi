"""
utils/image.py — 다마고치 상태 수치 기반 이미지 선택 로직

이미지 선택 우선순위:
  1순위: 특별 이벤트 (goal_achieved, birthday)
  2순위: 식사 상태 (overfed, underfed, eating)
  3순위: 배고픔 (hungry_cry, hungry)
  4순위: 날씨 (dusty, rainy, snowy, hot, cold, sunny, cloudy)
  5순위: 기본 감정 (sick, tired, normal, happy)
"""

from datetime import datetime, timedelta


def select_image(
    tama: dict,
    user: dict,
    weather: dict | None = None,
    *,
    just_ate: bool = False,
    overfed: bool = False,
    underfed: bool = False,
    goal_achieved: bool = False,
) -> str:
    """
    Parameters
    ----------
    tama          : Tamagotchi row  (hp, hunger, mood, last_fed_at, ...)
    user          : Users row       (daily_cal_target, ...)
    weather       : Weather_Log row (weather, temp, pm10, pm25) or None
    just_ate      : True if meal was recorded within last 3 minutes
    overfed       : True if 오후 10시 이후 총 칼로리 > daily_cal_target
    underfed      : True if 오후 10시 이후 총 칼로리 < daily_cal_target * 0.67
    goal_achieved : True if goal weight reached

    Returns
    -------
    str : 이미지 파일명 (예: 'happy.png')
    """

    hp = tama.get("hp", 70)
    hunger = tama.get("hunger", 70)
    mood = tama.get("mood", 70)
    last_fed_at = tama.get("last_fed_at")

    # ── 1순위: 특별 이벤트 ──────────────────────────────
    if goal_achieved:
        return "goal_achieved.png"

    # ── 2순위: 식사 직후 / 과식 / 소식 ─────────────────
    if just_ate or _within_minutes(last_fed_at, 3):
        return "eating.png"
    if overfed:
        return "overfed.png"
    if underfed:
        return "underfed.png"

    # ── 3순위: 배고픔 ────────────────────────────────────
    if hunger < 20:
        return "hungry_cry.png"
    if hunger < 40:
        return "hungry.png"

    # ── 4순위: 날씨 ──────────────────────────────────────
    if weather:
        img = _weather_image(weather)
        if img:
            return img

    # ── 5순위: 기본 감정 ─────────────────────────────────
    if hp < 40:
        return "sick.png"
    if mood < 40:
        return "tired.png"
    if hp >= 70 and hunger >= 70 and mood >= 70:
        return "happy.png"
    return "normal.png"


def _within_minutes(last_fed_at: str | None, minutes: int) -> bool:
    if not last_fed_at:
        return False
    try:
        fed_time = datetime.fromisoformat(last_fed_at)
        return datetime.now() - fed_time <= timedelta(minutes=minutes)
    except (ValueError, TypeError):
        return False


def _weather_image(weather: dict) -> str | None:
    w_text = (weather.get("weather") or "").strip()
    temp = weather.get("temp")
    pm10 = weather.get("pm10") or 0
    pm25 = weather.get("pm25") or 0

    if pm10 > 80 or pm25 > 35:
        return "dusty.png"
    if any(k in w_text for k in ("비", "소나기")):
        return "rainy.png"
    if "눈" in w_text:
        return "snowy.png"
    if temp is not None:
        if temp >= 26:
            return "hot.png"
        if temp <= 5:
            return "cold.png"
    if "맑음" in w_text and temp is not None and 15 <= temp <= 25:
        return "sunny.png"
    if "흐림" in w_text:
        return "cloudy.png"
    return None


# 이미지별 설명 (Embed alt-text 등에 활용)
IMAGE_DESCRIPTIONS: dict[str, str] = {
    "goal_achieved.png": "목표 달성! 🎉",
    "eating.png": "냠냠 먹는 중 😋",
    "overfed.png": "배 너무 부름... 🤢",
    "underfed.png": "오늘 많이 못 먹었어... 😢",
    "hungry_cry.png": "배고파서 울고 있어 😭",
    "hungry.png": "슬슬 배고픈데... 🥺",
    "dusty.png": "미세먼지 많은 날 😷",
    "rainy.png": "비 오는 날 🌧️",
    "snowy.png": "눈 오는 날 ❄️",
    "hot.png": "더운 날 ☀️🥵",
    "cold.png": "추운 날 🥶",
    "sunny.png": "맑고 쾌청한 날 ☀️",
    "cloudy.png": "흐린 날 ☁️",
    "sick.png": "몸이 안 좋아... 🤒",
    "tired.png": "피곤해... 😴",
    "normal.png": "오늘도 무난무난~ 😐",
    "happy.png": "기분 최고! 😄",
}
