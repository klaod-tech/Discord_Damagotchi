# 일정봇 개발 가이드 — Claude 전용

> **이 파일만 읽으면 일정봇을 처음부터 완전히 구현할 수 있습니다.**  
> 공통 참조: `01_ARCHITECTURE.md`, `02_SHARED_DB.md`, `03_SHARED_UTILS.md`

---

## 1. 봇 기본 정보

| 항목 | 내용 |
|------|------|
| 봇 파일 | `bot_schedule.py` |
| 토큰 환경변수 | `DISCORD_TOKEN_SCHEDULE` |
| 커맨드 prefix | `!schedule_` |
| 담당 Cog | `cogs/schedule.py` → `ScheduleCog` (신규 생성) |
| 담당 쓰레드 | `users.schedule_thread_id` (없으면 `thread_id` fallback) |
| 담당 DB 테이블 | `schedule_log` (신규 생성 필요) |
| 현재 상태 | 📋 구현 예정 — 이 문서가 스펙 |

---

## 2. 역할 및 범위

### 이 봇이 하는 것
- 일정 등록 (날짜/시간/제목/반복 여부)
- 일정 D-day 알림 (APScheduler — 등록 시간에 알림)
- 일정 목록 조회
- 일정 완료 체크
- 반복 일정 패턴 학습 (ML)

### 이 봇이 하지 않는 것
- 날씨봇/식사봇과 연계 일정 (예: "제주도 여행 → 날씨봇 자동 조회") — 향후 오케스트레이터에서 처리
- 식사 계획 → 식사봇 담당

---

## 3. 신규 구현 필요 항목

### 3-1. DB 마이그레이션 (utils/db.py에 추가)

```python
# init_db() 내에 추가

# schedule_thread_id 컬럼
cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS schedule_thread_id TEXT")

# schedule_log 테이블
cur.execute("""
    CREATE TABLE IF NOT EXISTS schedule_log (
        schedule_id   SERIAL PRIMARY KEY,
        user_id       TEXT REFERENCES users(user_id) ON DELETE CASCADE,
        title         TEXT NOT NULL,
        scheduled_at  TIMESTAMP NOT NULL,
        is_repeat     BOOLEAN DEFAULT FALSE,
        repeat_rule   TEXT,          -- 'daily' / 'weekly' / 'monthly' / 'weekday' / 없음
        is_done       BOOLEAN DEFAULT FALSE,
        notified      BOOLEAN DEFAULT FALSE,
        created_at    TIMESTAMP DEFAULT NOW()
    )
""")
```

### 3-2. DB 함수 추가 (utils/db.py에 추가)

```python
def set_schedule_thread_id(user_id: str, thread_id: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET schedule_thread_id = %s WHERE user_id = %s",
        (thread_id, user_id),
    )
    conn.commit()
    cur.close()
    conn.close()

def create_schedule(user_id: str, title: str, scheduled_at, is_repeat: bool = False, repeat_rule: str = None) -> int:
    """일정 등록. 생성된 schedule_id 반환."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO schedule_log (user_id, title, scheduled_at, is_repeat, repeat_rule)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING schedule_id
    """, (user_id, title, scheduled_at, is_repeat, repeat_rule))
    row = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return row["schedule_id"]

def get_upcoming_schedules(user_id: str, days: int = 7) -> list:
    """향후 N일 내 일정 조회"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM schedule_log
        WHERE user_id = %s
          AND is_done = FALSE
          AND scheduled_at BETWEEN NOW() AND NOW() + INTERVAL '%s days'
        ORDER BY scheduled_at ASC
    """, (user_id, days))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def get_all_pending_schedules() -> list:
    """알림 보내야 할 전체 유저 일정 (스케줄러용)"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT s.*, u.schedule_thread_id, u.thread_id
        FROM schedule_log s
        JOIN users u ON s.user_id = u.user_id
        WHERE s.is_done = FALSE
          AND s.notified = FALSE
          AND s.scheduled_at <= NOW() + INTERVAL '10 minutes'
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def mark_schedule_done(schedule_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE schedule_log SET is_done = TRUE WHERE schedule_id = %s", (schedule_id,))
    conn.commit()
    cur.close()
    conn.close()

def mark_schedule_notified(schedule_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE schedule_log SET notified = TRUE WHERE schedule_id = %s", (schedule_id,))
    conn.commit()
    cur.close()
    conn.close()

def delete_schedule(user_id: str, schedule_id: int) -> bool:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM schedule_log WHERE schedule_id = %s AND user_id = %s RETURNING schedule_id",
        (schedule_id, user_id),
    )
    deleted = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return deleted is not None
```

### 3-3. 온보딩 추가 (cogs/onboarding.py에 추가)

```python
# set_schedule_thread_id import 추가
from utils.db import (..., set_schedule_thread_id)

# OnboardingModal.on_submit() 내에 추가:
schedule_thread = await channel.create_thread(
    name=f"📅 {interaction.user.display_name}의 일정",
    auto_archive_duration=10080,
    invitable=False,
)
set_schedule_thread_id(user_id, str(schedule_thread.id))
await schedule_thread.send(
    f"📅 안녕, {interaction.user.mention}!\n"
    f"여기는 **일정 전용** 쓰레드야.\n"
    f"`/일정등록` 명령어로 일정을 추가하면 알림을 보내줄게!\n"
    f"`/일정목록` 으로 등록된 일정을 확인할 수 있어."
)
```

---

## 4. cogs/schedule.py 구현 스펙

### 4-1. 파일 구조

```
cogs/schedule.py
  ├── parse_schedule_input(text: str) -> dict   # GPT 날짜/시간 파싱
  ├── ScheduleInputModal (Modal)
  │   └── on_submit: 파싱 → DB 저장 → Job 등록 → Embed 전송
  ├── ScheduleListView (View)                    # 일정 목록 + 완료 체크
  ├── ScheduleDeleteSelect (Select)              # 일정 삭제
  └── ScheduleCog (Cog)
        ├── APScheduler: 5분마다 알림 체크
        └── slash commands: /일정등록, /일정목록, /일정삭제
```

### 4-2. GPT 날짜/시간 파싱

```python
async def parse_schedule_input(text: str) -> dict:
    """
    자연어 일정 파싱.
    반환: {
        "title": str,
        "scheduled_at": str,   # ISO 8601 (KST 기준)
        "is_repeat": bool,
        "repeat_rule": str | None,  # "daily"/"weekly"/"monthly"/"weekday"/None
    }
    예시 입력 → 출력:
        "내일 오전 10시 병원 예약" → {"title": "병원 예약", "scheduled_at": "2026-04-14T10:00:00", ...}
        "매주 월요일 운동" → {"title": "운동", "is_repeat": True, "repeat_rule": "weekly", ...}
    """
    import os, json
    from openai import AsyncOpenAI
    from datetime import datetime

    client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])
    today = datetime.now().strftime("%Y-%m-%d %H:%M")

    system_prompt = (
        f"오늘 날짜/시간: {today} (KST)\n"
        "일정 텍스트를 분석해서 JSON으로 반환해. JSON 외 텍스트 없음.\n"
        "{\n"
        '  "title": "일정 제목",\n'
        '  "scheduled_at": "YYYY-MM-DDTHH:MM:SS",\n'
        '  "is_repeat": true/false,\n'
        '  "repeat_rule": "daily"/"weekly"/"monthly"/"weekday"/null\n'
        "}"
    )

    response = await client.chat.completions.create(
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
```

### 4-3. ScheduleInputModal

```python
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
            user = get_user(user_id)
            if not user:
                await interaction.followup.send("❌ 등록된 유저가 아니야!", ephemeral=True)
                return

            text = self.schedule_input.value.strip()

            # GPT 파싱
            parsed = await parse_schedule_input(text)
            title        = parsed["title"]
            scheduled_at = parsed["scheduled_at"]
            is_repeat    = parsed.get("is_repeat", False)
            repeat_rule  = parsed.get("repeat_rule")

            # DB 저장
            from datetime import datetime
            dt = datetime.fromisoformat(scheduled_at)
            schedule_id = create_schedule(user_id, title, dt, is_repeat, repeat_rule)

            # 날짜 포맷
            dt_str = dt.strftime("%Y년 %m월 %d일 %H:%M")
            repeat_str = {
                "daily": "매일", "weekly": "매주",
                "monthly": "매달", "weekday": "평일마다",
            }.get(repeat_rule, "") if is_repeat else ""

            embed = discord.Embed(
                title="📅 일정 등록 완료",
                color=0x5865F2,
            )
            embed.add_field(name="📌 일정", value=title, inline=False)
            embed.add_field(name="📆 날짜/시간", value=dt_str, inline=True)
            if repeat_str:
                embed.add_field(name="🔁 반복", value=repeat_str, inline=True)
            embed.set_footer(text=f"일정 ID: {schedule_id}")

            # 일정 전용 쓰레드에 전송
            thread_id = user.get("schedule_thread_id") or user.get("thread_id")
            if thread_id:
                guild = interaction.guild
                thread = guild.get_thread(int(thread_id))
                if thread:
                    await thread.send(embed=embed)

            await interaction.followup.send("✅ 일정이 등록됐어!", ephemeral=True)

        except Exception as e:
            import traceback; traceback.print_exc()
            await interaction.followup.send(f"❌ 오류: {e}", ephemeral=True)
```

### 4-4. ScheduleCog (알림 스케줄러)

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

class ScheduleCog(commands.Cog):
    def __init__(self, bot):
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

                # 알림 Embed
                dt_str = s["scheduled_at"].strftime("%Y년 %m월 %d일 %H:%M")
                embed = discord.Embed(
                    title="📅 일정 알림!",
                    description=f"**{s['title']}**\n{dt_str}",
                    color=0xFEE75C,
                )
                embed.set_footer(text="일정을 완료했으면 체크해줘!")
                await thread.send(embed=embed)

                # 알림 완료 표시 (중복 방지)
                mark_schedule_notified(s["schedule_id"])

                # 반복 일정: 다음 일정 자동 생성
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
        user_id = str(interaction.user.id)
        schedules = get_upcoming_schedules(user_id, days=30)

        if not schedules:
            await interaction.followup.send("등록된 일정이 없어!", ephemeral=True)
            return

        lines = []
        for s in schedules[:10]:  # 최대 10개
            dt_str = s["scheduled_at"].strftime("%m/%d %H:%M")
            repeat = " 🔁" if s.get("is_repeat") else ""
            lines.append(f"• `{dt_str}` {s['title']}{repeat}")

        embed = discord.Embed(
            title="📅 등록된 일정",
            description="\n".join(lines),
            color=0x5865F2,
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="일정삭제", description="등록된 일정을 삭제합니다.")
    async def schedule_delete_cmd(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        schedules = get_upcoming_schedules(user_id, days=30)

        if not schedules:
            await interaction.response.send_message("삭제할 일정이 없어!", ephemeral=True)
            return

        options = [
            discord.SelectOption(
                label=f"{s['scheduled_at'].strftime('%m/%d %H:%M')} {s['title']}",
                value=str(s["schedule_id"]),
            )
            for s in schedules[:25]  # Select 최대 25개
        ]

        select = discord.ui.Select(placeholder="삭제할 일정 선택", options=options)

        async def select_callback(inter: discord.Interaction):
            sid = int(inter.data["values"][0])
            deleted = delete_schedule(user_id, sid)
            await inter.response.send_message(
                "✅ 삭제했어!" if deleted else "❌ 삭제 실패", ephemeral=True
            )

        select.callback = select_callback
        view = discord.ui.View(timeout=120)
        view.add_item(select)
        await interaction.response.send_message("삭제할 일정을 선택해줘:", view=view, ephemeral=True)


async def setup(bot):
    await bot.add_cog(ScheduleCog(bot))
```

### 4-5. 반복 일정 자동 생성

```python
from datetime import timedelta
from dateutil.relativedelta import relativedelta  # pip install python-dateutil

def _create_next_repeat(s: dict):
    """반복 일정의 다음 회차 자동 생성"""
    from datetime import datetime
    dt = s["scheduled_at"]
    rule = s.get("repeat_rule", "weekly")

    if rule == "daily":
        next_dt = dt + timedelta(days=1)
    elif rule == "weekly":
        next_dt = dt + timedelta(weeks=1)
    elif rule == "monthly":
        next_dt = dt + relativedelta(months=1)
    elif rule == "weekday":
        next_dt = dt + timedelta(days=1)
        while next_dt.weekday() >= 5:  # 토/일 건너뜀
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
```

---

## 5. DB 사용 목록

### 읽기 (Read)
```python
get_user(user_id)               # schedule_thread_id
get_upcoming_schedules(user_id)
get_all_pending_schedules()     # 스케줄러 알림 체크용
```

### 쓰기 (Write — 소유)
```python
create_schedule(user_id, title, scheduled_at, is_repeat, repeat_rule) -> int
mark_schedule_done(schedule_id)
mark_schedule_notified(schedule_id)
delete_schedule(user_id, schedule_id) -> bool
set_schedule_thread_id(user_id, thread_id)
```

### 절대 건드리지 말 것
- `meals`, `weather_log`, `weight_log`, `email_*`, `diary_log` 금지

---

## 6. ML 계획 — 반복 패턴 학습

### 현재: 사용자가 직접 반복 여부 설정
- `is_repeat`, `repeat_rule` 직접 입력

### 향후: 자동 패턴 감지
- 동일 제목/요일의 일정이 반복되면 자동으로 "매주 반복으로 등록할까?" 제안
- 시퀀스 분석: 특정 요일 패턴 → 자동 반복 감지

```python
# 패턴 분석 예시 쿼리
SELECT title, 
       EXTRACT(DOW FROM scheduled_at) as day_of_week,
       COUNT(*) as cnt
FROM schedule_log
WHERE user_id = %s
GROUP BY title, day_of_week
HAVING COUNT(*) >= 3  -- 3번 이상이면 패턴 의심
```

---

## 7. bot_schedule.py 전체 코드

```python
"""
bot_schedule.py — 일정 전용 봇 진입점

역할: 일정 등록 / 알림 / 반복 일정 패턴 학습
DB : 먹구름과 동일한 Supabase 공유
토큰: .env의 DISCORD_TOKEN_SCHEDULE 사용
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
    init_db()          # schedule_log 테이블 + schedule_thread_id 컬럼 마이그레이션 포함
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

## 8. 구현 체크리스트

- [ ] `utils/db.py`: `schedule_thread_id` 컬럼 마이그레이션
- [ ] `utils/db.py`: `schedule_log` 테이블 생성
- [ ] `utils/db.py`: DB 함수 6개 추가 (`create_schedule`, `get_upcoming_schedules`, `get_all_pending_schedules`, `mark_schedule_done`, `mark_schedule_notified`, `delete_schedule`, `set_schedule_thread_id`)
- [ ] `cogs/onboarding.py`: 일정 전용 쓰레드 생성
- [ ] `cogs/schedule.py`: `parse_schedule_input()`, `ScheduleInputModal`, `ScheduleCog` 구현
- [ ] `bot_schedule.py`: `cogs.schedule` 로드 활성화

---

## 9. 개발 시 주의사항

- GPT 날짜 파싱 실패 시 → "날짜를 인식하지 못했어. 예: '내일 오전 10시 병원'" 안내
- `scheduled_at`은 KST 기준으로 파싱 → DB 저장 시 UTC 변환 없이 그대로 저장 (PostgreSQL이 TIMESTAMP WITHOUT TIME ZONE으로 저장)
- `get_all_pending_schedules()`는 전체 유저 대상 → 결과가 많을 수 있으니 인덱스 고려: `CREATE INDEX ON schedule_log(scheduled_at, is_done, notified)`
- 반복 일정은 `notified=True`가 된 후 새 레코드 생성 방식 (원본 업데이트 X)
- `python-dateutil` 패키지 필요 (`pip install python-dateutil`)
