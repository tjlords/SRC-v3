# plugins/autoforward.py
# FINAL, WORKING autoforward for SRCV3
# Pyrogram USERBOT only
# v9 parity + proper handler filters

import re
import asyncio
from pyrogram import filters
from pyrogram.types import Message
from shared_client import app, userbot

TASK_LOCK = asyncio.Lock()


def parse_ids(text: str):
    ids = set()
    for part in re.split(r"[,\s]+", text):
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
        elif "/" in part:
            a, b = part.split("/", 1)
        else:
            try:
                ids.add(int(part))
            except:
                pass
            continue

        try:
            a, b = int(a), int(b)
            if b < a:
                a, b = b, a
            ids.update(range(a, b + 1))
        except:
            pass

    return sorted(ids)


def parse_link(link: str):
    link = link.strip()

    m = re.match(r"https?://t\.me/c/(\d+)/(.*)", link)
    if m:
        chat_id = int(f"-100{m.group(1)}")
        return chat_id, parse_ids(m.group(2))

    m = re.match(r"https?://t\.me/([^/]+)/(.+)", link)
    if m:
        return m.group(1), parse_ids(m.group(2))

    return None, []


async def resolve_chat(chat):
    # Hydrate peer cache (access_hash) – REQUIRED
    try:
        await userbot.get_chat(chat)
    except:
        pass


async def copy_one(dest_chat, source_chat, msg_id):
    try:
        msg = await userbot.get_messages(source_chat, msg_id)
        if not msg:
            return False

        # Skip only true system messages
        if msg.service:
            return False

        kwargs = {}
        if msg.message_thread_id:
            kwargs["message_thread_id"] = msg.message_thread_id

        await userbot.copy_message(
            chat_id=dest_chat,
            from_chat_id=source_chat,
            message_id=msg_id,
            **kwargs
        )
        return True

    except Exception:
        return False


@app.on_message(
    filters.command("forward", prefixes="/")
    & (filters.private | filters.group | filters.supergroup | filters.channel)
)
async def forward_handler(_, message: Message):

    if TASK_LOCK.locked():
        return await message.reply(
            "⚠️ Another task is already running.",
            quote=True
        )

    if len(message.command) < 2:
        return await message.reply(
            "❌ Usage:\n`/forward https://t.me/c/CHAT/ID`",
            quote=True
        )

    source_chat, msg_ids = parse_link(message.command[1])
    if not source_chat or not msg_ids:
        return await message.reply("❌ Invalid link.", quote=True)

    dest_chat = message.chat.id

    await TASK_LOCK.acquire()
    try:
        status = await message.reply(
            f"🔍 Processing forward: {message.command[1]}",
            quote=True
        )

        # REQUIRED for fresh deploys
        await resolve_chat(source_chat)

        ok = 0
        fail = 0

        for mid in msg_ids:
            await asyncio.sleep(0.25)
            if await copy_one(dest_chat, source_chat, mid):
                ok += 1
            else:
                fail += 1

        await status.edit(
            f"✅ Forwarded {ok}, failures reported {fail}"
        )

    finally:
        TASK_LOCK.release()