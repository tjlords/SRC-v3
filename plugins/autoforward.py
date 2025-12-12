# plugins/autoforward.py
# Always use the project's Pyrogram user session (userbot) to copy messages.
# Single-task enforced (Option C). Lazy-start userbot only for task; stop it after if we started it.

from shared_client import app, userbot
from pyrogram import filters
from pyrogram.types import Message
import re
import asyncio

# module-level lock to ensure only one task runs at a time
TASK_LOCK = asyncio.Lock()

def parse_tg_link(link: str):
    link = link.strip()
    m_full = re.match(r"https?://t\.me/c/(\d+)/(.*)", link)
    if m_full:
        chat_raw = m_full.group(1)
        rest = m_full.group(2)
        try:
            chat_id = int(f"-100{chat_raw}")
        except:
            return None
        msg_ids = set()
        for part in rest.split(","):
            part = part.strip()
            if not part:
                continue
            if "-" in part:
                try:
                    a, b = part.split("-", 1)
                    a_i = int(a); b_i = int(b)
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

    m_pub = re.match(r"https?://t\.me/([^/]+)/(\d+)", link)
    if m_pub:
        uname = m_pub.group(1)
        mid = int(m_pub.group(2))
        return uname, [mid]

    return None


async def _ensure_userbot_started():
    """
    Start userbot if not started. Return True if we started it here, False if already running.
    May raise if start fails.
    """
    # many pyrogram versions don't expose is_connected publicly; use attribute flag
    if getattr(userbot, "_is_connected", False):
        return False
    # If pyrogram Client has .is_connected()
    try:
        is_conn = await userbot.is_connected()
    except Exception:
        is_conn = getattr(userbot, "_is_connected", False)
    if is_conn:
        userbot._is_connected = True
        return False
    # start and mark
    await userbot.start()
    userbot._is_connected = True
    return True


async def _maybe_stop_userbot(started_here: bool):
    """
    Stop userbot if we started it here. If it was already running, keep it running.
    """
    if started_here:
        try:
            await userbot.stop()
            userbot._is_connected = False
        except Exception:
            # ignore stop errors but clear flag
            userbot._is_connected = False


@app.on_message(filters.command("forward"))
async def forward_command(client: app.__class__, message: Message):
    # enforce single-task
    if TASK_LOCK.locked():
        return await message.reply("⚠️ Another task is already running. Try again later.", quote=True)

    if len(message.command) < 2:
        return await message.reply("❌ Usage:\n`/forward https://t.me/c/CHAT/ID-ID`", quote=True)

    link = message.command[1].strip()
    parsed = parse_tg_link(link)
    if not parsed:
        return await message.reply("❌ Invalid link format. Use https://t.me/c/CHAT/ID or https://t.me/c/CHAT/ID-ID or comma list like 12,15", quote=True)

    source_chat, msg_list = parsed
    dest_chat = message.chat.id

    # Acquire lock for entire operation
    await TASK_LOCK.acquire()
    started_userbot = False
    try:
        status = await message.reply(f"📥 Copying {len(msg_list)} messages from `{source_chat}` to this chat...", quote=True)

        # Start userbot lazily (only for the duration). If start fails, report.
        try:
            started_userbot = await _ensure_userbot_started()
        except Exception as e:
            await status.edit(f"❌ Failed to start user session: {e}")
            return

        success = 0
        failed = 0
        for mid in msg_list:
            try:
                await asyncio.sleep(0.25)
                source_msg = None
                try:
                    source_msg = await userbot.get_messages(source_chat, mid)
                except Exception:
                    source_msg = None

                kwargs = {}
                if source_msg and getattr(source_msg, "message_thread_id", None):
                    kwargs["message_thread_id"] = source_msg.message_thread_id

                # Copy using userbot (will hide original sender)
                await userbot.copy_message(dest_chat, source_chat, mid, **kwargs)
                success += 1
            except Exception:
                failed += 1

        await status.edit(f"✅ Done. Copied: `{success}`. Failed: `{failed}`")
    finally:
        # stop userbot only if we started it here
        try:
            await _maybe_stop_userbot(started_userbot)
        finally:
            if TASK_LOCK.locked():
                TASK_LOCK.release()


# required by your main.py plugin loader
async def run_autoforward_plugin():
    print("Autoforward plugin loaded")