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

import asyncio
import discord
from discord.ext import commands
from datetime import date, datetime, timedelta
import aiohttp
import base64
import time

from utils.db import (
    get_user, get_tamagotchi, create_meal,
    update_tamagotchi, get_calories_by_date,
    get_meals_by_date, is_all_meals_done_on_date,
    is_meal_waiting, clear_meal_waiting,
    set_meal_clarification, get_meal_clarification, clear_meal_clarification,
)

MEAL_CATEGORIES = {
    "한식", "양식", "일식", "중식", "분식",
    "패스트푸드", "배달음식", "배달", "음식", "식사",
    "밥", "간식", "야식",
}
from utils.gpt import generate_comment, parse_meal_input, analyze_meal_text
from utils.gpt_ml_bridge import get_corrected_calories
from utils.nutrition import search_food_nutrition
from utils.embed import create_or_update_embed, _hunger_gain, _post_meal_embed, _send_daily_analysis


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
        self.message: discord.Message | None = None

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
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass


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
        self.message: discord.Message | None = None

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

            confirm_msg = await interaction.followup.send(embed=embed, view=confirm_view)
            confirm_view.message = confirm_msg

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
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass


# ──────────────────────────────────────────────
# 텍스트 식사 입력 처리 (식사 기록 쓰레드 직접 입력)
# ──────────────────────────────────────────────

async def _process_text_meal(message: discord.Message, user_id: str, user: dict):
    tama = get_tamagotchi(user_id)
    if not tama:
        return

    raw_text = message.content.strip()
    if not raw_text:
        return

    thinking_msg = await message.reply("🤔 분석 중...")

    results           = []
    today_hunger_gain = 0
    today_mood_gain   = 0
    any_today         = False

    parsed_meals = await parse_meal_input(raw_text)

    # 카테고리 감지 → 재질문 (1회만)
    for parsed in parsed_meals:
        food_name = parsed.get("food_name", "")
        if food_name in MEAL_CATEGORIES:
            set_meal_clarification(user_id, raw_text)
            await thinking_msg.edit(
                content=f"'{food_name}'이라고 하셨는데, 어떤 음식을 드셨어요? 😊"
            )
            return

    for parsed in parsed_meals:
        days_ago  = parsed.get("days_ago", 0)
        meal_type = parsed.get("meal_type", "식사")
        food_name = parsed.get("food_name", raw_text)

        target_date = date.today() - timedelta(days=days_ago)
        is_past     = days_ago > 0

        if days_ago == 0:
            date_label = "오늘"
        elif days_ago == 1:
            date_label = f"어제({target_date.strftime('%m/%d')})"
        else:
            date_label = f"그저께({target_date.strftime('%m/%d')})"

        result = await search_food_nutrition(food_name)
        if result is None:
            result = await analyze_meal_text(food_name)
        calories = result.get("calories", 0)
        protein  = result.get("protein", 0)
        carbs    = result.get("carbs", 0)
        fat      = result.get("fat", 0)
        fiber    = result.get("fiber", 0)

        calories = get_corrected_calories(
            user_id=user_id,
            food_name=food_name,
            meal_type=meal_type,
            gpt_calories=calories,
        )

        if calories == 0:
            results.append({"error": True, "food_name": food_name})
            continue

        create_meal(
            user_id=user_id,
            meal_type=meal_type,
            food_name=food_name,
            calories=calories,
            protein=protein,
            carbs=carbs,
            fat=fat,
            fiber=fiber,
            input_method="text",
            gpt_comment="",
            recorded_date=target_date if is_past else None,
        )

        if not is_past:
            any_today         = True
            today_hunger_gain += _hunger_gain(calories)
            today_mood_gain   += 5

        results.append({
            "error":       False,
            "date_label":  date_label,
            "meal_type":   meal_type,
            "food_name":   food_name,
            "calories":    calories,
            "protein":     protein,
            "carbs":       carbs,
            "fat":         fat,
            "is_past":     is_past,
            "target_date": target_date,
        })

    ok_results = [r for r in results if not r.get("error")]

    if not ok_results:
        await thinking_msg.edit(content="❌ 식사 내용을 인식하지 못했어. 더 구체적으로 말해줘!")
        return

    if any_today:
        new_hunger = min(100, (tama.get("hunger") or 50) + today_hunger_gain)
        new_mood   = min(100, (tama.get("mood") or 50) + today_mood_gain)
        new_hp     = min(100, (tama.get("hp") or 100) + today_mood_gain)
        update_tamagotchi(user_id, {
            "hunger":      new_hunger,
            "mood":        new_mood,
            "hp":          new_hp,
            "last_fed_at": datetime.utcnow().isoformat(),
        })

    food_names = ", ".join(r["food_name"] for r in ok_results)
    today_cal  = get_calories_by_date(user_id, date.today())

    comment = await generate_comment(
        context=f"방금 {food_names}을 먹었어. 반응해줘!",
        user=user,
        today_calories=today_cal,
        recent_meals=food_names,
        weather_info=None,
    )

    lines = []
    for r in results:
        if r.get("error"):
            lines.append(f"⚠️ **{r['food_name']}** — 칼로리 분석 실패")
        else:
            lines.append(
                f"✅ **{r['date_label']} {r['meal_type']}** — {r['food_name']}\n"
                f"칼로리: **{r['calories']} kcal** | "
                f"단백질: {r['protein']}g | 탄수화물: {r['carbs']}g | 지방: {r['fat']}g"
            )
    lines.append(f"\n오늘 총 칼로리: **{today_cal} kcal**")
    await thinking_msg.edit(content="\n".join(lines))

    past_dates = {r["target_date"] for r in ok_results if r["is_past"]}
    for pd in past_dates:
        if is_all_meals_done_on_date(user_id, pd):
            meals_pd   = get_meals_by_date(user_id, pd)
            total      = get_calories_by_date(user_id, pd)
            target_cal = user.get("daily_cal_target") or 2000
            thread_id  = user.get("thread_id")
            if thread_id:
                thread = message.guild.get_thread(int(thread_id)) if message.guild else None
                if thread:
                    await _send_daily_analysis(thread, user, tama, meals_pd, total, target_cal, pd)

    if any_today:
        thread_id = user.get("thread_id")
        if thread_id:
            guild  = message.guild
            thread = guild.get_thread(int(thread_id)) if guild else None
            if thread:
                tama_updated = get_tamagotchi(user_id)
                await create_or_update_embed(thread, user, tama_updated, comment, just_ate=True)
                asyncio.create_task(
                    _post_meal_embed(thread, user, user_id, food_names)
                )


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
        유저 전용 쓰레드에서 사진 또는 텍스트로 식사 입력 감지.
        """
        if message.author.bot:
            return

        if not isinstance(message.channel, discord.Thread):
            return

        user_id = str(message.author.id)
        user    = get_user(user_id)
        if not user:
            return

        # 본인 전용 쓰레드인지 확인 (식사 전용 쓰레드 우선, fallback: 메인 쓰레드)
        allowed_thread_id = user.get("meal_thread_id") or user.get("thread_id")
        if str(allowed_thread_id or "") != str(message.channel.id):
            return

        # 이미지 첨부 확인 → 사진 입력 처리
        image_attachments = [
            a for a in message.attachments
            if a.content_type and a.content_type.startswith("image/")
        ]
        if image_attachments:
            image_url = image_attachments[0].url

            if is_meal_waiting(user_id):
                clear_meal_waiting(user_id)
                thinking_msg = await message.channel.send("📸 사진 분석 중... 잠깐만 기다려줘!")
                try:
                    analysis = await analyze_food_image(image_url)
                    embed = _build_analysis_embed(analysis)
                    confirm_view = MealPhotoConfirmView(user_id=user_id, analysis=analysis)
                    await thinking_msg.delete()
                    confirm_msg = await message.channel.send(embed=embed, view=confirm_view)
                    confirm_view.message = confirm_msg
                except Exception as e:
                    print(f"[on_message 사진 분석 오류] {e}")
                    import traceback
                    traceback.print_exc()
                    await thinking_msg.edit(content=f"❌ 음식 인식에 실패했어: {e}\n텍스트로 직접 입력해줘!")
                return

            # 대기 만료 후 사진 업로드 시 안내
            waiting_until = user.get("meal_waiting_until")
            if waiting_until:
                from datetime import timezone
                now = datetime.now(timezone.utc)
                exp = waiting_until if waiting_until.tzinfo else waiting_until.replace(tzinfo=timezone.utc)
                if now > exp:
                    await message.channel.send(
                        f"<@{message.author.id}> 사진 입력 시간이 초과됐어요. 다시 📸 버튼을 눌러주세요!",
                        delete_after=10,
                    )
                    return

            detect_view = MealPhotoDetectView(user_id=user_id, image_url=image_url)
            detect_msg = await message.channel.send("📸 음식 사진이에요?", view=detect_view)
            detect_view.message = detect_msg
            return

        # 텍스트 입력 → 식사 파싱 처리
        if message.content.strip() and not message.content.strip().startswith(('/', '!')):
            clarification = get_meal_clarification(user_id)
            if clarification:
                clear_meal_clarification(user_id)
            await _process_text_meal(message, user_id, user)


async def setup(bot: commands.Bot):
    await bot.add_cog(MealPhotoCog(bot))
