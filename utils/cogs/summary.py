"""
cogs/summary.py — 오늘 요약 (추후 구현)
"""

import discord
from utils.db import get_user, get_today_meals, get_today_calories


async def send_summary(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    user = get_user(user_id)
    if not user:
        await interaction.followup.send("먼저 /start 로 등록해줘!", ephemeral=True)
        return

    meals = get_today_meals(user_id)
    total_cal = get_today_calories(user_id)
    target = user.get("daily_cal_target", 2000)

    if not meals:
        await interaction.followup.send("오늘 아직 아무것도 안 먹었네! 🥺", ephemeral=True)
        return

    lines = [f"• {m['meal_type']} — {m['food_name']} ({m['calories']} kcal)" for m in meals]
    summary_text = "\n".join(lines)

    embed = discord.Embed(
        title="📊 오늘의 식사 요약",
        description=summary_text,
        color=0x5865F2,
    )
    embed.add_field(name="총 칼로리", value=f"{total_cal} / {target} kcal", inline=False)

    await interaction.followup.send(embed=embed, ephemeral=True)
