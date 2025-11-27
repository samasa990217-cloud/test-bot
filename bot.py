# ==========================================================
# 🔥 /新增自動公告
# ==========================================================
@bot.tree.command(name="新增自動公告", description="設定自動公告排程")
@app_commands.describe(
    time="格式：YYYY-MM-DD HH:MM 或 W週X HH:MM（例：W週2 15:30 代表每週二15:30）",
    content="公告內容",
    mention_verified="是否 @已驗證身分組 (是/否)"
)
async def add_auto_announce(interaction: discord.Interaction, time: str, content: str, mention_verified: str):
    if COMMAND_STATUS.get("新增自動公告", False) in [True, "維修"]:
        return await interaction.response.send_message("🟡 指令忙碌或維修中", ephemeral=True)
    COMMAND_STATUS["新增自動公告"] = True
    try:
        mention_bool = mention_verified.lower() == "是"
        channel_id = interaction.channel_id

        # 每週公告格式 W週X HH:MM
        if time.startswith("W週"):
            parts = time.split()
            weekday = int(parts[0].replace("W週", ""))
            hour, minute = map(int, parts[1].split(":"))
            WEEKLY_ANNOUNCEMENTS.append({
                "weekday": weekday,
                "hour": hour,
                "minute": minute,
                "content": content,
                "mention_verified": mention_bool,
                "channel_id": channel_id
            })
            msg_type = "每週公告"
        else:
            # 臨時公告
            TEMP_ANNOUNCEMENTS.append({
                "time": time,
                "content": content,
                "mention_verified": mention_bool,
                "channel_id": channel_id
            })
            msg_type = "臨時公告"

        await interaction.response.send_message(
            f"✅ 已新增 {msg_type}：\n• 時間/週期：{time}\n• 內容：{content}\n• @已驗證：{'是' if mention_bool else '否'}",
            ephemeral=True
        )
    finally:
        COMMAND_STATUS["新增自動公告"] = False

# ==========================================================
# 🔥 /查看排程
# ==========================================================
@bot.tree.command(name="查看排程", description="查看所有自動公告排程")
async def view_schedule(interaction: discord.Interaction):
    if COMMAND_STATUS.get("查看排程", False) in [True, "維修"]:
        return await interaction.response.send_message("🟡 指令忙碌或維修中", ephemeral=True)
    COMMAND_STATUS["查看排程"] = True
    try:
        msg = "📋 **臨時公告列表：**\n"
        if not TEMP_ANNOUNCEMENTS:
            msg += "無臨時公告\n"
        else:
            for idx, t in enumerate(TEMP_ANNOUNCEMENTS, start=1):
                msg += f"{idx}. 時間：{t['time']}，內容：{t['content']}，@已驗證：{'是' if t['mention_verified'] else '否'}，頻道：<#{t['channel_id']}>\n"

        msg += "\n📋 **每週公告列表：**\n"
        if not WEEKLY_ANNOUNCEMENTS:
            msg += "無每週公告\n"
        else:
            for idx, t in enumerate(WEEKLY_ANNOUNCEMENTS, start=1):
                msg += f"{idx}. 星期{t['weekday']} {t['hour']:02d}:{t['minute']:02d}，內容：{t['content']}，@已驗證：{'是' if t['mention_verified'] else '否'}，頻道：<#{t['channel_id']}>\n"

        await interaction.response.send_message(msg, ephemeral=True)
    finally:
        COMMAND_STATUS["查看排程"] = False

# ==========================================================
# 🔥 /刪除排程
# ==========================================================
@bot.tree.command(name="刪除排程", description="刪除指定自動公告排程")
@app_commands.describe(index="排程編號（在 /查看排程 查看，先臨時公告，再每週公告）")
async def delete_schedule(interaction: discord.Interaction, index: int):
    if COMMAND_STATUS.get("刪除排程", False) in [True, "維修"]:
        return await interaction.response.send_message("🟡 指令忙碌或維修中", ephemeral=True)
    COMMAND_STATUS["刪除排程"] = True
    try:
        total_list = TEMP_ANNOUNCEMENTS + WEEKLY_ANNOUNCEMENTS
        if index < 1 or index > len(total_list):
            return await interaction.response.send_message("❌ 無效的排程編號。", ephemeral=True)

        if index <= len(TEMP_ANNOUNCEMENTS):
            removed = TEMP_ANNOUNCEMENTS.pop(index - 1)
        else:
            removed = WEEKLY_ANNOUNCEMENTS.pop(index - 1 - len(TEMP_ANNOUNCEMENTS))

        await interaction.response.send_message(
            f"🗑️ 已刪除排程：{removed.get('time', f'每週星期{removed.get('weekday')} {removed.get('hour'):02d}:{removed.get('minute'):02d}')} — {removed['content']}",
            ephemeral=True
        )
    finally:
        COMMAND_STATUS["刪除排程"] = False

# ==========================================================
# 🔥 /查詢所有指令狀態
# ==========================================================
@bot.tree.command(name="查詢所有指令狀態", description="查看所有指令目前狀態")
async def query_all_commands(interaction: discord.Interaction):
    if COMMAND_STATUS.get("查詢所有指令狀態", False) in [True, "維修"]:
        return await interaction.response.send_message("🟡 指令忙碌或維修中", ephemeral=True)
    COMMAND_STATUS["查詢所有指令狀態"] = True
    try:
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
    finally:
        COMMAND_STATUS["查詢所有指令狀態"] = False

# ==========================================================
# 🔥 Bot Ready 與自動排程啟動
# ==========================================================
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    try:
        await bot.tree.sync()
        print("Slash commands synced.")
    except Exception as e:
        print(e)

    # ⭐ 開始自動排程任務
    if not auto_announce_task.is_running():
        auto_announce_task.start()
        print("Auto announcement task started.")

# ==========================================================
# 🔥 啟動 BOT
# ==========================================================
TOKEN = os.environ.get("DISCORD_TOKEN")
if not TOKEN:
    print("❌ DISCORD_TOKEN 未設定")
else:
    bot.run(TOKEN)
