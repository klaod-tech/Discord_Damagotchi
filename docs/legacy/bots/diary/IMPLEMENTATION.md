# 일기봇 — 전체 구현 코드

> Claude 세션에서 이 파일을 읽으면 `cogs/diary.py`와 `bot_diary.py`를 바로 구현할 수 있습니다.  
> 먼저 `diary/DB.md`를 읽고 DB 마이그레이션을 `utils/db.py`에 적용한 후 구현하세요.

---

## bot_diary.py

```python
"""
bot_diary.py — 일기 전용 봇 진입점

역할: 일기 작성 / 감정 분석 / 식사×감정 상관관계 데이터 누적
DB : 먹구름과 동일한 Supabase 공유
토큰: .env의 DISCORD_TOKEN_DIARY 사용
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
        await bot.load_extension("cogs.diary")
        print("[일기봇] cogs.diary 로드 완료")
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
```

---

## cogs/diary.py

```python
"""
cogs/diary.py — 일기 입력 + 감정 분석 기능

흐름:
  1. /일기 슬래시 커맨드 → DiaryInputModal 팝업
  2. 일기 텍스트 입력 → GPT-4o 감정 분석
  3. diary_log DB 저장
  4. 일기 전용 쓰레드에 감정 Embed 전송
"""
import os
import json
import discord
from discord.ext import commands
from discord import app_commands
from openai import AsyncOpenAI

from utils.db import get_user, save_diary, get_emotion_stats

_client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])


# ──────────────────────────────────────────────
# GPT 감정 분석
# ──────────────────────────────────────────────

async def analyze_emotion(text: str) -> dict:
    """
    GPT-4o로 일기 텍스트 감정 분석.
    반환: {
        "emotion_tag": str,     # 기쁨/슬픔/화남/평온/불안/설렘
        "emotion_score": float, # 0.0 ~ 1.0
        "comment": str,         # 다마고치 반응 대사 (2문장 이내)
    }
    """
    system_prompt = (
        "너는 일기를 읽고 감정을 분석하는 AI야. "
        "다음 JSON만 반환해:\n"
        "{\n"
        '  "emotion_tag": "기쁨/슬픔/화남/평온/불안/설렘 중 하나",\n'
        '  "emotion_score": 0.0~1.0 숫자,\n'
        '  "comment": "일기에 대한 따뜻한 반응 (2문장 이내, 친근한 말투)"\n'
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
    result = json.loads(raw)

    return {
        "emotion_tag":   str(result.get("emotion_tag", "평온")),
        "emotion_score": float(result.get("emotion_score", 0.5)),
        "comment":       str(result.get("comment", "")),
    }


def _emotion_color(emotion_tag: str) -> int:
    return {
        "기쁨": 0xFFD700,
        "슬픔": 0x4169E1,
        "화남": 0xFF4500,
        "평온": 0x90EE90,
        "불안": 0xFFA500,
        "설렘": 0xFF69B4,
    }.get(emotion_tag, 0x808080)


EMOTION_EMOJI = {
    "기쁨": "😊", "슬픔": "😢", "화남": "😤",
    "평온": "😌", "불안": "😰", "설렘": "🥰",
}


# ──────────────────────────────────────────────
# 일기 입력 Modal
# ──────────────────────────────────────────────

class DiaryInputModal(discord.ui.Modal, title="📔 오늘의 일기"):
    content_input = discord.ui.TextInput(
        label="오늘 하루 어땠어? 자유롭게 적어줘",
        placeholder=(
            "예: 오늘 친구랑 카페 갔다가 맛있는 케이크 먹었어. 기분이 좋았어!\n"
            "10자 이상 적어줘야 분석할 수 있어."
        ),
        style=discord.TextStyle.paragraph,
        max_length=1000,
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            user_id = str(interaction.user.id)
            user = get_user(user_id)
            if not user:
                await interaction.followup.send("❌ 등록된 유저가 아니야!", ephemeral=True)
                return

            text = self.content_input.value.strip()
            if len(text) < 10:
                await interaction.followup.send(
                    "❌ 너무 짧아! 10자 이상 적어줘.", ephemeral=True
                )
                return

            # GPT 감정 분석
            result        = await analyze_emotion(text)
            emotion_tag   = result["emotion_tag"]
            emotion_score = result["emotion_score"]
            comment       = result["comment"]

            # DB 저장
            save_diary(user_id, text, emotion_tag, emotion_score, comment)

            emoji = EMOTION_EMOJI.get(emotion_tag, "📔")

            embed = discord.Embed(
                title=f"{emoji} 오늘의 일기 기록 완료",
                description=f"*{comment}*",
                color=_emotion_color(emotion_tag),
            )
            embed.add_field(
                name="📝 일기",
                value=text[:200] + ("..." if len(text) > 200 else ""),
                inline=False,
            )
            embed.add_field(
                name="🎭 감정",
                value=f"{emoji} **{emotion_tag}** (강도: {int(emotion_score * 100)}%)",
                inline=True,
            )
            embed.set_footer(text="오늘도 수고했어 🌙")

            # 일기 전용 쓰레드에 전송
            thread_id = user.get("diary_thread_id") or user.get("thread_id")
            if thread_id:
                guild  = interaction.guild
                thread = guild.get_thread(int(thread_id))
                if thread:
                    await thread.send(embed=embed)

            await interaction.followup.send("✅ 일기가 기록됐어!", ephemeral=True)

        except Exception as e:
            import traceback; traceback.print_exc()
            await interaction.followup.send(f"❌ 오류: {e}", ephemeral=True)


# ──────────────────────────────────────────────
# Cog
# ──────────────────────────────────────────────

class DiaryCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        print("[DiaryCog] 로드 완료")

    @app_commands.command(name="일기", description="오늘의 일기를 작성합니다.")
    async def diary_cmd(self, interaction: discord.Interaction):
        await interaction.response.send_modal(DiaryInputModal())

    @app_commands.command(name="감정통계", description="최근 7일 감정 분포를 확인합니다.")
    async def emotion_stats_cmd(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        user_id = str(interaction.user.id)
        stats = get_emotion_stats(user_id, days=7)

        if not stats:
            await interaction.followup.send("아직 일기 기록이 없어! `/일기`로 첫 일기를 써봐 📔", ephemeral=True)
            return

        lines = [
            f"{EMOTION_EMOJI.get(e, '📔')} {e}: {cnt}회"
            for e, cnt in stats.items()
        ]
        top_emotion = next(iter(stats))
        embed = discord.Embed(
            title="📊 최근 7일 감정 통계",
            description="\n".join(lines),
            color=_emotion_color(top_emotion),
        )
        embed.set_footer(text=f"가장 많은 감정: {EMOTION_EMOJI.get(top_emotion, '')} {top_emotion}")
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(DiaryCog(bot))
```
