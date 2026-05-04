# 일기봇 (bot_diary.py) 제작 로드맵

> last_updated: 2026-04-13 | 현재 버전: 📋 미구현

---

## 개요

유저가 하루 일기를 Discord에 작성하면 GPT가 감정을 분석하고,  
주간/월간 감정 추이를 트래킹한다.  
식사 데이터와 교차 분석하여 "무엇을 먹을 때 기분이 좋은가"를 발견한다.

---

## Phase 0 — 사전 준비

### 0-1. Discord Application 생성

- discord.com/developers → 새 Application 생성
- Bot 탭 → 토큰 발급
- `.env`에 `DISCORD_TOKEN_DIARY` 추가

### 0-2. 온보딩 수정 — 일기봇 쓰레드 추가

**v4.0 채널 구조 전환 후**: 유저 전용 채널 안에 일기봇 쓰레드 생성.

```python
# cogs/onboarding.py — 채널 구조 전환 시 함께 추가

diary_thread = await personal_channel.create_thread(
    name=f"📔 {name}의 일기장",
    auto_archive_duration=10080,  # 7일
    type=discord.ChannelType.public_thread
)
set_diary_thread_id(user_id, str(diary_thread.id))
```

### 0-3. users 테이블 컬럼 추가

```python
# utils/db.py init_db() 내 마이그레이션 추가
cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS diary_thread_id TEXT")
```

### 0-4. diary_log 테이블 생성

```python
# utils/db.py init_db()
cur.execute("""
    CREATE TABLE IF NOT EXISTS diary_log (
        log_id      SERIAL PRIMARY KEY,
        user_id     TEXT REFERENCES users(user_id),
        content     TEXT NOT NULL,
        emotion     TEXT,          -- '긍정' | '부정' | '중립'
        intensity   INTEGER,       -- 1~5 강도
        keywords    TEXT,          -- JSON 배열: ["피곤함", "스트레스", "뿌듯함"]
        written_at  TIMESTAMP DEFAULT NOW()
    )
""")
```

---

## Phase 1 — 일기 작성 기능 (v3.4)

### 1-1. bot_diary.py 구성

```python
# bot_diary.py
import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN_DIARY")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

COGS = ["cogs.diary"]

@bot.event
async def on_ready():
    for cog in COGS:
        await bot.load_extension(cog)
    await bot.tree.sync()
    print(f"일기봇 로그인: {bot.user}")

async def main():
    async with bot:
        await bot.start(TOKEN)

import asyncio
asyncio.run(main())
```

### 1-2. cogs/diary.py 구성

```python
# cogs/diary.py
import discord
from discord.ext import commands
from discord import app_commands
from utils.db import get_user, create_diary_log
from utils.gpt import analyze_emotion

class DiaryInputModal(discord.ui.Modal, title="오늘 하루 일기"):
    content = discord.ui.TextInput(
        label="오늘 하루 어떠셨나요?",
        style=discord.TextStyle.paragraph,
        placeholder="자유롭게 적어주세요. (최대 500자)",
        max_length=500,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        user = get_user(str(interaction.user.id))
        if not user:
            await interaction.followup.send("먼저 온보딩을 완료해주세요.", ephemeral=True)
            return

        text = str(self.content.value)

        # GPT 감정 분석
        emotion_result = await analyze_emotion(text)
        # 반환: {"emotion": "긍정", "intensity": 3, "keywords": ["뿌듯함", "피곤함"]}

        # DB 저장
        create_diary_log(
            user_id=user["user_id"],
            content=text,
            emotion=emotion_result["emotion"],
            intensity=emotion_result["intensity"],
            keywords=emotion_result["keywords"]
        )

        # 일기 Embed 생성
        embed = build_diary_embed(text, emotion_result, user["tamagotchi_name"])

        # 일기 쓰레드에 전송
        thread_id = user.get("diary_thread_id") or user.get("thread_id")
        if thread_id:
            thread = interaction.guild.get_thread(int(thread_id))
            if thread:
                await thread.send(embed=embed)

        await interaction.followup.send("일기가 저장됐어요!", ephemeral=True)


class DiaryCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="일기작성", description="오늘 하루 일기를 작성해요")
    async def write_diary(self, interaction: discord.Interaction):
        await interaction.response.send_modal(DiaryInputModal())

    @app_commands.command(name="감정기록", description="오늘 감정만 빠르게 남겨요")
    async def quick_emotion(self, interaction: discord.Interaction):
        # 버튼 5개: 😊 좋음 / 😌 평온 / 😐 보통 / 😔 우울 / 😤 화남
        await interaction.response.send_message(
            "오늘 기분이 어때요?",
            view=EmotionQuickView(interaction.user.id),
            ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(DiaryCog(bot))
```

### 1-3. GPT 감정 분석 프롬프트

```python
# utils/gpt.py 추가

EMOTION_PROMPT = """
다음 일기 텍스트를 분석하여 JSON으로만 답하세요:
{
  "emotion": "긍정" | "부정" | "중립",
  "intensity": 1~5 (1=약함, 5=강함),
  "keywords": ["감정 키워드 최대 3개"]
}

일기: {text}
"""

async def analyze_emotion(text: str) -> dict:
    response = await openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": EMOTION_PROMPT.format(text=text)}],
        response_format={"type": "json_object"},
        max_tokens=150
    )
    return json.loads(response.choices[0].message.content)
```

### 1-4. 일기 Embed 구성

```python
def build_diary_embed(content: str, emotion: dict, name: str) -> discord.Embed:
    EMOTION_COLORS = {"긍정": 0x57F287, "부정": 0xED4245, "중립": 0xFEE75C}
    EMOTION_ICONS  = {"긍정": "😊", "부정": "😔", "중립": "😐"}

    color = EMOTION_COLORS.get(emotion["emotion"], 0x99AAB5)
    icon  = EMOTION_ICONS.get(emotion["emotion"], "📓")

    intensity_bar = "●" * emotion["intensity"] + "○" * (5 - emotion["intensity"])

    embed = discord.Embed(
        title=f"{icon} {name}의 오늘 일기",
        description=content[:300] + ("..." if len(content) > 300 else ""),
        color=color
    )
    embed.add_field(name="감정", value=f"{emotion['emotion']} {intensity_bar}", inline=True)
    embed.add_field(name="키워드", value=" · ".join(emotion["keywords"]), inline=True)
    embed.set_footer(text=datetime.now(KST).strftime("%Y년 %m월 %d일"))
    return embed
```

---

## Phase 2 — 감정 추이 조회 (v3.4)

### 2-1. 주간 감정 요약 슬래시 커맨드

```python
# cogs/diary.py 추가

@app_commands.command(name="감정조회", description="이번 주 감정 변화를 봐요")
async def emotion_summary(self, interaction: discord.Interaction):
    user = get_user(str(interaction.user.id))
    week_logs = get_diary_logs(user["user_id"], days=7)

    if not week_logs:
        await interaction.response.send_message("아직 일기가 없어요.", ephemeral=True)
        return

    # 감정별 카운트
    pos = sum(1 for l in week_logs if l["emotion"] == "긍정")
    neg = sum(1 for l in week_logs if l["emotion"] == "부정")
    neu = sum(1 for l in week_logs if l["emotion"] == "중립")

    # 자주 등장한 키워드
    all_kw = [kw for log in week_logs for kw in json.loads(log["keywords"] or "[]")]
    top_kw = Counter(all_kw).most_common(3)

    embed = discord.Embed(title="이번 주 감정 기록", color=0x5865F2)
    embed.add_field(name="감정 분포", value=f"😊 {pos}일  😔 {neg}일  😐 {neu}일", inline=False)
    embed.add_field(name="자주 느낀 감정", value=" · ".join([k for k, _ in top_kw]) or "없음", inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)
```

### 2-2. 주간 자동 감정 리포트 (APScheduler)

```python
# cogs/diary.py — 매주 일요일 09:00

@scheduler.scheduled_job('cron', day_of_week='sun', hour=9, minute=0, timezone='Asia/Seoul')
async def weekly_emotion_report():
    users = get_all_users()
    for user in users:
        logs = get_diary_logs(user["user_id"], days=7)
        if not logs: continue

        embed = build_weekly_emotion_embed(logs, user["tamagotchi_name"])
        thread_id = user.get("diary_thread_id") or user.get("thread_id")
        if thread_id:
            thread = guild.get_thread(int(thread_id))
            if thread:
                await thread.send(embed=embed)
```

---

## Phase 3 — 식사 × 감정 교차 분석 (v3.5)

> "어떤 음식을 먹은 날 기분이 좋은가?"

### 3-1. 교차 분석 쿼리

```python
# utils/db.py 추가

def get_meal_emotion_correlation(user_id: str) -> list[dict]:
    """같은 날의 식사 기록과 감정 기록을 조인"""
    cur.execute("""
        SELECT
            m.food_name,
            m.meal_type,
            d.emotion,
            d.intensity,
            COUNT(*) as count
        FROM meals m
        JOIN diary_log d ON m.user_id = d.user_id
            AND (m.recorded_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Seoul')::date
              = (d.written_at  AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Seoul')::date
        WHERE m.user_id = %s
        GROUP BY m.food_name, m.meal_type, d.emotion, d.intensity
        ORDER BY count DESC
        LIMIT 20
    """, (user_id,))
    return cur.fetchall()
```

### 3-2. 인사이트 Embed

```python
def build_correlation_insight(correlations: list) -> str:
    # "비빔밥을 먹은 날 긍정 감정이 많았어요"
    pos_foods = [c["food_name"] for c in correlations if c["emotion"] == "긍정"]
    neg_foods = [c["food_name"] for c in correlations if c["emotion"] == "부정"]

    insight = ""
    if pos_foods:
        insight += f"**{pos_foods[0]}**을(를) 먹은 날 기분이 좋았어요!\n"
    if neg_foods:
        insight += f"**{neg_foods[0]}**을(를) 먹은 날은 조금 힘들었던 것 같아요."
    return insight or "아직 패턴을 분석하기에 데이터가 부족해요."
```

---

## Phase 4 — ML 감정 패턴 (v4.0)

### 4-1. 감정 예측 모델

```python
# utils/ml.py EmotionPredictor 추가

# 입력 피처
features = [
    "avg_calories_today",     # 오늘 평균 칼로리
    "sleep_hour",             # 기상 시간 (간접 지표)
    "meal_skipped",           # 끼니 거름 여부
    "weather_condition",      # 날씨 상태 (맑음=1, 비=0)
    "day_of_week",            # 요일
]
# 레이블: emotion (긍정=1, 중립=0, 부정=-1)
```

### 4-2. 적용 — 먹구름봇 daily 코멘트 강화

```python
# utils/gpt_ml_bridge.py 확장
# 식사 패턴 + 감정 패턴을 합산하여 더 개인화된 코멘트 생성
```

---

## DB 테이블

```sql
diary_log (
  log_id      SERIAL PRIMARY KEY,
  user_id     TEXT REFERENCES users(user_id),
  content     TEXT NOT NULL,
  emotion     TEXT CHECK(emotion IN ('긍정', '부정', '중립')),
  intensity   INTEGER CHECK(intensity BETWEEN 1 AND 5),
  keywords    TEXT,          -- JSON: ["피곤함", "스트레스"]
  written_at  TIMESTAMP DEFAULT NOW()
)

-- users 컬럼 추가
users.diary_thread_id TEXT   -- 일기봇 전용 쓰레드
```

---

## 환경변수

| 변수명 | 상태 | 설명 |
|--------|------|------|
| `DISCORD_TOKEN_DIARY` | 📋 발급 필요 | 일기봇 토큰 |

---

## 제작 순서 요약

```
Step 0 — Discord Application 생성, DISCORD_TOKEN_DIARY 발급
Step 0 — cogs/onboarding.py에 diary_thread 생성 추가
Step 0 — users.diary_thread_id 컬럼 마이그레이션
Step 0 — diary_log 테이블 생성 (init_db)
Step 1 — bot_diary.py 기본 구조 작성
Step 1 — cogs/diary.py DiaryInputModal + DiaryCog 구현
Step 1 — utils/gpt.py analyze_emotion() 추가
Step 1 — utils/db.py create_diary_log(), get_diary_logs() 추가
Step 1 — build_diary_embed() 구현
Step 1 — /일기작성 슬래시 커맨드 테스트
Step 2 — /감정조회 슬래시 커맨드
Step 2 — 주간 자동 감정 리포트 APScheduler
Step 3 — 식사 × 감정 교차 분석 쿼리
Step 3 — /인사이트 슬래시 커맨드
Step 4 — ML 감정 예측 모델 (30개 이상 데이터 누적 후)
```
