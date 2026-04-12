"""
bot_mail.py — 메일 전용 봇 진입점

역할: 네이버 메일 1분 폴링 → Discord 스레드 알림
DB : 먹구름과 동일한 Supabase 공유
토큰: .env의 MAIL_BOT_TOKEN 사용

실행:
    python bot_mail.py
"""
import os
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv
from utils.db import init_db

load_dotenv()

MAIL_BOT_TOKEN = os.getenv("DISCORD_TOKEN_EMAIL")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!mail_", intents=intents)

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
    print(f"[메일봇] {bot.user} 로그인 완료 — 1분 폴링 시작")

@bot.event
async def on_error(event, *args, **kwargs):
    import traceback
    traceback.print_exc()

async def main():
    async with bot:
        try:
            await bot.load_extension("cogs.email_monitor")
            print("[COG] email_monitor 로드 완료")
        except Exception as e:
            print(f"[COG ERROR] email_monitor: {e}")
        await bot.start(MAIL_BOT_TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
