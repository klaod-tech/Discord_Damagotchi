import os
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv
from utils.db import init_db
from utils.embed import MainView

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
TAMAGOTCHI_CHANNEL_ID = int(os.getenv("TAMAGOTCHI_CHANNEL_ID", "0"))

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

COGS = [
    "cogs.onboarding",
]


@bot.event
async def on_ready():
    init_db()
    # 영구 View 등록 (봇 재시작 후에도 버튼 동작)
    bot.add_view(MainView())

    await bot.tree.sync()
    print(f"[✅] {bot.user} 로그인 완료 — 슬래시 커맨드 동기화 완료")


@bot.command(name="sync")
@commands.is_owner()
async def force_sync(ctx):
    synced = await bot.tree.sync()
    await ctx.send(f"커맨드 {len(synced)}개 동기화 완료")
    
@bot.command(name="setup")
@commands.has_permissions(administrator=True)
async def setup(ctx: commands.Context):
    channel = bot.get_channel(TAMAGOTCHI_CHANNEL_ID)
    if channel is None:
        await ctx.send("❌ TAMAGOTCHI_CHANNEL_ID를 확인해주세요.")
        return

    embed = discord.Embed(
        title="🐣 AI 다마고치에 오신 걸 환영해요!",
        description=(
            "다마고치와 함께 건강한 식습관을 만들어보세요.\n\n"
            "아래 버튼을 눌러 나만의 다마고치를 만들어보세요! 👇"
        ),
        color=discord.Color.from_rgb(255, 220, 120),
    )

    from cogs.onboarding import StartView
    await channel.send(embed=embed, view=StartView())
    await ctx.send("✅ 고정 메시지를 전송했어요!", delete_after=5)


async def main():
    async with bot:
        for cog in COGS:
            try:
                await bot.load_extension(cog)
                print(f"[COG] {cog} 로드 완료")
            except Exception as e:
                print(f"[COG ERROR] {cog}: {e}")
        await bot.start(DISCORD_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
