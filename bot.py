import discord
from discord.ext import commands
from discord import app_commands
import os
import datetime
from flask import Flask
import threading
import asyncio

# ==========================================================
#                   🔥 Render KeepAlive (最穩版本)
# ==========================================================
app = Flask("")

@app.route("/")
def home():
    return "Bot Running OK"

def run_flask():
    port = int(os.environ.get("PORT", 10000))   # ★ 使用 Render 自動給的 PORT（避免 503）
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_flask).start()


# ==========================================================
#                   🔥 Discord Bot 設定
# ==========================================================
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)


# ==========================================================
#                   🔧 你的參數設定
# ==========================================================
VERIFIED_ROLE_ID = 1442916731927396403      # 已驗證
BUYERS_ROLE_ID = 1442915193704157235        # 買帳成員
TRADE_CATEGORY_ID = 123456789012345678      # 你自己的交易分類 ID

LOG_FOLDER = "trade_logs"

# ★ 限制指令頻道 ID
ANNOUNCE_CHANNEL_ID = 1443115994431094784
TRADE_CHANNEL_ID = 1443118740802637905
QUERY_CHANNEL_ID = 1443118774818439290

# ★ 自動建立資料夾
if not os.path.exists(LOG_FOLDER):
    os.makedirs(LOG_FOLDER)


# ==========================================================
#                      🔥 Bot Ready
# ==========================================================
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    try:
        await bot.tree.sync()
        print("Commands Synced OK")
    except Exception as e:
        print(e)


# ==========================================================
#                     🔥 /公告
# ==========================================================
@bot.tree.command(name="公告", description="發布一則公告")
async def announce(interaction: discord.Interaction):

    # ★ 限制頻道
    if interaction.channel_id != ANNOUNCE_CHANNEL_ID:
        return await interaction.response.send_message("❌ 請到指定頻道使用此指令。", ephemeral=True)

    await interaction.response.send_message("📝 請輸入公告內容:", ephemeral=True)

    def check(m):
        return m.author == interaction.user and m.channel == interaction.channel

    try:
        # 取得公告內容
        msg = await bot.wait_for("message", check=check, timeout=60)
        content = msg.content
        await msg.delete()

        # 是否要 @已驗證
        await interaction.followup.send("👥 是否要 @已驗證身分組? (是/否)", ephemeral=True)
        msg2 = await bot.wait_for("message", check=check, timeout=60)
        mention_verified = msg2.content.lower() == "是"
        await msg2.delete()

        # 是否置頂
        await interaction.followup.send("📌 是否要置頂? (是/否)", ephemeral=True)
        msg3 = await bot.wait_for("message", check=check, timeout=60)
        pin_msg = msg3.content.lower() == "是"
        await msg3.delete()

        mention = f"<@&{VERIFIED_ROLE_ID}>" if mention_verified else ""
        send_msg = await interaction.channel.send(f"{mention}\n📢 公告內容:\n{content}")

        if pin_msg:
            await send_msg.pin()

        await interaction.followup.send("✅ 公告已發布！", ephemeral=True)

    except:
        await interaction.followup.send("⚠️ 超時，請重新使用指令。", ephemeral=True)


# ==========================================================
#                     🔥 交易編號（日期+流水號）
# ==========================================================
def generate_trade_id(guild):
    today = datetime.datetime.now().strftime("%Y%m%d")

    existing = [ch for ch in guild.channels if ch.name.startswith(f"trade-{today}")]
    numbers = []

    for ch in existing:
        suffix = ch.name.replace(f"trade-{today}", "")
        if suffix.isdigit():
            numbers.append(int(suffix))

    next_id = (max(numbers) + 1) if numbers else 1

    return f"{today}{next_id:03d}"   # e.g. 20250101001


# ==========================================================
#                     🔥 /買賣交易
# ==========================================================
@bot.tree.command(name="買賣交易", description="建立交易編號並發布交易訊息")
@app_commands.describe(item="交易物品", price="交易價格", mention_buyers="是否 @買帳成員 (是/否)")
async def trade(interaction: discord.Interaction, item: str, price: str, mention_buyers: str):

    # ★ 限制頻道
    if interaction.channel_id != TRADE_CHANNEL_ID:
        return await interaction.response.send_message("❌ 請到指定頻道使用此指令。", ephemeral=True)

    guild = interaction.guild
    author = interaction.user
    trade_id = generate_trade_id(guild)

    # 建立頻道名稱
    channel_name = f"trade-{trade_id}"
    if discord.utils.get(guild.channels, name=channel_name):
        return await interaction.response.send_message("⚠️ 此交易編號已存在。", ephemeral=True)

    mention = f"<@&{BUYERS_ROLE_ID}>" if mention_buyers.lower() == "是" else ""

    await interaction.response.send_message(
        f"{mention}\n🛒 **交易 {trade_id}** 由 {author.mention} 建立\n"
        f"物品：{item}\n價格：{price}\n使用 `/我要交易 {trade_id}` 進入私密頻道",
        ephemeral=False
    )

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        author: discord.PermissionOverwrite(read_messages=True, send_messages=True),
    }

    category = guild.get_channel(TRADE_CATEGORY_ID)

    channel = await guild.create_text_channel(
        name=channel_name,
        overwrites=overwrites,
        category=category,
        topic=f"交易編號 {trade_id} 由 {author}"
    )

    await channel.send(f"🔐 私密交易頻道已建立：{trade_id}")


# ==========================================================
#                     🔥 /我要交易
# ==========================================================
@bot.tree.command(name="我要交易", description="用交易編號加入交易頻道")
async def join_trade(interaction: discord.Interaction, trade_id: str):

    channel = discord.utils.get(interaction.guild.channels, name=f"trade-{trade_id}")

    if not channel:
        return await interaction.response.send_message("❌ 查無此交易編號。", ephemeral=True)

    await channel.set_permissions(interaction.user, read_messages=True, send_messages=True)

    await interaction.response.send_message(
        f"🔑 已授權你進入：{channel.mention}",
        ephemeral=True
    )


# ==========================================================
#                     🔥 /完成交易（存檔）
# ==========================================================
@bot.tree.command(name="完成交易", description="完成交易並儲存紀錄")
async def complete_trade(interaction: discord.Interaction, trade_id: str):

    name = f"trade-{trade_id}"
    guild = interaction.guild
    channel = discord.utils.get(guild.channels, name=name)

    if not channel:
        return await interaction.response.send_message("❌ 查無此交易編號。", ephemeral=True)

    records = []

    async for msg in channel.history(limit=None, oldest_first=True):
        time = msg.created_at.strftime("%Y-%m-%d %H:%M:%S")
        records.append(f"[{time}] {msg.author}: {msg.content}")

    filename = os.path.join(LOG_FOLDER, f"trade_{trade_id}.txt")
    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(records))

    await interaction.response.send_message("✅ 交易完成，紀錄已儲存。", ephemeral=True)

    await asyncio.sleep(1)
    await channel.delete()


# ==========================================================
#                     🔥 /查詢交易（TXT 查詢）
# ==========================================================
@bot.tree.command(name="查詢交易", description="輸入交易編號查詢並查看交易記錄")
async def query_trade(interaction: discord.Interaction, trade_id: str):

    # ★ 限制頻道
    if interaction.channel_id != QUERY_CHANNEL_ID:
        return await interaction.response.send_message("❌ 請到指定頻道使用此指令。", ephemeral=True)

    filename = os.path.join(LOG_FOLDER, f"trade_{trade_id}.txt")

    if not os.path.exists(filename):
        return await interaction.response.send_message("❌ 查無此交易紀錄。", ephemeral=True)

    with open(filename, "r", encoding="utf-8") as f:
        content = f.read()

    if len(content) < 1900:
        await interaction.response.send_message(
            f"📄 **交易紀錄 - {trade_id}**\n```\n{content}\n```",
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            f"📄 **交易紀錄 - {trade_id}（內容較長）**",
            ephemeral=True
        )

        for chunk in [content[i:i+1900] for i in range(0, len(content), 1900)]:
            await interaction.followup.send(f"```\n{chunk}\n```", ephemeral=True)


# ==========================================================
#                     🔥 啟動 BOT
# ==========================================================
TOKEN = os.environ.get("DISCORD_TOKEN")
if not TOKEN:
    print("❌ DISCORD_TOKEN 未設定")
else:
    bot.run(TOKEN)
