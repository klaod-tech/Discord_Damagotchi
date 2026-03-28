"""
cogs/summary.py — 오늘 요약
동작: 📊 오늘 요약 버튼 클릭 → Ephemeral Embed로 본인에게만 표시
표시 내용:
  - 총 칼로리 / 목표 칼로리 + 프로그레스 바
  - 탄단지 비율
  - 끼니별 내역 (아침/점심/저녁/간식)
  - GPT 다마고치 한마디
"""
import discord
from discord.ext import commands
from utils.db import get_user, get_today_meals, get_today_calories
from utils.gpt import generate_comment
from datetime import date


async def send_summary(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    user = get_user(user_id)

    if not user:
        await interaction.followup.send("먼저 /start 로 등록해줘!", ephemeral=True)
        return

    meals = get_today_meals(user_id)
    total_cal = get_today_calories(user_id)
    target = user.get("daily_cal_target") or 2000
    tama_name = user.get("tamagotchi_name", "타마")

    # 달성률 + 프로그레스 바
    ratio = min(total_cal / target, 1.0) if target > 0 else 0
    filled = int(ratio * 10)
    bar = "█" * filled + "░" * (10 - filled)
    percent = int(ratio * 100)

    # 탄단지 합산
    total_protein = sum(m.get("protein") or 0 for m in meals)
    total_carbs   = sum(m.get("carbs") or 0 for m in meals)
    total_fat     = sum(m.get("fat") or 0 for m in meals)

    # 끼니별 내역
    meal_icons = {
        "아침": "🌅",
        "점심": "☀️",
        "저녁": "🌙",
        "간식": "🌃",
        "식사": "🍽️",
    }
    meal_lines = []
    for m in meals:
        icon = meal_icons.get(m.get("meal_type", "식사"), "🍽️")
        meal_lines.append(
            f"{icon} {m.get('meal_type', '식사')}: {m.get('food_name', '?')} — {m.get('calories', 0)} kcal"
        )

    meal_text = "\n".join(meal_lines) if meal_lines else "아직 아무것도 안 먹었어 🥺"

    # 식사 요약 텍스트 (GPT용)
    meal_summary = ", ".join(
        f"{m.get('meal_type', '식사')} {m.get('food_name', '?')}"
        for m in meals
    ) or "없음"

    # GPT 코멘트 생성
    comment = await generate_comment(
        context=(
            f"오늘의 식사 데이터:\n"
            f"- 총 칼로리: {total_cal} / {target} kcal\n"
            f"- 탄수화물: {total_carbs}g, 단백질: {total_protein}g, 지방: {total_fat}g\n"
            f"- 끼니 기록: {meal_summary}\n"
            f"오늘 하루 식사를 보고 따뜻하고 짧게 한마디 해줘. (2문장 이내)"
        ),
        user=user,
        today_calories=total_cal,
        recent_meals=meal_summary,
        weather_info=None,
    )

    # Embed 생성
    today_str = date.today().strftime("%Y년 %m월 %d일")
    embed = discord.Embed(
        title=f"📊 오늘의 기록 — {today_str}",
        color=0x5865F2,
    )
    embed.add_field(
        name="🔥 총 칼로리",
        value=f"`{total_cal}` / `{target}` kcal  ({percent}%)\n`{bar}`",
        inline=False,
    )
    embed.add_field(
        name="🥗 탄단지 비율",
        value=f"탄수화물 `{total_carbs:.1f}g`  |  단백질 `{total_protein:.1f}g`  |  지방 `{total_fat:.1f}g`",
        inline=False,
    )
    embed.add_field(
        name="🍽️ 끼니별 내역",
        value=meal_text,
        inline=False,
    )
    embed.add_field(
        name=f"💬 {tama_name} 한마디",
        value=f"*{comment}*",
        inline=False,
    )
    embed.set_footer(text="이 메시지는 본인에게만 보여요 👀")

    await interaction.followup.send(embed=embed, ephemeral=True)


class SummaryCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot


async def setup(bot: commands.Bot):
    await bot.add_cog(SummaryCog(bot))
