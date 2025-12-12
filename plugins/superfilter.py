# patched superfilter.py
from shared_client import app
from pyrogram import filters
from utils.func import get_user_data_key, save_user_data
from plugins.batch import get_uclient
import re, asyncio

async def apply_rules(text, uid):
    if text is None:
        return text

    replaces = await get_user_data_key(uid, "super_replace", {}) or {}
    removes  = await get_user_data_key(uid, "super_remove", []) or []
    regexes  = await get_user_data_key(uid, "super_regex", []) or []
    cases    = await get_user_data_key(uid, "super_case", {}) or {}
    begins   = await get_user_data_key(uid, "super_begin", {}) or {}
    ends     = await get_user_data_key(uid, "super_end", {}) or {}

    output = str(text)

    for old, new in replaces.items():
        if old:
            output = output.replace(old, new)

    for old, new in cases.items():
        if old:
            try:
                output = re.sub(re.escape(old), new, output, flags=re.IGNORECASE)
            except:
                output = output.replace(old, new)

    for entry in regexes:
        try:
            pat = entry.get("pattern")
            rep = entry.get("replace", "")
            if pat:
                output = re.sub(pat, rep, output)
        except:
            pass

    if removes:
        lines = output.splitlines()
        lines = [l for l in lines if not any(rem in l for rem in removes)]
        output = "\n".join(lines)

    if begins:
        lines = output.splitlines()
        nl = []
        for l in lines:
            replaced = False
            for k,v in begins.items():
                if k and l.startswith(k):
                    nl.append(v + l[len(k):])
                    replaced = True
                    break
            if not replaced:
                nl.append(l)
        output = "\n".join(nl)

    if ends:
        lines = output.splitlines()
        nl = []
        for l in lines:
            replaced = False
            for k,v in ends.items():
                if k and l.endswith(k):
                    nl.append(l[:-len(k)] + v)
                    replaced = True
                    break
            if not replaced:
                nl.append(l)
        output = "\n".join(nl)

    return output


@app.on_message(filters.command("superfilter"))
async def superfilter_panel(client, message):
    await message.reply("Superfilter loaded and running.")

async def run_superfilter_plugin():
    print("Superfilter plugin loaded")
