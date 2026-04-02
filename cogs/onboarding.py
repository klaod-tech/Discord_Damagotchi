"""
cogs/onboarding.py — 온보딩 + 전용 쓰레드 생성
"""
import os
import discord
from discord.ext import commands
from discord import app_commands
from utils.db import (
    create_user,
    create_tamagotchi,
    get_user,
    get_tamagotchi,
    set_thread_id,
)
from utils.gpt import calculate_daily_calories, generate_comment
from utils.embed import create_or_update_embed

TAMAGOTCHI_CHANNEL_ID = int(os.getenv("TAMAGOTCHI_CHANNEL_ID", "0"))

# ══════════════════════════════════════════════════════
# Modal: 온보딩 (1단계 통합)
# ══════════════════════════════════════════════════════
class OnboardingModal(discord.ui.Modal, title="다마고치 시작하기"):
    tama_name = discord.ui.TextInput(
        label="다마고치 이름",
        placeholder="예: 뚜비",
        max_length=20,
    )
    city = discord.ui.TextInput(
        label="거주 도시",
        placeholder="예: 서울, 부산, 아산",
        max_length=20,
    )
    weight_info = discord.ui.TextInput(
        label="현재체중/목표체중 (kg/kg)",
        placeholder="예: 76/70",
        max_length=10,
    )
    body_info = discord.ui.TextInput(
        label="성별/나이/키 (남or여/나이/cm)",
        placeholder="예: 남/25/175",
        max_length=15,
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            # 체중 파싱
            weights     = self.weight_info.value.strip().split("/")
            init_weight = float(weights[0].strip())
            goal_weight = float(weights[1].strip())

            # 신체정보 파싱
            body   = self.body_info.value.strip().split("/")
            gender = body[0].strip()
            age    = int(body[1].strip())
            height = float(body[2].strip())

            # 시간 기본값 (시간 설정은 온보딩 완료 후 TimeStep1View에서 진행)
            wake_time = "07:00"
            breakfast = "08:00"
            lunch     = "12:00"
            dinner    = "18:00"

            # GPT 권장 칼로리 계산 (목표 체중 기반 동적 산출)
            daily_cal = await calculate_daily_calories(
                gender=gender,
                age=age,
                height=height,
                weight=init_weight,
                goal_weight=goal_weight,
                activity="보통",
            )

            user_id   = str(interaction.user.id)
            user_data = {
                "tamagotchi_name": self.tama_name.value.strip(),
                "city":            self.city.value.strip(),
                "wake_time":       wake_time,
                "init_weight":     init_weight,
                "goal_weight":     goal_weight,
                "daily_cal_target": daily_cal,
                "breakfast_time":  breakfast,
                "lunch_time":      lunch,
                "dinner_time":     dinner,
            }

            create_user(user_id, user_data)
            create_tamagotchi(user_id)

            # 날씨 스케줄러에 wake_time 자동 등록
            weather_cog = interaction.client.cogs.get("WeatherCog")
            if weather_cog:
                weather_cog.register_user_job(wake_time)
                print(f"[온보딩] {user_id} 날씨 스케줄러 등록 — wake_time: {wake_time}")

            # 전용 쓰레드 생성
            channel = interaction.guild.get_channel(TAMAGOTCHI_CHANNEL_ID)
            if channel is None:
                channel = interaction.channel

            thread = await channel.create_thread(
                name=f"{interaction.user.display_name}의 {self.tama_name.value.strip()}",
                auto_archive_duration=10080,
                invitable=False,
            )
            set_thread_id(user_id, str(thread.id))

            await thread.send(
                f"안녕, {interaction.user.mention}! 🥚\n"
                f"나는 **{self.tama_name.value.strip()}**야. 잘 부탁해!\n"
                f"권장 칼로리: **{daily_cal} kcal/일**\n"
                f"날씨 알림: 매일 **{wake_time}**에 보내줄게!"
            )

            # 메인 Embed 생성
            user    = get_user(user_id)
            tama    = get_tamagotchi(user_id)
            comment = await generate_comment(
                context="처음 만났을 때 인사",
                user=user,
                today_calories=0,
                recent_meals="없음",
                weather_info=None,
            )
            await create_or_update_embed(thread, user, tama, comment)

            await interaction.followup.send(
                f"✅ 설정 완료! {thread.mention} 에서 확인해봐!\n"
                f"이제 기상 시간과 식사 알림 시간을 설정해줘 ⏰",
                ephemeral=True,
            )

            from cogs.time_settings import TimeStep1View
            await interaction.followup.send(
                "⬇️ 아래에서 시간을 설정해줘!",
                view=TimeStep1View(user_id=user_id, from_onboarding=True),
                ephemeral=True,
            )

        except Exception as e:
            print(f"[OnboardingModal 오류] {e}")
            import traceback
            traceback.print_exc()
            await interaction.followup.send(
                f"❌ 오류가 발생했어: {e}", ephemeral=True
            )


# ══════════════════════════════════════════════════════
# 시작하기 버튼 View
# ══════════════════════════════════════════════════════
class StartView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="🥚 시작하기",
        style=discord.ButtonStyle.success,
        custom_id="btn_start",
    )
    async def start_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        user_id  = str(interaction.user.id)
        existing = get_user(user_id)
        if existing and existing.get("thread_id"):
            guild  = interaction.guild
            thread = guild.get_thread(int(existing["thread_id"]))
            if thread:
                await interaction.response.send_message(
                    f"이미 등록되어 있어! {thread.mention} 에서 확인해봐 😊",
                    ephemeral=True,
                )
                return
        await interaction.response.send_modal(OnboardingModal())


# ══════════════════════════════════════════════════════
# Cog
# ══════════════════════════════════════════════════════
class OnboardingCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="start", description="다마고치 봇 시작 메시지를 채널에 고정합니다.")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def start_cmd(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🥚 나만의 다마고치를 키워봐요!",
            description=(
                "아래 버튼을 눌러서 다마고치를 만들어보세요.\n\n"
                "• 음식을 입력하면 다마고치에게 밥을 줄 수 있어요 🍚\n"
                "• 칼로리와 날씨 정보가 캐릭터 표정으로 전달돼요 🌤️\n"
                "• 건강하게 먹으면 다마고치가 행복해져요 😄"
            ),
            color=0x57F287,
        )
        await interaction.response.send_message(embed=embed, view=StartView())


async def setup(bot: commands.Bot):
    await bot.add_cog(OnboardingCog(bot))
