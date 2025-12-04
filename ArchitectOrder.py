import discord
from discord.ext import commands
from discord.ui import View, Button

ARCHITECT_CATEGORY_ID = 1445455877283905621

class ArchitectOrderView(View):
    def __init__(self, client_member, architect_member):
        super().__init__(timeout=None)
        self.client_member = client_member
        self.architect_member = architect_member
        self.add_item(Button(label="結束委託", style=discord.ButtonStyle.danger, custom_id="end_order"))
        self.add_item(Button(label="離開頻道", style=discord.ButtonStyle.secondary, custom_id="leave_order"))

    @discord.ui.button(label="結束委託", style=discord.ButtonStyle.danger, custom_id="end_order")
    async def end_order(self, interaction: discord.Interaction, button: Button):
        channel = interaction.channel
        await channel.set_permissions(self.client_member, read_messages=False, send_messages=False)
        await interaction.response.send_message(f"✅ 已結束 {self.client_member.display_name} 的委託。", ephemeral=True)

    @discord.ui.button(label="離開頻道", style=discord.ButtonStyle.secondary, custom_id="leave_order")
    async def leave_order(self, interaction: discord.Interaction, button: Button):
        channel = interaction.channel
        await channel.set_permissions(interaction.user, read_messages=False, send_messages=False)
        await interaction.response.send_message("✅ 已離開頻道。", ephemeral=True)

class ArchitectOrder(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(name="找建築師", description="顯示建築師卡片並可聘請")
    async def find_architect(self, interaction: discord.Interaction):
        guild = interaction.guild
        role = guild.get_role(1445455534076592429)
        if not role:
            return await interaction.response.send_message("❌ 建築師身分組不存在", ephemeral=True)
        architects = [m for m in role.members if m.bot == False]
        if not architects:
            return await interaction.response.send_message("❌ 目前沒有建築師", ephemeral=True)
        # 目前只顯示第一個建築師作為示範
        arch = architects[0]
        embed = discord.Embed(
            title=f"🏗 {arch.display_name}",
            description="建築師資訊卡片",
            color=0x00FFAA
        )
        view = View(timeout=None)
        view.add_item(Button(label="聘請", style=discord.ButtonStyle.primary, custom_id=f"hired_{arch.id}"))
        await interaction.response.send_message(embed=embed, view=view, ephemeral=False)

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type != discord.InteractionType.component:
            return
        custom_id = interaction.data.get("custom_id", "")
        if custom_id.startswith("hired_"):
            arch_id = int(custom_id.split("_")[1])
            arch_member = interaction.guild.get_member(arch_id)
            client_member = interaction.user
            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                client_member: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                arch_member: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }
            category = interaction.guild.get_channel(ARCHITECT_CATEGORY_ID)
            channel_name = f"工作-{client_member.display_name}-{arch_member.display_name}"
            existing = discord.utils.get(interaction.guild.channels, name=channel_name)
            if existing:
                await interaction.response.send_message("⚠️ 工作頻道已存在。", ephemeral=True)
                return
            channel = await interaction.guild.create_text_channel(
                name=channel_name,
                overwrites=overwrites,
                category=category,
                topic=f"{client_member.display_name} 聘請 {arch_member.display_name}"
            )
            view = ArchitectOrderView(client_member, arch_member)
            await channel.send(f"👷 {client_member.mention} 已聘請 {arch_member.mention}", view=view)
            await interaction.response.send_message(f"✅ 已創建工作頻道 {channel.mention}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(ArchitectOrder(bot))
