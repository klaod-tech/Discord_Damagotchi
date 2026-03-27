"""
utils/embed.py — 다마고치 메인 Embed 생성 및 수정

Embed 구조:
  - 상단: 다마고치 이미지 (thumbnail)
  - 제목: {tamagotchi_name}의 하루
  - 설명: GPT 한마디
  - 버튼: [🍽️ 식사 입력] [📊 오늘 요약] [⚙️ 설정]
"""

import os
import discord
from utils.image import select_image, IMAGE_DESCRIPTIONS


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
    """
    메인 Embed와 첨부 이미지 파일 반환.
    """
    name = user.get("tamagotchi_name", "타마")
    description = IMAGE_DESCRIPTIONS.get(image_filename, "")

    embed = discord.Embed(
        title=f"{name}의 하루",
        description=f"{comment}\n\n*{description}*",
        color=_embed_color(tama),
    )
    embed.set_footer(text="밥을 챙겨줘야 건강하게 자라요 🌱")

    img_file = _image_file(image_filename)
    if img_file:
        embed.set_thumbnail(url=f"attachment://{image_filename}")

    return embed, img_file


def _embed_color(tama: dict) -> int:
    hp = tama.get("hp", 70)
    hunger = tama.get("hunger", 70)
    mood = tama.get("mood", 70)
    avg = (hp + hunger + mood) / 3

    if avg >= 70:
        return 0x57F287   # 초록 (good)
    if avg >= 40:
        return 0xFEE75C   # 노랑 (neutral)
    return 0xED4245       # 빨강 (bad)


class MainView(discord.ui.View):
    """메인 Embed 하단 버튼 뷰 (영구 지속)"""

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="🍽️ 식사 입력",
        style=discord.ButtonStyle.primary,
        custom_id="btn_meal",
    )
    async def meal_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.send_message(
            "먹은 음식을 입력해줘! (예: `삼겹살 200g, 된장찌개`)\n"
            "사진을 첨부해도 돼 📸",
            ephemeral=True,
        )

    @discord.ui.button(
        label="📊 오늘 요약",
        style=discord.ButtonStyle.secondary,
        custom_id="btn_summary",
    )
    async def summary_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        # summary cog에서 처리 — 여기선 placeholder
        await interaction.response.defer(ephemeral=True)
        from cogs.summary import send_summary
        await send_summary(interaction)

    @discord.ui.button(
        label="⚙️ 설정",
        style=discord.ButtonStyle.secondary,
        custom_id="btn_settings",
    )
    async def settings_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.send_message(
            "설정 기능은 준비 중이에요 🔧", ephemeral=True
        )


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
    """
    쓰레드 내 메인 Embed를 생성하거나 수정한다.
    Returns: embed_message_id (str)
    """
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

    # 기존 메시지 수정 시도
    if embed_msg_id:
        try:
            msg = await thread.fetch_message(int(embed_msg_id))
            if img_file:
                await msg.edit(embed=embed, attachments=[img_file], view=view)
            else:
                await msg.edit(embed=embed, view=view)
            return embed_msg_id
        except discord.NotFound:
            pass  # 메시지가 삭제된 경우 새로 생성

    # 새 메시지 생성
    if img_file:
        msg = await thread.send(file=img_file, embed=embed, view=view)
    else:
        msg = await thread.send(embed=embed, view=view)

    # DB에 메시지 ID 저장
    from utils.db import set_embed_message_id, update_tamagotchi
    set_embed_message_id(str(thread.owner_id or ""), str(msg.id))
    update_tamagotchi(str(thread.owner_id or ""), {"current_image": image_filename})

    return str(msg.id)
