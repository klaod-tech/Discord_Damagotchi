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
