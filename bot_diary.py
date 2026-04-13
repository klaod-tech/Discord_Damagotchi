"""
bot_diary.py — 일기 전용 봇 진입점

역할: 일기 작성 / 감정 분석 / 식사×감정 상관관계 데이터 누적
DB : 먹구름과 동일한 Supabase 공유
토큰: .env의 DISCORD_TOKEN_DIARY 사용

실행:
    python bot_diary.py
"""
import os
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv
from utils.db import init_db

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN_DIARY")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!diary_", intents=intents)

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
    print(f"[일기봇] {bot.user} 로그인 완료")

@bot.event
async def on_error(event, *args, **kwargs):
    import traceback
    traceback.print_exc()

async def main():
    async with bot:
        # TODO: 일기 관련 cog 로드
        # await bot.load_extension("cogs.diary")
        print("[일기봇] 준비 완료 — cog 미구현")
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
