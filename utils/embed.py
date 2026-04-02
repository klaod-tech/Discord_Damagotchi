"""
utils/embed.py — 다마고치 메인 Embed 생성 및 수정
Embed 구조:
  - 상단: 다마고치 이미지 (thumbnail)
  - 제목: {tamagotchi_name}의 하루
  - 설명: GPT 한마디
  - 버튼: [🍽️ 식사 입력] [📊 오늘 요약] [📅 오늘 일정] [⚙️ 설정 변경]
"""
import os
import asyncio
import discord
from datetime import date, timedelta
from utils.image import select_image, IMAGE_DESCRIPTIONS
from utils.gpt_ml_bridge import get_corrected_calories  # ✅ ML 보정 import

IMAGES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "images")


def _image_file(filename: str) -> discord.File | None:
    path = os.path.join(IMAGES_DIR, filename)
    if os.path.exists(path):
        return discord.File(path, filename=filename)
    return None


def build_main_embed(
    user: dict,
    tama: dict,
    comment: str,
    image_filename: str,
) -> tuple[discord.Embed, discord.File | None]:
    name = user.get("tamagotchi_name", "타마")
    description = IMAGE_DESCRIPTIONS.get(image_filename, "")

    embed = discord.Embed(
        title=f"{name}의 하루",
        description=f"{comment}\n\n*{description}*",
        color=_embed_color(tama),
    )
    embed.set_footer(text="밥을 챙겨줘야 건강하게 자라요 🌱")

    img_file = _image_file(image_filename)
    return embed, img_file


def _embed_color(tama: dict) -> int:
    hp     = tama.get("hp", 70)
    hunger = tama.get("hunger", 70)
    mood   = tama.get("mood", 70)
    avg = (hp + hunger + mood) / 3
    if avg >= 70:
        return 0x57F287
    if avg >= 40:
        return 0xFEE75C
    return 0xED4245


def _hunger_gain(calories: int) -> int:
    if calories >= 800:
        return 50
    if calories >= 400:
        return 35
    return 15


def _pm_grade(pm10: int, pm25: int) -> str:
    if pm10 > 150 or pm25 > 75:
        return "매우나쁨 😷"
    if pm10 > 80 or pm25 > 35:
        return "나쁨 😷"
    if pm10 > 30 or pm25 > 15:
        return "보통 😐"
    return "좋음 😊"


def _weather_icon(weather: str, temp: float) -> str:
    if "눈" in weather:
        return "❄️"
    if "비" in weather:
        return "🌧️"
    if "흐림" in weather or "구름" in weather:
        return "☁️"
    if temp >= 26:
        return "☀️🥵"
    if temp <= 5:
        return "🥶"
    return "☀️"


# ══════════════════════════════════════════════════════
# 식사 입력 Modal — 자연어 방식 + 합산 처리
# ══════════════════════════════════════════════════════
class MealInputModal(discord.ui.Modal, title="🍽️ 식사 입력"):
    food_input = discord.ui.TextInput(
        label="뭐 먹었어? 자유롭게 말해줘!",
        placeholder=(
            "예: 어제 저녁에 치킨 먹었어\n"
            "예: 오늘 점심 삼겹살이랑 된장찌개\n"
            "예: 그저께 아침에 시리얼\n"
            "예: 라면 한 그릇 (날짜/종류 생략하면 오늘 식사로 처리)"
        ),
        style=discord.TextStyle.paragraph,
        max_length=200,
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            from utils.db import (
                get_user, get_tamagotchi, create_meal, update_tamagotchi,
                get_calories_by_date, get_meals_by_date,
                is_all_meals_done_on_date,
            )
            from utils.gpt import parse_meal_input, analyze_meal_text, generate_comment

            user_id = str(interaction.user.id)
            user = get_user(user_id)
            tama = get_tamagotchi(user_id)

            if not user or not tama:
                await interaction.followup.send("❌ 등록된 유저가 아니야!", ephemeral=True)
                return

            raw_text = self.food_input.value.strip()

            # GPT로 자연어 파싱
            parsed    = await parse_meal_input(raw_text)
            days_ago  = parsed.get("days_ago", 0)
            meal_type = parsed.get("meal_type", "식사")
            food_name = parsed.get("food_name", raw_text)

            target_date = date.today() - timedelta(days=days_ago)
            is_past = days_ago > 0

            if days_ago == 0:
                date_label = "오늘"
            elif days_ago == 1:
                date_label = f"어제({target_date.strftime('%m/%d')})"
            else:
                date_label = f"그저께({target_date.strftime('%m/%d')})"

            # GPT로 영양 분석
            result   = await analyze_meal_text(food_name)
            calories = result.get("calories", 0)
            protein  = result.get("protein", 0)
            carbs    = result.get("carbs", 0)
            fat      = result.get("fat", 0)
            fiber    = result.get("fiber", 0)

            # ✅ ML 칼로리 보정 (양 표현 + 개인화 모델)
            calories = get_corrected_calories(
                user_id=user_id,
                food_name=food_name,
                meal_type=meal_type,
                gpt_calories=calories,
            )

            if calories == 0:
                await interaction.followup.send(
                    f"❌ **{food_name}**의 칼로리를 분석하지 못했어. 음식 이름을 더 구체적으로 입력해줘!",
                    ephemeral=True,
                )
                return

            today_cal_before = get_calories_by_date(user_id, target_date)

            comment = await generate_comment(
                context=f"방금 {food_name}을 먹었어. 반응해줘!",
                user=user,
                today_calories=today_cal_before + calories,
                recent_meals=food_name,
                weather_info=None,
            )

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
                gpt_comment=comment,
                recorded_date=target_date if is_past else None,
            )

            if not is_past:
                new_hunger = min(100, (tama.get("hunger") or 50) + _hunger_gain(calories))
                new_mood   = min(100, (tama.get("mood") or 50) + 5)
                new_hp     = min(100, (tama.get("hp") or 100) + 5)
                update_tamagotchi(user_id, {
                    "hunger": new_hunger,
                    "mood": new_mood,
                    "hp": new_hp,
                })

            today_cal = get_calories_by_date(user_id, target_date)

            await interaction.followup.send(
                f"✅ **{date_label} {meal_type}** — {food_name}\n"
                f"칼로리: **{calories} kcal** | "
                f"단백질: {protein}g | 탄수화물: {carbs}g | 지방: {fat}g\n"
                f"{date_label} 총 칼로리: **{today_cal} kcal**",
                ephemeral=True,
            )

            if is_past and is_all_meals_done_on_date(user_id, target_date):
                meals      = get_meals_by_date(user_id, target_date)
                total      = get_calories_by_date(user_id, target_date)
                target_cal = user.get("daily_cal_target") or 2000
                thread_id  = user.get("thread_id")
                if thread_id:
                    guild  = interaction.guild
                    thread = guild.get_thread(int(thread_id))
                    if thread:
                        await _send_daily_analysis(
                            thread, user, tama, meals, total, target_cal, target_date
                        )
                return

            if not is_past:
                thread_id = user.get("thread_id")
                if thread_id:
                    guild  = interaction.guild
                    thread = guild.get_thread(int(thread_id))
                    if thread:
                        tama_updated = get_tamagotchi(user_id)
                        await create_or_update_embed(
                            thread, user, tama_updated, comment, just_ate=True
                        )
                        await asyncio.sleep(180)
                        tama_final = get_tamagotchi(user_id)
                        from utils.gpt import generate_comment as gc
                        comment_after = await gc(
                            context="식사 후 잠시 지났어. 평소처럼 한마디 해줘.",
                            user=user,
                            today_calories=get_calories_by_date(user_id, date.today()),
                            recent_meals=food_name,
                            weather_info=None,
                        )
                        await create_or_update_embed(thread, user, tama_final, comment_after)

        except Exception as e:
            print(f"[MealInputModal 오류] {e}")
            import traceback
            traceback.print_exc()
            await interaction.followup.send(f"❌ 오류가 발생했어: {e}", ephemeral=True)


# ══════════════════════════════════════════════════════
# 식사 입력 방식 선택 View (텍스트 / 사진)
# ══════════════════════════════════════════════════════
class MealInputSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)

    @discord.ui.button(label="📝 텍스트로 입력", style=discord.ButtonStyle.primary, row=0)
    async def text_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(MealInputModal())

    @discord.ui.button(label="📸 사진으로 입력", style=discord.ButtonStyle.secondary, row=0)
    async def photo_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        import time
        cog = interaction.client.cogs.get("MealPhotoCog")
        if cog is not None:
            cog.waiting[str(interaction.user.id)] = time.time() + 60
        await interaction.response.edit_message(
            content="📸 지금 이 채팅에 음식 사진을 올려줘! (60초 안에)",
            view=None,
        )


async def _send_daily_analysis(thread, user, tama, meals, total_cal, target_cal, target_date):
    from utils.gpt import generate_comment
    from utils.db import get_tamagotchi

    user_id   = str(user.get("user_id") or "")
    tama_name = user.get("tamagotchi_name", "타마")
    date_label = target_date.strftime("%m월 %d일")

    overfed  = total_cal > target_cal
    underfed = total_cal < target_cal * 0.67

    if overfed:
        context = f"오늘 칼로리를 너무 많이 먹었어 ({total_cal}kcal). 걱정스럽지만 부드럽게 말해줘."
    elif underfed:
        context = f"오늘 칼로리를 너무 적게 먹었어 ({total_cal}kcal). 걱정스럽지만 부드럽게 말해줘."
    else:
        context = f"오늘 칼로리가 적당해 ({total_cal}kcal). 칭찬해줘!"

    comment = await generate_comment(
        context=context,
        user=user,
        today_calories=total_cal,
        recent_meals=", ".join(m.get("food_name", "") for m in meals),
        weather_info=None,
    )

    meal_icons = {"아침": "🌅", "점심": "☀️", "저녁": "🌙", "간식": "🌃", "식사": "🍽️"}

    meal_summary: dict[str, dict] = {}
    for m in meals:
        mt = m.get("meal_type", "식사")
        if mt not in meal_summary:
            meal_summary[mt] = {"foods": [], "calories": 0}
        meal_summary[mt]["foods"].append(m.get("food_name", ""))
        meal_summary[mt]["calories"] += m.get("calories", 0)

    lines = [
        f"{meal_icons.get(mt, '🍽️')} {mt}: {', '.join(v['foods'])} ({v['calories']} kcal)"
        for mt, v in meal_summary.items()
    ]

    embed = discord.Embed(
        title=f"📊 {date_label} 하루 결산",
        description="\n".join(lines) or "기록 없음",
        color=0xED4245 if (overfed or underfed) else 0x57F287,
    )
    embed.add_field(
        name="🔥 총 칼로리",
        value=f"`{total_cal}` / `{target_cal}` kcal",
        inline=False,
    )
    embed.add_field(
        name=f"💬 {tama_name} 한마디",
        value=f"*{comment}*",
        inline=False,
    )
    await thread.send(embed=embed)

    if target_date == date.today() and user_id:
        tama_updated = get_tamagotchi(user_id)
        if tama_updated:
            await create_or_update_embed(
                thread, user, tama_updated, comment,
                overfed=overfed, underfed=underfed
            )


# ══════════════════════════════════════════════════════
# 메인 버튼 View
# ══════════════════════════════════════════════════════
class MainView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="🍽️ 식사 입력",
        style=discord.ButtonStyle.primary,
        custom_id="btn_meal",
        row=0,
    )
    async def meal_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        print(f"[meal_button] 클릭 — user: {interaction.user}")
        await interaction.response.send_message(
            "어떻게 입력할까?",
            view=MealInputSelectView(),
            ephemeral=True,
        )

    @discord.ui.button(
        label="📊 오늘 요약",
        style=discord.ButtonStyle.secondary,
        custom_id="btn_summary",
        row=0,
    )
    async def summary_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        print(f"[summary_button] 클릭 — user: {interaction.user}")
        await interaction.response.defer(ephemeral=True)
        from cogs.summary import send_summary
        await send_summary(interaction)

    @discord.ui.button(
        label="📅 오늘 일정",
        style=discord.ButtonStyle.secondary,
        custom_id="btn_today",
        row=0,
    )
    async def today_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        print(f"[today_button] 클릭 — user: {interaction.user}")
        await interaction.response.defer(ephemeral=True)
        try:
            from utils.db import get_user, get_latest_weather, get_today_calories
            from utils.gpt import generate_comment
            from utils.pattern import analyze_eating_patterns
            from cogs.weight import get_weight_history, get_latest_weight

            user_id = str(interaction.user.id)
            user    = get_user(user_id)

            if not user:
                await interaction.followup.send("❌ 등록된 유저가 아니야!", ephemeral=True)
                return

            tama_name   = user.get("tamagotchi_name", "타마")
            goal_weight = float(user.get("goal_weight") or 70)
            init_weight = float(user.get("init_weight") or 76)
            base_cal    = user.get("daily_cal_target") or 2000
            today_cal   = get_today_calories(user_id)

            # ✅ ML 체중 기반 목표 칼로리 동적 조율
            weight_history = get_weight_history(user_id, limit=7)
            current_weight = weight_history[0]["weight"] if weight_history else None
            target_cal     = base_cal  # 기본값
            weight_context = ""        # GPT 주입용

            if current_weight and len(weight_history) >= 2:
                prev_weight  = weight_history[1]["weight"]
                weight_diff  = round(current_weight - prev_weight, 1)
                diff_to_goal = round(current_weight - goal_weight, 1)

                # 체중 증가 중 → 칼로리 목표 5% 감소
                if weight_diff > 0.3:
                    target_cal   = int(base_cal * 0.95)
                    weight_context = (
                        f"최근 체중이 {weight_diff}kg 늘었어 ({prev_weight}kg → {current_weight}kg). "
                        f"'어제 너무 많이 먹어서 좀 찐 거 같지 않아?' 같은 느낌으로 살짝 걱정해줘."
                    )
                # 체중 감소 중 → 칼로리 목표 유지 or 5% 증가 (너무 적게 먹으면)
                elif weight_diff < -0.3:
                    target_cal   = int(base_cal * 1.05) if diff_to_goal > 2 else base_cal
                    weight_context = (
                        f"최근 체중이 {abs(weight_diff)}kg 줄었어 ({prev_weight}kg → {current_weight}kg). "
                        f"'살이 조금씩 빠지고 있어!' 같은 느낌으로 신나게 칭찬해줘."
                    )
                # 체중 유지
                else:
                    weight_context = (
                        f"현재 체중 {current_weight}kg, 목표까지 {diff_to_goal}kg 남았어. "
                        f"꾸준히 유지하고 있다고 응원해줘."
                    )

            # 칼로리 바
            ratio  = min(today_cal / target_cal, 1.0) if target_cal > 0 else 0
            filled = int(ratio * 10)
            bar    = "█" * filled + "░" * (10 - filled)
            percent = int(ratio * 100)

            # 날씨 정보
            weather_log = get_latest_weather(user_id)
            city = user.get("city", "")
            if weather_log:
                weather  = weather_log.get("weather", "알 수 없음")
                temp     = weather_log.get("temp", 0)
                pm10     = weather_log.get("pm10", 0)
                pm25     = weather_log.get("pm25", 0)
                icon     = _weather_icon(weather, temp)
                pm_grade = _pm_grade(pm10, pm25)
                weather_text = (
                    f"{icon} {weather} / {temp}°C  📍 {city}\n"
                    f"미세먼지 PM10: {pm10} | PM2.5: {pm25} ({pm_grade})"
                )
            else:
                weather_text = "날씨 정보 없음 (기상 시간에 자동 갱신돼요)"

            # 식사 알림 시간
            breakfast = user.get("breakfast_time", "08:00")
            lunch     = user.get("lunch_time", "12:00")
            dinner    = user.get("dinner_time", "18:00")

            today_str = date.today().strftime("%Y년 %m월 %d일")

            # ✅ ML 패턴 분석 + 체중 컨텍스트 → GPT 다마고치 멘트 생성
            pattern_result  = analyze_eating_patterns(user_id, target_cal)
            pattern_context = pattern_result.get("gpt_context", "")
            full_context    = "\n".join(filter(None, [pattern_context, weight_context]))

            ml_comment = await generate_comment(
                context=(
                    f"오늘 일정을 확인하러 왔어. "
                    f"오늘 목표는 {target_cal}kcal인데 지금까지 {today_cal}kcal 먹었어. "
                    f"짧고 귀엽게 한마디 해줘!"
                ),
                user=user,
                today_calories=today_cal,
                recent_meals="",
                weather_info=weather_log,
                extra_context=full_context,  # ✅ 패턴 + 체중 변화 주입
            )

            # ✅ 체중 현황 필드 텍스트 생성
            if current_weight:
                w_total  = abs(init_weight - goal_weight)
                w_done   = abs(init_weight - current_weight)
                w_ratio  = min(w_done / w_total, 1.0) if w_total > 0 else 0
                w_filled = int(w_ratio * 10)
                w_bar    = "█" * w_filled + "░" * (10 - w_filled)
                w_pct    = int(w_ratio * 100)
                w_remain = round(max(current_weight - goal_weight, 0), 1)

                if len(weight_history) >= 2:
                    w_diff   = round(current_weight - weight_history[1]["weight"], 1)
                    w_change = f"▲ {w_diff}kg" if w_diff > 0 else (f"▼ {abs(w_diff)}kg" if w_diff < 0 else "→ 유지")
                else:
                    w_change = "→ 첫 기록"

                weight_text = (
                    f"현재: **{current_weight}kg** ({w_change})\n"
                    f"목표: **{goal_weight}kg** (남은 몸무게: {w_remain}kg)\n"
                    f"`{w_bar}` {w_pct}%"
                )
            else:
                weight_text = "아직 체중 기록이 없어요!\n[⚖️ 체중 기록] 버튼으로 입력해줘 🐣"

            # ✅ 목표 칼로리 조율 여부 표시
            if target_cal != base_cal:
                cal_adjust = f" (체중 변화로 {'+' if target_cal > base_cal else ''}{target_cal - base_cal}kcal 조정)"
            else:
                cal_adjust = ""

            embed = discord.Embed(
                title=f"📅 오늘 일정 — {today_str}",
                color=0x5865F2,
            )
            embed.add_field(
                name="🔥 목표 칼로리",
                value=f"목표: `{target_cal}` kcal{cal_adjust}\n현재: `{today_cal}` kcal ({percent}%)\n`{bar}`",
                inline=False,
            )
            embed.add_field(
                name="⚖️ 체중 현황",
                value=weight_text,
                inline=False,
            )
            embed.add_field(
                name="🍽️ 식사 알림 시간",
                value=f"🌅 아침: {breakfast}  ☀️ 점심: {lunch}  🌙 저녁: {dinner}",
                inline=False,
            )
            embed.add_field(
                name="🌤️ 현재 날씨",
                value=weather_text,
                inline=False,
            )
            # ✅ 패턴 + 체중 변화가 녹아든 다마고치 멘트
            embed.add_field(
                name=f"🐣 {tama_name}의 한마디",
                value=f"*{ml_comment}*",
                inline=False,
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            print(f"[today_button 오류] {e}")
            import traceback
            traceback.print_exc()
            await interaction.followup.send(f"❌ 오류가 발생했어: {e}", ephemeral=True)

    @discord.ui.button(
        label="⚙️ 설정 변경",
        style=discord.ButtonStyle.secondary,
        custom_id="btn_settings",
        row=1,
    )
    async def settings_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        print(f"[settings_button] 클릭 — user: {interaction.user}")
        from utils.db import get_user
        from cogs.settings import SettingsModal
        user = get_user(str(interaction.user.id))
        if not user:
            await interaction.response.send_message(
                "❌ 등록된 유저가 아니야!", ephemeral=True
            )
            return
        await interaction.response.send_modal(SettingsModal(user=user))

    @discord.ui.button(
        label="⏰ 시간 설정",
        style=discord.ButtonStyle.secondary,
        custom_id="btn_time_settings",
        row=1,
    )
    async def time_settings_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        print(f"[time_settings_button] 클릭 — user: {interaction.user}")
        from cogs.time_settings import TimeStep1View
        await interaction.response.send_message(
            "⏰ **시간 설정** — 1단계\n\n"
            "🌅 **기상 시간** — 시 / 분\n"
            "🍳 **아침 알림** — 시 / 분",
            view=TimeStep1View(user_id=str(interaction.user.id)),
            ephemeral=True,
        )

    @discord.ui.button(
        label="⚖️ 체중 기록",
        style=discord.ButtonStyle.secondary,
        custom_id="btn_weight",
        row=1,
    )
    async def weight_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        print(f"[weight_button] 클릭 — user: {interaction.user}")
        from cogs.weight import WeightInputModal
        await interaction.response.send_modal(WeightInputModal())


# ══════════════════════════════════════════════════════
# Embed 생성/수정
# ══════════════════════════════════════════════════════
async def create_or_update_embed(
    thread: discord.Thread,
    user: dict,
    tama: dict,
    comment: str,
    weather: dict | None = None,
    *,
    just_ate: bool = False,
    overfed: bool = False,
    underfed: bool = False,
    goal_achieved: bool = False,
) -> str:
    image_filename = select_image(
        tama, user, weather,
        just_ate=just_ate,
        overfed=overfed,
        underfed=underfed,
        goal_achieved=goal_achieved,
    )
    embed, img_file = build_main_embed(user, tama, comment, image_filename)
    view = MainView()

    embed_msg_id = tama.get("embed_message_id")

    if embed_msg_id:
        try:
            msg = await thread.fetch_message(int(embed_msg_id))
            if img_file:
                await msg.edit(embed=embed, attachments=[img_file], view=view)
            else:
                await msg.edit(embed=embed, view=view)
            return embed_msg_id
        except discord.NotFound:
            pass

    if img_file:
        msg = await thread.send(file=img_file, embed=embed, view=view)
    else:
        msg = await thread.send(embed=embed, view=view)

    from utils.db import set_embed_message_id, update_tamagotchi
    set_embed_message_id(str(thread.owner_id or ""), str(msg.id))
    update_tamagotchi(str(thread.owner_id or ""), {"current_image": image_filename})

    return str(msg.id)
