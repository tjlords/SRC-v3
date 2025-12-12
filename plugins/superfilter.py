# plugins/superfilter.py
# Advanced SUPERFILTER plugin for SRCV3
# - apply_rules(text, uid) exported so batch send pipeline can call it before sending
# - per-user storage via utils.func (get_user_data_key/save_user_data)
# - /superfilteredit uses per-user client (get_uclient) to edit ranges

from shared_client import app
from pyrogram import filters
from utils.func import get_user_data_key, save_user_data
from plugins.batch import get_uclient
import re
import asyncio

async def apply_rules(text, uid):
    """
    Apply all user-defined superfilter rules to the input text and return modified text.
    - text: str
    - uid: numeric user id (owner of rules)
    """
    if text is None:
        return text

    replaces = await get_user_data_key(uid, "super_replace", {}) or {}
    removes  = await get_user_data_key(uid, "super_remove", []) or []
    regexes  = await get_user_data_key(uid, "super_regex", []) or []
    cases    = await get_user_data_key(uid, "super_case", {}) or {}
    begins   = await get_user_data_key(uid, "super_begin", {}) or {}
    ends     = await get_user_data_key(uid, "super_end", {}) or {}

    output = str(text)

    # literal (case-sensitive) replaces
    for old, new in replaces.items():
        if not old:
            continue
        output = output.replace(old, new)

    # case-insensitive replaces
    for old, new in cases.items():
        if not old:
            continue
        try:
            output = re.sub(re.escape(old), new, output, flags=re.IGNORECASE)
        except Exception:
            output = output.replace(old, new)

    # regex replaces (pattern -> replace)
    for entry in regexes:
        try:
            pat = entry.get("pattern")
            rep = entry.get("replace", "")
            if pat:
                output = re.sub(pat, rep, output)
        except Exception:
            continue

    # remove lines containing any removal token
    if removes:
        lines = output.splitlines()
        lines = [l for l in lines if not any(rem in l for rem in removes)]
        output = "\n".join(lines)

    # replace at beginning of lines
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

    # replace at end of lines
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


# ---------------------------
# /superfilter panel
# ---------------------------
@app.on_message(filters.command("superfilter"))
async def superfilter_panel(client, message):
    uid = message.from_user.id
    repl  = await get_user_data_key(uid, "super_replace", {}) or {}
    rem   = await get_user_data_key(uid, "super_remove", []) or []
    regex = await get_user_data_key(uid, "super_regex", []) or []
    cases = await get_user_data_key(uid, "super_case", {}) or {}
    begins= await get_user_data_key(uid, "super_begin", {}) or {}
    ends  = await get_user_data_key(uid, "super_end", {}) or {}

    lines = [
        "🛠️ SUPER FILTER PANEL (per-user)",
        "(Advanced post-edit filters)",
        "",
        "🔄 Replace (literal, case-sensitive):"
    ]
    if repl:
        for k, v in repl.items():
            lines.append(f"• `{k}` → `{v}`")
    else:
        lines.append("• None")

    lines.append("")
    lines.append("🔤 Case-insensitive replace:")
    if cases:
        for k, v in cases.items():
            lines.append(f"• `{k}` → `{v}`")
    else:
        lines.append("• None")

    lines.append("")
    lines.append("🗑 Remove lines containing:")
    if rem:
        for r in rem:
            lines.append(f"• `{r}`")
    else:
        lines.append("• None")

    lines.append("")
    lines.append("🔍 Regex Filters:")
    if regex:
        for e in regex:
            lines.append(f"• `{e.get('pattern')}` → `{e.get('replace')}`")
    else:
        lines.append("• None")

    lines.append("")
    lines.append("⏩ Begin-with replace:")
    if begins:
        for k, v in begins.items():
            lines.append(f"• `{k}` → `{v}`")
    else:
        lines.append("• None")

    lines.append("")
    lines.append("⏪ End-with replace:")
    if ends:
        for k, v in ends.items():
            lines.append(f"• `{k}` → `{v}`")
    else:
        lines.append("• None")

    lines.append("")
    lines.append("Commands:")
    lines += [
        "/addsuperreplace old | new",
        "/addsupercase old | new",
        "/addsuperremove text",
        "/addsuperregex pattern | replace",
        "/addsuperbegin prefix | replace",
        "/addsuperend suffix | replace",
        "/clearsuperfilters",
        "/superfilteredit https://t.me/c/CHAT/ID-ID"
    ]

    await message.reply("\n".join(lines))


# ---------------------------
# Add handlers
# ---------------------------
@app.on_message(filters.command("addsuperreplace"))
async def add_super_replace(client, message):
    if "|" not in message.text:
        return await message.reply("❌ Usage: `/addsuperreplace old | new`")
    uid = message.from_user.id
    _, payload = message.text.split(" ", 1)
    old, new = [x.strip() for x in payload.split("|", 1)]
    data = await get_user_data_key(uid, "super_replace", {}) or {}
    data[old] = new
    await save_user_data(uid, "super_replace", data)
    await message.reply(f"✅ Replace added: `{old}` → `{new}`")


@app.on_message(filters.command("addsupercase"))
async def add_super_case(client, message):
    if "|" not in message.text:
        return await message.reply("❌ Usage: `/addsupercase old | new`")
    uid = message.from_user.id
    _, payload = message.text.split(" ", 1)
    old, new = [x.strip() for x in payload.split("|", 1)]
    data = await get_user_data_key(uid, "super_case", {}) or {}
    data[old] = new
    await save_user_data(uid, "super_case", data)
    await message.reply(f"✅ Case-insensitive replace added: `{old}` → `{new}`")


@app.on_message(filters.command("addsuperremove"))
async def add_super_remove(client, message):
    if len(message.command) < 2:
        return await message.reply("❌ Usage: `/addsuperremove text`")
    uid = message.from_user.id
    text = message.text.split(" ", 1)[1].strip()
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
    _, payload = message.text.split(" ", 1)
    pattern, rep = [x.strip() for x in payload.split("|", 1)]
    data = await get_user_data_key(uid, "super_regex", []) or []
    data.append({"pattern": pattern, "replace": rep})
    await save_user_data(uid, "super_regex", data)
    await message.reply(f"🔍 Regex rule added: `{pattern}` → `{rep}`")


@app.on_message(filters.command("addsuperbegin"))
async def add_super_begin(client, message):
    if "|" not in message.text:
        return await message.reply("❌ Usage: `/addsuperbegin prefix | replace`")
    uid = message.from_user.id
    _, payload = message.text.split(" ", 1)
    prefix, rep = [x.strip() for x in payload.split("|", 1)]
    data = await get_user_data_key(uid, "super_begin", {}) or {}
    data[prefix] = rep
    await save_user_data(uid, "super_begin", data)
    await message.reply(f"⏩ Begin-with rule added: `{prefix}` → `{rep}`")


@app.on_message(filters.command("addsuperend"))
async def add_super_end(client, message):
    if "|" not in message.text:
        return await message.reply("❌ Usage: `/addsuperend suffix | replace`")
    uid = message.from_user.id
    _, payload = message.text.split(" ", 1)
    suffix, rep = [x.strip() for x in payload.split("|", 1)]
    data = await get_user_data_key(uid, "super_end", {}) or {}
    data[suffix] = rep
    await save_user_data(uid, "super_end", data)
    await message.reply(f"⏪ End-with rule added: `{suffix}` → `{rep}`")


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


# ---------------------------
# /superfilteredit - edit a range using the per-user client (UC)
# ---------------------------
@app.on_message(filters.command("superfilteredit"))
async def superfilter_edit_range(client, message):
    if len(message.command) < 2:
        return await message.reply("❌ Usage: `/superfilteredit https://t.me/c/CHAT/ID-ID`")
    uid = message.from_user.id
    link = message.command[1].strip()

    pat = r"https?://t\\.me/c/(\\d+)/(\\d+)(?:-(\\d+))?"
    m = re.match(pat, link)
    if not m:
        return await message.reply("❌ Invalid link format. Use https://t.me/c/CHAT/START-END")

    chat_raw = m.group(1)
    msg_start = int(m.group(2))
    msg_end = int(m.group(3)) if m.group(3) else msg_start
    chat_id = int(f"-100{chat_raw}")

    await message.reply(f"🛠 Applying SUPERFILTER to messages `{msg_start}` → `{msg_end}`…")

    uc = await get_uclient(uid)
    if not uc:
        return await message.reply("❌ You are not logged in or no user session available.")

    edited = 0
    failed = 0
    for mid in range(msg_start, msg_end + 1):
        try:
            msg = await uc.get_messages(chat_id, mid)
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
                    await uc.edit_message(chat_id, mid, new_text)
                    edited += 1
                except Exception:
                    failed += 1
        except Exception:
            failed += 1

    await message.reply(f"✅ Done. Edited: `{edited}` ⚠️ Failed: `{failed}`")