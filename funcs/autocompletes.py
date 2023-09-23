
import discord 
from discord import app_commands
import client

async def player_autocomplete(interaction : discord.Interaction, current : str):

    c : client.Client = interaction.client.client
    return [app_commands.Choice(name=p.name, value=p.name) for p in c.world.search_player(current)]

async def town_autocomplete(interaction : discord.Interaction, current : str):

    c : client.Client = interaction.client.client

    return [app_commands.Choice(name=t.name_formatted, value=t.name) for t in c.world.search_town(current)]

async def nation_autocomplete(interaction : discord.Interaction, current : str):

    c : client.Client = interaction.client.client

    return [app_commands.Choice(name=n.name_formatted, value=n.name) for n in c.world.search_nation(current)]