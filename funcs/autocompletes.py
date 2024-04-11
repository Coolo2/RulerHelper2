
import discord 
from discord import app_commands
import client
import datetime

import setup as s

async def player_autocomplete(interaction : discord.Interaction, current : str):
    c : client.Client = interaction.client.client
    return [app_commands.Choice(name=p.name, value=p.name) for p in c.world.search_player(current)]

async def town_autocomplete(interaction : discord.Interaction, current : str):
    c : client.Client = interaction.client.client
    return [app_commands.Choice(name=t.name_formatted, value=t.name) for t in c.world.search_town(current)]

async def nation_autocomplete(interaction : discord.Interaction, current : str):
    c : client.Client = interaction.client.client
    return [app_commands.Choice(name=n.name_formatted, value=n.name) for n in c.world.search_nation(current)]

async def culture_autocomplete(interaction : discord.Interaction, current : str):
    c : client.Client = interaction.client.client
    return [app_commands.Choice(name=n.name_formatted, value=n.name) for n in c.world.search_culture(current)]

async def religion_autocomplete(interaction : discord.Interaction, current : str):
    c : client.Client = interaction.client.client
    return [app_commands.Choice(name=n.name_formatted[:100], value=n.name[:100]) for n in c.world.search_religion(current)]

async def players_today_autocomplete(interaction : discord.Interaction, current : str):
    c : client.Client = interaction.client.client
    rs = await (await c.execute("SELECT player FROM player_day_history WHERE player LIKE ? GROUP BY player", (f"%{current}%",))).fetchall()
    return [app_commands.Choice(name=r[0], value=r[0]) for r in rs][:25]

async def offline_players_autocomplete(interaction : discord.Interaction, current : str):
    c : client.Client = interaction.client.client
    return [app_commands.Choice(name=r.name, value=r.name) for r in c.world.get_object(c.world.offline_players, current, True, True, 25)]

async def deleted_towns_autocomplete(interaction : discord.Interaction, current : str):
    c : client.Client = interaction.client.client
    rs = await (await c.execute("SELECT town FROM town_history WHERE town LIKE ? GROUP BY town", (f"%{current}%",))).fetchall()
    rs = list(set(r[0] for r in rs) - set(n.name for n in c.world.towns))
    return [app_commands.Choice(name=r, value=r) for r in rs][:25]

async def deleted_nations_autocomplete(interaction : discord.Interaction, current : str):
    c : client.Client = interaction.client.client
    rs = await (await c.execute("SELECT nation FROM nation_history WHERE nation LIKE ? GROUP BY nation", (f"%{current}%",))).fetchall()
    rs = list(set(r[0] for r in rs) - set(n.name for n in c.world.nations))
    return [app_commands.Choice(name=r, value=r) for r in rs][:25]

def history_date_autocomplete_wrapper(object_type : str):
    async def history_date_autocomplete(interaction : discord.Interaction, current : str):
        c : client.Client = interaction.client.client
        rs = await (await c.execute(f"SELECT date FROM {object_type}_history GROUP BY date ORDER BY date ASC")).fetchall()
        dates_formatted = [datetime.datetime.strftime(r[0], s.DATE_STRFTIME) for r in rs ]
        return [
            app_commands.Choice(name=d, value=d)
            for d in dates_formatted if current.lower() in d.lower()
        ][:25]
    
    return history_date_autocomplete


