"""
cogs/meal.py — 사진 식사 입력 기능
────────────────────────────────────────────────────────────────
흐름:
  1. 유저가 자신의 전용 쓰레드에 사진 첨부
  2. on_message로 감지 → "📸 음식 사진이에요? [✅ 분석하기]" 버튼 응답
  3. [✅ 분석하기] 클릭 → GPT-4o Vision으로 음식 인식 + 칼로리 분석
  4. 분석 결과 Embed 표시 → [✅ 기록하기] / [❌ 취소] 버튼
  5. [✅ 기록하기] 클릭 → DB 저장 + Embed 갱신
────────────────────────────────────────────────────────────────
"""

import discord
from discord.ext import commands
from datetime import date, datetime
import aiohttp
import base64
import time

from utils.db import (
    get_user, get_tamagotchi, create_meal,
    update_tamagotchi, get_calories_by_date,
    is_meal_waiting, clear_meal_waiting,
)
from utils.gpt import generate_comment
from utils.gpt_ml_bridge import get_corrected_calories
from utils.embed import create_or_update_embed, _hunger_gain


# ──────────────────────────────────────────────
# 분석 결과 Embed 빌드 helper
# ──────────────────────────────────────────────

def _build_analysis_embed(analysis: dict) -> discord.Embed:
    embed = discord.Embed(
        title="🔍 음식 분석 결과",
        description=analysis.get("description", ""),
        color=0x57F287,
    )
    embed.add_field(
        name="🍽️ 음식",
        value=f"{analysis['food_name']} ({analysis['meal_type']})",
        inline=False,
    )
    embed.add_field(name="🔥 칼로리",   value=f"**{analysis['calories']} kcal**", inline=True)
    embed.add_field(name="💪 단백질",   value=f"{analysis['protein']}g",          inline=True)
    embed.add_field(name="🌾 탄수화물", value=f"{analysis['carbs']}g",            inline=True)
    embed.add_field(name="🥑 지방",     value=f"{analysis['fat']}g",              inline=True)
    embed.set_footer(text="기록하면 다마고치 수치에 반영돼요!")
    return embed


# ──────────────────────────────────────────────
# GPT-4o Vision 분석 함수
# ──────────────────────────────────────────────

async def analyze_food_image(image_url: str) -> dict:
    """
    GPT-4o Vision으로 음식 사진 분석.

    Returns
    -------
    {
        "food_name" : str,   # 인식된 음식명
        "meal_type" : str,   # 추정 끼니 (아침/점심/저녁/간식)
        "calories"  : int,
        "protein"   : float,
        "carbs"     : float,
        "fat"       : float,
        "fiber"     : float,
        "description": str,  # 음식 설명 (Embed용)
    }
    """
    import os, json
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])

    system_prompt = (
        "너는 음식 사진을 분석하는 영양사야. "
        "사진 속 음식을 인식하고 영양 정보를 JSON으로만 반환해. "
        "JSON 외 다른 텍스트는 절대 출력하지 마.\n"
        "반환 형식:\n"
        "{\n"
        '  "food_name": "음식명 (한국어)",\n'
        '  "meal_type": "아침/점심/저녁/간식 중 하나",\n'
        '  "calories": 숫자,\n'
        '  "protein": 숫자,\n'
        '  "carbs": 숫자,\n'
        '  "fat": 숫자,\n'
        '  "fiber": 숫자,\n'
        '  "description": "음식에 대한 한 줄 설명"\n'
        "}"
    )

    response = await client.chat.completions.create(
        model="gpt-4o",
        max_tokens=500,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": image_url, "detail": "low"},
                    },
                    {
                        "type": "text",
                        "text": system_prompt,
                    },
                ],
            }
        ],
    )

    raw = response.choices[0].message.content.strip()
    # JSON 펜스 제거
    raw = raw.replace("```json", "").replace("```", "").strip()

    result = json.loads(raw)

    # 타입 보정
    return {
        "food_name":   str(result.get("food_name", "알 수 없는 음식")),
        "meal_type":   str(result.get("meal_type", "식사")),
        "calories":    int(result.get("calories", 0)),
        "protein":     float(result.get("protein", 0)),
        "carbs":       float(result.get("carbs", 0)),
        "fat":         float(result.get("fat", 0)),
        "fiber":       float(result.get("fiber", 0)),
        "description": str(result.get("description", "")),
    }


# ──────────────────────────────────────────────
# 분석 결과 확인 버튼 View
# ──────────────────────────────────────────────

class MealPhotoConfirmView(discord.ui.View):
    """
    GPT Vision 분석 결과를 보여주고 [✅ 기록하기] / [❌ 취소] 버튼 제공.
    """

    def __init__(self, user_id: str, analysis: dict):
        super().__init__(timeout=180)  # 3분 후 만료
        self.user_id  = user_id
        self.analysis = analysis
        self.recorded = False

    @discord.ui.button(label="✅ 기록하기", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message(
                "❌ 본인의 식사만 기록할 수 있어!", ephemeral=True
            )
            return

        if self.recorded:
            await interaction.response.send_message(
                "이미 기록됐어!", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True, thinking=True)

        try:
            user = get_user(self.user_id)
            tama = get_tamagotchi(self.user_id)
            if not user or not tama:
                await interaction.followup.send("❌ 유저 정보를 찾을 수 없어!", ephemeral=True)
                return

            a = self.analysis
            today = date.today()

            # ML 칼로리 보정
            calories = get_corrected_calories(
                user_id      = self.user_id,
                food_name    = a["food_name"],
                meal_type    = a["meal_type"],
                gpt_calories = a["calories"],
            )

            if calories == 0:
                await interaction.followup.send(
                    f"❌ **{a['food_name']}**의 칼로리를 분석하지 못했어. 다시 시도해줘!",
                    ephemeral=True,
                )
                return

            today_cal_before = get_calories_by_date(self.user_id, today)

            # GPT 다마고치 대사 생성
            comment = await generate_comment(
                context       = f"방금 {a['food_name']} 사진을 찍어서 기록했어. 사진으로 식사를 기록한 것에 반응해줘!",
                user          = user,
                today_calories= today_cal_before + calories,
                recent_meals  = a["food_name"],
                weather_info  = None,
            )

            # DB 저장
            create_meal(
                user_id      = self.user_id,
                meal_type    = a["meal_type"],
                food_name    = a["food_name"],
                calories     = calories,
                protein      = a["protein"],
                carbs        = a["carbs"],
                fat          = a["fat"],
                fiber        = a["fiber"],
                input_method = "photo",   # ← 사진 입력 구분
                gpt_comment  = comment,
            )

            # 다마고치 수치 갱신
            new_hunger = min(100, (tama.get("hunger") or 50) + _hunger_gain(calories))
            new_mood   = min(100, (tama.get("mood") or 50) + 5)
            new_hp     = min(100, (tama.get("hp") or 100) + 5)
            update_tamagotchi(self.user_id, {
                "hunger":      new_hunger,
                "mood":        new_mood,
                "hp":          new_hp,
                "last_fed_at": datetime.utcnow().isoformat(),
            })

            today_cal = get_calories_by_date(self.user_id, today)

            await interaction.followup.send(
                f"✅ **오늘 {a['meal_type']}** — {a['food_name']}\n"
                f"칼로리: **{calories} kcal** | "
                f"단백질: {a['protein']}g | 탄수화물: {a['carbs']}g | 지방: {a['fat']}g\n"
                f"오늘 총 칼로리: **{today_cal} kcal**",
                ephemeral=True,
            )

            # Embed 갱신
            thread_id = user.get("thread_id")
            if thread_id:
                guild  = interaction.guild
                thread = guild.get_thread(int(thread_id))
                if thread:
                    tama_updated = get_tamagotchi(self.user_id)
                    await create_or_update_embed(
                        thread, user, tama_updated, comment, just_ate=True
                    )

            self.recorded = True

            # 버튼 비활성화
            for child in self.children:
                child.disabled = True
            await interaction.message.edit(view=self)

        except Exception as e:
            print(f"[MealPhotoConfirmView 오류] {e}")
            import traceback
            traceback.print_exc()
            await interaction.followup.send(f"❌ 오류가 발생했어: {e}", ephemeral=True)

    @discord.ui.button(label="❌ 취소", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message(
                "❌ 본인만 취소할 수 있어!", ephemeral=True
            )
            return

        for child in self.children:
            child.disabled = True
        await interaction.message.edit(view=self)
        await interaction.response.send_message("취소했어! 🙅", ephemeral=True)

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True


# ──────────────────────────────────────────────
# 사진 감지 확인 버튼 View
# ──────────────────────────────────────────────

class MealPhotoDetectView(discord.ui.View):
    """
    사진 감지 시 "📸 음식 사진이에요? [✅ 분석하기]" 버튼 제공.
    """

    def __init__(self, user_id: str, image_url: str):
        super().__init__(timeout=120)
        self.user_id   = user_id
        self.image_url = image_url
        self.analyzed  = False

    @discord.ui.button(label="✅ 분석하기", style=discord.ButtonStyle.primary)
    async def analyze(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message(
                "❌ 본인의 사진만 분석할 수 있어!", ephemeral=True
            )
            return

        if self.analyzed:
            await interaction.response.send_message(
                "이미 분석 중이야!", ephemeral=True
            )
            return

        self.analyzed = True
        await interaction.response.defer(thinking=True)

        try:
            # GPT-4o Vision 분석
            analysis = await analyze_food_image(self.image_url)

            # 결과 Embed 생성
            embed = _build_analysis_embed(analysis)

            # 확인 버튼 View
            confirm_view = MealPhotoConfirmView(
                user_id  = self.user_id,
                analysis = analysis,
            )

            # 기존 감지 메시지 버튼 비활성화
            for child in self.children:
                child.disabled = True
            await interaction.message.edit(view=self)

            await interaction.followup.send(embed=embed, view=confirm_view)

        except Exception as e:
            print(f"[MealPhotoDetectView 분석 오류] {e}")
            import traceback
            traceback.print_exc()
            await interaction.followup.send(
                f"❌ 음식 인식에 실패했어: {e}\n텍스트로 직접 입력해줘!", ephemeral=False
            )

    @discord.ui.button(label="❌ 아니야", style=discord.ButtonStyle.secondary)
    async def dismiss(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("❌", ephemeral=True)
            return

        for child in self.children:
            child.disabled = True
        await interaction.message.edit(view=self)
        await interaction.response.send_message("알겠어! 👍", ephemeral=True)

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True


# ──────────────────────────────────────────────
# Cog 본체
# ──────────────────────────────────────────────

class MealPhotoCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        print("[MealPhotoCog] 로드 완료")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """
        유저 전용 쓰레드에 사진 첨부 시 감지.
        """
        # 봇 메시지 무시
        if message.author.bot:
            return

        # 첨부파일 없으면 무시
        if not message.attachments:
            return

        # 이미지 첨부 확인
        image_attachments = [
            a for a in message.attachments
            if a.content_type and a.content_type.startswith("image/")
        ]
        if not image_attachments:
            return

        # 쓰레드인지 확인
        if not isinstance(message.channel, discord.Thread):
            return

        user_id = str(message.author.id)
        user    = get_user(user_id)

        # 등록된 유저인지 확인
        if not user:
            return

        # 본인 전용 쓰레드인지 확인 (식사 전용 쓰레드 우선, fallback: 메인 쓰레드)
        allowed_thread_id = user.get("meal_thread_id") or user.get("thread_id")
        if str(allowed_thread_id or "") != str(message.channel.id):
            return

        # 첫 번째 이미지만 처리
        image_url = image_attachments[0].url

        # 사진 입력 대기 중인 유저인지 확인 (DB 기반)
        if is_meal_waiting(user_id):
            clear_meal_waiting(user_id)
            thinking_msg = await message.channel.send("📸 사진 분석 중... 잠깐만 기다려줘!")
            try:
                analysis = await analyze_food_image(image_url)
                embed = _build_analysis_embed(analysis)
                confirm_view = MealPhotoConfirmView(user_id=user_id, analysis=analysis)
                await thinking_msg.delete()
                await message.channel.send(embed=embed, view=confirm_view)
            except Exception as e:
                print(f"[on_message 사진 분석 오류] {e}")
                import traceback
                traceback.print_exc()
                await thinking_msg.edit(content=f"❌ 음식 인식에 실패했어: {e}\n텍스트로 직접 입력해줘!")
            return

        await message.channel.send(
            f"📸 음식 사진이에요?",
            view=MealPhotoDetectView(user_id=user_id, image_url=image_url),
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(MealPhotoCog(bot))
