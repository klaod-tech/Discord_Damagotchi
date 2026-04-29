"""
all_bots.py — 전체 봇 일괄 실행
"""
import subprocess
import sys

BOTS = [
    "bot.py",
    "bot_mail.py",
    "bot_meal.py",
    "bot_weather.py",
    "bot_weight.py",
    "bot_diary.py",
    "bot_schedule.py",
]

if __name__ == "__main__":
    print("[all_bots] 봇 실행 시작...")
    processes = []
    for bot in BOTS:
        p = subprocess.Popen([sys.executable, bot])
        print(f"  ▶ {bot} (PID {p.pid})")
        processes.append(p)

    print(f"[all_bots] {len(BOTS)}개 봇 실행 중. 종료하려면 Ctrl+C\n")
    try:
        for p in processes:
            p.wait()
    except KeyboardInterrupt:
        print("\n[all_bots] 종료 중...")
        for p in processes:
            p.terminate()
        print("[all_bots] 전체 봇 종료 완료")
