
import discord 
from discord import app_commands
import client
import db

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

#

async def offline_players_autocomplete(interaction : discord.Interaction, current : str):

    c : client.Client = interaction.client.client

    return [app_commands.Choice(name=r.name, value=r.name) for r in c.world.get_object(c.world.offline_players, current, True, True, 25)]

async def deleted_towns_autocomplete(interaction : discord.Interaction, current : str):

    c : client.Client = interaction.client.client

    rs = [r.attribute("town") for r in await c.town_history_table.get_records([db.CreationCondition("town", f"%{current}%", "LIKE")], attributes=[c.town_history_table.attribute("town")], group=[c.town_history_table.attribute("town")])]
    rs = list(set(rs) - set(n.name for n in c.world.towns))

    return [app_commands.Choice(name=r, value=r) for r in rs][:25]

async def deleted_nations_autocomplete(interaction : discord.Interaction, current : str):

    c : client.Client = interaction.client.client

    rs = [r.attribute("nation") for r in await c.nation_history_table.get_records([db.CreationCondition("nation", f"%{current}%", "LIKE")], attributes=[c.nation_history_table.attribute("nation")], group=[c.nation_history_table.attribute("nation")])]
    rs = list(set(rs) - set(n.name for n in c.world.nations))

    return [app_commands.Choice(name=r, value=r) for r in rs][:25]