"""
utils/nutrition.py — 식품의약품안전처 식품영양성분 DB API 래퍼

역할:
  - 음식명으로 식약처 DB 조회 → 영양 정보 반환
  - 조회 실패 시 None 반환 → 호출부에서 GPT fallback 처리

환경변수:
  FOOD_API_KEY — 공공데이터포털 인증키
  (https://www.data.go.kr → 식품의약품안전처_식품영양성분 DB 정보 신청)

사용 위치:
  utils/embed.py → MealInputModal.on_submit()
"""

import os
import re
import logging
import aiohttp
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

FOOD_API_KEY = os.getenv("FOOD_API_KEY")
FOOD_API_URL = (
    "https://apis.data.go.kr/1471000/FoodNtrCpntDbInfo01/getFoodNtrCpntDbInq01"
)


async def search_food_nutrition(food_name: str) -> dict | None:
    """
    식약처 식품영양성분 DB에서 음식명으로 조회.

    Parameters
    ----------
    food_name : 조회할 음식명 (예: "순대국밥", "비빔밥")

    Returns
    -------
    {
        "calories": int,
        "protein" : float,  # g
        "carbs"   : float,  # g
        "fat"     : float,  # g
        "fiber"   : float,  # g
        "source"  : "식약처",
    }
    또는 None (API 키 없음 / 검색 결과 없음 / 오류)

    Notes
    -----
    - 영양 수치는 1회 제공량(SERVING_WT) 기준으로 계산
    - SERVING_WT 없으면 100g 기준 적용
    - API 응답의 수치는 100g 당 값 → serving_g / 100 배율 적용
    """
    if not FOOD_API_KEY:
        logger.debug("[nutrition] FOOD_API_KEY 미설정 — GPT fallback")
        return None

    params = {
        "serviceKey": FOOD_API_KEY,
        "pageNo":     "1",
        "numOfRows":  "3",
        "type":       "json",
        "FOOD_NM_KOR": food_name,
    }

    try:
        timeout = aiohttp.ClientTimeout(total=5)
        async with aiohttp.ClientSession() as session:
            async with session.get(FOOD_API_URL, params=params, timeout=timeout) as resp:
                if resp.status != 200:
                    return None

                data = await resp.json(content_type=None)

        items = data.get("body", {}).get("items", [])
        if not items:
            print(f"[nutrition] '{food_name}' 검색 결과 없음 — GPT fallback")
            return None

        item = items[0]

        # 1회 제공량이 없으면 100g 기준 그대로 사용
        serving_g = _to_float(item.get("SERVING_WT")) or 100.0
        factor    = serving_g / 100.0

        calories = _to_float(item.get("ENERC")) * factor
        protein  = _to_float(item.get("PROT"))  * factor
        carbs    = _to_float(item.get("CHO"))   * factor
        fat      = _to_float(item.get("FAT"))   * factor
        fiber    = _to_float(item.get("FIBTG")) * factor

        if calories <= 0:
            logger.debug(f"[nutrition] '{food_name}' 칼로리 0 — GPT fallback")
            return None

        print(
            f"[nutrition] '{food_name}' 식약처 조회 성공 "
            f"({int(calories)}kcal, 제공량 {serving_g}g)"
        )
        return {
            "calories": int(calories),
            "protein":  round(protein, 1),
            "carbs":    round(carbs, 1),
            "fat":      round(fat, 1),
            "fiber":    round(fiber, 1),
            "source":   "식약처",
        }

    except Exception:
        return None


def _to_float(val) -> float:
    """None / 빈 문자열 / 변환 불가 값을 0.0으로 처리"""
    try:
        return float(val or 0)
    except (ValueError, TypeError):
        return 0.0
