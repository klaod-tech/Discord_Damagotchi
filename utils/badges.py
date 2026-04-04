"""
utils/badges.py — 도전과제 배지 시스템

배지 종류:
  first_meal  : 첫 번째 식사 기록
  streak_3    : 3일 연속 기록
  streak_7    : 7일 연속 기록
  streak_30   : 30일 연속 기록
  calorie_10  : 목표 칼로리 달성 10일
  photo_10    : 사진으로 식사 입력 10회
  morning_7   : 아침 식사 기록 7회

사용 위치:
  cogs/scheduler.py → _nightly_analysis() 에서 매일 밤 체크
"""

import json
from utils.db import get_conn

# ──────────────────────────────────────────────
# 배지 정의
# ──────────────────────────────────────────────
BADGES: dict[str, dict] = {
    "first_meal": {
        "name": "🍽️ 첫 끼니",
        "desc": "처음으로 식사를 기록했어!",
    },
    "streak_3": {
        "name": "🔥 3일 연속",
        "desc": "3일 연속으로 식사를 기록했어!",
    },
    "streak_7": {
        "name": "🌟 일주일 달인",
        "desc": "7일 연속 완벽 기록!",
    },
    "streak_30": {
        "name": "👑 한 달 챔피언",
        "desc": "30일 연속! 진짜 대단해!",
    },
    "calorie_10": {
        "name": "🎯 목표 달성 10회",
        "desc": "목표 칼로리를 10번이나 달성했어!",
    },
    "photo_10": {
        "name": "📸 사진 마스터",
        "desc": "사진으로 10번 식사를 기록했어!",
    },
    "morning_7": {
        "name": "🌅 아침형 인간",
        "desc": "아침 식사를 7번 기록했어!",
    },
}


# ──────────────────────────────────────────────
# 헬퍼
# ──────────────────────────────────────────────

def get_earned_badges(user: dict) -> list[str]:
    """유저의 현재 배지 목록 반환"""
    raw = user.get("badges") or "[]"
    try:
        result = json.loads(raw) if isinstance(raw, str) else raw
        return result if isinstance(result, list) else []
    except Exception:
        return []


def check_new_badges(
    user_id: str,
    user: dict,
    new_streak: int,
) -> list[str]:
    """
    현재 상태를 기반으로 새로 달성된 배지 ID 목록 반환.
    이미 획득한 배지는 제외.

    Parameters
    ----------
    user_id    : 유저 ID
    user       : get_user() 반환값 (badges 필드 포함)
    new_streak : 오늘 nightly 업데이트 후 streak 값
    """
    earned = set(get_earned_badges(user))
    new_badges: list[str] = []

    def _check(badge_id: str, condition: bool):
        if condition and badge_id not in earned:
            new_badges.append(badge_id)

    # ── 스트릭 배지 ──────────────────────────────
    _check("streak_3",  new_streak >= 3)
    _check("streak_7",  new_streak >= 7)
    _check("streak_30", new_streak >= 30)

    # ── DB 기반 배지 ─────────────────────────────
    conn = get_conn()
    cur  = conn.cursor()

    # 첫 끼니
    cur.execute("SELECT COUNT(*) AS cnt FROM meals WHERE user_id = %s", (user_id,))
    _check("first_meal", (cur.fetchone()["cnt"] or 0) >= 1)

    # 사진 입력 10회
    cur.execute(
        "SELECT COUNT(*) AS cnt FROM meals WHERE user_id = %s AND input_method = 'photo'",
        (user_id,),
    )
    _check("photo_10", (cur.fetchone()["cnt"] or 0) >= 10)

    # 아침 기록 7회
    cur.execute(
        "SELECT COUNT(*) AS cnt FROM meals WHERE user_id = %s AND meal_type = '아침'",
        (user_id,),
    )
    _check("morning_7", (cur.fetchone()["cnt"] or 0) >= 7)

    # 목표 칼로리 달성 10일 (하루 총 칼로리 ≥ 목표의 90%)
    target_cal = int((user.get("daily_cal_target") or 2000) * 0.9)
    cur.execute(
        """
        SELECT COUNT(*) AS cnt FROM (
            SELECT (recorded_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Seoul')::date AS day
            FROM meals
            WHERE user_id = %s
            GROUP BY day
            HAVING SUM(calories) >= %s
        ) sub
        """,
        (user_id, target_cal),
    )
    _check("calorie_10", (cur.fetchone()["cnt"] or 0) >= 10)

    cur.close()
    conn.close()
    return new_badges
