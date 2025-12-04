import discord
from discord.ext import commands
from discord.ui import View, Button
from discord import app_commands
import asyncio

ARCHITECT_CATEGORY_ID = 1445455877283905621
ARCHITECT_ROLE_ID = 1445455534076592429
ARCHITECT_REVIEW_CHANNEL_ID = 1445457655555424347

class ArchitectApplyView(View):
    def __init__(self, applicant_id, data):
        super().__init__(timeout=None)
        self.applicant_id = applicant_id
        self.data = data

    @discord.ui.button(label="通過", style=discord.ButtonStyle.success)
    async def approve(self, interaction: discord.Interaction, button: Button):
        guild = interaction.guild
        member = guild.get_member(self.applicant_id)
        if not member:
            await interaction.response.send_message("❌ 申請者不在伺服器中。", ephemeral=True)
            return
        # 加建築師身分組
        role = guild.get_role(ARCHITECT_ROLE_ID)
        if role:
            await member.add_roles(role)
        # 創建永久頻道
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
        # 發卡片
        embed = discord.Embed(
            title=f"🏗 {member.display_name} 的建築師資訊",
            description="這是玩家申請的建築師卡片",
            color=0x00FFAA
        )
        for k, v in self.data.items():
            embed.add_field(name=k, value=v, inline=False)
        await channel.send(embed=embed)
        await interaction.response.send_message(f"✅ 已通過 {member.display_name} 的申請，永久頻道已建立。", ephemeral=True)
        await interaction.message.delete()

    @discord.ui.button(label="拒絕", style=discord.ButtonStyle.danger)
    async def reject(self, interaction: discord.Interaction, button: Button):
        member = interaction.guild.get_member(self.applicant_id)
        if member:
            await member.send("❌ 您的建築師申請未通過。")
        await interaction.response.send_message(f"❌ 已拒絕 {member.display_name if member else '申請者'} 的申請。", ephemeral=True)
        await interaction.message.delete()

class ArchitectApply(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.command_status = {
            "申請建築師": False
        }

    @app_commands.command(name="申請建築師", description="申請成為建築師")
    async def apply_architect(self, interaction: discord.Interaction):
        if self.command_status["申請建築師"] in [True, "維修"]:
            return await interaction.response.send_message("🟡 指令忙碌或維修中", ephemeral=True)
        self.command_status["申請建築師"] = True
        try:
            await interaction.response.send_message(
                "請依序輸入下列資訊（在聊天中回覆）：\n1️⃣ 您的姓名\n2️⃣ 遊戲住宅位置\n3️⃣ 建築風格\n4️⃣ 價格\n5️⃣ 補充（可選）", ephemeral=True
            )

            def check(m): return m.author == interaction.user and m.channel == interaction.channel

            answers = {}
            questions = ["建築師名稱", "遊戲住宅位置", "建築風格", "價格", "補充（可選）"]
            for q in questions:
                msg = await self.bot.wait_for("message", check=check, timeout=120)
                answers[q] = msg.content
                await msg.delete()

            # 送到審核頻道
            review_channel = self.bot.get_channel(ARCHITECT_REVIEW_CHANNEL_ID)
            if not review_channel:
                return await interaction.followup.send("❌ 審核頻道不存在", ephemeral=True)
            view = ArchitectApplyView(interaction.user.id, answers)
            embed = discord.Embed(
                title="🏗 新建築師申請",
                description=f"玩家 {interaction.user.mention} 申請成為建築師，請管理員審核。",
                color=0xFFA500
            )
            for k, v in answers.items():
                embed.add_field(name=k, value=v, inline=False)
            await review_channel.send(embed=embed, view=view)
            await interaction.followup.send("✅ 申請已送出，等待管理員審核。", ephemeral=True)
        except asyncio.TimeoutError:
            await interaction.followup.send("❌ 申請超時，請重新操作。", ephemeral=True)
        finally:
            self.command_status["申請建築師"] = False

async def setup(bot):
    await bot.add_cog(ArchitectApply(bot))
