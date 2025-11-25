import discord
from discord.ext import commands
from discord import app_commands
import os
import datetime
from flask import Flask
import threading

# ---------- Flask Keep-Alive ----------
app = Flask("")

@app.route("/")
def home():
    return "Discord Bot is running!"

def run_flask():
    app.run(host="0.0.0.0", port=10000)

threading.Thread(target=run_flask).start()

# ---------- Discord Bot 設定 ----------
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# 角色ID
VERIFIED_ROLE_ID = 1442916731927396403
BUYERS_ROLE_ID = 1442915193704157235
TRADE_CATEGORY_ID = 123456789012345678
WAIT_TIME = 60
LOG_FOLDER = "trade_logs"

if not os.path.exists(LOG_FOLDER):
    os.makedirs(LOG_FOLDER)

# ---------- Bot Ready ----------
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    try:
        await bot.tree.sync()
        print("Slash commands synced.")
    except Exception as e:
        print(e)

# ---------- /公告 指令 ----------
@bot.tree.command(name="公告", description="發布一則公告")
async def announce(interaction: discord.Interaction):
    await interaction.response.send_message("📝 請輸入公告內容:", ephemeral=True)
    def check(m): return m.author == interaction.user and m.channel == interaction.channel
    try:
        msg = await bot.wait_for('message', check=check, timeout=WAIT_TIME)
        content = msg.content
        await msg.delete()
        await interaction.followup.send("👥 是否要 @已驗證身分組? (是/否)", ephemeral=True)
        role_msg = await bot.wait_for('message', check=check, timeout=WAIT_TIME)
        role_response = role_msg.content
        await role_msg.delete()
        mention = f"<@&{VERIFIED_ROLE_ID}>" if role_response.lower() == "是" else ""
        await interaction.followup.send("📌 是否要置頂? (是/否)", ephemeral=True)
        pin_msg = await bot.wait_for('message', check=check, timeout=WAIT_TIME)
        pin_response = pin_msg.content
        await pin_msg.delete()
        sent_msg = await interaction.channel.send(f"{mention}\n📢 公告內容:\n{content}")
        if pin_response.lower() == "是":
            await sent_msg.pin()
        await interaction.followup.send("✅ 公告已發布！", ephemeral=True)
    except Exception as e:
        await interaction.followup.send("⚠️ 超時或錯誤，請重新操作。", ephemeral=True)
        print(e)

# ---------- 交易編號生成 ----------
def generate_trade_id():
    now = datetime.datetime.now()
    base_id = now.strftime("%Y%m%d")
    existing = [f for f in os.listdir(LOG_FOLDER) if f.startswith("trade_")]
    if not existing:
        count = 1
    else:
        nums = [int(f[9:]) for f in existing if f[9:].isdigit()]
        count = max(nums)+1 if nums else 1
    trade_id = f"{base_id}{count:03d}"
    return trade_id

# ---------- /買賣交易 指令 ----------
@bot.tree.command(name="買賣交易", description="發布買賣交易訊息並自動生成交易編號")
async def trade(interaction: discord.Interaction):
    await interaction.response.send_message("📦 請輸入交易物品內容:", ephemeral=True)
    def check(m): return m.author == interaction.user and m.channel == interaction.channel
    try:
        item_msg = await bot.wait_for('message', check=check, timeout=WAIT_TIME)
        item_content = item_msg.content
        await item_msg.delete()

        await interaction.followup.send("💰 價錢為多少呢?", ephemeral=True)
        price_msg = await bot.wait_for('message', check=check, timeout=WAIT_TIME)
        price_content = price_msg.content
        await price_msg.delete()

        await interaction.followup.send("🫂 是否要 @買帳成員身分組? (是/否)", ephemeral=True)
        role_msg = await bot.wait_for('message', check=check, timeout=WAIT_TIME)
        role_response = role_msg.content
        await role_msg.delete()

        mention = f"<@&{BUYERS_ROLE_ID}>" if role_response.lower() == "是" else ""

        # 生成交易編號
        trade_id = generate_trade_id()
        await interaction.followup.send(f"🆔 你的交易編號是：{trade_id}", ephemeral=True)

        # 發布交易訊息
        await interaction.channel.send(f"{mention}\n🛒 買賣交易內容:\n物品: {item_content}\n價錢: {price_content}\n編號: {trade_id}")

        # 建立交易頻道
        guild = interaction.guild
        author = interaction.user
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            author: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }
        category = guild.get_channel(TRADE_CATEGORY_ID)
        channel = await guild.create_text_channel(
            name=f"trade-{trade_id}",
            overwrites=overwrites,
            category=category,
            topic=f"交易編號 {trade_id} 由 {author} 建立"
        )

        # 完成交易按鈕
        class CompleteButton(discord.ui.View):
            @discord.ui.button(label="完成交易", style=discord.ButtonStyle.green)
            async def complete(self, button, button_interaction: discord.Interaction):
                messages = []
                async for msg in channel.history(limit=None, oldest_first=True):
                    timestamp = msg.created_at.strftime("%Y-%m-%d %H:%M:%S")
                    messages.append(f"[{timestamp}] {msg.author}: {msg.content}")
                filename = os.path.join(LOG_FOLDER, f"trade_{trade_id}.txt")
                with open(filename, "w", encoding="utf-8") as f:
                    f.write("\n".join(messages))
                await button_interaction.response.send_message(f"✅ 交易完成，紀錄已保存: `{filename}`", ephemeral=True)
                await channel.delete()

        await channel.send(f"🛒 交易 {trade_id} 開始，由 {author.mention} 建立。", view=CompleteButton())
        await interaction.followup.send("✅ 交易訊息已發布並建立交易頻道！", ephemeral=True)

    except Exception as e:
        await interaction.followup.send("⚠️ 超時或錯誤，請重新操作。", ephemeral=True)
        print(e)

# ---------- /我要交易 指令（手動編號） ----------
@bot.tree.command(name="我要交易", description="手動輸入交易編號建立交易頻道")
@app_commands.describe(trade_id="請輸入交易編號")
async def start_trade(interaction: discord.Interaction, trade_id: str):
    guild = interaction.guild
    author = interaction.user

    existing_channel = discord.utils.get(guild.channels, name=f"trade-{trade_id}")
    if existing_channel:
        await interaction.response.send_message("⚠️ 此交易編號已存在！", ephemeral=True)
        return

    # 先回應用戶，避免超時
    await interaction.response.send_message(f"🔧 正在建立交易頻道 `{trade_id}`...", ephemeral=True)

    try:
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            author: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }
        category = guild.get_channel(TRADE_CATEGORY_ID)
        channel = await guild.create_text_channel(
            name=f"trade-{trade_id}",
            overwrites=overwrites,
            category=category,
            topic=f"交易編號 {trade_id} 由 {author} 建立"
        )

        # 完成交易按鈕
        class CompleteButton(discord.ui.View):
            @discord.ui.button(label="完成交易", style=discord.ButtonStyle.green)
            async def complete(self, button, button_interaction: discord.Interaction):
                messages = []
                async for msg in channel.history(limit=None, oldest_first=True):
                    timestamp = msg.created_at.strftime("%Y-%m-%d %H:%M:%S")
                    messages.append(f"[{timestamp}] {msg.author}: {msg.content}")
                filename = os.path.join(LOG_FOLDER, f"trade_{trade_id}.txt")
                with open(filename, "w", encoding="utf-8") as f:
                    f.write("\n".join(messages))
                await button_interaction.response.send_message(f"✅ 交易完成，紀錄已保存: `{filename}`", ephemeral=True)
                await channel.delete()

        await channel.send(f"🛒 交易 {trade_id} 開始，由 {author.mention} 建立。", view=CompleteButton())

        # 更新用戶回應訊息（可選）
        await interaction.followup.send(f"✅ 交易頻道已建立: {channel.mention}", ephemeral=True)

    except discord.Forbidden:
        await interaction.followup.send("❌ 無法建立頻道，請檢查 Bot 權限", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ 發生錯誤: {e}", ephemeral=True)


    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        author: discord.PermissionOverwrite(read_messages=True, send_messages=True),
    }
    category = guild.get_channel(TRADE_CATEGORY_ID)
    channel = await guild.create_text_channel(
        name=f"trade-{trade_id}",
        overwrites=overwrites,
        category=category,
        topic=f"交易編號 {trade_id} 由 {author} 建立"
    )

    class CompleteButton(discord.ui.View):
        @discord.ui.button(label="完成交易", style=discord.ButtonStyle.green)
        async def complete(self, button, button_interaction: discord.Interaction):
            messages = []
            async for msg in channel.history(limit=None, oldest_first=True):
                timestamp = msg.created_at.strftime("%Y-%m-%d %H:%M:%S")
                messages.append(f"[{timestamp}] {msg.author}: {msg.content}")
            filename = os.path.join(LOG_FOLDER, f"trade_{trade_id}.txt")
            with open(filename, "w", encoding="utf-8") as f:
                f.write("\n".join(messages))
            await button_interaction.response.send_message(f"✅ 交易完成，紀錄已保存: `{filename}`", ephemeral=True)
            await channel.delete()

    await channel.send(f"🛒 交易 {trade_id} 開始，由 {author.mention} 建立。", view=CompleteButton())
    await interaction.response.send_message(f"✅ 交易頻道已建立: {channel.mention}", ephemeral=True)

# ---------- 啟動 Discord Bot ----------
TOKEN = os.environ.get("DISCORD_TOKEN")
if not TOKEN:
    print("⚠️ ERROR: DISCORD_TOKEN 環境變數未設定！")
else:
    bot.run(TOKEN)
