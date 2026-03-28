"""
cogs/settings.py — 설정 변경
동작: ⚙️ 설정 변경 버튼 클릭 → 현재 값이 미리 채워진 Modal 오픈
변경 가능 항목:
  - 다마고치 이름 → DB 업데이트 + 쓰레드 이름 변경
  - 거주 도시 → DB 업데이트
  - 식사 알림 시간 (아침/점심/저녁) → DB 업데이트
  - 목표 체중 → DB 업데이트 + GPT 권장 칼로리 재계산
"""
import discord
from discord.ext import commands
from utils.db import get_user, update_user, update_tamagotchi
from utils.gpt import calculate_daily_calories


class SettingsModal(discord.ui.Modal, title="⚙️ 설정 변경"):

    def __init__(self, user: dict, **kwargs):
        super().__init__(**kwargs)
        self._user = user

        # 현재 값을 default로 미리 채워넣기
        self.tama_name = discord.ui.TextInput(
            label="다마고치 이름",
            default=user.get("tamagotchi_name", ""),
            max_length=20,
        )
        self.city = discord.ui.TextInput(
            label="거주 도시",
            default=user.get("city", ""),
            max_length=20,
        )
        self.meal_times = discord.ui.TextInput(
            label="식사 알림 시간 (아침,점심,저녁 HH:MM)",
            placeholder="예: 08:00,12:30,18:30",
            default=f"{user.get('breakfast_time', '08:00')},{user.get('lunch_time', '12:00')},{user.get('dinner_time', '18:00')}",
            max_length=20,
        )
        self.goal_weight = discord.ui.TextInput(
            label="목표 체중 (kg)",
            default=str(user.get("goal_weight", "")),
            max_length=6,
        )

        self.add_item(self.tama_name)
        self.add_item(self.city)
        self.add_item(self.meal_times)
        self.add_item(self.goal_weight)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            user_id = str(interaction.user.id)
            old = self._user
            updates = {}
            messages = []

            # 이름 변경
            new_name = self.tama_name.value.strip()
            if new_name != old.get("tamagotchi_name", ""):
                updates["tamagotchi_name"] = new_name
                messages.append(f"다마고치 이름: **{new_name}**")

                # 쓰레드 이름 변경
                thread_id = old.get("thread_id")
                if thread_id:
                    guild = interaction.guild
                    thread = guild.get_thread(int(thread_id))
                    if thread:
                        await thread.edit(
                            name=f"{interaction.user.display_name}의 {new_name}"
                        )

            # 도시 변경
            new_city = self.city.value.strip()
            if new_city != old.get("city", ""):
                updates["city"] = new_city
                messages.append(f"거주 도시: **{new_city}**")

            # 식사 시간 변경
            times = [t.strip() for t in self.meal_times.value.split(",")]
            new_breakfast = times[0] if len(times) > 0 else old.get("breakfast_time", "08:00")
            new_lunch     = times[1] if len(times) > 1 else old.get("lunch_time", "12:00")
            new_dinner    = times[2] if len(times) > 2 else old.get("dinner_time", "18:00")

            if (new_breakfast != old.get("breakfast_time") or
                new_lunch != old.get("lunch_time") or
                new_dinner != old.get("dinner_time")):
                updates["breakfast_time"] = new_breakfast
                updates["lunch_time"]     = new_lunch
                updates["dinner_time"]    = new_dinner
                messages.append(f"식사 알림: **{new_breakfast} / {new_lunch} / {new_dinner}**")

            # 목표 체중 변경
            new_goal = float(self.goal_weight.value.strip())
            if new_goal != old.get("goal_weight"):
                updates["goal_weight"] = new_goal
                messages.append(f"목표 체중: **{new_goal}kg**")

                # 권장 칼로리 재계산
                new_cal = await calculate_daily_calories(
                    gender="남",         # 재계산 시 기존 값 활용 (추후 DB에 gender 저장 시 개선)
                    age=25,
                    height=170,
                    weight=old.get("init_weight", 70),
                    activity="보통",
                    goal="체중 감량" if new_goal < old.get("init_weight", 70) else "체중 유지",
                )
                updates["daily_cal_target"] = new_cal
                messages.append(f"권장 칼로리: **{new_cal} kcal/일**")

            # 변경 사항 없으면 안내
            if not updates:
                await interaction.followup.send(
                    "변경된 항목이 없어요!", ephemeral=True
                )
                return

            # DB 업데이트
            update_user(user_id, **updates)

            await interaction.followup.send(
                "✅ 설정이 저장됐어요!\n" + "\n".join(f"• {m}" for m in messages),
                ephemeral=True,
            )

        except Exception as e:
            print(f"[SettingsModal 오류] {e}")
            import traceback
            traceback.print_exc()
            await interaction.followup.send(
                f"❌ 오류가 발생했어: {e}", ephemeral=True
            )


class SettingsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot


async def setup(bot: commands.Bot):
    await bot.add_cog(SettingsCog(bot))
