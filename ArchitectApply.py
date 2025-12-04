# ------------------------------
# ArchitectApply.py
# ------------------------------
import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button

ARCHITECT_CATEGORY_ID = 1445455877283905621
ARCHITECT_ROLE_ID = 1445455534076592429
ALLOWED_ADMIN_ROLE_IDS = [1442915362600648714, 1442996893901918291]

# ------------------------------
# 申請按鈕的 View
# ------------------------------
class ArchitectApplyView(View):
    def __init__(self, bot, applicant_id, data):
        super().__init__(timeout=None)
        self.bot = bot
        self.applicant_id = applicant_id
        self.data = data

    @discord.ui.button(label="通過", style=discord.ButtonStyle.success)
    async def approve(self, interaction: discord.Interaction, button: Button):
        if not any(role.id in ALLOWED_ADMIN_ROLE_IDS for role in interaction.user.roles):
            await interaction.response.send_message("❌ 你沒有權限操作此按鈕。", ephemeral=True)
            return

        guild = interaction.guild
        member = guild.get_member(self.applicant_id)
        if not member:
            await interaction.response.send_message("❌ 申請者不在伺服器中。", ephemeral=True)
            return

        # ✅ 給建築師身分組
        role = guild.get_role(ARCHITECT_ROLE_ID)
        if role:
            await member.add_roles(role)

        # 存資料到 bot._architect_data
        if not hasattr(self.bot, "_architect_data"):
            self.bot._architect_data = {}
        self.bot._architect_data[member.id] = self.data

        # 創建專屬頻道
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

        # 發送申請資料卡片
        embed = discord.Embed(
            title=f"🏗 {member.display_name} 的建築師資訊",
            description="玩家提交的建築師卡片",
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


# ------------------------------
# Cog + Slash 指令
# ------------------------------
class ArchitectApply(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="申請建築師", description="提交建築師申請")
    @app_commands.describe(
        game_name="遊戲名稱",
        estate_address="遊戲莊園地址",
        style="風格",
        budget="金額",
        notes="補充"
    )
    async def apply(self, interaction: discord.Interaction,
                    game_name: str,
                    estate_address: str,
                    style: str,
                    budget: str,
                    notes: str):
        applicant_id = interaction.user.id
        data = {
            "遊戲名稱": game_name,
            "遊戲莊園地址": estate_address,
            "風格": style,
            "金額": budget,
            "補充": notes
        }

        # 發送給管理員審核
        embed = discord.Embed(
            title=f"🏗 {interaction.user.display_name} 的建築師申請",
            description="請管理員審核",
            color=0x00FFAA
        )
        for k, v in data.items():
            embed.add_field(name=k, value=v, inline=False)

        view = ArchitectApplyView(self.bot, applicant_id, data)

        review_channel = interaction.guild.get_channel(ARCHITECT_CATEGORY_ID)
        if not review_channel:
            await interaction.response.send_message("❌ 建築師審核頻道不存在", ephemeral=True)
            return

        await interaction.response.send_message(
            "✅ 已提交申請，等待管理員審核。",
            ephemeral=True
        )

        await review_channel.send(embed=embed, view=view)


# ------------------------------
# Cog setup
# ------------------------------
async def setup(bot):
    await bot.add_cog(ArchitectApply(bot))
