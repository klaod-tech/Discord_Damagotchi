"""
utils/thread_helper.py — 봇별 쓰레드 자동 참여 공용 헬퍼

각 전용봇(식사/날씨/메일/체중)이 담당 쓰레드에 join하기 위해 사용.
"""
import discord


async def join_assigned_threads(bot: discord.ext.commands.Bot, thread_field: str):
    """DB에서 thread_field에 해당하는 쓰레드 ID를 조회해 전부 join."""
    from utils.db import get_all_users
    for user_data in get_all_users():
        tid = user_data.get(thread_field)
        if not tid:
            continue
        for guild in bot.guilds:
            try:
                t = guild.get_thread(int(tid))
                if t is None:
                    t = await guild.fetch_channel(int(tid))
                if isinstance(t, discord.Thread):
                    await t.join()
            except Exception:
                pass


async def join_if_mine(bot: discord.ext.commands.Bot, thread: discord.Thread, thread_field: str):
    """신규 생성된 쓰레드가 담당 쓰레드이면 join. DB 저장 완료를 기다려 3초 후 조회."""
    import asyncio
    print(f"[join_if_mine] 호출됨 — thread={thread.id} ({thread.name}), field={thread_field}")
    await asyncio.sleep(3)
    from utils.db import get_all_users
    for user_data in get_all_users():
        if str(user_data.get(thread_field, "")) == str(thread.id):
            try:
                await thread.join()
                print(f"[join_if_mine] 성공 — {thread.id}")
            except Exception as e:
                print(f"[join_if_mine] 실패 — {e}")
            return
    print(f"[join_if_mine] 매칭 없음 — {thread.id}")
