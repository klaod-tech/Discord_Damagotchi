"""
cogs/scheduler.py — 오후 10시 칼로리 자동 판정
(날씨 스케줄러는 cogs/weather.py에서 별도 관리)
"""
import discord
from discord.ext import commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import date
from utils.db import get_all_users, get_tamagotchi, get_meals_by_date, get_calories_by_date
from utils.embed import _send_daily_analysis


class SchedulerCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.scheduler = AsyncIOScheduler()
        self._setup_jobs()
        self.scheduler.start()
        print("[스케줄러] 시작 완료")

    def _setup_jobs(self):
        # 오후 10시 — 당일 칼로리 판정
        self.scheduler.add_job(
            self._nightly_analysis,
            CronTrigger(hour=22, minute=0),
            id="nightly_analysis",
            replace_existing=True,
        )

    async def _nightly_analysis(self):
        """오후 10시 — 전체 유저 당일 칼로리 판정"""
        print("[스케줄러] 오후 10시 칼로리 판정 시작")
        today = date.today()
        users = get_all_users()

        for user in users:
            try:
                user_id   = str(user.get("user_id", ""))
                thread_id = user.get("thread_id")
                if not thread_id:
                    continue

                # 쓰레드 조회
                thread = None
                for guild in self.bot.guilds:
                    thread = guild.get_thread(int(thread_id))
                    if thread:
                        break

                if not thread:
                    continue

                tama = get_tamagotchi(user_id)
                if not tama:
                    continue

                meals     = get_meals_by_date(user_id, today)
                total_cal = get_calories_by_date(user_id, today)
                target_cal = user.get("daily_cal_target") or 2000

                # 식사 기록이 없으면 알림만
                if not meals:
                    await thread.send(
                        "🌙 오늘 식사 기록이 없어! 밥은 먹었어? 🥺\n"
                        "[🍽️ 식사 입력] 버튼으로 입력해줘!"
                    )
                    continue

                # 칼로리 판정 + 분석 전송
                await _send_daily_analysis(
                    thread, user, tama, meals, total_cal, target_cal, today
                )

            except Exception as e:
                print(f"[스케줄러 오류] user_id={user.get('user_id')}: {e}")
                import traceback
                traceback.print_exc()

    def cog_unload(self):
        self.scheduler.shutdown()


async def setup(bot: commands.Bot):
    await bot.add_cog(SchedulerCog(bot))
