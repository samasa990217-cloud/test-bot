import discord
from discord.ext import commands
from discord.ui import View, Button

ARCHITECT_CATEGORY_ID = 1445455877283905621
ARCHITECT_ROLE_ID = 1445455534076592429

class ArchitectOrderView(View):
    def __init__(self, user, architects):
        super().__init__(timeout=None)
        self.user = user
        self.architects = architects
        self.index = 0
        self.message = None
        self.update_embed()

    def update_embed(self):
        arch = self.architects[self.index]
        # 嘗試抓建築師頻道的 embed 資料
        guild = arch.guild
        channel_name = f"建築師-{arch.display_name}"
        channel = discord.utils.get(guild.channels, name=channel_name)
        embed = discord.Embed(
            title=f"🏗 {arch.display_name}",
            description="建築師資訊卡片",
            color=0x00FFAA
        )
        if channel:
            # 找頻道裡第一個 embed
            messages = channel.history(limit=50)
            # 因為是 async，之後要用 await
            # 暫時只存一個 placeholder
            embed.description += "\n❗ 資料可能抓不到歷史訊息"
        else:
            embed.add_field(name="⚠️ 注意", value="建築師頻道不存在，無法抓取資料", inline=False)
        self.embed = embed

    async def send_initial(self, channel):
        self.message = await channel.send(embed=self.embed, view=self)

    @discord.ui.button(label="上一個", style=discord.ButtonStyle.secondary)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index = (self.index - 1) % len(self.architects)
        await self.update_embed_with_data()
        await interaction.response.edit_message(embed=self.embed, view=self)

    @discord.ui.button(label="下一個", style=discord.ButtonStyle.secondary)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index = (self.index + 1) % len(self.architects)
        await self.update_embed_with_data()
        await interaction.response.edit_message(embed=self.embed, view=self)

    @discord.ui.button(label="聘請", style=discord.ButtonStyle.primary)
    async def hire(self, interaction: discord.Interaction, button: discord.ui.Button):
        arch = self.architects[self.index]
        guild = interaction.guild
        channel_name = f"建築師-{arch.display_name}"
        channel = discord.utils.get(guild.channels, name=channel_name)
        if not channel:
            return await interaction.response.send_message("❌ 建築師頻道不存在", ephemeral=True)
        # 授權使用者進入該頻道
        await channel.set_permissions(self.user, read_messages=True, send_messages=True)
        await interaction.response.send_message(
            f"✅ 已授權你進入 {arch.display_name} 的建築師頻道: {channel.mention}",
            ephemeral=True
        )

    async def update_embed_with_data(self):
        arch = self.architects[self.index]
        guild = arch.guild
        channel_name = f"建築師-{arch.display_name}"
        channel = discord.utils.get(guild.channels, name=channel_name)
        embed = discord.Embed(
            title=f"🏗 {arch.display_name}",
            description="建築師資訊卡片",
            color=0x00FFAA
        )
        if channel:
            async for msg in channel.history(limit=50):
                if msg.embeds:
                    old_embed = msg.embeds[0]
                    for field in old_embed.fields:
                        embed.add_field(name=field.name, value=field.value, inline=False)
                    break  # 只抓第一個 embed
        else:
            embed.add_field(name="⚠️ 注意", value="建築師頻道不存在，無法抓取資料", inline=False)
        self.embed = embed

class ArchitectOrder(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(name="找建築師", description="顯示建築師卡片並可聘請")
    async def find_architect(self, interaction: discord.Interaction):
        guild = interaction.guild
        role = guild.get_role(ARCHITECT_ROLE_ID)
        if not role:
            return await interaction.response.send_message("❌ 建築師身分組不存在", ephemeral=True)
        architects = [m for m in role.members if not m.bot]
        if not architects:
            return await interaction.response.send_message("❌ 目前沒有建築師", ephemeral=True)

        view = ArchitectOrderView(interaction.user, architects)
        await view.update_embed_with_data()  # 先抓資料
        await view.send_initial(interaction.channel)
        await interaction.response.send_message("✅ 建築師列表已生成", ephemeral=True)

async def setup(bot):
    await bot.add_cog(ArchitectOrder(bot))
