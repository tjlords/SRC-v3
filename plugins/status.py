# plugins/status.py
from shared_client import app, userbot, client as tclient
from pyrogram import filters
import asyncio


@app.on_message(filters.command("status"))
async def status_handler(_, message):
    # check Pyrogram bot
    bot_ok = "❌"
    try:
        me = await app.get_me()
        if me:
            bot_ok = "✅"
    except:
        bot_ok = "❌"

    # check Pyrogram userbot
    pyro_ok = "❌"
    try:
        me2 = await userbot.get_me()
        if me2:
            pyro_ok = "✅"
    except:
        pyro_ok = "❌"

    # check Telethon
    tele_ok = "❌"
    try:
        # Telethon must be connected and authorized
        if tclient.is_connected():
            tele_ok = "✅"
    except:
        tele_ok = "❌"

    await message.reply(
        f"📡 **SRCV3 Client Status**\n\n"
        f"🤖 Pyrogram Bot: {bot_ok}\n"
        f"👤 Userbot (Pyrogram): {pyro_ok}\n"
        f"🕵️ Telethon Client: {tele_ok}",
        quote=True
    )
