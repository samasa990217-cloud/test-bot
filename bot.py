import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
import datetime
import asyncio
from flask import Flask
import threading

# ==========================================================
# 🔥 Render KeepAlive
# ==========================================================
app = Flask("")

@app.route("/")
def home():
    return "Bot Running OK"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_flask).start()

# ==========================================================
# 🔥 Discord Bot 設定
# ==========================================================
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ==========================================================
# 🔥 全域參數
# ==========================================================
VERIFIED_ROLE_ID = 1442916731927396403
BUYERS_ROLE_ID = 1442915193704157235
TRADE_CATEGORY_ID = 123456789012345678
LOG_FOLDER = "trade_logs"

# 指令限制頻道
ANNOUNCE_CHANNEL_ID = 1443115994431094784
TRADE_CHANNEL_ID = 1443118740802637905
QUERY_CHANNEL_ID = 1443118774818439290

# 指令狀態
COMMAND_STATUS = {
    "公告": False,
    "買賣交易": False,
    "我要交易": False,
    "完成交易": False,
    "查詢交易": False,
    "新增自動公告": False,
    "查看排程": False,
    "刪除排程": False,
    "查詢所有指令狀態": False
}

if not os.path.exists(LOG_FOLDER):
    os.makedirs(LOG_FOLDER)

# ==========================================================
# 🔥 排程清單
# ==========================================================
TEMP_ANNOUNCEMENTS = []   # 臨時公告 YYYY-MM-DD HH:MM
WEEKLY_ANNOUNCEMENTS = [] # 固定每週公告 星期幾 + HH:MM

# ==========================================================
# 🔥 交易系統
# ==========================================================
def generate_trade_id(guild):
    today_str = datetime.datetime.now().strftime("%Y%m%d")
    existing_channels = [ch for ch in guild.channels if ch.name.startswith(f"trade-{today_str}")]
    if not existing_channels:
        count = 1
    else:
        nums = []
        for ch in existing_channels:
            suffix = ch.name.replace(f"trade-{today_str}", "")
            if suffix.isdigit():
                nums.append(int(suffix))
        count = max(nums) + 1 if nums else 1
    return f"{today_str}{count:03d}"

@bot.tree.command(name="買賣交易", description="發布買賣交易訊息並生成交易編號")
@app_commands.describe(item="交易物品內容", price="交易價錢", mention_buyers="是否@買帳成員身分組 (是/否)")
async def trade(interaction: discord.Interaction, item: str, price: str, mention_buyers: str):
    if interaction.channel_id != TRADE_CHANNEL_ID:
        return await interaction.response.send_message("❌ 請到指定頻道使用此指令。", ephemeral=True)
    status = COMMAND_STATUS.get("買賣交易", False)
    if status in [True, "維修"]:
        return await interaction.response.send_message("🟡 指令忙碌或維修中", ephemeral=True)
    COMMAND_STATUS["買賣交易"] = True
    try:
        author = interaction.user
        guild = interaction.guild
        trade_id = generate_trade_id(guild)
        channel_name = f"trade-{trade_id}"
        existing_channel = discord.utils.get(guild.channels, name=channel_name)
        if existing_channel:
            return await interaction.response.send_message("⚠️ 此交易編號頻道已存在，請稍後再試。", ephemeral=True)

        mention = f"<@&{BUYERS_ROLE_ID}>" if mention_buyers.lower() == "是" else ""
        await interaction.response.send_message(
            f"{mention}\n🛒 交易 {trade_id} 開始，由 {author.mention} 建立。\n"
            f"物品: {item}\n價錢: {price}\n輸入 /我要交易 {trade_id} 進入私密頻道",
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
            topic=f"交易編號 {trade_id} 由 {author} 建立"
        )
        await channel.send(f"🛒 私密交易 {trade_id} 頻道，僅授權成員可見。")
    finally:
        COMMAND_STATUS["買賣交易"] = False

@bot.tree.command(name="我要交易", description="輸入交易編號以進入私密交易頻道")
@app_commands.describe(trade_id="請輸入交易編號")
async def join_trade(interaction: discord.Interaction, trade_id: str):
    status = COMMAND_STATUS.get("我要交易", False)
    if status in [True, "維修"]:
        return await interaction.response.send_message("🟡 指令忙碌或維修中", ephemeral=True)
    COMMAND_STATUS["我要交易"] = True
    try:
        guild = interaction.guild
        channel_name = f"trade-{trade_id}"
        channel = discord.utils.get(guild.channels, name=channel_name)
        if not channel:
            return await interaction.response.send_message("❌ 查無此交易編號。", ephemeral=True)
        await channel.set_permissions(interaction.user, read_messages=True, send_messages=True)
        await interaction.response.send_message(f"🔑 你已被授權進入交易頻道: {channel.mention}", ephemeral=True)
    finally:
        COMMAND_STATUS["我要交易"] = False

@bot.tree.command(name="完成交易", description="完成交易並存檔")
@app_commands.describe(trade_id="請輸入交易編號")
async def complete_trade(interaction: discord.Interaction, trade_id: str):
    status = COMMAND_STATUS.get("完成交易", False)
    if status in [True, "維修"]:
        return await interaction.response.send_message("🟡 指令忙碌或維修中", ephemeral=True)
    COMMAND_STATUS["完成交易"] = True
    try:
        guild = interaction.guild
        channel_name = f"trade-{trade_id}"
        channel = discord.utils.get(guild.channels, name=channel_name)
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
    finally:
        COMMAND_STATUS["完成交易"] = False

@bot.tree.command(name="查詢交易", description="輸入交易編號查詢並查看交易記錄")
@app_commands.describe(trade_id="請輸入交易編號")
async def query_trade(interaction: discord.Interaction, trade_id: str):
    status = COMMAND_STATUS.get("查詢交易", False)
    if status in [True, "維修"]:
        return await interaction.response.send_message("🟡 指令忙碌或維修中", ephemeral=True)
    COMMAND_STATUS["查詢交易"] = True
    try:
        if interaction.channel_id != QUERY_CHANNEL_ID:
            return await interaction.response.send_message("❌ 請到指定頻道使用此指令。", ephemeral=True)
        filename = os.path.join(LOG_FOLDER, f"trade_{trade_id}.txt")
        if not os.path.exists(filename):
            return await interaction.response.send_message("❌ 查無此交易紀錄。", ephemeral=True)
        with open(filename, "r", encoding="utf-8") as f:
            content = f.read()
        if len(content) < 1900:
            await interaction.response.send_message(f"📄 **交易紀錄 - {trade_id}**\n```\n{content}\n```", ephemeral=True)
        else:
            await interaction.response.send_message(f"📄 **交易紀錄 - {trade_id}（內容較長）**", ephemeral=True)
            for chunk in [content[i:i+1900] for i in range(0, len(content), 1900)]:
                await interaction.followup.send(f"```\n{chunk}\n```", ephemeral=True)
    finally:
        COMMAND_STATUS["查詢交易"] = False

# ==========================================================
# 🔥 公告系統
# ==========================================================
@bot.tree.command(name="公告", description="發布一則公告")
async def announce(interaction: discord.Interaction):
    if interaction.channel_id != ANNOUNCE_CHANNEL_ID:
        return await interaction.response.send_message("❌ 請到指定頻道使用此指令。", ephemeral=True)
    status = COMMAND_STATUS.get("公告", False)
    if status in [True, "維修"]:
        return await interaction.response.send_message("🟡 指令忙碌或維修中", ephemeral=True)
    COMMAND_STATUS["公告"] = True
    try:
        await interaction.response.send_message("📝 請輸入公告內容:", ephemeral=True)
        def check(m): return m.author == interaction.user and m.channel == interaction.channel
        msg = await bot.wait_for('message', check=check, timeout=60)
        content = msg.content
        await msg.delete()

        await interaction.followup.send("👥 是否要 @已驗證身分組? (是/否)", ephemeral=True)
        role_msg = await bot.wait_for('message', check=check, timeout=60)
        role_response = role_msg.content
        await role_msg.delete()
        mention = f"<@&{VERIFIED_ROLE_ID}>" if role_response.lower() == "是" else ""

        await interaction.followup.send("📌 是否要置頂? (是/否)", ephemeral=True)
        pin_msg = await bot.wait_for('message', check=check, timeout=60)
        pin_response = pin_msg.content
        await pin_msg.delete()

        sent_msg = await interaction.channel.send(f"{mention}\n📢 公告內容:\n{content}")
        if pin_response.lower() == "是":
            await sent_msg.pin()

        await interaction.followup.send("✅ 公告已發布！", ephemeral=True)
    finally:
        COMMAND_STATUS["公告"] = False

# ==========================================================
# 🔥 自動公告排程系統
# ==========================================================
@tasks.loop(seconds=30)
async def auto_announce_task():
    now = datetime.datetime.now()
    # 臨時公告
    for t in TEMP_ANNOUNCEMENTS[:]:
        if t["time"] == now.strftime("%Y-%m-%d %H:%M"):
            channel = bot.get_channel(t["channel_id"])
            if channel:
                mention = f"<@&{VERIFIED_ROLE_ID}>" if t["mention_verified"] else ""
                await channel.send(f"{mention}\n📢 **自動公告：**\n{t['content']}")
            TEMP_ANNOUNCEMENTS.remove(t)
    # 每週公告
    for t in WEEKLY_ANNOUNCEMENTS:
        if now.weekday() == t["weekday"] and now.hour == t["hour"] and now.minute == t["minute"]:
            channel = bot.get_channel(t["channel_id"])
            if channel:
                mention = f"<@&{VERIFIED_ROLE_ID}>" if t["mention_verified"] else ""
                await channel.send(f"{mention}\n📢 **自動公告：**\n{t['content']}")

# ==========================================================
# 🔥 自動公告指令整合
# ==========================================================

# ==========================================================
# 🔥 /新增自動公告
# ==========================================================
@bot.tree.command(name="新增自動公告", description="設定自動公告排程")
@app_commands.describe(
    time="臨時公告格式：YYYY-MM-DD HH:MM，或每週公告格式：星期幾 HH:MM",
    content="公告內容",
    mention_verified="是否 @已驗證身分組 (是/否)"
)
async def add_auto_announce(interaction: discord.Interaction, time: str, content: str, mention_verified: str):
    status = COMMAND_STATUS.get("新增自動公告", False)
    if status in [True, "維修"]:
        return await interaction.response.send_message("🟡 指令忙碌或維修中", ephemeral=True)
    COMMAND_STATUS["新增自動公告"] = True
    try:
        mention = mention_verified.lower() == "是"
        try:
            if time[0].isdigit():
                dt = datetime.datetime.strptime(time, "%Y-%m-%d %H:%M")
                TEMP_ANNOUNCEMENTS.append({
                    "time": dt.strftime("%Y-%m-%d %H:%M"),
                    "content": content,
                    "mention_verified": mention,
                    "channel_id": interaction.channel_id
                })
                msg_time = dt.strftime("%Y-%m-%d %H:%M")
            else:
                week_map = {"一":0,"二":1,"三":2,"四":3,"五":4,"六":5,"日":6}
                day, hm = time.split()
                h, m = map(int, hm.split(":"))
                WEEKLY_ANNOUNCEMENTS.append({
                    "weekday": week_map[day],
                    "hour": h,
                    "minute": m,
                    "content": content,
                    "mention_verified": mention,
                    "channel_id": interaction.channel_id
                })
                msg_time = f"每週 {day} {hm}"
        except:
            return await interaction.response.send_message("❌ 時間格式錯誤", ephemeral=True)
        await interaction.response.send_message(
            f"⏰ 已新增自動公告：\n• 時間：{msg_time}\n• 內容：{content}\n• @已驗證：{'是' if mention else '否'}",
            ephemeral=True
        )
    finally:
        COMMAND_STATUS["新增自動公告"] = False

# ==========================================================
# 🔥 /查看排程
# ==========================================================
@bot.tree.command(name="查看排程", description="查看所有自動公告排程")
async def view_schedule(interaction: discord.Interaction):
    status = COMMAND_STATUS.get("查看排程", False)
    if status in [True, "維修"]:
        return await interaction.response.send_message("🟡 指令忙碌或維修中", ephemeral=True)
    COMMAND_STATUS["查看排程"] = True
    try:
        if not TEMP_ANNOUNCEMENTS and not WEEKLY_ANNOUNCEMENTS:
            return await interaction.response.send_message("📭 目前沒有任何排程公告。", ephemeral=True)
        msg = "📋 **排程公告列表：**\n\n"
        idx = 1
        for t in TEMP_ANNOUNCEMENTS:
            msg += f"**# {idx}** [臨時公告]\n• 時間：{t['time']}\n• 內容：{t['content']}\n• @已驗證：{'是' if t['mention_verified'] else '否'}\n• 頻道：<#{t['channel_id']}>\n\n"
            idx += 1
        for t in WEEKLY_ANNOUNCEMENTS:
            week_map_rev = ["一","二","三","四","五","六","日"]
            day = week_map_rev[t["weekday"]]
            msg += f"**# {idx}** [每週公告]\n• 時間：每週 {day} {t['hour']:02d}:{t['minute']:02d}\n• 內容：{t['content']}\n• @已驗證：{'是' if t['mention_verified'] else '否'}\n• 頻道：<#{t['channel_id']}>\n\n"
            idx += 1
        await interaction.response.send_message(msg, ephemeral=True)
    finally:
        COMMAND_STATUS["查看排程"] = False

# ==========================================================
# 🔥 /刪除排程
# ==========================================================
@bot.tree.command(name="刪除排程", description="刪除指定自動公告排程")
@app_commands.describe(index="排程編號（在 /查看排程 查看）")
async def delete_schedule(interaction: discord.Interaction, index: int):
    status = COMMAND_STATUS.get("刪除排程", False)
    if status in [True, "維修"]:
        return await interaction.response.send_message("🟡 指令忙碌或維修中", ephemeral=True)
    COMMAND_STATUS["刪除排程"] = True
    try:
        combined = TEMP_ANNOUNCEMENTS + WEEKLY_ANNOUNCEMENTS
        if index < 1 or index > len(combined):
            return await interaction.response.send_message("❌ 無效的排程編號。", ephemeral=True)
        if index <= len(TEMP_ANNOUNCEMENTS):
            removed = TEMP_ANNOUNCEMENTS.pop(index - 1)
        else:
            removed = WEEKLY_ANNOUNCEMENTS.pop(index - len(TEMP_ANNOUNCEMENTS) - 1)
        await interaction.response.send_message(f"🗑️ 已刪除排程：{removed['content']}", ephemeral=True)
    finally:
        COMMAND_STATUS["刪除排程"] = False


# ==========================================================
# 🔥 查詢所有指令狀態
# ==========================================================
@bot.tree.command(name="查詢所有指令狀態", description="查看所有指令目前狀態")
async def query_all_commands(interaction: discord.Interaction):
    msg = "📋 **所有指令狀態一覽**\n\n"
    for cmd, status in COMMAND_STATUS.items():
        if status == False:
            emoji = "🟢 正常"
        elif status == True:
            emoji = "🟡 使用中"
        elif status == "維修":
            emoji = "🔧 維修中"
        else:
            emoji = "⚪ 未知"
        msg += f"• **/{cmd}** → {emoji}\n"
    await interaction.response.send_message(msg, ephemeral=True)

# ==========================================================
# 🔥 啟動 BOT
# ==========================================================
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    try:
        await bot.tree.sync()
        print("Slash commands synced.")
    except Exception as e:
        print(e)
    if not auto_announce_task.is_running():
        auto_announce_task.start()
        print("Auto announcement task started.")

TOKEN = os.environ.get("DISCORD_TOKEN")
if not TOKEN:
    print("❌ DISCORD_TOKEN 未設定")
else:
    bot.run(TOKEN)
