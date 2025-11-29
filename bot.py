import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
import datetime
import asyncio
from flask import Flask
from waitress import serve
import threading


# ==========================================================
# 🔥 Render KeepAlive
# ==========================================================
app = Flask("")

@app.route("/")
def home():
    return "Bot 運行中", 200  # 一般首頁也回 200

@app.route("/健康檢查")
def health_check():
    return "服務正常 ✅", 200  # 專用健康檢查 endpoint

def run_flask():
    port = int(os.environ.get("PORT", 10000))  # Render 會提供 PORT
    serve(app, host="0.0.0.0", port=port)

# 啟動 Flask server 的 thread
threading.Thread(target=run_flask, daemon=True).start()

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
# 🔥 手動公告
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
# 🔥 排程管理指令（新增/查看/刪除）
# ==========================================================
@bot.tree.command(name="新增自動公告", description="設定自動公告排程")
@app_commands.describe(
    content="公告內容",
    mention_verified="是否 @已驗證身分組 (是/否)",
    time="臨時公告格式：YYYY-MM-DD HH:MM",
    weekday="固定每週公告星期幾 (0=星期一, 6=星期日)",
    hour="固定每週公告小時 0-23",
    minute="固定每週公告分鐘 0-59"
)
async def add_auto_announce(interaction: discord.Interaction, content: str, mention_verified: str, time: str = None, weekday: int = None, hour: int = None, minute: int = None):
    if time:
        TEMP_ANNOUNCEMENTS.append({
            "time": time,
            "content": content,
            "mention_verified": mention_verified == "是",
            "channel_id": interaction.channel_id
        })
        await interaction.response.send_message(
            f"⏰ 已新增臨時排程公告：\n• 時間：{time}\n• 內容：{content}\n• @已驗證：{'是' if mention_verified=='是' else '否'}",
            ephemeral=True
        )
    elif weekday is not None and hour is not None and minute is not None:
        WEEKLY_ANNOUNCEMENTS.append({
            "weekday": weekday,
            "hour": hour,
            "minute": minute,
            "content": content,
            "mention_verified": mention_verified == "是",
            "channel_id": interaction.channel_id
        })
        await interaction.response.send_message(
            f"⏰ 已新增每週排程公告：\n• 星期：{weekday} (0=一,6=日)\n• 時間：{hour:02d}:{minute:02d}\n• 內容：{content}\n• @已驗證：{'是' if mention_verified=='是' else '否'}",
            ephemeral=True
        )
    else:
        await interaction.response.send_message("❌ 請提供有效時間或每週時間參數。", ephemeral=True)

@bot.tree.command(name="查看排程", description="查看所有自動公告排程")
async def view_schedule(interaction: discord.Interaction):
    msg = "📋 **排程公告列表：**\n\n"
    if not TEMP_ANNOUNCEMENTS and not WEEKLY_ANNOUNCEMENTS:
        return await interaction.response.send_message("📭 目前沒有任何排程公告。", ephemeral=True)
    if TEMP_ANNOUNCEMENTS:
        msg += "**臨時公告：**\n"
        for idx, t in enumerate(TEMP_ANNOUNCEMENTS, start=1):
            msg += f"• #{idx} 時間：{t['time']} 內容：{t['content']} @已驗證：{'是' if t['mention_verified'] else '否'} 頻道：<#{t['channel_id']}>\n"
    if WEEKLY_ANNOUNCEMENTS:
        msg += "\n**每週固定公告：**\n"
        for idx, t in enumerate(WEEKLY_ANNOUNCEMENTS, start=1):
            msg += f"• #{idx} 星期：{t['weekday']} 時間：{t['hour']:02d}:{t['minute']:02d} 內容：{t['content']} @已驗證：{'是' if t['mention_verified'] else '否'} 頻道：<#{t['channel_id']}>\n"
    await interaction.response.send_message(msg, ephemeral=True)

@bot.tree.command(name="刪除排程", description="刪除指定自動公告排程")
@app_commands.describe(index="排程編號（在 /查看排程 查看）", type="排程類型 (臨時/每週)")
async def delete_schedule(interaction: discord.Interaction, index: int, type: str):
    if type.lower() == "臨時":
        if index < 1 or index > len(TEMP_ANNOUNCEMENTS):
            return await interaction.response.send_message("❌ 無效的臨時公告編號。", ephemeral=True)
        removed = TEMP_ANNOUNCEMENTS.pop(index - 1)
        await interaction.response.send_message(
            f"🗑️ 已刪除臨時公告：{removed['time']} — {removed['content']}", ephemeral=True
        )
    elif type.lower() == "每週":
        if index < 1 or index > len(WEEKLY_ANNOUNCEMENTS):
            return await interaction.response.send_message("❌ 無效的每週公告編號。", ephemeral=True)
        removed = WEEKLY_ANNOUNCEMENTS.pop(index - 1)
        await interaction.response.send_message(
            f"🗑️ 已刪除每週公告：星期{removed['weekday']} {removed['hour']:02d}:{removed['minute']:02d} — {removed['content']}", ephemeral=True
        )
    else:
        await interaction.response.send_message("❌ 請指定正確排程類型：臨時 / 每週", ephemeral=True)

# ==========================================================
# 🔥 查詢指令狀態
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

from discord.ui import View, Button

# ==========================================================
# 🔥 升級版星際操作手冊 Embed 指令
# ==========================================================
@bot.tree.command(name="星際手冊", description="顯示星際指令總覽（升級版）")
async def star_manual_advanced(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🚀 星際操作手冊 v2.0",
        description="指揮官，歡迎來到艦橋控制面板。以下為核心指令指南與使用範例，助你掌控艦隊運作。",
        color=0x1E90FF
    )

    # 每個指令加上範例用法
    embed.add_field(
        name="🛸 /公告",
        value="功能：發布重要公告，確保全員即時接收最新訊息。\n範例：`/公告` → 依提示輸入公告內容、是否 @已驗證、是否置頂",
        inline=False
    )
    embed.add_field(
        name="🛰 /新增自動公告",
        value="功能：設定自動公告排程。\n範例：\n• 固定排程: `/新增自動公告 content:'公告內容' weekday:1 hour:12 minute:30 mention_verified:是`\n• 臨時排程: `/新增自動公告 content:'公告內容' time:'2025-11-28 15:00' mention_verified:否`",
        inline=False
    )
    embed.add_field(
        name="🗑 /刪除排程",
        value="功能：移除指定自動公告排程。\n範例：`/刪除排程 index:1 type:臨時`",
        inline=False
    )
    embed.add_field(
        name="📡 /查看排程",
        value="功能：查看所有自動公告排程。\n範例：`/查看排程`",
        inline=False
    )
    embed.add_field(
        name="💱 /我要交易",
        value="功能：輸入交易編號進入私密交易頻道。\n範例：`/我要交易 trade_id:20251128001`",
        inline=False
    )
    embed.add_field(
        name="✅ /完成交易",
        value="功能：完成交易並自動存檔。\n範例：`/完成交易 trade_id:20251128001`",
        inline=False
    )
    embed.add_field(
        name="📜 /查詢交易",
        value="功能：查詢交易紀錄。\n範例：`/查詢交易 trade_id:20251128001`",
        inline=False
    )
    embed.add_field(
        name="🔍 /查詢所有指令狀態",
        value="功能：查看所有指令的運行狀態。\n範例：`/查詢所有指令狀態`",
        inline=False
    )
    embed.add_field(
        name="💹 /買賣交易",
        value="功能：發布買賣交易訊息並生成交易編號。\n範例：`/買賣交易 item:'激光炮' price:'5000' mention_buyers:是`",
        inline=False
    )

    # 分隔線與提示
    embed.add_field(
        name="――――――――――――――――――――――――",
        value="💡 提示：所有指令可在此艦橋操作，確保資訊掌控與交易流程安全。",
        inline=False
    )

    embed.set_footer(text="指揮官提示：掌控全局，方能制勝星際戰場。")

    await interaction.response.send_message(embed=embed, ephemeral=False)

import aiohttp

async def self_ping():
    await bot.wait_until_ready()
    url = "https://test-bot-iu8p.onrender.com/健康檢查"  # 改成你的 Render 網址
    async with aiohttp.ClientSession() as session:
        while not bot.is_closed():
            try:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        print("✅ 自我 ping 成功")
                    else:
                        print(f"⚠️ 自我 ping 回傳 {resp.status}")
            except Exception as e:
                print(f"❌ 自我 ping 失敗: {e}")
            await asyncio.sleep(5*60)  # 每 5 分鐘 ping 一次

bot.loop.create_task(self_ping())
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
