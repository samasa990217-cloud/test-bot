import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button
import asyncio

ARCHITECT_CATEGORY_ID = 1445455877283905621
ARCHITECT_ROLE_ID = 1445455534076592429

# ------------------------------
# 1️⃣ 建築師固定頻道按鈕
# ------------------------------
class ArchitectOrderView(View):
    def __init__(self, client_member, architect_member):
        super().__init__(timeout=None)
        self.client_member = client_member
        self.architect_member = architect_member

    @discord.ui.button(label="結束委託", style=discord.ButtonStyle.danger)
    async def end_order(self, interaction: discord.Interaction, button: Button):
        # 對客戶收回頻道權限
        await interaction.channel.set_permissions(self.client_member, read_messages=False, send_messages=False)
        await interaction.response.send_message(f"✅ 已結束 {self.client_member.display_name} 的委託，對他不再顯示此頻道。", ephemeral=True)

    @discord.ui.button(label="離開頻道", style=discord.ButtonStyle.secondary)
    async def leave_order(self, interaction: discord.Interaction, button: Button):
        # 對點擊者收回權限
        await interaction.channel.set_permissions(interaction.user, read_messages=False, send_messages=False)
        await interaction.response.send_message("✅ 您已離開此頻道，不再顯示。", ephemeral=True)

# ------------------------------
# 2️⃣ 找建築師翻頁 + 聘請
# ------------------------------
class ArchitectBrowseView(View):
    def __init__(self, user, architects, index=0):
        super().__init__(timeout=None)
        self.user = user
        self.architects = architects
        self.index = index

    async def update_embed(self, interaction: discord.Interaction):
        arch = self.architects[self.index]
        # 找建築師固定頻道
        guild = interaction.guild
        channel_name = f"建築師-{arch.display_name}"
        channel = discord.utils.get(guild.channels, name=channel_name)

        embed = discord.Embed(
            title=f"🏗 {arch.display_name}",
            description=f"建築師資訊卡片",
            color=0x00FFAA
        )
        embed.add_field(name="固定頻道", value=channel.mention if channel else "未建立", inline=False)
        await interaction.message.edit(embed=embed, view=self)

    @discord.ui.button(label="上一個", style=discord.ButtonStyle.secondary)
    async def prev_architect(self, interaction: discord.Interaction, button: Button):
        self.index = (self.index - 1) % len(self.architects)
        await self.update_embed(interaction)
        await interaction.response.defer()  # 不發新訊息

    @discord.ui.button(label="下一個", style=discord.ButtonStyle.secondary)
    async def next_architect(self, interaction: discord.Interaction, button: Button):
        self.index = (self.index + 1) % len(self.architects)
        await self.update_embed(interaction)
        await interaction.response.defer()

    @discord.ui.button(label="聘請", style=discord.ButtonStyle.success)
    async def hire(self, interaction: discord.Interaction, button: Button):
        arch = self.architects[self.index]
        guild = interaction.guild
        channel_name = f"建築師-{arch.display_name}"
        channel = discord.utils.get(guild.channels, name=channel_name)
        if not channel:
            await interaction.response.send_message("❌ 該建築師的頻道不存在。", ephemeral=True)
            return
        # 給聘請者加入該頻道
        await channel.set_permissions(interaction.user, read_messages=True, send_messages=True)
        # 也給建築師確認權限（如果尚未給）
        await channel.set_permissions(arch, read_messages=True, send_messages=True)
        # 附加固定頻道的按鈕
        view = ArchitectOrderView(interaction.user, arch)
        await channel.send(f"👷 {interaction.user.mention} 已加入 {arch.mention} 的建築師頻道", view=view)
        await interaction.response.send_message(f"✅ 已加入 {arch.display_name} 的建築師頻道：{channel.mention}", ephemeral=True)

# ------------------------------
# 3️⃣ Cog 指令
# ------------------------------
class ArchitectOrder(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="找建築師", description="顯示建築師卡片並可聘請")
    async def find_architect(self, interaction: discord.Interaction):
        guild = interaction.guild
        role = guild.get_role(ARCHITECT_ROLE_ID)
        if not role:
            await interaction.response.send_message("❌ 建築師身分組不存在", ephemeral=True)
            return
        architects = [m for m in role.members if not m.bot]
        if not architects:
            await interaction.response.send_message("❌ 目前沒有建築師", ephemeral=True)
            return

        view = ArchitectBrowseView(interaction.user, architects)
        arch = architects[0]
        # 找建築師固定頻道
        channel_name = f"建築師-{arch.display_name}"
        channel = discord.utils.get(guild.channels, name=channel_name)

        embed = discord.Embed(
            title=f"🏗 {arch.display_name}",
            description=f"建築師資訊卡片",
            color=0x00FFAA
        )
        embed.add_field(name="固定頻道", value=channel.mention if channel else "未建立", inline=False)

        await interaction.response.send_message(embed=embed, view=view, ephemeral=False)

# ------------------------------
# 4️⃣ setup
# ------------------------------
async def setup(bot):
    await bot.add_cog(ArchitectOrder(bot))
