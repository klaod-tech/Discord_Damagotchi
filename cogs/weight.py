"""
cogs/weight.py — 체중 기록 기능
────────────────────────────────────────────────────────────────
흐름:
  1. [⚖️ 체중 기록] 버튼 클릭 또는 ⚙️ 내 정보 설정에서 현재 체중 입력
  2. 체중 입력 Modal (현재 체중 kg 입력)
  3. DB weight_log 저장
  4. 목표 체중과 비교 → 다마고치 반응
  5. (추후) ML 2순위 강화학습 Y값으로 활용
────────────────────────────────────────────────────────────────
"""

import discord
from discord.ext import commands

from utils.weight_ui import (  # noqa: F401  (re-export for backward compat)
    WeightInputModal,
    save_weight_log,
    get_weight_history,
    get_latest_weight,
    get_latest_weight_before,
)


# ──────────────────────────────────────────────
# Cog 본체
# ──────────────────────────────────────────────

class WeightCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        print("[WeightCog] 로드 완료")


async def setup(bot: commands.Bot):
    await bot.add_cog(WeightCog(bot))
