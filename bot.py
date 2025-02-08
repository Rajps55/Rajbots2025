import sys
import glob
import importlib
import asyncio
import logging
import logging.config
import time
from pathlib import Path
from pyrogram import Client, idle, __version__
from pyrogram.raw.all import layer
from database.ia_filterdb import Media, Media2, tempDict, choose_mediaDB, db as clientDB
from database.users_chats_db import db
from info import *
from utils import temp
from typing import AsyncGenerator
from aiohttp import web
from plugins import web_server, check_expired_premium
from Deendayal_botz import DeendayalBot
from util.keepalive import ping_server
from Deendayal_botz.clients import initialize_clients
import pytz
from datetime import date, datetime

# ✅ Logging setup
logging.config.fileConfig('logging.conf')
logging.getLogger().setLevel(logging.INFO)
logging.getLogger("pyrogram").setLevel(logging.ERROR)
logging.getLogger("aiohttp").setLevel(logging.ERROR)

# ✅ Bot Start Time
botStartTime = time.time()

# ✅ Plugin Path
ppath = "plugins/*.py"
files = glob.glob(ppath)

async def Deendayal_start():
    print('\nInitializing Deendayal Dhakad Bot...')
    
    # ✅ Fix: Properly start the bot
    await DeendayalBot.start()

    bot_info = await DeendayalBot.get_me()
    DeendayalBot.username = bot_info.username
    await initialize_clients()

    # ✅ Plugin Loader
    for name in files:
        plugin_name = Path(name).stem
        import_path = f"plugins.{plugin_name}"
        
        try:
            spec = importlib.util.spec_from_file_location(import_path, name)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            sys.modules[import_path] = module
            print(f"Deendayal Dhakad Imported => {plugin_name}")
        except Exception as e:
            print(f"❌ Error loading {plugin_name}: {e}")

    if ON_HEROKU:
        asyncio.create_task(ping_server())

    # ✅ Fetch Banned Users & Chats
    temp.BANNED_USERS, temp.BANNED_CHATS = await db.get_banned()

    # ✅ Indexes Setup
    await Media.ensure_indexes()
    await Media2.ensure_indexes()

    # ✅ Check Database Space
    stats = await clientDB.command('dbStats')
    free_dbSize = round(512 - ((stats['dataSize']/(1024*1024)) + (stats['indexSize']/(1024*1024))), 2)

    if DATABASE_URI2 and free_dbSize < 62:
        tempDict["indexDB"] = DATABASE_URI2
        logging.info(f"Using Secondary DB (Primary DB has {free_dbSize} MB left).")
    elif DATABASE_URI2 is None:
        logging.error("❌ Missing SECONDDB_URI! Exiting...")
        exit()
    else:
        logging.info(f"Primary DB has enough space ({free_dbSize} MB), using it.")

    await choose_mediaDB()  

    # ✅ Fetch Bot Info
    me = await DeendayalBot.get_me()
    temp.ME = me.id
    temp.U_NAME = me.username
    temp.B_NAME = me.first_name
    temp.B_LINK = me.mention
    DeendayalBot.username = '@' + me.username

    # ✅ Start Premium Checker
    DeendayalBot.loop.create_task(check_expired_premium(DeendayalBot))

    logging.info(f"{me.first_name} (Pyrogram v{__version__} | Layer {layer}) started on {me.username}.")
    
    # ✅ Send Restart Message
    tz = pytz.timezone('Asia/Kolkata')
    today = date.today()
    now = datetime.now(tz)
    time_str = now.strftime("%H:%M:%S %p")

    await DeendayalBot.send_message(chat_id=LOG_CHANNEL, text=f"🤖 **Bot Restarted!**\n🔹 Name: {temp.B_NAME}\n📅 Date: {today}\n🕒 Time: {time_str}")

    # ✅ Web Server Setup
    app = web.AppRunner(await web_server())
    await app.setup()
    await web.TCPSite(app, "0.0.0.0", PORT).start()

    # ✅ Keep Bot Running
    await idle()

    # ✅ Stop Bot Gracefully
    await DeendayalBot.stop()
    logging.info("Bot Stopped.")

if __name__ == '__main__':
    try:
        asyncio.run(Deendayal_start())  # ✅ Fix: Correct event loop handling
    except KeyboardInterrupt:
        logging.info("Service Stopped. Bye 👋")
