"""
cogs/scheduler.py — 전체 스케줄 관리
  1. 오후 10시 — 당일 칼로리 자동 판정
  2. 매 시간 — hunger 시간 감소 (-5/시간)
  3. 유저별 식사 알림 3단계:
       식사시간 -30분 → 쓰레드 알림 메시지
       식사시간 정각  → Embed upset.png 교체 (미입력 시)
       식사시간 +1시간 → 추가 대사 (미입력 시)
"""
import discord
from discord.ext import commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import date, datetime
from utils.db import (
    get_all_users, get_tamagotchi, get_meals_by_date,
    get_calories_by_date, update_tamagotchi, get_user,
    has_meal_type_on_date,
)
from utils.embed import _send_daily_analysis, create_or_update_embed
from utils.gpt import generate_comment
from utils.ml import retrain_all_users


MEAL_TYPES = [
    ("아침", "breakfast_time"),
    ("점심", "lunch_time"),
    ("저녁", "dinner_time"),
]


class SchedulerCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.scheduler = AsyncIOScheduler()
        self._setup_fixed_jobs()
        self.scheduler.start()
        print("[스케줄러] 시작 완료")

    # ──────────────────────────────────────────────
    # 고정 Job (모든 유저 공통)
    # ──────────────────────────────────────────────

    def _setup_fixed_jobs(self):
        # 오후 10시 — 당일 칼로리 판정
        self.scheduler.add_job(
            self._nightly_analysis,
            CronTrigger(hour=22, minute=0),
            id="nightly_analysis",
            replace_existing=True,
        )
        # 매 시간 정각 — hunger 감소
        self.scheduler.add_job(
            self._hourly_hunger_decay,
            CronTrigger(minute=0),
            id="hourly_hunger_decay",
            replace_existing=True,
        )
        # 매주 일요일 03:00 — ML 칼로리 모델 재학습
        self.scheduler.add_job(
            self._weekly_ml_retrain,
            CronTrigger(day_of_week="sun", hour=3, minute=0),
            id="weekly_ml_retrain",
            replace_existing=True,
        )

    # ──────────────────────────────────────────────
    # 유저별 식사 알림 Job 등록 / 재등록
    # ──────────────────────────────────────────────

    def register_meal_jobs(self, user_id: str):
        """
        유저의 breakfast/lunch/dinner_time 기준으로
        -30분 알림, 정각 upset, +1시간 추가 대사 Job 등록.
        온보딩 및 시간 설정 변경 시 호출.
        """
        user = get_user(user_id)
        if not user:
            return

        for meal_label, time_field in MEAL_TYPES:
            time_str = user.get(time_field, "")
            if not time_str:
                continue
            try:
                h, m = map(int, time_str.split(":"))
            except ValueError:
                continue

            # -30분
            pre_h, pre_m = (h, m - 30) if m >= 30 else (h - 1, m + 30)
            if pre_h < 0:
                pre_h = 23

            # +1시간
            post_h = (h + 1) % 24
            post_m = m

            self.scheduler.add_job(
                self._meal_reminder,
                CronTrigger(hour=pre_h, minute=pre_m),
                id=f"meal_pre_{user_id}_{meal_label}",
                replace_existing=True,
                kwargs={"user_id": user_id, "meal_label": meal_label},
            )
            self.scheduler.add_job(
                self._meal_upset,
                CronTrigger(hour=h, minute=m),
                id=f"meal_upset_{user_id}_{meal_label}",
                replace_existing=True,
                kwargs={"user_id": user_id, "meal_label": meal_label},
            )
            self.scheduler.add_job(
                self._meal_late,
                CronTrigger(hour=post_h, minute=post_m),
                id=f"meal_late_{user_id}_{meal_label}",
                replace_existing=True,
                kwargs={"user_id": user_id, "meal_label": meal_label},
            )

        print(f"[스케줄러] {user_id} 식사 알림 Job 등록 완료")

    def register_all_users(self):
        """봇 시작 시 전체 유저 식사 알림 Job 일괄 등록"""
        users = get_all_users()
        for user in users:
            uid = str(user.get("user_id", ""))
            if uid:
                self.register_meal_jobs(uid)
        print(f"[스케줄러] 전체 유저 ({len(users)}명) 식사 알림 등록 완료")

    # ──────────────────────────────────────────────
    # 식사 알림 핸들러
    # ──────────────────────────────────────────────

    async def _meal_reminder(self, user_id: str, meal_label: str):
        """식사시간 -30분 — 쓰레드에 배고픔 예고 메시지"""
        thread = await self._get_thread(user_id)
        if not thread:
            return
        user = get_user(user_id)
        if not user:
            return
        name = user.get("tamagotchi_name", "")
        await thread.send(f"🍽️ {name}이(가) 슬슬 배가 고파지고 있어!")

    async def _meal_upset(self, user_id: str, meal_label: str):
        """식사시간 정각 — 미입력 시 upset.png 교체 + 대사"""
        if has_meal_type_on_date(user_id, meal_label, date.today()):
            return  # 이미 먹었으면 패스

        thread = await self._get_thread(user_id)
        if not thread:
            return
        user = get_user(user_id)
        tama = get_tamagotchi(user_id)
        if not user or not tama:
            return

        comment = await generate_comment(
            context=f"{meal_label} 시간인데 밥을 안 줬어. 배고파서 짧게 말해줘!",
            user=user,
            today_calories=0,
            recent_meals="없음",
            weather_info=None,
        )
        await create_or_update_embed(thread, user, tama, comment)

    async def _meal_late(self, user_id: str, meal_label: str):
        """식사시간 +1시간 — 미입력 시 추가 대사"""
        if has_meal_type_on_date(user_id, meal_label, date.today()):
            return  # 이미 먹었으면 패스

        thread = await self._get_thread(user_id)
        if not thread:
            return
        user = get_user(user_id)
        tama = get_tamagotchi(user_id)
        if not user or not tama:
            return

        comment = await generate_comment(
            context=f"{meal_label} 시간이 1시간 넘게 지났는데 아직 밥을 못 먹었어. 슬프고 걱정돼서 짧게 말해줘.",
            user=user,
            today_calories=0,
            recent_meals="없음",
            weather_info=None,
        )
        await thread.send(f"😢 *{comment}*")

    # ──────────────────────────────────────────────
    # Hunger 시간 감소
    # ──────────────────────────────────────────────

    async def _hourly_hunger_decay(self):
        """매 시간 — 전체 유저 hunger -5"""
        users = get_all_users()
        for user in users:
            try:
                uid = str(user.get("user_id", ""))
                if not uid:
                    continue
                tama = get_tamagotchi(uid)
                if not tama:
                    continue
                current = tama.get("hunger", 50)
                new_hunger = max(0, current - 5)
                update_tamagotchi(uid, {"hunger": new_hunger})
            except Exception as e:
                print(f"[hunger decay 오류] {user.get('user_id')}: {e}")

    # ──────────────────────────────────────────────
    # 오후 10시 칼로리 판정
    # ──────────────────────────────────────────────

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

                thread = await self._get_thread(user_id)
                if not thread:
                    continue

                tama = get_tamagotchi(user_id)
                if not tama:
                    continue

                meals     = get_meals_by_date(user_id, today)
                total_cal = get_calories_by_date(user_id, today)
                target_cal = user.get("daily_cal_target") or 2000

                if not meals:
                    await thread.send(
                        "🌙 오늘 식사 기록이 없어! 밥은 먹었어? 🥺\n"
                        "[🍽️ 식사 입력] 버튼으로 입력해줘!"
                    )
                    continue

                await _send_daily_analysis(
                    thread, user, tama, meals, total_cal, target_cal, today
                )

            except Exception as e:
                print(f"[스케줄러 오류] user_id={user.get('user_id')}: {e}")
                import traceback
                traceback.print_exc()

    # ──────────────────────────────────────────────
    # ML 재학습
    # ──────────────────────────────────────────────

    async def _weekly_ml_retrain(self):
        """매주 일요일 03:00 — 전체 유저 칼로리 보정 모델 재학습"""
        print("[스케줄러] ML 재학습 시작")
        try:
            retrain_all_users()
            print("[스케줄러] ML 재학습 완료")
        except Exception as e:
            print(f"[스케줄러] ML 재학습 오류: {e}")
            import traceback
            traceback.print_exc()

    # ──────────────────────────────────────────────
    # 헬퍼
    # ──────────────────────────────────────────────

    async def _get_thread(self, user_id: str) -> discord.Thread | None:
        user = get_user(user_id)
        if not user or not user.get("thread_id"):
            return None
        thread_id = int(user["thread_id"])
        for guild in self.bot.guilds:
            thread = guild.get_thread(thread_id)
            if thread:
                return thread
        return None

    def cog_unload(self):
        self.scheduler.shutdown()


async def setup(bot: commands.Bot):
    await bot.add_cog(SchedulerCog(bot))
