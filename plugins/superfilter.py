
# plugins/superfilter.py
# Advanced SuperFilter plugin for SRCV3
from shared_client import app
from pyrogram import filters
from utils.func import get_user_data_key, save_user_data
import re
import asyncio

async def apply_rules(text, uid):
    """Apply all user-defined superfilter rules to the input text and return modified text."""
    replaces = await get_user_data_key(uid, "super_replace", {}) or {}
    removes  = await get_user_data_key(uid, "super_remove", []) or []
    regexes  = await get_user_data_key(uid, "super_regex", []) or []
    cases    = await get_user_data_key(uid, "super_case", {}) or {}
    begins   = await get_user_data_key(uid, "super_begin", {}) or {}
    ends     = await get_user_data_key(uid, "super_end", {}) or {}

    output = text

    # Normal (case-sensitive) literal replaces
    for old, new in replaces.items():
        if old:
            output = output.replace(old, new)

    # Case-insensitive replaces using re.sub with IGNORECASE
    for old, new in cases.items():
        if old:
            try:
                output = re.sub(re.escape(old), new, output, flags=re.IGNORECASE)
            except Exception:
                output = output.replace(old, new)

    # Regex replaces
    for entry in regexes:
        try:
            pat = entry.get("pattern")
            rep = entry.get("replace", "")
            if pat:
                output = re.sub(pat, rep, output)
        except Exception:
            continue

    # Remove lines that contain any removal token
    if removes:
        lines = output.splitlines()
        lines = [l for l in lines if not any(rem in l for rem in removes)]
        output = "\n".join(lines)

    # Replace only at beginning of lines
    if begins:
        lines = output.splitlines()
        new_lines = []
        for l in lines:
            replaced = False
            for start_text, repl in begins.items():
                if start_text and l.startswith(start_text):
                    new_lines.append(repl + l[len(start_text):])
                    replaced = True
                    break
            if not replaced:
                new_lines.append(l)
        output = "\n".join(new_lines)

    # Replace only at end of lines
    if ends:
        lines = output.splitlines()
        new_lines = []
        for l in lines:
            replaced = False
            for end_text, repl in ends.items():
                if end_text and l.endswith(end_text):
                    new_lines.append(l[:-len(end_text)] + repl)
                    replaced = True
                    break
            if not replaced:
                new_lines.append(l)
        output = "\n".join(new_lines)

    return output

@app.on_message(filters.command("superfilter"))
async def superfilter_panel(client, message):
    uid = message.from_user.id

    repl  = await get_user_data_key(uid, "super_replace", {}) or {}
    rem   = await get_user_data_key(uid, "super_remove", []) or []
    regex = await get_user_data_key(uid, "super_regex", []) or []
    cases = await get_user_data_key(uid, "super_case", {}) or {}
    begins= await get_user_data_key(uid, "super_begin", {}) or {}
    ends  = await get_user_data_key(uid, "super_end", {}) or {}

    txt = "🛠️ **SUPER FILTER PANEL**\n(Advanced post-edit filters)\n\n"

    txt += "🔄 **Replace (literal, case-sensitive):**\n"
    if repl:
        for k,v in repl.items():
            txt += f"• `{k}` → `{v}`\n"
    else:
        txt += "• None\n"

    txt += "\n🔤 **Case-insensitive replace:**\n"
    if cases:
        for k,v in cases.items():
            txt += f"• `{k}` → `{v}`\n"
    else:
        txt += "• None\n"

    txt += "\n\n🗑 **Remove lines containing:**\n"
    if rem:
        for r in rem:
            txt += f"• `{r}`\n"
    else:
        txt += "• None\n"

    txt += "\n\n🔍 **Regex Filters:**\n"
    if regex:
        for e in regex:
            txt += f"• `{e.get('pattern')}` → `{e.get('replace')}`\n"
    else:
        txt += "• None\n"

    txt += "\n\n⏩ **Begin-with replace:**\n"
    if begins:
        for k,v in begins.items():
            txt += f"• `{k}` → `{v}`\n"
    else:
        txt += "• None\n"

    txt += "\n\n⏪ **End-with replace:**\n"
    if ends:
        for k,v in ends.items():
            txt += f"• `{k}` → `{v}`\n"
    else:
        txt += "• None\n"

    txt += (
        "\n\n🔧 **Commands:**\n"
        "`/addsuperreplace old | new`\n"
        "`/addsupercase old | new` (case-insensitive)\n"
        "`/addsuperremove text`\n"
        "`/addsuperregex pattern | replace`\n"
        "`/addsuperbegin prefix | replace`\n"
        "`/addsuperend suffix | replace`\n"
        "`/clearsuperfilters`\n"
        "`/superfilteredit https://t.me/c/CHAT/ID-ID`\n"
    )

    await message.reply(txt)

@app.on_message(filters.command("addsuperreplace"))
async def add_super_replace(client, message):
    if "|" not in message.text:
        return await message.reply("❌ Usage: `/addsuperreplace old | new`")

    uid = message.from_user.id
    _, payload = message.text.split(" ",1)
    old, new = [x.strip() for x in payload.split("|",1)]

    data = await get_user_data_key(uid, "super_replace", {}) or {}
    data[old] = new
    await save_user_data(uid, "super_replace", data)

    await message.reply(f"✅ Replace added:\n`{old}` → `{new}`")

@app.on_message(filters.command("addsupercase"))
async def add_super_case(client, message):
    if "|" not in message.text:
        return await message.reply("❌ Usage: `/addsupercase old | new`")

    uid = message.from_user.id
    _, payload = message.text.split(" ",1)
    old, new = [x.strip() for x in payload.split("|",1)]

    data = await get_user_data_key(uid, "super_case", {}) or {}
    data[old] = new
    await save_user_data(uid, "super_case", data)

    await message.reply(f"🔤 Case-insensitive replace added:\n`{old}` → `{new}`")

@app.on_message(filters.command("addsuperremove"))
async def add_super_remove(client, message):
    if len(message.command) < 2:
        return await message.reply("❌ Usage: `/addsuperremove text`")

    uid = message.from_user.id
    text = message.text.split(" ",1)[1].strip()

    data = await get_user_data_key(uid, "super_remove", []) or []
    if text not in data:
        data.append(text)

    await save_user_data(uid, "super_remove", data)
    await message.reply(f"🗑 Rule added: `{text}`")

@app.on_message(filters.command("addsuperregex"))
async def add_super_regex(client, message):
    if "|" not in message.text:
        return await message.reply("❌ Usage: `/addsuperregex pattern | replace`")

    uid = message.from_user.id
    _, payload = message.text.split(" ",1)
    pattern, rep = [x.strip() for x in payload.split("|",1)]

    data = await get_user_data_key(uid, "super_regex", []) or []
    data.append({"pattern": pattern, "replace": rep})

    await save_user_data(uid, "super_regex", data)
    await message.reply(f"🔍 Regex rule added:\n`{pattern}` → `{rep}`")

@app.on_message(filters.command("addsuperbegin"))
async def add_super_begin(client, message):
    if "|" not in message.text:
        return await message.reply("❌ Usage: `/addsuperbegin prefix | replace`")

    uid = message.from_user.id
    _, payload = message.text.split(" ",1)
    prefix, rep = [x.strip() for x in payload.split("|",1)]

    data = await get_user_data_key(uid, "super_begin", {}) or {}
    data[prefix] = rep
    await save_user_data(uid, "super_begin", data)
    await message.reply(f"⏩ Begin-with rule added:\n`{prefix}` → `{rep}`")

@app.on_message(filters.command("addsuperend"))
async def add_super_end(client, message):
    if "|" not in message.text:
        return await message.reply("❌ Usage: `/addsuperend suffix | replace`")

    uid = message.from_user.id
    _, payload = message.text.split(" ",1)
    suffix, rep = [x.strip() for x in payload.split("|",1)]

    data = await get_user_data_key(uid, "super_end", {}) or {}
    data[suffix] = rep
    await save_user_data(uid, "super_end", data)
    await message.reply(f"⏪ End-with rule added:\n`{suffix}` → `{rep}`")

@app.on_message(filters.command("clearsuperfilters"))
async def clear_super_filters(client, message):
    uid = message.from_user.id
    await save_user_data(uid, "super_replace", {})
    await save_user_data(uid, "super_remove", [])
    await save_user_data(uid, "super_regex", [])
    await save_user_data(uid, "super_case", {})
    await save_user_data(uid, "super_begin", {})
    await save_user_data(uid, "super_end", {})
    await message.reply("♻️ All superfilters cleared!")

@app.on_message(filters.me)
async def auto_super_edit(client, message):
    uid = message.from_user.id

    # Only edit if there are rules
    replaces = await get_user_data_key(uid, "super_replace", {}) or {}
    removes  = await get_user_data_key(uid, "super_remove", []) or []
    regexes  = await get_user_data_key(uid, "super_regex", []) or {}
    cases    = await get_user_data_key(uid, "super_case", {}) or {}
    begins   = await get_user_data_key(uid, "super_begin", {}) or {}
    ends     = await get_user_data_key(uid, "super_end", {}) or {}

    if not (replaces or removes or regexes or cases or begins or ends):
        return

    original = message.text or message.caption
    if not original:
        return

    await asyncio.sleep(0.6)
    try:
        new = await apply_rules(original, uid)
        if new != original:
            try:
                await message.edit(new)
            except Exception:
                pass
    except Exception:
        pass

@app.on_message(filters.command("superfilteredit"))
async def superfilter_edit_range(client, message):
    if len(message.command) < 2:
        return await message.reply("❌ Usage:\n`/superfilteredit https://t.me/c/CHAT/ID-ID`")

    uid = message.from_user.id
    link = message.command[1]

    pat = r"https?://t\.me/c/(\d+)/(\d+)(?:-(\d+))?"
    m = re.match(pat, link)
    if not m:
        return await message.reply("❌ Invalid link format. Use https://t.me/c/CHAT/START-END")

    chat_raw = m.group(1)
    msg_start = int(m.group(2))
    msg_end = int(m.group(3)) if m.group(3) else msg_start
    chat_id = int(f"-100{chat_raw}")

    await message.reply(f"🛠 Applying SUPERFILTER to messages `{msg_start}` → `{msg_end}`…")

    edited = 0
    failed = 0

    for mid in range(msg_start, msg_end + 1):
        try:
            msg = await client.get_messages(chat_id, mid)
            if not msg:
                failed += 1
                continue

            original = msg.text or msg.caption
            if not original:
                continue

            new_text = await apply_rules(original, uid)
            if new_text != original:
                await asyncio.sleep(0.45)
                try:
                    await msg.edit(new_text)
                    edited += 1
                except Exception:
                    failed += 1
        except Exception:
            failed += 1

    await message.reply(f"✅ Done. Edited: `{edited}` ⚠️ Failed: `{failed}`")
