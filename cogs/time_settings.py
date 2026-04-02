"""
cogs/time_settings.py — 시간 설정 (Select Menu 2단계)

흐름:
  1단계: 기상 시간 + 아침 알림 (시 select × 2 + 분 select × 2 + 다음 버튼)
  2단계: 점심 알림 + 저녁 알림 (시 select × 2 + 분 select × 2 + 저장 버튼)

사용처:
  - 온보딩 완료 후 자동 유도
  - MainView "⏰ 시간 설정" 버튼
"""

import discord
from discord.ext import commands
from utils.db import update_user


def _hour_options(default: int = 0) -> list[discord.SelectOption]:
    return [
        discord.SelectOption(label=f"{h}시", value=str(h), default=(h == default))
        for h in range(24)
    ]


def _minute_options(default: int = 0) -> list[discord.SelectOption]:
    return [
        discord.SelectOption(label=f"{m:02d}분", value=str(m), default=(default == m))
        for m in range(0, 60, 10)
    ]


# ══════════════════════════════════════════════════════
# 1단계: 기상 시간 + 아침 알림
# ══════════════════════════════════════════════════════
class TimeStep1View(discord.ui.View):

    def __init__(self, user_id: str, *, from_onboarding: bool = False):
        super().__init__(timeout=300)
        self.user_id         = user_id
        self.from_onboarding = from_onboarding
        self.wake_hour       = 7
        self.wake_minute     = 0
        self.breakfast_hour  = 8
        self.breakfast_minute= 0

        wake_h = discord.ui.Select(
            placeholder="🌅 기상 시간 · 시 (0~23시)",
            options=_hour_options(7),
            custom_id="wake_hour",
            row=0,
        )
        wake_h.callback = self._on_wake_hour
        self.add_item(wake_h)

        wake_m = discord.ui.Select(
            placeholder="🌅 기상 시간 · 분 (10분 단위)",
            options=_minute_options(0),
            custom_id="wake_minute",
            row=1,
        )
        wake_m.callback = self._on_wake_minute
        self.add_item(wake_m)

        bf_h = discord.ui.Select(
            placeholder="🍳 아침 알림 · 시 (0~23시)",
            options=_hour_options(8),
            custom_id="breakfast_hour",
            row=2,
        )
        bf_h.callback = self._on_breakfast_hour
        self.add_item(bf_h)

        bf_m = discord.ui.Select(
            placeholder="🍳 아침 알림 · 분 (10분 단위)",
            options=_minute_options(0),
            custom_id="breakfast_minute",
            row=3,
        )
        bf_m.callback = self._on_breakfast_minute
        self.add_item(bf_m)

    async def _on_wake_hour(self, interaction: discord.Interaction):
        self.wake_hour = int(interaction.data["values"][0])
        await interaction.response.defer()

    async def _on_wake_minute(self, interaction: discord.Interaction):
        self.wake_minute = int(interaction.data["values"][0])
        await interaction.response.defer()

    async def _on_breakfast_hour(self, interaction: discord.Interaction):
        self.breakfast_hour = int(interaction.data["values"][0])
        await interaction.response.defer()

    async def _on_breakfast_minute(self, interaction: discord.Interaction):
        self.breakfast_minute = int(interaction.data["values"][0])
        await interaction.response.defer()

    @discord.ui.button(label="다음 →", style=discord.ButtonStyle.primary, row=4)
    async def next_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("❌ 본인만 설정할 수 있어!", ephemeral=True)
            return

        wake      = f"{self.wake_hour:02d}:{self.wake_minute:02d}"
        breakfast = f"{self.breakfast_hour:02d}:{self.breakfast_minute:02d}"

        await interaction.response.edit_message(
            content=(
                f"✅ 기상: **{wake}** / 아침: **{breakfast}** 저장됨\n\n"
                "⏰ **시간 설정** — 2단계\n\n"
                "🌞 **점심 알림** — 시 / 분\n"
                "🌙 **저녁 알림** — 시 / 분"
            ),
            view=TimeStep2View(
                user_id       = self.user_id,
                wake_time     = wake,
                breakfast_time= breakfast,
                from_onboarding=self.from_onboarding,
            ),
        )


# ══════════════════════════════════════════════════════
# 2단계: 점심 알림 + 저녁 알림
# ══════════════════════════════════════════════════════
class TimeStep2View(discord.ui.View):

    def __init__(self, user_id: str, wake_time: str, breakfast_time: str, *, from_onboarding: bool = False):
        super().__init__(timeout=300)
        self.user_id        = user_id
        self.wake_time      = wake_time
        self.breakfast_time = breakfast_time
        self.from_onboarding= from_onboarding
        self.lunch_hour     = 12
        self.lunch_minute   = 0
        self.dinner_hour    = 18
        self.dinner_minute  = 0

        lunch_h = discord.ui.Select(
            placeholder="🌞 점심 알림 · 시 (0~23시)",
            options=_hour_options(12),
            custom_id="lunch_hour",
            row=0,
        )
        lunch_h.callback = self._on_lunch_hour
        self.add_item(lunch_h)

        lunch_m = discord.ui.Select(
            placeholder="🌞 점심 알림 · 분 (10분 단위)",
            options=_minute_options(0),
            custom_id="lunch_minute",
            row=1,
        )
        lunch_m.callback = self._on_lunch_minute
        self.add_item(lunch_m)

        dinner_h = discord.ui.Select(
            placeholder="🌙 저녁 알림 · 시 (0~23시)",
            options=_hour_options(18),
            custom_id="dinner_hour",
            row=2,
        )
        dinner_h.callback = self._on_dinner_hour
        self.add_item(dinner_h)

        dinner_m = discord.ui.Select(
            placeholder="🌙 저녁 알림 · 분 (10분 단위)",
            options=_minute_options(0),
            custom_id="dinner_minute",
            row=3,
        )
        dinner_m.callback = self._on_dinner_minute
        self.add_item(dinner_m)

    async def _on_lunch_hour(self, interaction: discord.Interaction):
        self.lunch_hour = int(interaction.data["values"][0])
        await interaction.response.defer()

    async def _on_lunch_minute(self, interaction: discord.Interaction):
        self.lunch_minute = int(interaction.data["values"][0])
        await interaction.response.defer()

    async def _on_dinner_hour(self, interaction: discord.Interaction):
        self.dinner_hour = int(interaction.data["values"][0])
        await interaction.response.defer()

    async def _on_dinner_minute(self, interaction: discord.Interaction):
        self.dinner_minute = int(interaction.data["values"][0])
        await interaction.response.defer()

    @discord.ui.button(label="✅ 저장", style=discord.ButtonStyle.success, row=4)
    async def save_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("❌ 본인만 설정할 수 있어!", ephemeral=True)
            return

        lunch  = f"{self.lunch_hour:02d}:{self.lunch_minute:02d}"
        dinner = f"{self.dinner_hour:02d}:{self.dinner_minute:02d}"

        update_user(self.user_id,
            wake_time      = self.wake_time,
            breakfast_time = self.breakfast_time,
            lunch_time     = lunch,
            dinner_time    = dinner,
        )

        # 날씨 스케줄러 재등록
        weather_cog = interaction.client.cogs.get("WeatherCog")
        if weather_cog:
            weather_cog.register_user_job(self.wake_time)
        # 식사 알림 Job 재등록
        scheduler_cog = interaction.client.cogs.get("SchedulerCog")
        if scheduler_cog:
            scheduler_cog.register_meal_jobs(self.user_id)

        tail = "\n\n이제 다마고치와 함께 건강한 식습관을 만들어봐! 🐣" if self.from_onboarding else ""

        await interaction.response.edit_message(
            content=(
                f"⏰ 시간 설정 완료!\n\n"
                f"🌅 기상: **{self.wake_time}**\n"
                f"☀️ 아침: **{self.breakfast_time}**\n"
                f"🌞 점심: **{lunch}**\n"
                f"🌙 저녁: **{dinner}**"
                f"{tail}"
            ),
            view=None,
        )


# ══════════════════════════════════════════════════════
# Cog
# ══════════════════════════════════════════════════════
class TimeSettingCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot


async def setup(bot: commands.Bot):
    await bot.add_cog(TimeSettingCog(bot))
