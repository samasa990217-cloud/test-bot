import discord
from discord.ext import commands
from discord import app_commands
import os
import datetime
from flask import Flask
import threading

# Flask Keep-Alive
app = Flask("")
@app.route("/")
def home():
    return "Discord Bot is running!"

def run_flask():
    app.run(host="0.0.0.0", port=10000)

threading.Thread(target=run_flask).start()

# Discord Bot
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

VERIFIED_ROLE_ID = 1442916731927396403
BUYERS_ROLE_ID = 1442915193704157235
TRADE_CATEGORY_ID = 123456789012345678
WAIT_TIME = 60
LOG_FOLDER = "trade_logs"
if not os.path.exists(LOG_FOLDER):
    os.makedirs(LOG_FOLDER)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    try:
        await bot.tree.sync()
        print("Slash commands synced.")
    except Exception as e:
        print(e)

# /公告 /買賣交易 /我要交易 指令內容可貼前一個版本
import os

TOKEN = os.environ.get("DISCORD_TOKEN")  # 從環境變數取得 Token
bot.run(TOKEN)

