"""
cogs/onboarding.py — 온보딩 + 유저 전용 채널 생성
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
    set_mail_thread_id,
    set_meal_thread_id,
    set_weather_thread_id,
    set_weight_thread_id,
    set_diary_thread_id,
    set_schedule_thread_id,
    set_user_channel_id,
    reset_user_threads,
    update_tamagotchi,
)
from utils.gpt import calculate_daily_calories, generate_comment
from utils.embed import create_or_update_embed

TAMAGOTCHI_CHANNEL_ID = int(os.getenv("TAMAGOTCHI_CHANNEL_ID", "0"))
BOT_ROLE_ID = int(os.getenv("BOT_ROLE_ID", "0"))


# ══════════════════════════════════════════════════════
# Modal: 온보딩 (1단계 통합)
# ══════════════════════════════════════════════════════
class OnboardingModal(discord.ui.Modal, title="먹구름 시작하기"):
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
        print(f"[MODAL] OnboardingModal 제출 — {interaction.user}")
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            # 체중 파싱
            weights = self.weight_info.value.strip().split("/")
            if len(weights) < 2:
                await interaction.followup.send(
                    "❌ 체중 형식이 올바르지 않아!\n"
                    "예시: `76/70` (현재체중/목표체중) 형태로 입력해줘.",
                    ephemeral=True,
                )
                return
            init_weight = float(weights[0].strip())
            goal_weight = float(weights[1].strip())

            # 신체정보 파싱
            body = self.body_info.value.strip().split("/")
            if len(body) < 3:
                await interaction.followup.send(
                    "❌ 성별/나이/키 형식이 올바르지 않아!\n"
                    "예시: `남/25/175` 또는 `여/23/162` 형태로 입력해줘.",
                    ephemeral=True,
                )
                return
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
                "gender":          gender,
                "age":             age,
                "height":          height,
            }

            create_user(user_id, user_data)
            create_tamagotchi(user_id)

            # 날씨 스케줄러에 wake_time 자동 등록
            weather_cog = interaction.client.cogs.get("WeatherCog")
            if weather_cog:
                weather_cog.register_user_job(wake_time)
                print(f"[온보딩] {user_id} 날씨 스케줄러 등록 — wake_time: {wake_time}")
            # 식사 알림 Job 등록 (기본 시간 기준, 이후 시간 설정에서 재등록)
            scheduler_cog = interaction.client.cogs.get("SchedulerCog")
            if scheduler_cog:
                scheduler_cog.register_meal_jobs(user_id)

            # ── 유저 전용 비공개 채널 생성 ──────────────────────────
            guild = interaction.guild

            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                interaction.user: discord.PermissionOverwrite(
                    view_channel=True, send_messages=True, read_message_history=True
                ),
            }
            if BOT_ROLE_ID:
                bot_role = guild.get_role(BOT_ROLE_ID)
                if bot_role:
                    overwrites[bot_role] = discord.PermissionOverwrite(
                        view_channel=True, send_messages=True, read_message_history=True
                    )

            user_channel = await guild.create_text_channel(
                name=f"{interaction.user.display_name}의 먹구름",
                overwrites=overwrites,
            )
            set_user_channel_id(user_id, str(user_channel.id))
            # ────────────────────────────────────────────────────────

            # 채널 내 공개 스레드 생성
            thread = await user_channel.create_thread(
                name=f"{interaction.user.display_name}의 {self.tama_name.value.strip()}",
                auto_archive_duration=10080,
                type=discord.ChannelType.public_thread,
            )
            set_thread_id(user_id, str(thread.id))

            mail_thread = await user_channel.create_thread(
                name=f"📧 {interaction.user.display_name}의 메일함",
                auto_archive_duration=10080,
                type=discord.ChannelType.public_thread,
            )
            set_mail_thread_id(user_id, str(mail_thread.id))
            await mail_thread.send(
                f"📬 안녕, {interaction.user.mention}!\n"
                f"여기는 **메일 알림 전용** 스레드야.\n"
                f"등록된 발신자에게 메일이 오면 여기에 요약해서 알려줄게!\n\n"
                f"**시작 방법:**\n"
                f"1. `/이메일설정` — 네이버 계정 연동\n"
                f"2. `/발신자추가` — 알림 받을 발신자 등록"
            )

            meal_thread = await user_channel.create_thread(
                name=f"🍽️ {interaction.user.display_name}의 식사 기록",
                auto_archive_duration=10080,
                type=discord.ChannelType.public_thread,
            )
            set_meal_thread_id(user_id, str(meal_thread.id))
            await meal_thread.send(
                f"🍽️ 안녕, {interaction.user.mention}!\n"
                f"여기는 **식사 기록 전용** 스레드야.\n"
                f"사진을 올리거나 먹은 음식을 말해주면 칼로리를 분석해줄게!"
            )

            weather_thread = await user_channel.create_thread(
                name=f"🌤️ {interaction.user.display_name}의 날씨",
                auto_archive_duration=10080,
                type=discord.ChannelType.public_thread,
            )
            set_weather_thread_id(user_id, str(weather_thread.id))
            await weather_thread.send(
                f"🌤️ 안녕, {interaction.user.mention}!\n"
                f"여기는 **날씨 알림 전용** 스레드야.\n"
                f"매일 기상 시간({wake_time})에 날씨와 미세먼지 정보를 알려줄게!"
            )

            weight_thread = await user_channel.create_thread(
                name=f"⚖️ {interaction.user.display_name}의 체중관리",
                auto_archive_duration=10080,
                type=discord.ChannelType.public_thread,
            )
            set_weight_thread_id(user_id, str(weight_thread.id))
            await weight_thread.send(
                f"⚖️ 안녕, {interaction.user.mention}!\n"
                f"여기는 **체중관리 전용** 스레드야.\n"
                f"체중을 기록하면 목표 달성률과 추이를 여기에 보여줄게!\n"
                f"목표 체중: **{goal_weight}kg**"
            )

            diary_thread = await user_channel.create_thread(
                name=f"📔 {interaction.user.display_name}의 일기장",
                auto_archive_duration=10080,
                type=discord.ChannelType.public_thread,
            )
            set_diary_thread_id(user_id, str(diary_thread.id))
            await diary_thread.send(
                f"📔 안녕, {interaction.user.mention}!\n"
                f"여기는 **일기 전용** 스레드야.\n"
                f"오늘 있었던 일이나 감정을 자유롭게 적어줘. 감정을 분석해줄게!"
            )

            schedule_thread = await user_channel.create_thread(
                name=f"📅 {interaction.user.display_name}의 일정표",
                auto_archive_duration=10080,
                type=discord.ChannelType.public_thread,
            )
            set_schedule_thread_id(user_id, str(schedule_thread.id))
            await schedule_thread.send(
                f"📅 안녕, {interaction.user.mention}!\n"
                f"여기는 **일정 알림 전용** 스레드야.\n"
                f"`/일정추가` 로 일정을 등록하면 시간에 맞춰 알려줄게!"
            )

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
                f"✅ 설정 완료! {user_channel.mention} 에서 확인해봐!\n"
                f"이제 기상 시간과 식사 알림 시간을 설정해줘 ⏰",
                ephemeral=True,
            )

            from cogs.time_settings import TimeStep1View
            await interaction.followup.send(
                "⏰ **시간 설정** — 1단계\n\n"
                "🌅 **기상 시간** — 시 / 분\n"
                "🍳 **아침 알림** — 시 / 분",
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
# 리셋 확인 View
# ══════════════════════════════════════════════════════
class ResetConfirmView(discord.ui.View):
    def __init__(self, user_id: str):
        super().__init__(timeout=60)
        self.user_id = user_id

    @discord.ui.button(label="✅ 확인", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("❌ 본인만 리셋할 수 있어!", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True, thinking=True)

        user = get_user(self.user_id)
        if not user:
            await interaction.edit_original_response(
                content="❌ 등록된 유저 정보가 없어!",
            )
            return

        # 유저 전용 채널 삭제 (내부 스레드 전부 자동 삭제)
        channel_id = user.get("user_channel_id")
        if channel_id:
            try:
                ch = interaction.guild.get_channel(int(channel_id))
                if ch is None:
                    ch = await interaction.guild.fetch_channel(int(channel_id))
                if ch:
                    await ch.delete()
            except Exception:
                pass

        # DB 초기화
        reset_user_threads(self.user_id)
        update_tamagotchi(self.user_id, {"embed_message_id": None})

        await interaction.edit_original_response(
            content="✅ 리셋 완료!\n채널이 삭제됐어. 시작하기 버튼을 눌러 다시 시작해줘 🥚",
            view=None,
        )

    @discord.ui.button(label="❌ 취소", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("❌", ephemeral=True)
            return
        for child in self.children:
            child.disabled = True
        await interaction.message.edit(view=self)
        await interaction.response.send_message("취소했어!", ephemeral=True)


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
        print(f"[BTN] 시작하기 — {interaction.user}")
        existing = get_user(user_id)
        if existing and existing.get("user_channel_id"):
            guild = interaction.guild
            ch = guild.get_channel(int(existing["user_channel_id"]))
            if ch:
                await interaction.response.send_message(
                    f"이미 등록되어 있어! {ch.mention} 에서 확인해봐 😊",
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

    @app_commands.command(name="리셋", description="내 채널을 전부 삭제하고 처음부터 다시 시작해요.")
    async def reset_cmd(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        user = get_user(user_id)
        if not user:
            await interaction.response.send_message(
                "❌ 등록된 유저가 없어! 먼저 시작하기 버튼을 눌러줘.", ephemeral=True
            )
            return
        await interaction.response.send_message(
            "⚠️ 정말 리셋할까요?\n**전용 채널이 삭제**되고 처음부터 다시 시작해야 해.\n(식사 기록, 체중 기록 등 DB 데이터는 유지돼요)",
            view=ResetConfirmView(user_id=user_id),
            ephemeral=True,
        )

    @app_commands.command(name="start", description="다마고치 봇 시작 메시지를 채널에 고정합니다.")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def start_cmd(self, interaction: discord.Interaction):
        print(f"[CMD] /start — {interaction.user}")
        embed = discord.Embed(
            title="🌧️ 먹구름을 시작해봐요!",
            description=(
                "아래 버튼을 눌러서 나만의 캐릭터를 만들어보세요.\n\n"
                "• 음식을 입력하면 캐릭터에게 밥을 줄 수 있어요 🍚\n"
                "• 칼로리와 날씨 정보가 캐릭터 표정으로 전달돼요 🌤️\n"
                "• 건강하게 먹으면 캐릭터가 행복해져요 😄"
            ),
            color=0x57F287,
        )
        await interaction.response.send_message(embed=embed, view=StartView())


async def setup(bot: commands.Bot):
    await bot.add_cog(OnboardingCog(bot))
