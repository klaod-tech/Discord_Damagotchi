# 일정봇 (bot_schedule.py) 제작 로드맵

> last_updated: 2026-04-13 | 현재 버전: 📋 미구현

---

## 개요

유저가 할일과 일정을 Discord에 등록하면 지정 시간에 알림을 보내고,  
반복 패턴을 학습하여 시간 관리 인사이트를 제공한다.

---

## Phase 0 — 사전 준비

### 0-1. Discord Application 생성

- discord.com/developers → 새 Application 생성
- Bot 탭 → 토큰 발급
- `.env`에 `DISCORD_TOKEN_SCHEDULE` 추가

### 0-2. 온보딩 수정 — 일정봇 쓰레드 추가

**v4.0 채널 구조 전환 후**: 유저 전용 채널 안에 일정봇 쓰레드 생성.

```python
# cogs/onboarding.py — 채널 구조 전환 시 함께 추가

schedule_thread = await personal_channel.create_thread(
    name=f"📅 {name}의 일정표",
    auto_archive_duration=10080,   # 7일
    type=discord.ChannelType.public_thread
)
set_schedule_thread_id(user_id, str(schedule_thread.id))
```

### 0-3. users 테이블 컬럼 추가

```python
# utils/db.py init_db()
cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS schedule_thread_id TEXT")
```

### 0-4. schedules 테이블 생성

```python
# utils/db.py init_db()
cur.execute("""
    CREATE TABLE IF NOT EXISTS schedules (
        schedule_id  SERIAL PRIMARY KEY,
        user_id      TEXT REFERENCES users(user_id),
        title        TEXT NOT NULL,
        description  TEXT,
        scheduled_at TIMESTAMP NOT NULL,          -- KST 기준으로 저장
        repeat_type  TEXT DEFAULT 'none',          -- 'none' | 'daily' | 'weekly' | 'monthly'
        notified     BOOLEAN DEFAULT FALSE,
        completed    BOOLEAN DEFAULT FALSE,
        created_at   TIMESTAMP DEFAULT NOW()
    )
""")
```

---

## Phase 1 — 일정 등록 / 알림 (v3.5)

### 1-1. bot_schedule.py 구성

```python
# bot_schedule.py
import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN_SCHEDULE")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

COGS = ["cogs.schedule"]

@bot.event
async def on_ready():
    for cog in COGS:
        await bot.load_extension(cog)
    await bot.tree.sync()
    print(f"일정봇 로그인: {bot.user}")

async def main():
    async with bot:
        await bot.start(TOKEN)

import asyncio
asyncio.run(main())
```

### 1-2. cogs/schedule.py 구성

```python
# cogs/schedule.py
import discord
from discord.ext import commands
from discord import app_commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import pytz
from utils.db import get_user, create_schedule, get_pending_schedules, mark_schedule_notified

KST = pytz.timezone("Asia/Seoul")


class ScheduleInputModal(discord.ui.Modal, title="일정 등록"):
    title_input = discord.ui.TextInput(
        label="일정 제목",
        placeholder="예: 병원 예약, 팀 미팅",
        max_length=50,
        required=True
    )
    date_input = discord.ui.TextInput(
        label="날짜 (YYYY-MM-DD)",
        placeholder="예: 2026-04-20",
        max_length=10,
        required=True
    )
    time_input = discord.ui.TextInput(
        label="시간 (HH:MM)",
        placeholder="예: 14:30",
        max_length=5,
        required=True
    )
    repeat_input = discord.ui.TextInput(
        label="반복 (none / daily / weekly / monthly)",
        placeholder="반복 없으면 none",
        default="none",
        max_length=10,
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        user = get_user(str(interaction.user.id))
        if not user:
            await interaction.followup.send("먼저 온보딩을 완료해주세요.", ephemeral=True)
            return

        # 날짜/시간 파싱
        try:
            scheduled_dt = KST.localize(
                datetime.strptime(
                    f"{self.date_input.value} {self.time_input.value}",
                    "%Y-%m-%d %H:%M"
                )
            )
        except ValueError:
            await interaction.followup.send(
                "날짜/시간 형식이 잘못됐어요. 예: 2026-04-20 / 14:30",
                ephemeral=True
            )
            return

        repeat = str(self.repeat_input.value).strip().lower()
        if repeat not in ("none", "daily", "weekly", "monthly"):
            repeat = "none"

        schedule_id = create_schedule(
            user_id=user["user_id"],
            title=str(self.title_input.value),
            scheduled_at=scheduled_dt,
            repeat_type=repeat
        )

        # APScheduler에 알림 Job 등록
        register_schedule_job(schedule_id, scheduled_dt, user, interaction.guild)

        embed = discord.Embed(
            title="✅ 일정 등록 완료",
            description=f"**{self.title_input.value}**\n"
                        f"{scheduled_dt.strftime('%Y년 %m월 %d일 %H:%M')}",
            color=0x57F287
        )
        if repeat != "none":
            embed.set_footer(text=f"반복: {repeat}")

        # 일정 쓰레드에 알림
        thread_id = user.get("schedule_thread_id") or user.get("thread_id")
        if thread_id:
            thread = interaction.guild.get_thread(int(thread_id))
            if thread:
                await thread.send(embed=embed)

        await interaction.followup.send("일정이 등록됐어요!", ephemeral=True)


class ScheduleCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.scheduler = AsyncIOScheduler(timezone=KST)
        self.scheduler.start()

    @app_commands.command(name="일정등록", description="새 일정을 등록해요")
    async def add_schedule(self, interaction: discord.Interaction):
        await interaction.response.send_modal(ScheduleInputModal())

    @app_commands.command(name="일정목록", description="오늘과 이번 주 일정을 확인해요")
    async def list_schedules(self, interaction: discord.Interaction):
        user = get_user(str(interaction.user.id))
        schedules = get_upcoming_schedules(user["user_id"], days=7)

        if not schedules:
            await interaction.response.send_message("등록된 일정이 없어요.", ephemeral=True)
            return

        embed = discord.Embed(title="📅 이번 주 일정", color=0x5865F2)
        for s in schedules[:10]:
            dt_str = s["scheduled_at"].strftime("%m/%d %H:%M")
            status = "✅" if s["completed"] else "⏰"
            embed.add_field(
                name=f"{status} {s['title']}",
                value=dt_str,
                inline=False
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="일정완료", description="일정을 완료 처리해요")
    async def complete_schedule(self, interaction: discord.Interaction):
        user = get_user(str(interaction.user.id))
        pending = get_pending_schedules(user["user_id"])

        if not pending:
            await interaction.response.send_message("완료할 일정이 없어요.", ephemeral=True)
            return

        await interaction.response.send_message(
            "완료할 일정을 선택해주세요:",
            view=ScheduleCompleteView(pending, user["user_id"]),
            ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(ScheduleCog(bot))
```

### 1-3. 알림 Job 등록 함수

```python
# cogs/schedule.py 내 헬퍼

def register_schedule_job(schedule_id: int, scheduled_dt: datetime, user: dict, guild):
    repeat = user_schedule.get("repeat_type", "none")

    async def notify():
        thread_id = user.get("schedule_thread_id") or user.get("thread_id")
        if not thread_id: return

        thread = guild.get_thread(int(thread_id))
        if not thread: return

        embed = discord.Embed(
            title="⏰ 일정 알림",
            description=f"**{user_schedule['title']}** 시간이에요!",
            color=0xFEE75C
        )
        await thread.send(embed=embed)
        mark_schedule_notified(schedule_id)

        # 반복 처리
        if repeat == "daily":
            next_dt = scheduled_dt + timedelta(days=1)
            new_id = create_schedule(..., scheduled_at=next_dt)
            register_schedule_job(new_id, next_dt, user, guild)
        elif repeat == "weekly":
            next_dt = scheduled_dt + timedelta(weeks=1)
            ...

    if repeat == "none":
        scheduler.add_job(notify, DateTrigger(run_date=scheduled_dt), id=f"schedule_{schedule_id}")
    else:
        # 첫 번째 발화는 DateTrigger
        scheduler.add_job(notify, DateTrigger(run_date=scheduled_dt), id=f"schedule_{schedule_id}")
```

### 1-4. DB 함수 추가 (utils/db.py)

```python
def create_schedule(user_id, title, scheduled_at, repeat_type="none", description=None):
    cur.execute("""
        INSERT INTO schedules (user_id, title, description, scheduled_at, repeat_type)
        VALUES (%s, %s, %s, %s, %s) RETURNING schedule_id
    """, (user_id, title, description, scheduled_at, repeat_type))
    return cur.fetchone()[0]

def get_upcoming_schedules(user_id, days=7):
    from datetime import date, timedelta
    end = datetime.now(KST) + timedelta(days=days)
    cur.execute("""
        SELECT * FROM schedules
        WHERE user_id = %s
          AND scheduled_at <= %s
          AND completed = FALSE
        ORDER BY scheduled_at
    """, (user_id, end))
    return cur.fetchall()

def get_pending_schedules(user_id):
    cur.execute("""
        SELECT * FROM schedules
        WHERE user_id = %s AND notified = FALSE AND completed = FALSE
        ORDER BY scheduled_at
    """, (user_id,))
    return cur.fetchall()

def mark_schedule_notified(schedule_id):
    cur.execute("UPDATE schedules SET notified = TRUE WHERE schedule_id = %s", (schedule_id,))

def mark_schedule_completed(schedule_id):
    cur.execute("UPDATE schedules SET completed = TRUE WHERE schedule_id = %s", (schedule_id,))

def set_schedule_thread_id(user_id, thread_id):
    cur.execute("UPDATE users SET schedule_thread_id = %s WHERE user_id = %s", (thread_id, user_id))
```

---

## Phase 2 — 일정 관리 UI (v3.5)

### 2-1. 일정 목록 + 완료 체크 View

```python
class ScheduleCompleteView(discord.ui.View):
    def __init__(self, schedules, user_id):
        super().__init__()
        options = [
            discord.SelectOption(
                label=s["title"][:25],
                description=s["scheduled_at"].strftime("%m/%d %H:%M"),
                value=str(s["schedule_id"])
            )
            for s in schedules[:25]
        ]
        select = discord.ui.Select(placeholder="완료할 일정 선택", options=options)

        async def select_callback(interaction):
            schedule_id = int(select.values[0])
            mark_schedule_completed(schedule_id)
            await interaction.response.send_message("일정을 완료했어요! ✅", ephemeral=True)

        select.callback = select_callback
        self.add_item(select)
```

### 2-2. 일정 취소 커맨드

```python
@app_commands.command(name="일정취소", description="등록된 일정을 취소해요")
async def cancel_schedule(self, interaction: discord.Interaction):
    user = get_user(str(interaction.user.id))
    schedules = get_upcoming_schedules(user["user_id"], days=30)

    view = ScheduleCancelView(schedules, user["user_id"])
    await interaction.response.send_message("취소할 일정을 선택해주세요:", view=view, ephemeral=True)
```

### 2-3. 오늘 일정 자동 아침 브리핑

```python
# cogs/schedule.py APScheduler

@scheduler.scheduled_job('cron', hour=8, minute=0, timezone='Asia/Seoul')
async def morning_briefing():
    """오늘 일정이 있는 유저에게 아침 8시 브리핑"""
    users = get_all_users()
    for user in users:
        today_schedules = get_today_schedules(user["user_id"])
        if not today_schedules: continue

        items = "\n".join([f"• {s['title']} — {s['scheduled_at'].strftime('%H:%M')}" for s in today_schedules])
        embed = discord.Embed(
            title=f"📅 오늘 {user['tamagotchi_name']}의 일정",
            description=items,
            color=0x5865F2
        )

        thread_id = user.get("schedule_thread_id") or user.get("thread_id")
        if thread_id:
            thread = guild.get_thread(int(thread_id))
            if thread:
                await thread.send(embed=embed)
```

---

## Phase 3 — 일정 패턴 분석 (v4.0)

### 3-1. 완료율 분석

```python
def get_schedule_adherence(user_id: str, days: int = 30) -> dict:
    """
    최근 30일간 일정 완료율 분석
    반환: {"total": 15, "completed": 12, "rate": 0.8, "best_day": "월요일"}
    """
    cur.execute("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN completed THEN 1 ELSE 0 END) as completed,
            EXTRACT(DOW FROM scheduled_at) as day_of_week
        FROM schedules
        WHERE user_id = %s
          AND scheduled_at >= NOW() - INTERVAL '%s days'
        GROUP BY day_of_week
        ORDER BY completed DESC
    """, (user_id, days))
    ...
```

### 3-2. 시간대별 완료율 분석

```python
def get_best_schedule_time(user_id: str) -> str:
    """
    어떤 시간대에 등록한 일정이 가장 잘 완료되는지 분석
    반환: "오전 10시~12시 일정 완료율이 가장 높아요"
    """
```

### 3-3. 인사이트 슬래시 커맨드

```python
@app_commands.command(name="일정인사이트", description="나의 일정 패턴을 분석해요")
async def schedule_insight(self, interaction):
    user = get_user(str(interaction.user.id))
    adherence = get_schedule_adherence(user["user_id"])
    best_time = get_best_schedule_time(user["user_id"])

    embed = discord.Embed(title="📊 일정 패턴 분석", color=0x5865F2)
    embed.add_field(name="완료율", value=f"{adherence['rate']*100:.0f}%", inline=True)
    embed.add_field(name="이번 달 완료", value=f"{adherence['completed']}/{adherence['total']}건", inline=True)
    embed.add_field(name="추천 시간대", value=best_time, inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)
```

---

## Phase 4 — 오케스트레이터 연동 (v4.0)

### 4-1. 태스크 큐 폴링

```python
# 먹구름봇이 "내일 제주도 가" 같은 미래 일정 언급 감지
# → task_queue에 {'bot_target': 'schedule', 'payload': '{"title": "제주도", "hint_date": "내일"}'} 삽입
# 일정봇이 30초 폴링 → GPT로 날짜 파싱 → 일정 등록 유도 Embed 전송

@scheduler.scheduled_job('interval', seconds=30)
async def poll_task_queue():
    tasks = get_pending_tasks(bot_target='schedule')
    for task in tasks:
        payload = json.loads(task['payload'])
        # GPT로 hint_date → 실제 날짜 변환
        parsed_date = await parse_date_hint(payload.get("hint_date", ""))
        # 유저에게 일정 등록 유도
        await send_schedule_suggestion(task['user_id'], payload['title'], parsed_date)
        mark_task_done(task['task_id'])
```

### 4-2. 날짜 힌트 파싱

```python
async def parse_date_hint(hint: str) -> str:
    """
    "내일" → "2026-04-14"
    "다음 주 월요일" → "2026-04-20"
    """
    prompt = f"""
    오늘은 {datetime.now(KST).strftime('%Y-%m-%d')}입니다.
    "{hint}"는 어떤 날짜인가요? YYYY-MM-DD 형식으로만 답하세요.
    """
    ...
```

---

## DB 테이블

```sql
schedules (
  schedule_id  SERIAL PRIMARY KEY,
  user_id      TEXT REFERENCES users(user_id),
  title        TEXT NOT NULL,
  description  TEXT,
  scheduled_at TIMESTAMP NOT NULL,
  repeat_type  TEXT DEFAULT 'none',     -- 'none' | 'daily' | 'weekly' | 'monthly'
  notified     BOOLEAN DEFAULT FALSE,
  completed    BOOLEAN DEFAULT FALSE,
  created_at   TIMESTAMP DEFAULT NOW()
)

-- users 컬럼 추가
users.schedule_thread_id TEXT
```

---

## 환경변수

| 변수명 | 상태 | 설명 |
|--------|------|------|
| `DISCORD_TOKEN_SCHEDULE` | 📋 발급 필요 | 일정봇 토큰 |

---

## 제작 순서 요약

```
Step 0 — Discord Application 생성, DISCORD_TOKEN_SCHEDULE 발급
Step 0 — cogs/onboarding.py에 schedule_thread 생성 추가
Step 0 — users.schedule_thread_id 컬럼 마이그레이션
Step 0 — schedules 테이블 생성 (init_db)
Step 0 — utils/db.py schedule CRUD 함수 추가
Step 1 — bot_schedule.py 기본 구조 작성
Step 1 — cogs/schedule.py ScheduleInputModal 구현
Step 1 — APScheduler DateTrigger 알림 Job 등록
Step 1 — /일정등록 슬래시 커맨드 테스트
Step 2 — /일정목록 슬래시 커맨드
Step 2 — /일정완료 슬래시 커맨드 + Select View
Step 2 — /일정취소 슬래시 커맨드
Step 2 — 아침 8시 브리핑 APScheduler
Step 3 — 완료율/시간대 분석 쿼리
Step 3 — /일정인사이트 슬래시 커맨드
Step 4 — 태스크 큐 폴링 (오케스트레이터 연동)
Step 4 — 날짜 힌트 GPT 파싱
```
