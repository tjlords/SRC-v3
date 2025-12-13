# plugins/autoforward.py
# Clean, from-scratch /forward
# Pyrogram USERBOT ONLY
# v9-equivalent behavior

import re
import asyncio
from pyrogram import filters
from pyrogram.types import Message
from shared_client import app, userbot

TASK_LOCK = asyncio.Lock()


def parse_link(link: str):
    """
    Supports:
    - https://t.me/c/<chatid>/<msg or range>
    - https://t.me/<username>/<msg or range>
    """
    link = link.strip()

    m = re.match(r"https?://t\.me/c/(\d+)/(.*)", link)
    if m:
        chat_id = int(f"-100{m.group(1)}")
        return chat_id, parse_ids(m.group(2))

    m = re.match(r"https?://t\.me/([^/]+)/(.+)", link)
    if m:
        return m.group(1), parse_ids(m.group(2))

    return None, []


def parse_ids(text: str):
    """
    Parse:
    123
    123-130
    123/130
    123,125,128
    """
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


async def resolve_chat(chat):
    """
    CRITICAL:
    Hydrates access_hash & peer cache
    This is what v9 was doing implicitly
    """
    try:
        await userbot.get_chat(chat)
    except:
        pass


async def copy_one(dest_chat, source_chat, msg_id):
    try:
        # Fetch message first (hydrates peer + thread)
        msg = await userbot.get_messages(source_chat, msg_id)
        if not msg:
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
    except Exception as e:
        return False


@app.on_message(filters.command("forward"))
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
            f"📥 Copying `{len(msg_ids)}` message(s)…",
            quote=True
        )

        # 🔥 THIS IS THE KEY LINE
        await resolve_chat(source_chat)

        ok = 0
        fail = 0

        for mid in msg_ids:
            await asyncio.sleep(0.25)
            if await copy_one(dest_chat, source_chat, mid):
                ok += 1
            else:
                fail += 1

        await status.edit(f"✅ Copied: `{ok}` | ❌ Failed: `{fail}`")

    finally:
        TASK_LOCK.release()