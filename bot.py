import os
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv
from utils.db import init_db
from utils.embed import MainView
from cogs.onboarding import StartView

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
TAMAGOTCHI_CHANNEL_ID = int(os.getenv("TAMAGOTCHI_CHANNEL_ID", "0"))

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

COGS = [
    "cogs.onboarding",
    "cogs.summary",
    "cogs.settings",
    "cogs.time_settings",
    "cogs.scheduler",
    "cogs.weather",
    "cogs.meal",
    "cogs.weight",
]

# 봇이 디스코드에 로그인 완료됐을 때, 딱 한번만 작동하는 코드
@bot.event
async def on_ready():
    init_db()
    # 영구 View 등록 (봇 재시작 후에도 버튼 동작)
    bot.add_view(MainView())
    bot.add_view(StartView())   # 시작하기 버튼 영구 등록
    await bot.tree.sync()
    print(f"[✅] {bot.user} 로그인 완료 — 슬래시 커맨드 동기화 완료")

# 에러 로깅
@bot.event
async def on_error(event, *args, **kwargs):
    import traceback
    traceback.print_exc()

# 슬래시 커맨드 수동 동기화 (개발 중 코드 변경 후 사용)
@bot.command(name="sync")
@commands.is_owner()
async def force_sync(ctx):
    synced = await bot.tree.sync()
    await ctx.send(f"커맨드 {len(synced)}개 동기화 완료")

# 서버 최초 설정 — #다마고치 채널에 시작 버튼 고정 메시지 전송
@bot.command(name="setup")
@commands.has_permissions(administrator=True)
async def setup(ctx: commands.Context):
    channel = bot.get_channel(TAMAGOTCHI_CHANNEL_ID)
    if channel is None:
        await ctx.send("❌ TAMAGOTCHI_CHANNEL_ID를 확인해주세요.")
        return

    embed = discord.Embed(
        title="🌧️ 먹구름에 오신 걸 환영해요!",
        description=(
            "먹구름과 함께 건강한 식습관을 만들어보세요.\n\n"
            "아래 버튼을 눌러 나만의 캐릭터를 만들어보세요! 👇"
        ),
        color=discord.Color.from_rgb(255, 220, 120),
    )
    await channel.send(embed=embed, view=StartView())
    await ctx.send("✅ 고정 메시지를 전송했어요!", delete_after=5)

@bot.command(name="소환")
async def recall_embed(ctx: commands.Context):
    from utils.db import get_user, get_tamagotchi, get_latest_weather, update_tamagotchi
    from utils.gpt import generate_comment
    from utils.embed import create_or_update_embed

    user_id = str(ctx.author.id)
    user = get_user(user_id)

    if not user or not user.get("thread_id"):
        await ctx.send("❌ 먼저 다마고치를 등록해줘!", delete_after=5)
        return

    thread_id = user.get("thread_id")
    thread = ctx.guild.get_thread(int(thread_id))

    if not thread:
        await ctx.send("❌ 쓰레드를 찾을 수 없어!", delete_after=5)
        return

    tama = get_tamagotchi(user_id)
    weather = get_latest_weather(user_id)

    comment = await generate_comment(
        context="다마고치를 소환했어! 반갑게 인사해줘.",
        user=user,
        today_calories=0,
        recent_meals="없음",
        weather_info=weather,
    )

    # embed_message_id 초기화해서 새 메시지로 강제 생성
    update_tamagotchi(user_id, {"embed_message_id": None})
    tama["embed_message_id"] = None

    await create_or_update_embed(thread, user, tama, comment, weather=weather)
    await ctx.send(f"✅ {thread.mention} 에 소환했어!", delete_after=5)

# 봇 실행 — Cog 로드 후 디스코드 연결 시작
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