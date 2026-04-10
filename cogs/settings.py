"""
cogs/settings.py — 설정 변경
⚙️ 설정 버튼 클릭 → SettingsSubView (하위 메뉴)
  Row 0: [👤 내 정보]   → InfoModal (이름, 목표체중)
          [📍 위치 설정] → CityModal (거주 도시)
          [⏰ 시간 설정] → TimeStep1View
  Row 1: [📧 이메일 설정] → EmailSetupModal (네이버 계정 연동)
"""
import discord
from discord.ext import commands
from utils.db import get_user, update_user
from utils.gpt import calculate_daily_calories


# ══════════════════════════════════════════════════════
# 내 정보 Modal — 이름 + 목표 체중
# ══════════════════════════════════════════════════════
class InfoModal(discord.ui.Modal, title="👤 내 정보 변경"):

    def __init__(self, user: dict, **kwargs):
        super().__init__(**kwargs)
        self._user = user

        self.tama_name = discord.ui.TextInput(
            label="다마고치 이름",
            default=user.get("tamagotchi_name", ""),
            max_length=20,
        )
        self.goal_weight = discord.ui.TextInput(
            label="목표 체중 (kg)",
            default=str(user.get("goal_weight", "")),
            max_length=6,
        )

        self.add_item(self.tama_name)
        self.add_item(self.goal_weight)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            user_id  = str(interaction.user.id)
            old      = self._user
            updates  = {}
            messages = []

            # 이름 변경
            new_name = self.tama_name.value.strip()
            if new_name != old.get("tamagotchi_name", ""):
                updates["tamagotchi_name"] = new_name
                messages.append(f"다마고치 이름: **{new_name}**")
                thread_id = old.get("thread_id")
                if thread_id:
                    thread = interaction.guild.get_thread(int(thread_id))
                    if thread:
                        await thread.edit(
                            name=f"{interaction.user.display_name}의 {new_name}"
                        )

            # 목표 체중 변경
            new_goal = float(self.goal_weight.value.strip())
            if new_goal != old.get("goal_weight"):
                updates["goal_weight"] = new_goal
                messages.append(f"목표 체중: **{new_goal}kg**")
                new_cal = await calculate_daily_calories(
                    gender=old.get("gender", "남"),
                    age=old.get("age", 25),
                    height=old.get("height", 170),
                    weight=old.get("init_weight", 70),
                    goal_weight=new_goal,
                )
                updates["daily_cal_target"] = new_cal
                messages.append(f"권장 칼로리: **{new_cal} kcal/일**")

            if not updates:
                await interaction.followup.send("변경된 항목이 없어요!", ephemeral=True)
                return

            update_user(user_id, **updates)
            await interaction.followup.send(
                "✅ 설정이 저장됐어요!\n" + "\n".join(f"• {m}" for m in messages),
                ephemeral=True,
            )

        except Exception as e:
            print(f"[InfoModal 오류] {e}")
            import traceback
            traceback.print_exc()
            await interaction.followup.send(f"❌ 오류가 발생했어: {e}", ephemeral=True)


# ══════════════════════════════════════════════════════
# 위치 설정 Modal — 거주 도시
# ══════════════════════════════════════════════════════
class CityModal(discord.ui.Modal, title="📍 위치 설정"):

    def __init__(self, user: dict, **kwargs):
        super().__init__(**kwargs)
        self._user = user

        self.city = discord.ui.TextInput(
            label="거주 도시",
            placeholder="예: 서울, 부산, 대구, 인천",
            default=user.get("city", ""),
            max_length=20,
        )
        self.add_item(self.city)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            user_id  = str(interaction.user.id)
            new_city = self.city.value.strip()

            if new_city == self._user.get("city", ""):
                await interaction.followup.send("변경된 항목이 없어요!", ephemeral=True)
                return

            update_user(user_id, city=new_city)
            await interaction.followup.send(
                f"✅ 거주 도시가 **{new_city}**(으)로 변경됐어요!\n"
                f"다음 기상 시간부터 새 도시의 날씨로 갱신돼요 🌤️",
                ephemeral=True,
            )

        except Exception as e:
            print(f"[CityModal 오류] {e}")
            import traceback
            traceback.print_exc()
            await interaction.followup.send(f"❌ 오류가 발생했어: {e}", ephemeral=True)


# ══════════════════════════════════════════════════════
# 설정 하위 메뉴 View
# ══════════════════════════════════════════════════════
class SettingsSubView(discord.ui.View):
    def __init__(self, user: dict):
        super().__init__(timeout=60)
        self._user = user

    @discord.ui.button(label="👤 내 정보", style=discord.ButtonStyle.primary, row=0)
    async def info_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(InfoModal(user=self._user))

    @discord.ui.button(label="📍 위치 설정", style=discord.ButtonStyle.secondary, row=0)
    async def city_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(CityModal(user=self._user))

    @discord.ui.button(label="⏰ 시간 설정", style=discord.ButtonStyle.secondary, row=0)
    async def time_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        from cogs.time_settings import TimeStep1View
        await interaction.response.send_message(
            "⏰ **시간 설정** — 1단계\n\n"
            "🌅 **기상 시간** — 시 / 분\n"
            "🍳 **아침 알림** — 시 / 분",
            view=TimeStep1View(user_id=str(interaction.user.id)),
            ephemeral=True,
        )

    @discord.ui.button(label="📧 이메일 설정", style=discord.ButtonStyle.secondary, row=1)
    async def email_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        from cogs.email_monitor import EmailSetupModal
        await interaction.response.send_modal(EmailSetupModal())


# ══════════════════════════════════════════════════════
# 하위 호환 — 기존 코드에서 SettingsModal을 직접 import하는 경우 대비
# ══════════════════════════════════════════════════════
SettingsModal = InfoModal


class SettingsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot


async def setup(bot: commands.Bot):
    await bot.add_cog(SettingsCog(bot))
