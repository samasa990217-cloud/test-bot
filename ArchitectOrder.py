import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button

ARCHITECT_CATEGORY_ID = 1445455877283905621
ARCHITECT_ROLE_ID = 1445455534076592429

# 專屬頻道按鈕
class ArchitectOrderView(View):
    def __init__(self, client_member, architect_member):
        super().__init__(timeout=None)
        self.client_member = client_member
        self.architect_member = architect_member

    @discord.ui.button(label="結束委託", style=discord.ButtonStyle.danger)
    async def end_order(self, interaction: discord.Interaction, button: Button):
        await interaction.channel.set_permissions(self.client_member, read_messages=False, send_messages=False)
        await interaction.response.send_message(
            f"✅ 已結束 {self.client_member.display_name} 的委託，不再顯示此頻道。", ephemeral=True
        )

    @discord.ui.button(label="離開頻道", style=discord.ButtonStyle.secondary)
    async def leave_order(self, interaction: discord.Interaction, button: Button):
        await interaction.channel.set_permissions(interaction.user, read_messages=False, send_messages=False)
        await interaction.response.send_message("✅ 您已離開此頻道，不再顯示。", ephemeral=True)


# 瀏覽建築師 + 聘請
class ArchitectBrowseView(View):
    def __init__(self, user, architects, architect_data, index=0):
        super().__init__(timeout=None)
        self.user = user
        self.architects = architects
        self.index = index
        self.architect_data = architect_data

    async def update_embed(self, interaction: discord.Interaction):
        arch = self.architects[self.index]
        data = self.architect_data.get(arch.id, {})
        guild = interaction.guild
        channel_name = f"建築師-{arch.display_name}"
        channel = discord.utils.get(guild.channels, name=channel_name)

        embed = discord.Embed(
            title=f"🏗 {arch.display_name}",
            description="建築師資訊卡片",
            color=0x00FFAA
        )
        if data:
            for k, v in data.items():
                embed.add_field(name=k, value=v, inline=False)
        embed.add_field(name="固定頻道", value=channel.mention if channel else "未建立", inline=False)

        await interaction.message.edit(embed=embed, view=self)

    @discord.ui.button(label="上一個", style=discord.ButtonStyle.secondary)
    async def prev_architect(self, interaction: discord.Interaction, button: Button):
        self.index = (self.index - 1) % len(self.architects)
        await self.update_embed(interaction)
        await interaction.response.defer()

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

        await channel.set_permissions(interaction.user, read_messages=True, send_messages=True)
        await channel.set_permissions(arch, read_messages=True, send_messages=True)
        view = ArchitectOrderView(interaction.user, arch)
        await channel.send(f"👷 {interaction.user.mention} 已加入 {arch.mention} 的建築師頻道", view=view)
        await interaction.response.send_message(
            f"✅ 已加入 {arch.display_name} 的建築師頻道：{channel.mention}", ephemeral=True
        )


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

        architect_data = getattr(self.bot, "_architect_data", {})

        view = ArchitectBrowseView(interaction.user, architects, architect_data)
        arch = architects[0]
        data = architect_data.get(arch.id, {})

        channel_name = f"建築師-{arch.display_name}"
        channel = discord.utils.get(guild.channels, name=channel_name)
        embed = discord.Embed(
            title=f"🏗 {arch.display_name}",
            description="建築師資訊卡片",
            color=0x00FFAA
        )
        if data:
            for k, v in data.items():
                embed.add_field(name=k, value=v, inline=False)
        embed.add_field(name="固定頻道", value=channel.mention if channel else "未建立", inline=False)

        await interaction.response.send_message(embed=embed, view=view, ephemeral=False)


async def setup(bot):
    await bot.add_cog(ArchitectOrder(bot))    # ==============================
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

        # 如果你有保存申請資料
        architect_data = getattr(self.bot, "_architect_data", {})

        view = ArchitectBrowseView(interaction.user, architects, architect_data)
        arch = architects[0]
        data = architect_data.get(arch.id, {})

        channel_name = f"建築師-{arch.display_name}"
        channel = discord.utils.get(guild.channels, name=channel_name)

        embed = discord.Embed(
            title=f"🏗 {arch.display_name}",
            description="建築師資訊卡片",
            color=0x00FFAA
        )
        if data:
            for k, v in data.items():
                embed.add_field(name=k, value=v, inline=False)
        embed.add_field(name="固定頻道", value=channel.mention if channel else "未建立", inline=False)

        await interaction.response.send_message(embed=embed, view=view, ephemeral=False)


# ------------------------------
# Cog setup
# ------------------------------
async def setup(bot: commands.Bot):
    await bot.add_cog(ArchitectOrder(bot))

