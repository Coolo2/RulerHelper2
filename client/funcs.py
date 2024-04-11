
from __future__ import annotations
import typing
if typing.TYPE_CHECKING:
    import client as client_pre

import datetime
import discord


def _total(arr : list, attr : str):
    t = 0
    for o in arr:
        t += getattr(o, attr) or 0
    return t

def generate_time(time):
    timeSeconds = time
    day = timeSeconds // (24 * 3600)
    timeSeconds = timeSeconds % (24 * 3600)
    hour = timeSeconds // 3600
    timeSeconds %= 3600
    minutes = timeSeconds // 60
    timeSeconds %= 60
    seconds = timeSeconds

    day = f" {round(day)}d" if day != 0 else ""
    hour = f" {round(hour)}h" if hour != 0 else ""
    minutes = f" {round(minutes)}m" if minutes != 0 else ""

    if day == "" and hour == "" and minutes == "":
        return f"{round(seconds)}s"
    
    return f"{day}{hour}{minutes}".lstrip()

def top_rankings_to_text(rankings : dict, object_name : str, notable_only = True) -> str:
    
    notable_statistics = f""
    for (leaderboard), (value, ranking, notable) in rankings.items():
        if notable: notable_statistics += f"\n - **#{ranking}** on the **{leaderboard.replace('_', ' ')}** ranking"
    
    if not notable_only or notable_statistics == "": 
        notable_statistics = "None"
    else:
        notable_statistics = f"\n- {discord.utils.escape_markdown(object_name)} is:" + notable_statistics

    return notable_statistics

def validate_datetime(date_text, format):
    try:
        if date_text != datetime.datetime.strptime(date_text, format).strftime(format):
            raise ValueError
        return True
    except ValueError:
        return False

async def set_flag(client : client_pre.Client, object_type : str, object_name : str, flag_name : str, flag_value):
    import setup as s
    # Updates a flag in the database for this object
    
    if s.flags["player"][flag_name].get("unique"):
        await client.execute("DELETE FROM flags WHERE object_type=? AND name=? AND value=?", (object_type, flag_name, flag_value))
    
    await client.execute("REPLACE INTO flags VALUES (?, ?, ?, ?)", (object_type, object_name, flag_name, flag_value))