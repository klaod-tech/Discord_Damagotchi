"""
utils/gpt_ml_bridge.py
────────────────────────────────────────────────────────────────
ML 패턴 분석 결과를 GPT 대사 생성에 주입하는 브릿지 모듈.

기존 utils/gpt.py의 generate_comment()를 대체하지 않고,
ML 컨텍스트가 주입된 강화 버전의 generate_comment를 제공.

사용 예:
    from utils.gpt_ml_bridge import generate_comment_with_pattern

    comment = await generate_comment_with_pattern(
        user_id         = "123456789",
        daily_cal_target = 2000,
        today_calories   = 1800,
        meal_summary     = "아침: 토스트, 점심: 비빔밥, 저녁: 삼겹살",
        tamagotchi_name  = "몽실이",
    )
────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import logging
from typing import Optional

from utils.pattern import analyze_eating_patterns, forecast_weekly_calories
from utils.ml import correct_calories
from utils.gpt import generate_comment   # 기존 GPT 래퍼 재사용

logger = logging.getLogger(__name__)


async def generate_comment_with_pattern(
    user_id: str,
    user: dict,
    daily_cal_target: int,
    today_calories: int,
    meal_summary: str,
    include_forecast: bool = False,
) -> str:
    """
    ML 패턴 분석 결과를 반영한 다마고치 대사 생성.

    Parameters
    ----------
    user_id          : 디스코드 유저 ID
    user             : get_user() 반환 dict
    daily_cal_target : 권장 칼로리
    today_calories   : 오늘 총 섭취 칼로리
    meal_summary     : 오늘 식사 요약 문자열
    include_forecast : Prophet 예측 포함 여부

    Returns
    -------
    다마고치 대사 문자열
    """
    # 1. 패턴 분석
    pattern_result = analyze_eating_patterns(user_id, daily_cal_target)
    gpt_context = pattern_result.get("gpt_context", "")

    # 2. Prophet 예측 (선택적)
    forecast_text = ""
    if include_forecast:
        forecast = forecast_weekly_calories(user_id, daily_cal_target)
        if forecast:
            forecast_text = f"\n[예측] {forecast}"

    # 3. 패턴 컨텍스트 + 예측 합산
    full_context = gpt_context + forecast_text

    # 4. 기존 generate_comment에 extra_context 주입
    comment = await generate_comment(
        context=(
            f"오늘 하루 기록을 봐줘. "
            f"목표 {daily_cal_target}kcal 중 {today_calories}kcal 먹었어. "
            f"짧게 한마디 해줘!"
        ),
        user=user,
        today_calories=today_calories,
        recent_meals=meal_summary,
        extra_context=full_context,
    )

    return comment


def get_corrected_calories(
    user_id: str,
    food_name: str,
    meal_type: str,
    gpt_calories: int,
    recorded_at=None,
) -> int:
    """
    ML 보정된 칼로리 반환. embed.py의 MealInputModal에서 호출.

    기존 코드 변경 최소화를 위해 int만 반환.
    """
    result = correct_calories(
        user_id       = user_id,
        food_name     = food_name,
        meal_type     = meal_type,
        gpt_calories  = gpt_calories,
        recorded_at   = recorded_at,
    )

    if result["model_used"] or result["correction_pct"] != 0.0:
        pct = result["correction_pct"]
        sign = "+" if pct >= 0 else ""
        logger.info(
            f"[ml-bridge] 칼로리 보정 | {food_name} | "
            f"{gpt_calories} → {result['corrected_cal']}kcal ({sign}{pct:.1f}%)"
        )

    return result["corrected_cal"]
