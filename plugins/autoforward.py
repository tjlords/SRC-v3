# patched autoforward.py
from shared_client import app
from plugins.batch import get_uclient, UB
from pyrogram import filters
import re, asyncio

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
                    a,b = part.split("-",1)
                    a_i = int(a); b_i = int(b)
                    if b_i < a_i: a_i,b_i = b_i,a_i
                    msg_ids.update(range(a_i, b_i+1))
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


@app.on_message(filters.command("forward"))
async def forward_command(client, message):
    if len(message.command) < 2:
        return await message.reply("❌ Usage:\n`/forward https://t.me/c/CHAT/ID-ID`")

    link = message.command[1].strip()
    parsed = parse_tg_link(link)
    if not parsed:
        return await message.reply("❌ Invalid link format.")

    source_chat, msg_list = parsed
    dest_chat = message.chat.id
    uid = message.from_user.id

    status = await message.reply(f"📥 Copying {len(msg_list)} messages from `{source_chat}`...")

    uc = await get_uclient(uid)
    ubot = UB.get(uid)
    fallback_clients = [uc, ubot, app]
    client_to_use = next((c for c in fallback_clients if c), app)

    success = 0
    failed = 0
    for mid in msg_list:
        try:
            await asyncio.sleep(0.25)
            source_msg = None
            for c in [uc, ubot, app]:
                if not c:
                    continue
                try:
                    source_msg = await c.get_messages(source_chat, mid)
                    if source_msg:
                        break
                except Exception:
                    continue

            kwargs = {}
            if source_msg and getattr(source_msg, "message_thread_id", None):
                kwargs["message_thread_id"] = source_msg.message_thread_id

            await client_to_use.copy_message(dest_chat, source_chat, mid, **kwargs)
            success += 1
        except Exception:
            failed += 1

    await status.edit(f"✅ Done. Copied: `{success}`, Failed: `{failed}`")

async def run_autoforward_plugin():
    print("Autoforward plugin loaded")
