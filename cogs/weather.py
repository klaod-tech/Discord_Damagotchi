"""
cogs/weather.py — 날씨 연동
동작:
  - 유저 기상 시간(wake_time)에 날씨 데이터 수집
  - 기상청 공공데이터 API (초단기실황) + 에어코리아 API (미세먼지)
  - DB Weather_Log 저장
  - 쓰레드에 날씨 알림 메시지 전송
  - Embed 이미지 교체
  - !weather 명령어로 관리자 즉시 갱신 가능
  - 매 10분마다 새 유저 스케줄러 자동 등록 체크
"""
import os
import aiohttp
import discord
from discord.ext import commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
from dotenv import load_dotenv
from utils.db import (
    get_all_users, get_tamagotchi,
    create_weather_log
)
from utils.gpt import generate_comment
from utils.embed import create_or_update_embed

load_dotenv()

WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
AIR_API_KEY     = os.getenv("AIR_API_KEY")

# ── 도시명 → 기상청 격자 좌표 매핑 ──────────────────────
CITY_GRID: dict[str, tuple[int, int]] = {
    "서울": (60, 127), "부산": (98, 76), "대구": (89, 90),
    "인천": (55, 124), "광주": (58, 74), "대전": (67, 100),
    "울산": (102, 84), "세종": (66, 103), "수원": (60, 121),
    "성남": (62, 123), "고양": (57, 128), "용인": (64, 119),
    "창원": (90, 77), "청주": (69, 106), "전주": (63, 89),
    "천안": (63, 110), "아산": (63, 110), "포항": (102, 94),
    "제주": (52, 38), "춘천": (73, 134), "강릉": (92, 131),
    "원주": (76, 122), "안양": (59, 123), "안산": (57, 121),
    "평택": (62, 114), "시흥": (57, 122), "파주": (56, 131),
    "의정부": (61, 130), "남양주": (64, 128), "화성": (59, 118),
    "김포": (55, 128), "광명": (58, 125), "군포": (59, 122),
    "하남": (65, 124), "구리": (62, 127), "오산": (62, 117),
    "이천": (68, 121), "양주": (61, 131), "경주": (100, 91),
    "김해": (96, 77), "거제": (91, 68), "여수": (73, 66),
    "순천": (75, 70), "목포": (50, 67), "익산": (60, 91),
    "군산": (56, 92), "구미": (84, 96), "안동": (91, 106),
    "진주": (81, 75),
}

def _find_grid(city: str) -> tuple[int, int]:
    city = city.strip()
    if city in CITY_GRID:
        return CITY_GRID[city]
    for key in CITY_GRID:
        if key in city or city in key:
            return CITY_GRID[key]
    return CITY_GRID["서울"]

def _pm_grade(pm10: int, pm25: int) -> str:
    if pm10 > 150 or pm25 > 75:
        return "매우나쁨 😷"
    if pm10 > 80 or pm25 > 35:
        return "나쁨 😷"
    if pm10 > 30 or pm25 > 15:
        return "보통 😐"
    return "좋음 😊"

def _weather_icon(weather: str, temp: float) -> str:
    if "눈" in weather:
        return "❄️"
    if "비" in weather:
        return "🌧️"
    if "흐림" in weather or "구름" in weather:
        return "☁️"
    if temp >= 26:
        return "☀️🥵"
    if temp <= 5:
        return "🥶"
    return "☀️"


# ── 기상청 초단기실황 API ────────────────────────────────
async def fetch_weather(nx: int, ny: int) -> dict:
    now = datetime.now()
    base_date = now.strftime("%Y%m%d")
    base_time = now.strftime("%H00")

    url = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtNcst"
    params = {
        "serviceKey": WEATHER_API_KEY,
        "numOfRows": 10,
        "pageNo": 1,
        "dataType": "JSON",
        "base_date": base_date,
        "base_time": base_time,
        "nx": nx,
        "ny": ny,
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                data = await resp.json(content_type=None)

        items = data["response"]["body"]["items"]["item"]
        result = {item["category"]: item["obsrValue"] for item in items}

        pty  = int(result.get("PTY", 0))
        sky  = int(result.get("SKY", 1)) if "SKY" in result else 1
        temp = float(result.get("T1H", 15))

        if pty in (1, 5):   weather = "비"
        elif pty in (2, 6): weather = "비/눈"
        elif pty in (3, 7): weather = "눈"
        elif sky == 4:      weather = "흐림"
        elif sky == 3:      weather = "구름많음"
        else:               weather = "맑음"

        return {"weather": weather, "temp": temp}

    except Exception as e:
        print(f"[날씨 API 오류] {e}")
        return {"weather": "알 수 없음", "temp": 15.0}


# ── 에어코리아 미세먼지 API ──────────────────────────────
async def fetch_air(city: str) -> dict:
    city_map = {
        "서울": "서울", "부산": "부산", "대구": "대구", "인천": "인천",
        "광주": "광주", "대전": "대전", "울산": "울산", "경기": "경기",
        "강원": "강원", "충북": "충북", "충남": "충남", "전북": "전북",
        "전남": "전남", "경북": "경북", "경남": "경남", "제주": "제주",
        "세종": "세종",
    }
    sido = "서울"
    for key in city_map:
        if key in city:
            sido = city_map[key]
            break

    if city in ("아산", "천안", "공주", "논산", "보령"):
        sido = "충남"

    url = "http://apis.data.go.kr/B552584/ArpltnInforInqireSvc/getCtprvnRltmMesureDnsty"
    params = {
        "serviceKey": AIR_API_KEY,
        "returnType": "json",
        "numOfRows": 1,
        "pageNo": 1,
        "sidoName": sido,
        "ver": "1.0",
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                data = await resp.json(content_type=None)

        items = data["response"]["body"]["items"]
        if items:
            item = items[0]
            pm10 = int(item.get("pm10Value") or 0)
            pm25 = int(item.get("pm25Value") or 0)
            return {"pm10": pm10, "pm25": pm25}

    except Exception as e:
        print(f"[에어코리아 API 오류] {e}")

    return {"pm10": 0, "pm25": 0}


# ── 유저 1명 날씨 업데이트 ───────────────────────────────
async def update_weather_for_user(bot: commands.Bot, user: dict):
    user_id   = str(user.get("user_id", ""))
    city      = user.get("city", "서울")
    thread_id = user.get("thread_id")

    if not thread_id:
        return

    thread = None
    for guild in bot.guilds:
        thread = guild.get_thread(int(thread_id))
        if thread:
            break

    if not thread:
        return

    tama = get_tamagotchi(user_id)
    if not tama:
        return

    nx, ny = _find_grid(city)

    weather_data = await fetch_weather(nx, ny)
    air_data     = await fetch_air(city)

    weather  = weather_data.get("weather", "맑음")
    temp     = weather_data.get("temp", 15.0)
    pm10     = air_data.get("pm10", 0)
    pm25     = air_data.get("pm25", 0)
    icon     = _weather_icon(weather, temp)
    pm_grade = _pm_grade(pm10, pm25)

    comment = await generate_comment(
        context=(
            f"오늘 날씨를 보고 사용자에게 한마디 해줘.\n"
            f"날씨: {weather}, 기온: {temp}°C\n"
            f"짧고 친근하게, 2문장 이내로. 수치는 직접 언급하지 말고 느낌으로."
        ),
        user=user,
        today_calories=0,
        recent_meals="없음",
        weather_info={"weather": weather, "temp": temp},
    )

    create_weather_log(
        user_id=user_id,
        weather=weather,
        temp=temp,
        pm10=pm10,
        pm25=pm25,
        selected_image="",
        gpt_comment=comment,
    )

    tama_name = user.get("tamagotchi_name", "타마")
    weather_embed = discord.Embed(
        title=f"{icon} 오늘의 날씨 — {city}",
        color=0x87CEEB,
    )
    weather_embed.add_field(
        name="🌡️ 날씨 / 기온",
        value=f"{weather} / {temp}°C",
        inline=True,
    )
    weather_embed.add_field(
        name="💨 미세먼지",
        value=f"PM10: {pm10} | PM2.5: {pm25}\n등급: {pm_grade}",
        inline=True,
    )
    weather_embed.add_field(
        name=f"💬 {tama_name} 한마디",
        value=f"*{comment}*",
        inline=False,
    )
    weather_embed.set_footer(text="좋은 아침이야! 오늘도 파이팅 🌱")
    await thread.send(embed=weather_embed)

    await create_or_update_embed(
        thread, user, tama, comment,
        weather={"weather": weather, "temp": temp, "pm10": pm10, "pm25": pm25},
    )

    print(f"[날씨] {user_id} — {city} / {weather} {temp}°C / PM10:{pm10} PM2.5:{pm25}")


# ══════════════════════════════════════════════════════
# Cog
# ══════════════════════════════════════════════════════
class WeatherCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.scheduler = AsyncIOScheduler()
        self._registered_jobs: set[str] = set()
        self._setup_jobs()
        # 매 10분마다 새 유저 스케줄러 자동 등록 체크
        self.scheduler.add_job(
            self._check_new_users,
            IntervalTrigger(minutes=10),
            id="check_new_users",
            replace_existing=True,
        )
        self.scheduler.start()
        print("[날씨 스케줄러] 시작 완료")

    def _register_job_for_wake_time(self, wake_time: str):
        """wake_time 기준으로 Job 등록 (중복 방지)"""
        try:
            hour, minute = map(int, wake_time.split(":"))
        except Exception:
            hour, minute = 7, 0

        job_id = f"weather_{hour:02d}{minute:02d}"
        if job_id not in self._registered_jobs:
            self.scheduler.add_job(
                self._run_weather_update,
                CronTrigger(hour=hour, minute=minute),
                id=job_id,
                replace_existing=True,
                args=[hour, minute],
            )
            self._registered_jobs.add(job_id)
            print(f"[날씨 스케줄러] {hour:02d}:{minute:02d} Job 등록")

    def _setup_jobs(self):
        """봇 시작 시 현재 유저들의 wake_time Job 등록"""
        users = get_all_users()
        for user in users:
            wake_time = user.get("wake_time") or "07:00"
            self._register_job_for_wake_time(wake_time)

    async def _check_new_users(self):
        """10분마다 새 유저의 wake_time Job 자동 등록"""
        users = get_all_users()
        for user in users:
            wake_time = user.get("wake_time") or "07:00"
            self._register_job_for_wake_time(wake_time)

    async def _run_weather_update(self, hour: int, minute: int):
        """해당 wake_time 유저들 날씨 업데이트"""
        wake_time = f"{hour:02d}:{minute:02d}"
        users = get_all_users()
        for user in users:
            if user.get("wake_time") == wake_time:
                try:
                    await update_weather_for_user(self.bot, user)
                except Exception as e:
                    print(f"[날씨 오류] {user.get('user_id')}: {e}")
                    import traceback
                    traceback.print_exc()

    def register_user_job(self, wake_time: str):
        """온보딩 완료 후 외부에서 즉시 Job 등록 호출용"""
        self._register_job_for_wake_time(wake_time)

    @commands.command(name="weather")
    @commands.has_permissions(administrator=True)
    async def force_weather(self, ctx: commands.Context):
        """!weather — 전체 유저 날씨 즉시 업데이트 (관리자 전용)"""
        await ctx.send("🌤️ 날씨 즉시 업데이트 시작...", delete_after=5)
        users = get_all_users()
        for user in users:
            try:
                await update_weather_for_user(self.bot, user)
            except Exception as e:
                print(f"[날씨 즉시 오류] {user.get('user_id')}: {e}")
        await ctx.send(f"✅ 전체 유저 날씨 업데이트 완료! ({len(users)}명)", delete_after=10)

    def cog_unload(self):
        self.scheduler.shutdown()


async def setup(bot: commands.Bot):
    await bot.add_cog(WeatherCog(bot))
