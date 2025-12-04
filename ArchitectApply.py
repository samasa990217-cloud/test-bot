import discord
from discord.ext import commands
from discord import app_commands

ADMIN_IDS = [1442915362600648714, 1442996893901918291]  # 允許按按鈕的管理員身分組

class ReviewView(discord.ui.View):
    def __init__(self, user_data):
        super().__init__(timeout=None)
        self.user_data = user_data

    # -------------------------
    # 批准申請
    # -------------------------
    @discord.ui.button(label="批准申請", style=discord.ButtonStyle.green, custom_id="approve_architect")
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        # 只有指定身分組可以按按鈕
        if not any(role.id in ADMIN_IDS for role in interaction.user.roles):
            return await interaction.response.send_message("❌ 你沒有權限批准。", ephemeral=True)

        guild = interaction.guild

        # 創建專屬頻道
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        channel = await guild.create_text_channel(
            name=f"建築師-{self.user_data['player']}",
            overwrites=overwrites
        )

        await interaction.response.send_message(
            f"✅ 已批准申請！\n已建立專屬建築頻道：{channel.mention}",
            ephemeral=True
        )

    # -------------------------
    # 拒絕申請
    # -------------------------
    @discord.ui.button(label="拒絕申請", style=discord.ButtonStyle.red, custom_id="reject_architect")
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not any(role.id in ADMIN_IDS for role in interaction.user.roles):
            return await interaction.response.send_message("❌ 你沒有權限拒絕。", ephemeral=True)

        await interaction.response.send_message("❌ 已拒絕此申請。", ephemeral=True)


class ArchitectApply(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="申請建築師", description="提交建築師設計申請")
    async def apply_architect(
        self,
        interaction: discord.Interaction,
        遊戲名稱: str,
        遊戲莊園地址: str,
        風格: str,
        金額: str,
        補充: str = "無"
    ):

        user_data = {
            "player": 遊戲名稱,
            "address": 遊戲莊園地址,
            "style": 風格,
            "price": 金額,
            "extra": 補充
        }

        embed = discord.Embed(
            title="📨 建築師申請表",
            color=0x5865F2
        )
        embed.add_field(name="🎮 遊戲名稱", value=遊戲名稱, inline=False)
        embed.add_field(name="📍 莊園地址", value=遊戲莊園地址, inline=False)
        embed.add_field(name="🎨 風格需求", value=風格, inline=False)
        embed.add_field(name="💰 預算金額", value=金額, inline=False)
        embed.add_field(name="📝 補充描述", value=補充, inline=False)
        embed.set_footer(text=f"申請者：{interaction.user}")

        review_view = ReviewView(user_data)

        await interaction.response.send_message(
            "✅ 已提交申請！請等待管理員審核。",
            ephemeral=True
        )

        # 發送到審核頻道（你自己改 channel_id）
        review_channel = interaction.guild.get_channel(  # 🔥記得填自己的頻道
            1442916731927396403
        )
        await review_channel.send(embed=embed, view=review_view)


async def setup(bot):
    await bot.add_cog(ArchitectApply(bot))
