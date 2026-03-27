"""
cogs/onboarding.py — 온보딩 + 전용 쓰레드 생성

흐름:
  1. /start 명령어 → 채널에 고정 메시지 전송
  2. [🥚 시작하기] 버튼 클릭 → Step1Modal (이름, 도시, 기상시간, 체중, 목표체중)
  3. Step1 제출 → Step2Modal (성별, 나이, 키, 활동량, 목표, 식사 알림 시간)
  4. Step2 제출 → GPT 칼로리 계산 → DB 저장 → 전용 쓰레드 생성 → 메인 Embed 전송
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
# Modal: Step 1 — 기본 정보
# ══════════════════════════════════════════════════════
class Step1Modal(discord.ui.Modal, title="다마고치 시작하기 (1/2)"):
    tama_name = discord.ui.TextInput(
        label="다마고치 이름",
        placeholder="예: 뚜비",
        max_length=20,
    )
    city = discord.ui.TextInput(
        label="거주 도시",
        placeholder="예: 서울, 부산, 대구",
        max_length=20,
    )
    wake_time = discord.ui.TextInput(
        label="기상 시간 (HH:MM)",
        placeholder="예: 07:30",
        max_length=5,
    )
    init_weight = discord.ui.TextInput(
        label="현재 체중 (kg)",
        placeholder="예: 65.5",
        max_length=6,
    )
    goal_weight = discord.ui.TextInput(
        label="목표 체중 (kg)",
        placeholder="예: 60.0",
        max_length=6,
    )

    async def on_submit(self, interaction: discord.Interaction):
        # Step2 Modal로 이어서 진행
        step2 = Step2Modal(step1_data={
            "tamagotchi_name": self.tama_name.value.strip(),
            "city": self.city.value.strip(),
            "wake_time": self.wake_time.value.strip(),
            "init_weight": float(self.init_weight.value.strip()),
            "goal_weight": float(self.goal_weight.value.strip()),
        })
        await interaction.response.send_modal(step2)


# ══════════════════════════════════════════════════════
# Modal: Step 2 — 신체 정보 + 알림 시간
# ══════════════════════════════════════════════════════
class Step2Modal(discord.ui.Modal, title="다마고치 시작하기 (2/2)"):
    gender = discord.ui.TextInput(
        label="성별 (남 / 여)",
        placeholder="남 또는 여",
        max_length=1,
    )
    age = discord.ui.TextInput(
        label="나이",
        placeholder="예: 25",
        max_length=3,
    )
    height = discord.ui.TextInput(
        label="키 (cm)",
        placeholder="예: 170",
        max_length=5,
    )
    activity = discord.ui.TextInput(
        label="활동량 (낮음 / 보통 / 높음)",
        placeholder="낮음, 보통, 높음 중 하나",
        max_length=5,
    )
    meal_times = discord.ui.TextInput(
        label="식사 알림 시간 (아침,점심,저녁 HH:MM)",
        placeholder="예: 08:00,12:30,18:30",
        max_length=20,
    )

    def __init__(self, step1_data: dict):
        super().__init__()
        self._step1 = step1_data

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)

        try:
            times = [t.strip() for t in self.meal_times.value.split(",")]
            breakfast = times[0] if len(times) > 0 else "08:00"
            lunch = times[1] if len(times) > 1 else "12:00"
            dinner = times[2] if len(times) > 2 else "18:00"

            daily_cal = await calculate_daily_calories(
                gender=self.gender.value.strip(),
                age=int(self.age.value.strip()),
                height=float(self.height.value.strip()),
                weight=self._step1["init_weight"],
                activity=self.activity.value.strip(),
                goal="체중 감량" if self._step1["goal_weight"] < self._step1["init_weight"] else "체중 유지",
            )

            user_id = str(interaction.user.id)
            user_data = {
                **self._step1,
                "daily_cal_target": daily_cal,
                "breakfast_time": breakfast,
                "lunch_time": lunch,
                "dinner_time": dinner,
            }

            create_user(user_id, user_data)
            create_tamagotchi(user_id)

            # 전용 쓰레드 생성
            channel = interaction.guild.get_channel(TAMAGOTCHI_CHANNEL_ID)
            if channel is None:
                channel = interaction.channel

            thread = await channel.create_thread(
                name=f"{interaction.user.display_name}의 {self._step1['tamagotchi_name']}",
                type=discord.ChannelType.public_thread,
                auto_archive_duration=10080,  # 7일
            )
            set_thread_id(user_id, str(thread.id))

            # 쓰레드에 유저 멘션
            await thread.send(
                f"안녕, {interaction.user.mention}! 🥚\n"
                f"나는 **{self._step1['tamagotchi_name']}**야. 잘 부탁해!\n"
                f"권장 칼로리: **{daily_cal} kcal/일**"
            )

            # 메인 Embed 생성
            user = get_user(user_id)
            tama = get_tamagotchi(user_id)
            comment = await generate_comment(
                context="처음 만났을 때 인사",
                user=user,
                today_calories=0,
                recent_meals="없음",
                weather_info=None,
            )
            await create_or_update_embed(thread, user, tama, comment)

            await interaction.followup.send(
                f"✅ 설정 완료! {thread.mention} 에서 확인해봐!", ephemeral=True
            )

        except Exception as e:
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
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        user_id = str(interaction.user.id)
        existing = get_user(user_id)
        if existing and existing.get("thread_id"):
            guild = interaction.guild
            thread = guild.get_thread(int(existing["thread_id"]))
            if thread:
                await interaction.response.send_message(
                    f"이미 등록되어 있어! {thread.mention} 에서 확인해봐 😊",
                    ephemeral=True,
                )
                return
        await interaction.response.send_modal(Step1Modal())


# ══════════════════════════════════════════════════════
# Cog
# ══════════════════════════════════════════════════════
class OnboardingCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        bot.add_view(StartView())

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
