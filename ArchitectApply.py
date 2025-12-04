# ------------------------------
# ArchitectApply.py
# ------------------------------

import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button, Modal, InputText

ARCHITECT_CATEGORY_ID = 1445455877283905621
ARCHITECT_ROLE_ID = 1445455534076592429
ARCHITECT_REVIEW_CHANNEL_ID = 1445457655555424347

ALLOWED_ADMIN_ROLE_IDS = [1442915362600648714, 1442996893901918291]


# ==========================================================
# 申請按鈕的審核 View
# ==========================================================
class ArchitectApplyView(View):
    def __init__(self, applicant_id, data):
        super().__init__(timeout=None)
        self.applicant_id = applicant_id
        self.data = data

    @discord.ui.button(label="通過", style=discord.ButtonStyle.success)
    async def approve(self, interaction: discord.Interaction, button: Button):

        # 權限檢查
        if not any(role.id in ALLOWED_ADMIN_ROLE_IDS for role in interaction.user.roles):
            await interaction.response.send_message("❌ 你沒有權限操作此按鈕。", ephemeral=True)
            return

        guild = interaction.guild
        member = guild.get_member(self.applicant_id)
        if not member:
            await interaction.response.send_message("❌ 申請者不在伺服器中。", ephemeral=True)
            return

        # 加建築師身分組
        role = guild.get_role(ARCHITECT_ROLE_ID)
        if role:
            await member.add_roles(role)

        # 創建建築師專屬頻道
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            member: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        category = guild.get_channel(ARCHITECT_CATEGORY_ID)
        channel_name = f"建築師-{member.display_name}"

        existing_channel = discord.utils.get(guild.channels, name=channel_name)
        if existing_channel:
            await interaction.response.send_message("⚠️ 頻道已存在。", ephemeral=True)
            return

        channel = await guild.create_text_channel(
            name=channel_name,
            overwrites=overwrites,
            category=category,
            topic=f"{member.display_name} 的建築師頻道"
        )

        # 卡片
        embed = discord.Embed(
            title=f"🏗 {member.display_name} 的建築師資訊",
            description="以下為玩家提交的建築師資料：",
            color=0x00FFAA
        )
        for k, v in self.data.items():
            embed.add_field(name=k, value=v, inline=False)

        await channel.send(embed=embed)
        await interaction.response.send_message(f"✅ 已通過 {member.display_name} 的申請。", ephemeral=True)
        await interaction.message.delete()

    @discord.ui.button(label="拒絕", style=discord.ButtonStyle.danger)
    async def reject(self, interaction: discord.Interaction, button: Button):

        if not any(role.id in ALLOWED_ADMIN_ROLE_IDS for role in interaction.user.roles):
            await interaction.response.send_message("❌ 你沒有權限操作此按鈕。", ephemeral=True)
            return

        member = interaction.guild.get_member(self.applicant_id)
        if member:
            try:
                await member.send("❌ 您的建築師申請未通過。")
            except:
                pass

        await interaction.response.send_message("❌ 已拒絕申請。", ephemeral=True)
        await interaction.message.delete()


# ==========================================================
# 申請表 Modal
# ==========================================================
class ArchitectApplyForm(Modal, title="建築師申請表"):

    name = InputText(label="你的暱稱")
    experience = InputText(label="建造經驗")
    style = InputText(label="擅長風格")
    contact = InputText(label="聯絡方式")

    async def callback(self, interaction: discord.Interaction):
        data = {
            "暱稱": self.name.value,
            "建造經驗": self.experience.value,
            "擅長風格": self.style.value,
            "聯絡方式": self.contact.value,
        }

        review_channel = interaction.guild.get_channel(ARCHITECT_REVIEW_CHANNEL_ID)

        embed = discord.Embed(
            title="📝 建築師申請表",
            color=0x00AAFF
        )
        for k, v in data.items():
            embed.add_field(name=k, value=v, inline=False)

        await review_channel.send(
            embed=embed,
            view=ArchitectApplyView(interaction.user.id, data)
        )

        await interaction.response.send_message("📩 已提交申請，等待審核！", ephemeral=True)


# ==========================================================
# Cog：包含 slash 指令
# ==========================================================
class ArchitectApply(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # 🔥 這就是你的 slash 指令
    @app_commands.command(name="申請建築師", description="開啟建築師申請表單")
    async def apply_architect(self, interaction: discord.Interaction):
        await interaction.response.send_modal(ArchitectApplyForm())


# ==========================================================
# 必要的 setup
# ==========================================================
async def setup(bot):
    await bot.add_cog(ArchitectApply(bot))
