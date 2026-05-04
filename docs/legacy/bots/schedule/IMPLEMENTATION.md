# 일정봇 — 전체 구현 코드

> Claude 세션에서 이 파일을 읽으면 `cogs/schedule.py`와 `bot_schedule.py`를 바로 구현할 수 있습니다.  
> 먼저 `schedule/DB.md`를 읽고 DB 마이그레이션을 `utils/db.py`에 적용한 후 구현하세요.

---

## bot_schedule.py

```python
"""
bot_schedule.py — 일정 전용 봇 진입점
"""
import os
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv
from utils.db import init_db

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN_SCHEDULE")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!schedule_", intents=intents)
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
    print(f"[일정봇] {bot.user} 로그인 완료")

@bot.event
async def on_error(event, *args, **kwargs):
    import traceback
    traceback.print_exc()

async def main():
    async with bot:
        await bot.load_extension("cogs.schedule")
        print("[일정봇] cogs.schedule 로드 완료")
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
```

---

## cogs/schedule.py

```python
"""
cogs/schedule.py — 일정 등록/알림/관리 기능

흐름:
  1. /일정등록 → ScheduleInputModal → GPT 파싱 → DB 저장 → 쓰레드 알림
  2. 5분 간격 스케줄러 → 알림 발송 + 반복 일정 자동 생성
  3. /일정목록 → 향후 30일 조회
  4. /일정삭제 → Select Menu → 삭제
"""
import os
import json
import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timedelta
from openai import AsyncOpenAI
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from utils.db import (
    get_user,
    create_schedule,
    get_upcoming_schedules,
    get_all_pending_schedules,
    mark_schedule_done,
    mark_schedule_notified,
    delete_schedule,
)

_client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])


# ──────────────────────────────────────────────
# GPT 날짜/시간 파싱
# ──────────────────────────────────────────────

async def parse_schedule_input(text: str) -> dict:
    """
    자연어 일정 텍스트 → {title, scheduled_at, is_repeat, repeat_rule}
    """
    today = datetime.now().strftime("%Y-%m-%d %H:%M")
    system_prompt = (
        f"오늘 날짜/시간: {today} (KST)\n"
        "일정 텍스트를 분석해서 JSON으로만 반환해:\n"
        "{\n"
        '  "title": "일정 제목",\n'
        '  "scheduled_at": "YYYY-MM-DDTHH:MM:SS",\n'
        '  "is_repeat": true/false,\n'
        '  "repeat_rule": "daily"/"weekly"/"monthly"/"weekday"/null\n'
        "}"
    )
    response = await _client.chat.completions.create(
        model="gpt-4o",
        max_tokens=200,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text},
        ],
    )
    raw = response.choices[0].message.content.strip()
    raw = raw.replace("```json", "").replace("```", "").strip()
    return json.loads(raw)


def _create_next_repeat(s: dict):
    """반복 일정의 다음 회차 자동 생성"""
    dt   = s["scheduled_at"]
    rule = s.get("repeat_rule", "weekly")

    if rule == "daily":
        next_dt = dt + timedelta(days=1)
    elif rule == "weekly":
        next_dt = dt + timedelta(weeks=1)
    elif rule == "monthly":
        month = dt.month % 12 + 1
        year  = dt.year + (1 if month == 1 else 0)
        next_dt = dt.replace(year=year, month=month)
    elif rule == "weekday":
        next_dt = dt + timedelta(days=1)
        while next_dt.weekday() >= 5:
            next_dt += timedelta(days=1)
    else:
        return

    create_schedule(
        user_id=s["user_id"],
        title=s["title"],
        scheduled_at=next_dt,
        is_repeat=True,
        repeat_rule=rule,
    )


# ──────────────────────────────────────────────
# 일정 등록 Modal
# ──────────────────────────────────────────────

class ScheduleInputModal(discord.ui.Modal, title="📅 일정 등록"):
    schedule_input = discord.ui.TextInput(
        label="언제 뭐 할 거야? 자유롭게 말해줘",
        placeholder=(
            "예: 내일 오전 10시 병원 예약\n"
            "예: 매주 월요일 오전 7시 운동\n"
            "예: 4월 20일 친구 생일 파티"
        ),
        style=discord.TextStyle.paragraph,
        max_length=200,
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            user_id = str(interaction.user.id)
            user    = get_user(user_id)
            if not user:
                await interaction.followup.send("❌ 등록된 유저가 아니야!", ephemeral=True)
                return

            text   = self.schedule_input.value.strip()
            parsed = await parse_schedule_input(text)

            title        = parsed["title"]
            scheduled_at = datetime.fromisoformat(parsed["scheduled_at"])
            is_repeat    = parsed.get("is_repeat", False)
            repeat_rule  = parsed.get("repeat_rule")

            schedule_id = create_schedule(user_id, title, scheduled_at, is_repeat, repeat_rule)

            dt_str     = scheduled_at.strftime("%Y년 %m월 %d일 %H:%M")
            repeat_str = {
                "daily": "매일", "weekly": "매주",
                "monthly": "매달", "weekday": "평일마다",
            }.get(repeat_rule or "", "")

            embed = discord.Embed(title="📅 일정 등록 완료", color=0x5865F2)
            embed.add_field(name="📌 일정", value=title, inline=False)
            embed.add_field(name="📆 날짜/시간", value=dt_str, inline=True)
            if repeat_str:
                embed.add_field(name="🔁 반복", value=repeat_str, inline=True)
            embed.set_footer(text=f"일정 ID: {schedule_id}")

            thread_id = user.get("schedule_thread_id") or user.get("thread_id")
            if thread_id:
                guild  = interaction.guild
                thread = guild.get_thread(int(thread_id))
                if thread:
                    await thread.send(embed=embed)

            await interaction.followup.send("✅ 일정이 등록됐어!", ephemeral=True)

        except Exception as e:
            import traceback; traceback.print_exc()
            await interaction.followup.send(f"❌ 오류: {e}", ephemeral=True)


# ──────────────────────────────────────────────
# Cog
# ──────────────────────────────────────────────

class ScheduleCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.scheduler = AsyncIOScheduler()
        self.scheduler.add_job(
            self._check_notifications,
            IntervalTrigger(minutes=5),
            id="schedule_notify",
            replace_existing=True,
        )
        self.scheduler.start()
        print("[ScheduleCog] 로드 완료")

    async def _check_notifications(self):
        """5분마다 알림 보낼 일정 체크"""
        schedules = get_all_pending_schedules()
        for s in schedules:
            try:
                thread_id = s.get("schedule_thread_id") or s.get("thread_id")
                if not thread_id:
                    continue

                thread = None
                for guild in self.bot.guilds:
                    thread = guild.get_thread(int(thread_id))
                    if thread:
                        break
                if not thread:
                    continue

                dt_str = s["scheduled_at"].strftime("%Y년 %m월 %d일 %H:%M")
                embed  = discord.Embed(
                    title="⏰ 일정 알림!",
                    description=f"**{s['title']}**\n{dt_str}",
                    color=0xFEE75C,
                )
                embed.set_footer(text="일정을 완료했으면 /일정목록에서 체크해줘!")
                await thread.send(embed=embed)

                mark_schedule_notified(s["schedule_id"])

                if s.get("is_repeat") and s.get("repeat_rule"):
                    _create_next_repeat(s)

            except Exception as e:
                print(f"[일정봇 알림 오류] {s.get('schedule_id')}: {e}")

    def cog_unload(self):
        self.scheduler.shutdown()

    @app_commands.command(name="일정등록", description="새 일정을 등록합니다.")
    async def schedule_add_cmd(self, interaction: discord.Interaction):
        await interaction.response.send_modal(ScheduleInputModal())

    @app_commands.command(name="일정목록", description="등록된 일정을 확인합니다.")
    async def schedule_list_cmd(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        user_id   = str(interaction.user.id)
        schedules = get_upcoming_schedules(user_id, days=30)

        if not schedules:
            await interaction.followup.send("등록된 일정이 없어! `/일정등록`으로 추가해봐 📅", ephemeral=True)
            return

        lines = []
        for s in schedules[:10]:
            dt_str  = s["scheduled_at"].strftime("%m/%d %H:%M")
            repeat  = " 🔁" if s.get("is_repeat") else ""
            lines.append(f"• `{dt_str}` {s['title']}{repeat}")

        embed = discord.Embed(
            title="📅 등록된 일정",
            description="\n".join(lines),
            color=0x5865F2,
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="일정삭제", description="등록된 일정을 삭제합니다.")
    async def schedule_delete_cmd(self, interaction: discord.Interaction):
        user_id   = str(interaction.user.id)
        schedules = get_upcoming_schedules(user_id, days=30)

        if not schedules:
            await interaction.response.send_message("삭제할 일정이 없어!", ephemeral=True)
            return

        options = [
            discord.SelectOption(
                label=f"{s['scheduled_at'].strftime('%m/%d %H:%M')} {s['title']}"[:100],
                value=str(s["schedule_id"]),
            )
            for s in schedules[:25]
        ]

        select = discord.ui.Select(placeholder="삭제할 일정 선택", options=options)

        async def select_callback(inter: discord.Interaction):
            sid     = int(inter.data["values"][0])
            deleted = delete_schedule(user_id, sid)
            await inter.response.send_message(
                "✅ 삭제했어!" if deleted else "❌ 삭제 실패", ephemeral=True
            )

        select.callback = select_callback
        view = discord.ui.View(timeout=120)
        view.add_item(select)
        await interaction.response.send_message("삭제할 일정을 선택해줘:", view=view, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(ScheduleCog(bot))
```
