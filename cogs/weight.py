"""
cogs/weight.py — 체중 기록 기능
────────────────────────────────────────────────────────────────
흐름:
  1. [⚖️ 체중 기록] 버튼 클릭
  2. 체중 입력 Modal (현재 체중 kg 입력)
  3. DB weight_log 저장
  4. 목표 체중과 비교 → 다마고치 반응
  5. (추후) ML 2순위 강화학습 Y값으로 활용
────────────────────────────────────────────────────────────────
"""

import discord
from discord.ext import commands
from datetime import date

from utils.db import get_user, get_tamagotchi
from utils.gpt import generate_comment
from utils.embed import create_or_update_embed


# ──────────────────────────────────────────────
# DB 함수 (utils/db.py에 추가 필요)
# ──────────────────────────────────────────────

def save_weight_log(user_id: str, weight: float) -> None:
    """weight_log 테이블에 체중 기록 저장"""
    from utils.db import get_conn
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO weight_log (user_id, weight, recorded_at) VALUES (%s, %s, NOW())",
        (user_id, weight),
    )
    conn.commit()
    cur.close()
    conn.close()


def get_weight_history(user_id: str, limit: int = 7) -> list[dict]:
    """최근 체중 기록 조회"""
    from utils.db import get_conn
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT weight, recorded_at
        FROM weight_log
        WHERE user_id = %s
        ORDER BY recorded_at DESC
        LIMIT %s
        """,
        (user_id, limit),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [{"weight": float(r["weight"]), "recorded_at": r["recorded_at"]} for r in rows]


def get_latest_weight(user_id: str) -> float | None:
    """가장 최근 체중 반환"""
    history = get_weight_history(user_id, limit=1)
    return history[0]["weight"] if history else None


# ──────────────────────────────────────────────
# 체중 입력 Modal
# ──────────────────────────────────────────────

class WeightInputModal(discord.ui.Modal, title="⚖️ 체중 기록"):
    weight_input = discord.ui.TextInput(
        label="현재 체중을 입력해줘 (kg)",
        placeholder="예: 75.3",
        max_length=5,
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            user_id = str(interaction.user.id)
            user    = get_user(user_id)
            tama    = get_tamagotchi(user_id)

            if not user or not tama:
                await interaction.followup.send("❌ 등록된 유저가 아니야!", ephemeral=True)
                return

            # 체중 파싱
            try:
                weight = float(self.weight_input.value.strip().replace("kg", ""))
            except ValueError:
                await interaction.followup.send(
                    "❌ 숫자로 입력해줘! (예: 75.3)", ephemeral=True
                )
                return

            if not (20.0 <= weight <= 300.0):
                await interaction.followup.send(
                    "❌ 올바른 체중 범위가 아니야! (20~300kg)", ephemeral=True
                )
                return

            # DB 저장
            save_weight_log(user_id, weight)

            # 목표 체중과 비교
            goal_weight  = float(user.get("goal_weight") or 70)
            init_weight  = float(user.get("init_weight") or weight)
            tama_name    = user.get("tamagotchi_name", "타마")

            diff_from_goal = round(weight - goal_weight, 1)
            diff_from_init = round(weight - init_weight, 1)

            # 이전 체중과 비교
            prev_weight = get_latest_weight_before(user_id)
            diff_from_prev = round(weight - prev_weight, 1) if prev_weight else 0

            # 상황에 맞는 컨텍스트 생성
            if diff_from_goal <= 0:
                context = (
                    f"목표 체중({goal_weight}kg)을 달성했어! "
                    f"현재 체중 {weight}kg. 축하해줘!"
                )
                goal_achieved = True
            elif diff_from_prev < 0:
                context = (
                    f"체중이 {abs(diff_from_prev)}kg 줄었어! "
                    f"현재 {weight}kg, 목표까지 {diff_from_goal}kg 남았어. 칭찬해줘!"
                )
                goal_achieved = False
            elif diff_from_prev > 0:
                context = (
                    f"체중이 {diff_from_prev}kg 늘었어. "
                    f"현재 {weight}kg, 목표까지 {diff_from_goal}kg 남았어. "
                    f"걱정되지만 부드럽게 응원해줘!"
                )
                goal_achieved = False
            else:
                context = (
                    f"체중이 유지되고 있어. "
                    f"현재 {weight}kg, 목표까지 {diff_from_goal}kg 남았어. 응원해줘!"
                )
                goal_achieved = False

            comment = await generate_comment(
                context=context,
                user=user,
                today_calories=0,
                recent_meals="없음",
                weather_info=None,
            )

            # 프로그레스 바 (초기 체중 → 목표 체중)
            total_diff  = abs(init_weight - goal_weight)
            done_diff   = abs(init_weight - weight)
            ratio       = min(done_diff / total_diff, 1.0) if total_diff > 0 else 0
            filled      = int(ratio * 10)
            bar         = "█" * filled + "░" * (10 - filled)
            percent     = int(ratio * 100)

            # 체중 변화 표시
            if diff_from_prev > 0:
                change_text = f"▲ {diff_from_prev}kg 증가"
            elif diff_from_prev < 0:
                change_text = f"▼ {abs(diff_from_prev)}kg 감소"
            else:
                change_text = "→ 변화 없음"

            embed = discord.Embed(
                title="⚖️ 체중 기록 완료",
                color=0x57F287 if goal_achieved else (0xFEE75C if diff_from_prev >= 0 else 0x57F287),
            )
            embed.add_field(
                name="📊 현재 체중",
                value=f"**{weight}kg** ({change_text})",
                inline=True,
            )
            embed.add_field(
                name="🎯 목표 체중",
                value=f"**{goal_weight}kg** (남은 몸무게: {max(diff_from_goal, 0)}kg)",
                inline=True,
            )
            embed.add_field(
                name="📈 달성률",
                value=f"`{bar}` {percent}%\n({init_weight}kg → {goal_weight}kg)",
                inline=False,
            )
            embed.add_field(
                name=f"💬 {tama_name} 한마디",
                value=f"*{comment}*",
                inline=False,
            )
            embed.set_footer(text="꾸준히 기록하면 목표에 가까워져요 🌱")

            await interaction.followup.send(embed=embed, ephemeral=True)

            # 목표 달성 시 Embed 갱신 (체중관리 전용 쓰레드 우선, fallback: 메인 쓰레드)
            if goal_achieved:
                thread_id = user.get("weight_thread_id") or user.get("thread_id")
                if thread_id:
                    guild  = interaction.guild
                    thread = guild.get_thread(int(thread_id))
                    if thread:
                        tama_updated = get_tamagotchi(user_id)
                        await create_or_update_embed(
                            thread, user, tama_updated, comment,
                            goal_achieved=True,
                        )

        except Exception as e:
            print(f"[WeightInputModal 오류] {e}")
            import traceback
            traceback.print_exc()
            await interaction.followup.send(f"❌ 오류가 발생했어: {e}", ephemeral=True)


def get_latest_weight_before(user_id: str) -> float | None:
    """직전 체중 기록 반환 (현재 입력 전 마지막 기록)"""
    history = get_weight_history(user_id, limit=2)
    return history[1]["weight"] if len(history) >= 2 else None


# ──────────────────────────────────────────────
# Cog 본체
# ──────────────────────────────────────────────

class WeightCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        print("[WeightCog] 로드 완료")


async def setup(bot: commands.Bot):
    await bot.add_cog(WeightCog(bot))
