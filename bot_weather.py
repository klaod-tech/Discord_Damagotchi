"""
bot_weather.py — 날씨 전용 봇 진입점

역할: 기상청 / 에어코리아 API 폴링 → 날씨 스레드 알림
DB : 먹구름과 동일한 Supabase 공유
토큰: .env의 DISCORD_TOKEN_WEATHER 사용

실행:
    python bot_weather.py
"""
import os
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv
from utils.db import init_db

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN_WEATHER")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!weather_", intents=intents)

_bot_ready = False

@bot.event
async def on_ready():
    global _bot_ready
    if _bot_ready:
        print(f"[RECONNECT] {bot.user} 재연결됨 — 초기화 생략")
        return
    _bot_ready = True

    init_db()
    await bot.tree.sync()
    print(f"[날씨봇] {bot.user} 로그인 완료")

@bot.event
async def on_error(event, *args, **kwargs):
    import traceback
    traceback.print_exc()

async def main():
    async with bot:
        await bot.load_extension("cogs.weather")
        print("[날씨봇] cogs.weather 로드 완료")
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
