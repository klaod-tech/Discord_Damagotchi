"""
cogs/email_monitor.py — 이메일 수신 모니터링 (메일봇 전용)

스케줄: 1분마다 전체 이메일 설정 유저 폴링
흐름:
  IMAP 수신 → 스팸 필터 → 등록 발신자 확인
  → GPT 요약 → Discord 스레드 알림 → email_log 저장

슬래시 커맨드:
  /이메일설정   — Naver 계정 + 앱 비밀번호 등록
  /발신자추가   — 알림 받을 발신자 이메일 등록
  /발신자목록   — 등록된 발신자 목록 조회
  /발신자삭제   — 발신자 삭제
"""
import asyncio
import discord
from discord import app_commands
from discord.ext import commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from utils.db import (
    get_email_users, get_email_senders,
    update_email_last_uid, save_email_log, get_user,
)
from utils.email_ui import EmailSetupModal, SenderAddModal
from utils.mail import fetch_new_emails
from utils.gpt import summarize_email


# ══════════════════════════════════════════════════════
# 이메일 모니터링 Cog
# ══════════════════════════════════════════════════════
class EmailMonitorCog(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot       = bot
        self.scheduler = AsyncIOScheduler(timezone="Asia/Seoul")
        self.scheduler.add_job(
            self._poll_all_users,
            trigger="interval",
            minutes=1,
            id="email_poll",
        )
        self.scheduler.start()
        print("[이메일] 모니터링 스케줄러 시작 (1분 간격)")

    # ── 1분마다 전체 유저 폴링 ────────────────────────
    async def _poll_all_users(self):
        users = get_email_users()
        if not users:
            return
        for user in users:
            await self._poll_user(user)

    async def _poll_user(self, user: dict):
        user_id   = str(user["user_id"])
        naver_id  = user.get("naver_email", "")
        app_pw    = user.get("naver_app_pw", "")
        last_uid  = int(user.get("email_last_uid") or 0)

        senders_rows = get_email_senders(user_id)
        registered   = [row["sender_email"] for row in senders_rows]
        nickname_map = {row["sender_email"]: row["nickname"] for row in senders_rows}

        if not registered:
            return

        try:
            loop = asyncio.get_event_loop()
            new_emails, max_uid = await loop.run_in_executor(
                None,
                fetch_new_emails,
                naver_id, app_pw, registered, last_uid,
            )
        except Exception as e:
            print(f"[이메일 폴링 오류] {user_id}: {e}")
            return

        if max_uid > last_uid:
            update_email_last_uid(user_id, max_uid)

        if not new_emails:
            return

        # 메일 전용 스레드 가져오기
        user_data      = get_user(user_id)
        mail_thread_id = user_data.get("mail_thread_id") if user_data else None
        thread         = None
        if mail_thread_id:
            for guild in self.bot.guilds:
                thread = guild.get_thread(int(mail_thread_id))
                if thread:
                    break

        for mail_item in new_emails:
            sender_email = mail_item["sender_email"]
            sender_name  = mail_item["sender_name"] or sender_email
            nickname     = nickname_map.get(sender_email, sender_name)
            subject      = mail_item["subject"]
            body         = mail_item["body"]
            sent_at      = mail_item.get("sent_at")
            sent_at_str  = (
                sent_at.strftime("%Y년 %m월 %d일 %H:%M")
                if sent_at else "알 수 없음"
            )

            body_stripped = body.strip()
            if len(body_stripped) <= 200:
                summary = body_stripped or "(본문 없음)"
            else:
                try:
                    summary = await summarize_email(subject, body)
                except Exception as e:
                    print(f"[이메일 요약 오류] {e}")
                    summary = "요약을 가져오지 못했어요."

            save_email_log(user_id, sender_email, subject, summary)

            if thread:
                embed = discord.Embed(
                    title=f"📧 새 메일 — {nickname}",
                    color=0x03C75A,
                )
                embed.add_field(
                    name="보낸 사람",
                    value=f"{nickname} (`{sender_email}`)",
                    inline=True,
                )
                embed.add_field(name="📅 발송 일시", value=sent_at_str, inline=True)
                embed.add_field(name="제목", value=subject or "(제목 없음)", inline=False)
                embed.add_field(name="📝 요약", value=summary, inline=False)
                embed.set_footer(text="네이버 메일에서 전체 내용을 확인하세요.")
                await thread.send(embed=embed)
                print(f"[이메일] {user_id} → Discord 알림 전송: {subject}")

    # ── 슬래시 커맨드 ─────────────────────────────────

    @app_commands.command(name="이메일설정", description="네이버 메일 연동 설정")
    async def email_setup(self, interaction: discord.Interaction):
        print(f"[CMD] /이메일설정 — {interaction.user}")
        await interaction.response.send_modal(EmailSetupModal())

    @app_commands.command(name="발신자추가", description="알림 받을 발신자 이메일 등록")
    async def sender_add(self, interaction: discord.Interaction):
        print(f"[CMD] /발신자추가 — {interaction.user}")
        user = get_user(str(interaction.user.id))
        if not user or not user.get("naver_email"):
            await interaction.response.send_message(
                "❌ 먼저 `/이메일설정`으로 네이버 계정을 연동해줘!", ephemeral=True
            )
            return
        await interaction.response.send_modal(SenderAddModal())

    @app_commands.command(name="발신자목록", description="등록된 발신자 목록 확인")
    async def sender_list(self, interaction: discord.Interaction):
        print(f"[CMD] /발신자목록 — {interaction.user}")
        user_id = str(interaction.user.id)
        senders = get_email_senders(user_id)
        if not senders:
            await interaction.response.send_message(
                "등록된 발신자가 없어!\n`/발신자추가`로 추가해봐 📬", ephemeral=True
            )
            return
        lines = [
            f"`{i+1}.` **{row['nickname']}** — `{row['sender_email']}`"
            for i, row in enumerate(senders)
        ]
        embed = discord.Embed(
            title="📋 등록된 발신자 목록",
            description="\n".join(lines),
            color=0x5865F2,
        )
        embed.set_footer(text="삭제하려면 /발신자삭제 를 사용해줘")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="발신자삭제", description="등록된 발신자 삭제")
    @app_commands.describe(sender_email="삭제할 발신자 이메일")
    async def sender_remove(self, interaction: discord.Interaction, sender_email: str):
        print(f"[CMD] /발신자삭제 — {interaction.user} / {sender_email}")
        user_id = str(interaction.user.id)
        from utils.db import remove_email_sender
        success = remove_email_sender(user_id, sender_email.strip())
        if success:
            await interaction.response.send_message(
                f"✅ `{sender_email}` 삭제 완료!", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"❌ `{sender_email}` 은 등록되지 않은 발신자야.", ephemeral=True
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(EmailMonitorCog(bot))
