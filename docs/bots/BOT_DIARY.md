# 일기봇 개발 가이드 — Claude 전용

> **이 파일만 읽으면 일기봇을 처음부터 완전히 구현할 수 있습니다.**  
> 공통 참조: `01_ARCHITECTURE.md`, `02_SHARED_DB.md`, `03_SHARED_UTILS.md`

---

## 1. 봇 기본 정보

| 항목 | 내용 |
|------|------|
| 봇 파일 | `bot_diary.py` |
| 토큰 환경변수 | `DISCORD_TOKEN_DIARY` |
| 커맨드 prefix | `!diary_` |
| 담당 Cog | `cogs/diary.py` → `DiaryCog` (신규 생성) |
| 담당 쓰레드 | `users.diary_thread_id` (없으면 `thread_id` fallback) |
| 담당 DB 테이블 | `diary_log` (신규 생성 필요) |
| 현재 상태 | 📋 구현 예정 — 이 문서가 스펙 |

---

## 2. 역할 및 범위

### 이 봇이 하는 것
- 일기 전용 쓰레드에서 일기 입력 감지 (슬래시 커맨드 또는 버튼)
- GPT-4o로 감정 분류 (기쁨/슬픔/화남/평온/불안/설렘) + 강도 0.0~1.0
- 분석 결과 + 다마고치 반응 대사를 쓰레드에 전송
- 식사 × 감정 상관 데이터 자동 누적 (ML용)
- 주간 감정 통계 리포트 (향후)

### 이 봇이 하지 않는 것
- 일기 입력 버튼 — 먹구름봇 `MainView`에 추가해야 함 (추후)
- 식사 분석 — 식사봇 담당

---

## 3. 신규 구현 필요 항목

### 3-1. DB 마이그레이션 (utils/db.py에 추가)

```python
# init_db() 내에 추가

# diary_thread_id 컬럼
cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS diary_thread_id TEXT")

# diary_log 테이블
cur.execute("""
    CREATE TABLE IF NOT EXISTS diary_log (
        diary_id      SERIAL PRIMARY KEY,
        user_id       TEXT REFERENCES users(user_id) ON DELETE CASCADE,
        content       TEXT NOT NULL,
        emotion_tag   TEXT,          -- 기쁨/슬픔/화남/평온/불안/설렘
        emotion_score REAL,          -- 0.0 ~ 1.0
        gpt_comment   TEXT,
        recorded_at   TIMESTAMP DEFAULT NOW()
    )
""")
```

### 3-2. DB 함수 추가 (utils/db.py에 추가)

```python
def set_diary_thread_id(user_id: str, thread_id: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET diary_thread_id = %s WHERE user_id = %s",
        (thread_id, user_id),
    )
    conn.commit()
    cur.close()
    conn.close()

def save_diary(user_id: str, content: str, emotion_tag: str, emotion_score: float, gpt_comment: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO diary_log (user_id, content, emotion_tag, emotion_score, gpt_comment)
        VALUES (%s, %s, %s, %s, %s)
    """, (user_id, content, emotion_tag, emotion_score, gpt_comment))
    conn.commit()
    cur.close()
    conn.close()

def get_diaries_by_date(user_id: str, target_date) -> list:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM diary_log
        WHERE user_id = %s
        AND (recorded_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Seoul')::date = %s
        ORDER BY recorded_at ASC
    """, (user_id, target_date))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def get_recent_diaries(user_id: str, limit: int = 7) -> list:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM diary_log
        WHERE user_id = %s
        ORDER BY recorded_at DESC
        LIMIT %s
    """, (user_id, limit))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def get_emotion_stats(user_id: str, days: int = 7) -> dict:
    """최근 N일 감정 태그 분포"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT emotion_tag, COUNT(*) as cnt
        FROM diary_log
        WHERE user_id = %s
          AND recorded_at >= NOW() - INTERVAL '%s days'
        GROUP BY emotion_tag
        ORDER BY cnt DESC
    """, (user_id, days))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return {r["emotion_tag"]: r["cnt"] for r in rows if r["emotion_tag"]}
```

### 3-3. 온보딩 추가 (cogs/onboarding.py에 추가)

```python
# set_diary_thread_id import 추가
from utils.db import (..., set_diary_thread_id)

# OnboardingModal.on_submit() 내에 추가:
diary_thread = await channel.create_thread(
    name=f"📔 {interaction.user.display_name}의 일기",
    auto_archive_duration=10080,
    invitable=False,
)
set_diary_thread_id(user_id, str(diary_thread.id))
await diary_thread.send(
    f"📔 안녕, {interaction.user.mention}!\n"
    f"여기는 **일기 전용** 쓰레드야.\n"
    f"오늘 하루 어땠어? 자유롭게 적어줘!\n"
    f"`/일기` 명령어나 버튼으로 일기를 쓸 수 있어."
)
```

---

## 4. cogs/diary.py 구현 스펙

### 4-1. 파일 구조

```
cogs/diary.py
  ├── analyze_emotion(text: str) -> dict   # GPT 감정 분석
  ├── DiaryInputModal (Modal)
  │   └── on_submit: 감정 분석 → DB 저장 → Embed 전송
  ├── DiaryWeeklyView (View)               # 주간 감정 통계 버튼
  └── DiaryCog (Cog)
        ├── on_message: 일기 쓰레드 메시지 감지 (선택적)
        └── slash commands: /일기, /감정통계
```

### 4-2. GPT 감정 분석 함수

```python
async def analyze_emotion(text: str) -> dict:
    """
    GPT-4o로 일기 텍스트 감정 분석.
    반환: {
        "emotion_tag": str,    # 기쁨/슬픔/화남/평온/불안/설렘
        "emotion_score": float, # 0.0 ~ 1.0
        "comment": str,        # 다마고치 반응 대사 (2문장 이내)
    }
    """
    import os, json
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])

    system_prompt = (
        "너는 일기를 읽고 감정을 분석하는 AI야. "
        "다음 JSON만 반환해:\n"
        "{\n"
        '  "emotion_tag": "기쁨/슬픔/화남/평온/불안/설렘 중 하나",\n'
        '  "emotion_score": 0.0~1.0 숫자,\n'
        '  "comment": "일기에 대한 따뜻한 반응 (2문장 이내, 친근한 말투)"\n'
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
    result = json.loads(raw)

    return {
        "emotion_tag":   str(result.get("emotion_tag", "평온")),
        "emotion_score": float(result.get("emotion_score", 0.5)),
        "comment":       str(result.get("comment", "")),
    }
```

### 4-3. DiaryInputModal

```python
class DiaryInputModal(discord.ui.Modal, title="📔 오늘의 일기"):
    content_input = discord.ui.TextInput(
        label="오늘 하루 어땠어? 자유롭게 적어줘",
        placeholder="예: 오늘 친구랑 카페 갔다가 맛있는 케이크 먹었어. 기분이 좋았어!",
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

            # GPT 감정 분석
            result = await analyze_emotion(text)
            emotion_tag   = result["emotion_tag"]
            emotion_score = result["emotion_score"]
            comment       = result["comment"]

            # DB 저장
            save_diary(user_id, text, emotion_tag, emotion_score, comment)

            # 감정 이모지 매핑
            emotion_emoji = {
                "기쁨": "😊", "슬픔": "😢", "화남": "😤",
                "평온": "😌", "불안": "😰", "설렘": "🥰",
            }
            emoji = emotion_emoji.get(emotion_tag, "📔")

            # Embed 전송
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
                guild = interaction.guild
                thread = guild.get_thread(int(thread_id))
                if thread:
                    await thread.send(embed=embed)

            await interaction.followup.send("✅ 일기가 기록됐어!", ephemeral=True)

        except Exception as e:
            import traceback; traceback.print_exc()
            await interaction.followup.send(f"❌ 오류: {e}", ephemeral=True)


def _emotion_color(emotion_tag: str) -> int:
    return {
        "기쁨": 0xFFD700,  # 금색
        "슬픔": 0x4169E1,  # 파란색
        "화남": 0xFF4500,  # 빨간색
        "평온": 0x90EE90,  # 연두색
        "불안": 0xFFA500,  # 주황색
        "설렘": 0xFF69B4,  # 핑크
    }.get(emotion_tag, 0x808080)
```

### 4-4. 슬래시 커맨드

```python
class DiaryCog(commands.Cog):
    def __init__(self, bot):
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
            await interaction.followup.send("아직 일기 기록이 없어!", ephemeral=True)
            return

        emotion_emoji = {
            "기쁨": "😊", "슬픔": "😢", "화남": "😤",
            "평온": "😌", "불안": "😰", "설렘": "🥰",
        }
        lines = [
            f"{emotion_emoji.get(e, '📔')} {e}: {cnt}회"
            for e, cnt in stats.items()
        ]
        embed = discord.Embed(
            title="📊 최근 7일 감정 통계",
            description="\n".join(lines),
            color=0x5865F2,
        )
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(DiaryCog(bot))
```

---

## 5. DB 사용 목록

### 읽기 (Read)
```python
get_user(user_id)           # diary_thread_id, tamagotchi_name
get_diaries_by_date(user_id, date)
get_recent_diaries(user_id, limit=7)
get_emotion_stats(user_id, days=7)
```

### 쓰기 (Write — 소유)
```python
save_diary(user_id, content, emotion_tag, emotion_score, gpt_comment)
set_diary_thread_id(user_id, thread_id)  # 온보딩 시
```

### 절대 건드리지 말 것
- `meals`, `weather_log`, `weight_log`, `email_*`, `schedule_log` 금지
- `tamagotchi` 수치 갱신 금지 (식사봇 전용)

---

## 6. 식사 × 감정 상관관계 (ML 데이터 누적)

일기봇이 저장하는 `diary_log.emotion_tag`와 `meals`를 조인하면 식사와 감정의 상관관계 분석이 가능합니다.

```sql
-- 감정별 평균 칼로리
SELECT d.emotion_tag, AVG(m.calories) as avg_cal
FROM diary_log d
JOIN meals m ON d.user_id = m.user_id
  AND DATE(d.recorded_at) = DATE(m.recorded_at)
GROUP BY d.emotion_tag;
```

**활용 예시**:
- 슬픔 날 과식 패턴 감지 → 먹구름봇이 "오늘 힘들어 보이는데 조금만 먹어도 괜찮아" 코멘트
- 기쁨 날 균형잡힌 식사 → "오늘 기분도 좋고 식사도 완벽해!" 칭찬
- 불안 날 식사 불규칙 → "오늘 많이 불안했구나, 규칙적인 식사가 도움이 돼"

---

## 7. ML 계획

### 현재: GPT 감정 분류
- `emotion_tag`: 기쁨/슬픔/화남/평온/불안/설렘 6종
- `emotion_score`: 0.0~1.0 강도

### 향후: KoBERT 감정 분류
- `diary_log` 데이터 누적 후 KoBERT fine-tuning
- GPT 레이블 → KoBERT 학습 데이터로 활용
- 한국어 감정 분류 정확도 향상

### 스팸/노이즈 제거
- "없음", "ㅇ", "ㅋㅋ" 등 의미없는 입력 필터링
- `len(content) < 10` 이면 "더 자세히 적어줘" 안내

---

## 8. bot_diary.py 전체 코드

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
    init_db()          # diary_log 테이블 + diary_thread_id 컬럼 마이그레이션 포함
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

## 9. 구현 체크리스트

- [ ] `utils/db.py`: `diary_thread_id` 컬럼 마이그레이션 추가
- [ ] `utils/db.py`: `diary_log` 테이블 생성 추가
- [ ] `utils/db.py`: `set_diary_thread_id()`, `save_diary()`, `get_diaries_by_date()`, `get_recent_diaries()`, `get_emotion_stats()` 추가
- [ ] `cogs/onboarding.py`: 일기 전용 쓰레드 생성 + `set_diary_thread_id()` 추가
- [ ] `cogs/diary.py`: `analyze_emotion()`, `DiaryInputModal`, `DiaryCog` 구현
- [ ] `bot_diary.py`: `cogs.diary` 로드 활성화
- [ ] 먹구름봇 `MainView` 또는 슬래시 커맨드에 일기 입력 진입점 추가 (선택)

---

## 10. 개발 시 주의사항

- GPT 감정 분석 결과가 JSON 파싱 실패할 수 있음 → try/except로 기본값 "평온" fallback
- `emotion_score`는 반드시 0.0~1.0 범위 검증
- 일기 내용이 너무 짧으면 (10자 미만) 입력 거부 또는 경고
- 일기봇의 `on_message`는 일기 전용 쓰레드에서만 동작하도록 채널 필터링 필수
- 모든 슬래시 커맨드는 `bot.tree.sync()` 후 반영 (처음 배포 시 최대 1시간 소요)
