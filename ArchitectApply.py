import discord
from discord.ext import commands
from discord.ui import View, Button

ARCHITECT_CATEGORY_ID = 1445455877283905621
ARCHITECT_ROLE_ID = 1445455534076592429
ARCHITECT_REVIEW_CHANNEL_ID = 1445457655555424347

ALLOWED_ADMIN_ROLE_IDS = [1442915362600648714, 1442996893901918291]

class ArchitectApplyView(View):
    def __init__(self, applicant_id, data, bot):
        super().__init__(timeout=None)
        self.applicant_id = applicant_id
        self.data = data
        self.bot = bot  # 保存 bot 參考，用來存資料

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

        # 加建築師身分組
        role = guild.get_role(ARCHITECT_ROLE_ID)
        if role:
            await member.add_roles(role)

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

        # 儲存申請資料到 bot._architect_data
        if not hasattr(self.bot, "_architect_data"):
            self.bot._architect_data = {}
        self.bot._architect_data[member.id] = self.data

        # 發送卡片到專屬頻道
        embed = discord.Embed(
            title=f"🏗 {member.display_name} 的建築師資訊",
            description="玩家申請的建築師卡片",
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


class ArchitectApply(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


async def setup(bot):
    await bot.add_cog(ArchitectApply(bot))                    extra: str):
        # 整理資料
        data = {
            "遊戲名稱": game_name,
            "遊戲莊園地址": manor_address,
            "風格": style,
            "金額": price,
            "補充": extra
        }

        # 發送到審核頻道
        review_channel = interaction.guild.get_channel(ARCHITECT_REVIEW_CHANNEL_ID)
        if not review_channel:
            await interaction.response.send_message("❌ 審核頻道不存在", ephemeral=True)
            return

        view = ArchitectApplyView(interaction.user.id, data)
        embed = discord.Embed(
            title=f"🏗 {interaction.user.display_name} 的建築師申請",
            color=0x00FFAA
        )
        for k, v in data.items():
            embed.add_field(name=k, value=v, inline=False)

        await review_channel.send(embed=embed, view=view)
        await interaction.response.send_message("✅ 已提交建築師申請，請等待管理員審核。", ephemeral=True)


# ==========================================================
# Cog setup
# ==========================================================
async def setup(bot):
    await bot.add_cog(ArchitectApply(bot))
    

