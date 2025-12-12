# plugins/autoforward.py
# Telethon read -> Pyrogram userbot copy_message (sender hidden)
# Single-task enforced, lazy use of shared userbot (no start/stop here)

import re
import asyncio
from shared_client import client as tclient, userbot, app
from pyrogram import filters
from pyrogram.types import Message

TASK_LOCK = asyncio.Lock()


def parse_tg_link(link: str):
    """
    Accepts:
      - https://t.me/c/<id>/<idspec>
      - https://t.me/<username>/<idspec>
    Where <idspec> can be:
      - single id (123)
      - range a-b (12-15)
      - slash form start/end (12/15)
      - comma list (12,14,18)
    Returns: (chat_identifier_for_telethon, [msg_ids]) or None
    """
    link = link.strip()
    # /c/<chatid>/<idspec> form (private)
    m = re.match(r"https?://t\.me/c/(\d+)/(.*)", link)
    if m:
        raw = m.group(1)
        rest = m.group(2)
        chat_id = int(f"-100{raw}")
        msg_ids = set()
        for part in re.split(r"[,\s]+", rest):
            if not part:
                continue
            if "-" in part:
                try:
                    a, b = part.split("-", 1)
                    a_i, b_i = int(a), int(b)
                    if b_i < a_i:
                        a_i, b_i = b_i, a_i
                    msg_ids.update(range(a_i, b_i + 1))
                except:
                    continue
            elif "/" in part:
                try:
                    a, b = part.split("/", 1)
                    a_i, b_i = int(a), int(b)
                    if b_i < a_i:
                        a_i, b_i = b_i, a_i
                    msg_ids.update(range(a_i, b_i + 1))
                except:
                    continue
            else:
                try:
                    msg_ids.add(int(part))
                except:
                    continue
        if not msg_ids:
            return None
        return chat_id, sorted(msg_ids)

    # public username form: https://t.me/username/123  or /username/12-15 or /username/12/15
    m2 = re.match(r"https?://t\.me/([^/]+)/(.+)", link)
    if m2:
        uname = m2.group(1)
        rest = m2.group(2)
        msg_ids = set()
        for part in re.split(r"[,\s]+", rest):
            if not part:
                continue
            if "-" in part:
                try:
                    a, b = part.split("-", 1)
                    a_i, b_i = int(a), int(b)
                    if b_i < a_i:
                        a_i, b_i = b_i, a_i
                    msg_ids.update(range(a_i, b_i + 1))
                except:
                    continue
            elif "/" in part:
                try:
                    a, b = part.split("/", 1)
                    a_i, b_i = int(a), int(b)
                    if b_i < a_i:
                        a_i, b_i = b_i, a_i
                    msg_ids.update(range(a_i, b_i + 1))
                except:
                    continue
            else:
                try:
                    msg_ids.add(int(part))
                except:
                    continue
        if not msg_ids:
            return None
        return uname, sorted(msg_ids)

    return None


async def _copy_single(dest_chat, source_chat, mid):
    """
    Read via Telethon and copy via Pyrogram userbot.
    Return True on success, False otherwise.
    """
    try:
        # Telethon read
        try:
            tmsg = await tclient.get_messages(source_chat, ids=mid)
        except Exception:
            tmsg = None

        # preserve thread id if available
        thread_id = None
        if tmsg is not None:
            # Telethon attribute possibilities: message_thread_id, thread_id
            thread_id = getattr(tmsg, "message_thread_id", None) or getattr(tmsg, "thread_id", None) or None

        # Copy via userbot (userbot must be running as SRCV3 ensures)
        kwargs = {}
        if thread_id:
            kwargs["message_thread_id"] = thread_id

        await userbot.copy_message(dest_chat, source_chat, mid, **kwargs)
        return True
    except Exception:
        return False


@app.on_message(filters.command("forward"))
async def forward_command(client: app.__class__, message: Message):
    """
    /forward <link>
    """
    if TASK_LOCK.locked():
        return await message.reply("⚠️ Another task is already running. Try again later.", quote=True)

    if len(message.command) < 2:
        return await message.reply("❌ Usage:\n`/forward https://t.me/c/CHAT/ID-ID`", quote=True)

    link = message.command[1].strip()
    parsed = parse_tg_link(link)
    if not parsed:
        return await message.reply("❌ Invalid link format. Use https://t.me/c/CHAT/ID-ID or https://t.me/username/ID-ID", quote=True)

    source_chat, msg_list = parsed
    dest_chat = message.chat.id

    # run single task
    await TASK_LOCK.acquire()
    try:
        status = await message.reply(f"📥 Copying {len(msg_list)} messages from `{source_chat}` to this chat...", quote=True)

        success = 0
        failed = 0
        for mid in msg_list:
            await asyncio.sleep(0.20)  # throttle a bit
            ok = await _copy_single(dest_chat, source_chat, mid)
            if ok:
                success += 1
            else:
                failed += 1

        await status.edit(f"✅ Done. Copied: `{success}`. Failed: `{failed}`")
    finally:
        if TASK_LOCK.locked():
            TASK_LOCK.release()


# plugin loader compatibility
async def run_autoforward_plugin():
    print("Autoforward plugin loaded")