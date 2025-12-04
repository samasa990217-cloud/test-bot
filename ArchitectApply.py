# ------------------------------
# ArchitectApply.py
# ------------------------------

import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button

ARCHITECT_CATEGORY_ID = 1445455877283905621      # 建築師私人頻道分類
ARCHITECT_ROLE_ID = 1445455534076592429          # 建築師角色
REVIEW_CHANNEL_ID = 1445457655555424347          # 審核頻道
ALLOWED_ADMIN_ROLE_IDS = [1442915362600648714, 1442996893901918291]  # 管理員角色

# ------------------------------
# 審核按鈕 view
# ------------------------------
class ArchitectApplyReviewView(View):
    def __init__(self, applicant_id, data, bot):
        super().__init__(timeout=None)
        self.applicant_id = applicant_id
        self.data = data
        self.bot = bot
        self.message = None

    def user_is_admin(self, interaction: discord.Interaction):
        return any(role.id in ALLOWED_ADMIN_ROLE_IDS for role in interaction.user.roles)

    @discord.ui.button(label="通過", style=discord.ButtonStyle.success)
    async def approve(self, interaction: discord.Interaction, button: Button):
        if not self.user_is_admin(interaction):
            await interaction.response.send_message("❌ 你沒有權限。", ephemeral=True)
            return

        guild = interaction.guild
        member = guild.get_member(self.applicant_id)
        if not member:
            await interaction.response.send_message("❌ 玩家已不在伺服器。", ephemeral=True)
            return

        # 加建築師角色
        role = guild.get_role(ARCHITECT_ROLE_ID)
        if role:
            await member.add_roles(role)

        # 建立專屬頻道
        category = guild.get_channel(ARCHITECT_CATEGORY_ID)
        if not category:
            await interaction.response.send_message("❌ 無法找到建築師分類。", ephemeral=True)
            return

        channel_name = f"建築師-{member.display_name}"
        existing = discord.utils.get(guild.channels, name=channel_name)
        if existing:
            await interaction.response.send_message("⚠️ 此玩家的建築師專屬頻道已存在。", ephemeral=True)
            return

        overwrites = {guild.default_role: discord.PermissionOverwrite(read_messages=False),
                      member: discord.PermissionOverwrite(read_messages=True, send_messages=True)}

        # 管理員可讀
        for role_id in ALLOWED_ADMIN_ROLE_IDS:
            admin_role = guild.get_role(role_id)
            if admin_role:
                overwrites[admin_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        channel = await guild.create_text_channel(
            name=channel_name,
            category=category,
            overwrites=overwrites,
            topic=f"{member.display_name} 的建築師專屬頻道"
        )

        # 存玩家申請資料
        if not hasattr(self.bot, "_architect_data"):
            self.bot._architect_data = {}
        self.bot._architect_data[member.id] = self.data

        # 發卡片到專屬頻道
        embed = discord.Embed(
            title=f"🏗 {member.display_name} 的建築師卡片",
            color=0x00FFAA
        )
        for k, v in self.data.items():
            embed.add_field(name=k, value=v, inline=False)
        await channel.send(embed=embed)

        await interaction.response.send_message("✅ 已通過申請並建立專屬頻道。", ephemeral=True)

        # 刪除審核訊息
        try:
            if self.message:
                await self.message.delete()
        except:
            pass

    @discord.ui.button(label="拒絕", style=discord.ButtonStyle.danger)
    async def reject(self, interaction: discord.Interaction, button: Button):
        if not self.user_is_admin(interaction):
            await interaction.response.send_message("❌ 你沒有權限。", ephemeral=True)
            return

        member = interaction.guild.get_member(self.applicant_id)
        if member:
            try:
                await member.send("❌ 您的建築師申請未通過。")
            except:
                pass

        await interaction.response.send_message("❌ 已拒絕該申請。", ephemeral=True)

        # 刪除審核訊息
        try:
            if self.message:
                await self.message.delete()
        except:
            pass

# ------------------------------
# Slash 指令：申請建築師
# ------------------------------
class ArchitectApply(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        if not hasattr(bot, "_architect_data"):
            bot._architect_data = {}

    @app_commands.command(name="申請建築師", description="提交建築師申請")
    async def apply_architect(
        self,
        interaction: discord.Interaction,
        遊戲名稱: str,
        遊戲莊園地址: str,
        風格: str,
        金額: str,
        補充: str = "無"
    ):
        await interaction.response.send_message("✅ 已提交申請，等待管理員審核。", ephemeral=True)

        guild = interaction.guild
        review_channel = guild.get_channel(REVIEW_CHANNEL_ID)
        if not review_channel:
            print(f"[錯誤] 找不到審核頻道 ID：{REVIEW_CHANNEL_ID}")
            return

        data = {
            "遊戲名稱": 遊戲名稱,
            "莊園地址": 遊戲莊園地址,
            "風格": 風格,
            "金額": 金額,
            "補充": 補充
        }

        embed = discord.Embed(
            title=f"📨 建築師申請 — {interaction.user.display_name}",
            color=0xFFA500
        )
        for k, v in data.items():
            embed.add_field(name=k, value=v, inline=False)

        review_view = ArchitectApplyReviewView(interaction.user.id, data, self.bot)
        msg = await review_channel.send(embed=embed, view=review_view)
        review_view.message = msg

# ------------------------------
# Cog setup
# ------------------------------
async def setup(bot):
    await bot.add_cog(ArchitectApply(bot))
