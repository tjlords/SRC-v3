
# plugins/autoforward.py
# Auto-forward / copy plugin for SRCV3
from shared_client import app
from pyrogram import filters
import re
import asyncio

def parse_tg_link(link: str):
    """Parse t.me/c/CHAT/ID or t.me/c/CHAT/ID-ID or t.me/c/CHAT/ID,ID2"""
    link = link.strip()
    m_full = re.match(r"https?://t\.me/c/(\d+)/(.*)", link)
    if not m_full:
        return None
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
                if b_i < a_i:
                    a_i, b_i = b_i, a_i
                for i in range(a_i, b_i+1):
                    msg_ids.add(i)
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

@app.on_message(filters.command("forward"))
async def forward_command(client, message):
    if len(message.command) < 2:
        return await message.reply("❌ Usage:\n`/forward https://t.me/c/CHAT/ID-ID`")

    link = message.command[1].strip()
    parsed = parse_tg_link(link)
    if not parsed:
        return await message.reply("❌ Invalid link format. Use https://t.me/c/CHAT/ID or https://t.me/c/CHAT/ID-ID or comma list like 12,15")

    source_chat, msg_list = parsed
    dest_chat = message.chat.id

    status = await message.reply(f"📥 Copying {len(msg_list)} messages from `{source_chat}` to this chat...")

    success = 0
    failed = 0
    for mid in msg_list:
        try:
            await asyncio.sleep(0.25)  # small delay to be gentle
            await client.copy_message(dest_chat, source_chat, mid)
            success += 1
        except Exception:
            failed += 1
    await status.edit(f"✅ Done. Copied: `{success}`. Failed: `{failed}`")
