"""
run_all.py — 전체 봇 통합 실행 (개발용)

개발 중에는 이 파일 하나로 모든 봇을 실행해요.
프로덕션 환경에서는 PM2 등 프로세스 매니저 사용을 권장해요.

실행:
    python run_all.py
"""
import asyncio
import importlib
import traceback

BOTS = [
    ("bot",           "메인봇(다마고치)"),
    ("bot_weight",    "체중관리봇"),
    ("bot_meal",      "식사봇"),
    ("bot_weather",   "날씨봇"),
    ("bot_mail",      "메일봇"),
    ("bot_diary",     "일기봇"),
    ("bot_schedule",  "스케줄봇"),
]


async def run_bot(module_name: str, label: str):
    try:
        mod = importlib.import_module(module_name)
        await mod.main()
    except Exception as e:
        print(f"[{label}] 오류 발생: {e}")
        traceback.print_exc()


async def main():
    print("=" * 40)
    print("  먹구름 봇 통합 실행 시작")
    print("=" * 40)
    await asyncio.gather(*[run_bot(name, label) for name, label in BOTS])


if __name__ == "__main__":
    asyncio.run(main())
