"""
utils/email_ui.py — 이메일 관련 공통 Modal 정의

먹구름 봇(settings.py)과 메일봇(email_monitor.py) 양쪽에서 import.
"""
import imaplib
import discord

from utils.db import (
    get_user, set_email_credentials, set_mail_thread_id, add_email_sender,
)


# ══════════════════════════════════════════════════════
# 이메일 설정 Modal
# ══════════════════════════════════════════════════════
class EmailSetupModal(discord.ui.Modal, title="📧 이메일 설정"):
    naver_id = discord.ui.TextInput(
        label="네이버 아이디",
        placeholder="예: klaod  (@naver.com 제외)",
        max_length=30,
    )
    app_pw = discord.ui.TextInput(
        label="앱 비밀번호",
        placeholder="네이버 보안설정 → 2단계 인증 → 앱 비밀번호",
        max_length=20,
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            user_id  = str(interaction.user.id)
            naver_id = self.naver_id.value.strip().replace("@naver.com", "")
            app_pw   = self.app_pw.value.strip()

            # IMAP 연결 테스트 + 현재 최대 UID 초기화 (기존 메일 무시)
            initial_uid = 0
            try:
                mail = imaplib.IMAP4_SSL("imap.naver.com", 993)
                mail.login(naver_id, app_pw)
                mail.select("INBOX")
                _, data = mail.uid("search", None, "ALL")
                if data and data[0]:
                    uids = data[0].split()
                    if uids:
                        initial_uid = int(uids[-1])
                mail.logout()
            except imaplib.IMAP4.error:
                await interaction.followup.send(
                    "❌ 로그인 실패!\n아이디 또는 앱 비밀번호를 확인해줘.\n"
                    "앱 비밀번호는 네이버 **보안설정 → 2단계 인증 → 앱 비밀번호**에서 발급받을 수 있어.",
                    ephemeral=True,
                )
                return

            set_email_credentials(user_id, naver_id, app_pw, initial_uid)

            # 메일 전용 스레드 생성 또는 유저 참여 보장
            user_data = get_user(user_id)
            mail_thread_id = user_data.get("mail_thread_id") if user_data else None
            existing_thread = None
            if mail_thread_id:
                for guild in interaction.client.guilds:
                    existing_thread = guild.get_thread(int(mail_thread_id))
                    if existing_thread:
                        break

            if existing_thread:
                await existing_thread.add_user(interaction.user)
            else:
                parent_channel = None
                tama_thread_id = user_data.get("thread_id") if user_data else None
                if tama_thread_id:
                    for guild in interaction.client.guilds:
                        t = guild.get_thread(int(tama_thread_id))
                        if t:
                            parent_channel = t.parent
                            break
                if not parent_channel:
                    ch = interaction.channel
                    parent_channel = ch.parent if isinstance(ch, discord.Thread) else ch

                mail_thread = await parent_channel.create_thread(
                    name=f"📧 {interaction.user.display_name}의 메일함",
                    auto_archive_duration=10080,
                )
                await mail_thread.add_user(interaction.user)
                set_mail_thread_id(user_id, str(mail_thread.id))
                await mail_thread.send(
                    f"📬 안녕, **{interaction.user.display_name}**!\n"
                    f"여기는 **메일 알림 전용 스레드**야.\n"
                    f"등록된 발신자에게서 메일이 오면 여기서 바로 알려줄게 ✉️"
                )

            await interaction.followup.send(
                f"✅ **{naver_id}@naver.com** 연결 완료!\n"
                f"이제 `📬 발신자 추가` 버튼으로 알림 받을 발신자를 등록해봐 📬",
                ephemeral=True,
            )
        except Exception as e:
            print(f"[EmailSetupModal 오류] {e}")
            await interaction.followup.send(f"❌ 오류: {e}", ephemeral=True)


# ══════════════════════════════════════════════════════
# 발신자 추가 Modal
# ══════════════════════════════════════════════════════
class SenderAddModal(discord.ui.Modal, title="📬 발신자 등록"):
    sender_email = discord.ui.TextInput(
        label="발신자 이메일",
        placeholder="예: boss@company.com",
        max_length=100,
    )
    nickname = discord.ui.TextInput(
        label="별명 (구분용)",
        placeholder="예: 사장님, 학교, 팀장",
        max_length=20,
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        user_id      = str(interaction.user.id)
        sender_email = self.sender_email.value.strip().lower()
        nickname     = self.nickname.value.strip()

        if "@" not in sender_email or "." not in sender_email.split("@")[-1]:
            await interaction.followup.send(
                "❌ 이메일 형식이 올바르지 않아!\n예: `boss@company.com`", ephemeral=True
            )
            return

        success = add_email_sender(user_id, sender_email, nickname)
        if success:
            await interaction.followup.send(
                f"✅ **{nickname}** (`{sender_email}`) 등록 완료!\n"
                f"앞으로 이 주소에서 메일이 오면 여기에 알려줄게 📩",
                ephemeral=True,
            )
        else:
            await interaction.followup.send(
                f"⚠️ `{sender_email}` 은 이미 등록된 발신자야!", ephemeral=True
            )
