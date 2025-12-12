# plugins/superfilter.py
# Apply per-user superfilters and allow editing posted messages.
# Uses app (bot) to edit bot-posted messages and userbot to edit user-posted (/batch etc).
# Single-task enforced; no start/stop of userbot here (shared_client manages lifecycle).

import re
import asyncio
from shared_client import app, userbot
from pyrogram import filters
from pyrogram.types import Message
from utils.func import get_user_data_key, save_user_data

TASK_LOCK = asyncio.Lock()


async def apply_rules(text: str, uid: int):
    if text is None:
        return text

    replaces = await get_user_data_key(uid, "super_replace", {}) or {}
    removes  = await get_user_data_key(uid, "super_remove", []) or []
    regexes  = await get_user_data_key(uid, "super_regex", []) or []
    cases    = await get_user_data_key(uid, "super_case", {}) or {}
    begins   = await get_user_data_key(uid, "super_begin", {}) or {}
    ends     = await get_user_data_key(uid, "super_end", {}) or {}

    out = str(text)

    # literal replace
    for old, new in replaces.items():
        if old:
            out = out.replace(old, new)

    # case-insensitive
    for old, new in cases.items():
        if old:
            try:
                out = re.sub(re.escape(old), new, out, flags=re.IGNORECASE)
            except Exception:
                out = out.replace(old, new)

    # regex entries
    for entry in regexes:
        try:
            pat = entry.get("pattern")
            rep = entry.get("replace", "")
            if pat:
                out = re.sub(pat, rep, out)
        except Exception:
            pass

    # remove lines containing tokens
    if removes:
        lines = out.splitlines()
        lines = [l for l in lines if not any(rem in l for rem in removes)]
        out = "\n".join(lines)

    # begin replacements
    if begins:
        lines = out.splitlines()
        newl = []
        for l in lines:
            replaced = False
            for k, v in begins.items():
                if k and l.startswith(k):
                    newl.append(v + l[len(k):])
                    replaced = True
                    break
            if not replaced:
                newl.append(l)
        out = "\n".join(newl)

    # end replacements
    if ends:
        lines = out.splitlines()
        newl = []
        for l in lines:
            replaced = False
            for k, v in ends.items():
                if k and l.endswith(k):
                    newl.append(l[:-len(k)] + v)
                    replaced = True
                    break
            if not replaced:
                newl.append(l)
        out = "\n".join(newl)

    return out


def _parse_edit_link(link: str):
    """
    Accept /c/<id>/<start>-<end>, /c/<id>/<start>/<end>, /username/<start>-<end>, /username/<start>/<end>
    Returns (chat_identifier, start, end) or None
    """
    link = link.strip()
    m = re.match(r"https?://t\.me/c/(\d+)/(\d+)(?:-(\d+)|/(\d+))?", link)
    if m:
        raw = m.group(1)
        s = int(m.group(2))
        e = m.group(3) or m.group(4)
        if e:
            e = int(e)
        else:
            e = s
        chat_id = int(f"-100{raw}")
        return chat_id, s, e

    m2 = re.match(r"https?://t\.me/([^/]+)/(\d+)(?:-(\d+)|/(\d+))?", link)
    if m2:
        uname = m2.group(1)
        s = int(m2.group(2))
        e = m2.group(3) or m2.group(4)
        if e:
            e = int(e)
        else:
            e = s
        return uname, s, e

    return None


@app.on_message(filters.command("superfilter"))
async def superfilter_panel(client: app.__class__, message: Message):
    uid = message.from_user.id
    repl  = await get_user_data_key(uid, "super_replace", {}) or {}
    rem   = await get_user_data_key(uid, "super_remove", []) or []
    regex = await get_user_data_key(uid, "super_regex", []) or []
    cases = await get_user_data_key(uid, "super_case", {}) or {}
    begins= await get_user_data_key(uid, "super_begin", {}) or {}
    ends  = await get_user_data_key(uid, "super_end", {}) or {}

    lines = ["🛠️ SUPER FILTER PANEL (per-user)", ""]
    lines.append("🔄 Replace (literal):")
    if repl:
        for k, v in repl.items():
            lines.append(f"• `{k}` → `{v}`")
    else:
        lines.append("• None")

    lines += ["", "🔤 Case-insensitive replace:"]
    if cases:
        for k, v in cases.items():
            lines.append(f"• `{k}` → `{v}`")
    else:
        lines.append("• None")

    lines += ["", "🗑 Remove lines containing:"]
    if rem:
        for r in rem:
            lines.append(f"• `{r}`")
    else:
        lines.append("• None")

    lines += ["", "🔍 Regex rules:"]
    if regex:
        for e in regex:
            lines.append(f"• `{e.get('pattern')}` → `{e.get('replace')}`")
    else:
        lines.append("• None")

    lines += ["", "⏩ Begin-with replace:"]
    if begins:
        for k, v in begins.items():
            lines.append(f"• `{k}` → `{v}`")
    else:
        lines.append("• None")

    lines += ["", "⏪ End-with replace:"]
    if ends:
        for k, v in ends.items():
            lines.append(f"• `{k}` → `{v}`")
    else:
        lines.append("• None")

    lines += ["", "Commands:",
              "/addsuperreplace old | new",
              "/addsupercase old | new",
              "/addsuperremove text",
              "/addsuperregex pattern | replace",
              "/addsuperbegin prefix | replace",
              "/addsuperend suffix | replace",
              "/clearsuperfilters",
              "/superfilteredit https://t.me/c/CHAT/START-END"]
    await message.reply("\n".join(lines), quote=True)


# add handlers (same as before)
@app.on_message(filters.command("addsuperreplace"))
async def add_super_replace(client, message: Message):
    if "|" not in message.text:
        return await message.reply("❌ Usage: `/addsuperreplace old | new`", quote=True)
    uid = message.from_user.id
    _, payload = message.text.split(" ", 1)
    old, new = [x.strip() for x in payload.split("|", 1)]
    data = await get_user_data_key(uid, "super_replace", {}) or {}
    data[old] = new
    await save_user_data(uid, "super_replace", data)
    await message.reply(f"✅ Replace added: `{old}` → `{new}`", quote=True)


@app.on_message(filters.command("addsupercase"))
async def add_super_case(client, message: Message):
    if "|" not in message.text:
        return await message.reply("❌ Usage: `/addsupercase old | new`", quote=True)
    uid = message.from_user.id
    _, payload = message.text.split(" ", 1)
    old, new = [x.strip() for x in payload.split("|", 1)]
    data = await get_user_data_key(uid, "super_case", {}) or {}
    data[old] = new
    await save_user_data(uid, "super_case", data)
    await message.reply(f"✅ Case-insensitive replace added: `{old}` → `{new}`", quote=True)


@app.on_message(filters.command("addsuperremove"))
async def add_super_remove(client, message: Message):
    if len(message.command) < 2:
        return await message.reply("❌ Usage: `/addsuperremove text`", quote=True)
    uid = message.from_user.id
    text = message.text.split(" ", 1)[1].strip()
    data = await get_user_data_key(uid, "super_remove", []) or []
    if text not in data:
        data.append(text)
    await save_user_data(uid, "super_remove", data)
    await message.reply(f"🗑 Rule added: `{text}`", quote=True)


@app.on_message(filters.command("addsuperregex"))
async def add_super_regex(client, message: Message):
    if "|" not in message.text:
        return await message.reply("❌ Usage: `/addsuperregex pattern | replace`", quote=True)
    uid = message.from_user.id
    _, payload = message.text.split(" ", 1)
    pattern, rep = [x.strip() for x in payload.split("|", 1)]
    data = await get_user_data_key(uid, "super_regex", []) or []
    data.append({"pattern": pattern, "replace": rep})
    await save_user_data(uid, "super_regex", data)
    await message.reply(f"🔍 Regex rule added: `{pattern}` → `{rep}`", quote=True)


@app.on_message(filters.command("addsuperbegin"))
async def add_super_begin(client, message: Message):
    if "|" not in message.text:
        return await message.reply("❌ Usage: `/addsuperbegin prefix | replace`", quote=True)
    uid = message.from_user.id
    _, payload = message.text.split(" ", 1)
    prefix, rep = [x.strip() for x in payload.split("|", 1)]
    data = await get_user_data_key(uid, "super_begin", {}) or {}
    data[prefix] = rep
    await save_user_data(uid, "super_begin", data)
    await message.reply(f"⏩ Begin-with rule added: `{prefix}` → `{rep}`", quote=True)


@app.on_message(filters.command("addsuperend"))
async def add_super_end(client, message: Message):
    if "|" not in message.text:
        return await message.reply("❌ Usage: `/addsuperend suffix | replace`", quote=True)
    uid = message.from_user.id
    _, payload = message.text.split(" ", 1)
    suffix, rep = [x.strip() for x in payload.split("|", 1)]
    data = await get_user_data_key(uid, "super_end", {}) or {}
    data[suffix] = rep
    await save_user_data(uid, "super_end", data)
    await message.reply(f"⏪ End-with rule added: `{suffix}` → `{rep}`", quote=True)


@app.on_message(filters.command("clearsuperfilters"))
async def clear_super_filters(client, message: Message):
    uid = message.from_user.id
    await save_user_data(uid, "super_replace", {})
    await save_user_data(uid, "super_remove", [])
    await save_user_data(uid, "super_regex", [])
    await save_user_data(uid, "super_case", {})
    await save_user_data(uid, "super_begin", {})
    await save_user_data(uid, "super_end", {})
    await message.reply("♻️ All superfilters cleared!", quote=True)


# -------------------------
# /superfilteredit - edit a range using the user session for user-posted messages
# Single-task enforced: rejects if another task is running (Option C)
# -------------------------
@app.on_message(filters.command("superfilteredit"))
async def superfilter_edit_range(client: app.__class__, message: Message):
    if TASK_LOCK.locked():
        return await message.reply("⚠️ Another task is already running. Try again later.", quote=True)

    if len(message.command) < 2:
        return await message.reply("❌ Usage: `/superfilteredit https://t.me/c/CHAT/START-END`", quote=True)
    uid = message.from_user.id
    link = message.command[1].strip()

    parsed = _parse_edit_link(link)
    if not parsed:
        return await message.reply("❌ Invalid link format. Use https://t.me/c/CHAT/START-END", quote=True)

    chat_id, msg_start, msg_end = parsed

    await TASK_LOCK.acquire()
    try:
        await message.reply(f"🛠 Applying SUPERFILTER to messages `{msg_start}` → `{msg_end}`…", quote=True)

        edited = 0
        failed = 0

        # fetch my own user id (userbot) to compare
        my_id = None
        try:
            me = await userbot.get_me()
            my_id = me.id
        except Exception:
            my_id = None

        for mid in range(msg_start, msg_end + 1):
            try:
                # try to fetch via userbot first (user-posted messages)
                msg = None
                try:
                    msg = await userbot.get_messages(chat_id, mid)
                except Exception:
                    msg = None

                # fallback to bot for bot-posted messages
                if not msg:
                    try:
                        msg = await app.get_messages(chat_id, mid)
                    except Exception:
                        msg = None

                if not msg:
                    failed += 1
                    continue

                original = msg.text or msg.caption or ""
                if not original:
                    continue

                new_text = await apply_rules(original, uid)
                if new_text == original:
                    continue

                edited_ok = False
                try:
                    # if user account is the author -> edit with userbot
                    if my_id and getattr(msg, "from_user", None) and getattr(msg.from_user, "id", None) == my_id:
                        await userbot.edit_message(chat_id, mid, new_text)
                        edited_ok = True
                    else:
                        # if authored by bot -> edit with app
                        if getattr(msg, "from_user", None) and getattr(msg.from_user, "is_bot", False):
                            await app.edit_message(chat_id, mid, new_text)
                            edited_ok = True
                        else:
                            # otherwise try userbot edit (covers /batch and other user posts)
                            try:
                                await userbot.edit_message(chat_id, mid, new_text)
                                edited_ok = True
                            except Exception:
                                edited_ok = False
                except Exception:
                    edited_ok = False

                if edited_ok:
                    edited += 1
                    await asyncio.sleep(0.45)
                else:
                    failed += 1

            except Exception:
                failed += 1

        await message.reply(f"✅ Done. Edited: `{edited}` ⚠️ Failed: `{failed}`", quote=True)
    finally:
        if TASK_LOCK.locked():
            TASK_LOCK.release()


# plugin loader
async def run_superfilter_plugin():
    print("Superfilter plugin loaded")