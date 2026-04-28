"""
bot_weight.py — 체중관리 전용 봇 진입점

역할: 체중 기록 / 칼로리 목표 동적 조정 / 체중 추이 예측
DB : 먹구름과 동일한 Supabase 공유
토큰: .env의 DISCORD_TOKEN_WEIGHT 사용

실행:
    python bot_weight.py
"""
import os
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv
from utils.db import init_db
from utils.thread_helper import join_assigned_threads, join_if_mine

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN_WEIGHT")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!weight_", intents=intents)

_bot_ready = False


@bot.event
async def on_thread_create(thread: discord.Thread):
    await join_if_mine(bot, thread, "weight_thread_id")


@bot.event
async def on_ready():
    global _bot_ready
    if _bot_ready:
        print(f"[RECONNECT] {bot.user} 재연결됨 — 초기화 생략")
        return
    _bot_ready = True

    init_db()
    await bot.tree.sync()
    await join_assigned_threads(bot, "weight_thread_id")
    print(f"[체중관리봇] {bot.user} 로그인 완료")


@bot.event
async def on_error(event, *args, **kwargs):
    import traceback
    traceback.print_exc()

async def main():
    async with bot:
        await bot.load_extension("cogs.weight")
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
