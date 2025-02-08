import sys
import glob
import importlib
from pathlib import Path
from pyrogram import idle, Client, __version__
import logging
import logging.config
import time  
import asyncio
import pytz
from datetime import date, datetime
from aiohttp import web
from database.ia_filterdb import Media, Media2, tempDict, choose_mediaDB, db as clientDB
from database.users_chats_db import db
from info import *
from utils import temp
from typing import Union, Optional, AsyncGenerator
from pyrogram import types
from Script import script 
from plugins import web_server, check_expired_premium
from Deendayal_botz import DeendayalBot
from util.keepalive import ping_server
from Deendayal_botz.clients import initialize_clients

# ✅ Logging Configuration
logging.config.fileConfig('logging.conf')
logging.getLogger().setLevel(logging.INFO)
logging.getLogger("pyrogram").setLevel(logging.ERROR)
logging.getLogger("imdbpy").setLevel(logging.ERROR)
logging.getLogger("aiohttp").setLevel(logging.ERROR)
logging.getLogger("aiohttp.web").setLevel(logging.ERROR)

# ✅ Start Time
botStartTime = time.time()

# ✅ Fix: Ensure asyncio event loop is set properly
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

# ✅ Plugin Path
ppath = "plugins/*.py"
files = glob.glob(ppath)

async def Deendayal_start():
    print('\nInitializing Deendayal Dhakad Bot...')

    # ✅ Fix: Properly start the bot
    await DeendayalBot.start()  # 🛠️ Await bot start

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
            print(f"✅ Deendayal Dhakad Imported => {plugin_name}")
        except Exception as e:
            print(f"❌ Error loading {plugin_name}: {e}")

    # ✅ Ping Server for Heroku
    if ON_HEROKU:
        asyncio.create_task(ping_server())

    # ✅ Fetch Banned Users & Chats
    b_users, b_chats = await db.get_banned()
    temp.BANNED_USERS = b_users
    temp.BANNED_CHATS = b_chats

    # ✅ Database Size Check
    await Media.ensure_indexes()
    await Media2.ensure_indexes()
    stats = await clientDB.command('dbStats')
    free_dbSize = round(512 - ((stats['dataSize']/(1024*1024)) + (stats['indexSize']/(1024*1024))), 2)

    if DATABASE_URI2 and free_dbSize < 62:
        tempDict["indexDB"] = DATABASE_URI2
        logging.info(f"Since Primary DB has only {free_dbSize} MB left, switching to Secondary DB.")
    elif not DATABASE_URI2:
        logging.error("❌ Missing SECONDDB_URI! Exiting...")
        exit()
    else:
        logging.info(f"Primary DB has enough space ({free_dbSize}MB), continuing...")

    await choose_mediaDB()

    # ✅ Set Bot Variables
    temp.ME = bot_info.id
    temp.U_NAME = bot_info.username
    temp.B_NAME = bot_info.first_name
    temp.B_LINK = bot_info.mention
    DeendayalBot.username = '@' + bot_info.username

    # ✅ Start Premium Expiry Checker
    DeendayalBot.loop.create_task(check_expired_premium(DeendayalBot))

    logging.info(f"{bot_info.first_name} (Pyrogram v{__version__}) started on {bot_info.username}.")
    logging.info(LOG_STR)
    logging.info(script.LOGO)

    # ✅ Send Bot Start Message
    tz = pytz.timezone('Asia/Kolkata')
    today = date.today()
    now = datetime.now(tz)
    current_time = now.strftime("%H:%M:%S %p")

    await DeendayalBot.send_message(
        chat_id=LOG_CHANNEL, 
        text=script.RESTART_TXT.format(temp.B_LINK, today, current_time)
    )

    # ✅ Web Server Start
    app = web.AppRunner(await web_server())
    await app.setup()
    await web.TCPSite(app, "0.0.0.0", PORT).start()

    # ✅ Idle
    await idle()

if __name__ == '__main__':
    try:
        loop.run_until_complete(Deendayal_start())
    except KeyboardInterrupt:
        logging.info('Service Stopped. Bye 👋')
