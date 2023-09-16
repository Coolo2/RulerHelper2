
import discord 
import json
import io

import setup as s
from funcs import autocompletes, commands_view, paginator, graphs

from discord import app_commands
from discord.ext import commands

import db

import client
from client.object import generate_time

from matplotlib.pyplot import plot

def generate_command(c : client.Client, attribute : str, qualitative=False, formatter = str, parser = None, is_town : bool = False, is_player : bool = False, attname : str = None):
    async def cmd_uni(interaction : discord.Interaction, town : str = None, player : str = None):

        
        if town:
            o = c.world.get_town(town, True)
            if not o: raise client.errors.MildError("Nothing found!")
            rs = await c.town_history_table.get_records([db.CreationCondition("town", o.name)], ["date", attribute], order=db.CreationOrder("date", db.types.OrderAscending))
        if player:
            o = c.world.get_player(player, True)
            if not o: raise client.errors.MildError("Nothing found!")
            rs = await c.player_history_table.get_records([db.CreationCondition("player", o.name)], ["date", attribute], order=db.CreationOrder("date", db.types.OrderAscending))

        log = ""
        last = None
        values = {}
        for record in rs:
            parsed = parser(record.attribute(attribute)) if parser else record.attribute(attribute)
            val = formatter(parsed)
            if qualitative and last == val:
                continue
            log = f"**{record.attribute('date')}**: {val}\n" + log
            last = val

            values[str(record.attribute('date'))] = str(parsed)

        if not qualitative:
            file = graphs.save_graph(values, f"{o.name_formatted} {attname} history", "Date", "Value", plot)
        else:
            file = graphs.save_timeline(values, f"{o.name_formatted} {attname} history")
        graph = discord.File(file, filename="graph.png")

        embed = discord.Embed(title=f"{o.name_formatted}'s {attname} history", color=s.embed)
        embed.set_image(url="attachment://graph.png")

        view = paginator.PaginatorView(embed, log)
        
        return await interaction.response.send_message(embed=embed, view=view, file=graph)

    if is_town:
        async def cmd(interaction : discord.Interaction, town : str):
            await cmd_uni(interaction, town=town)
    if is_player:
        async def cmd(interaction : discord.Interaction, player : str):
            await cmd_uni(interaction, player=player)
    return cmd



class History(commands.Cog):

    def __init__(self, bot : commands.Bot, client : client.Client):
        self.bot = bot
        self.client = client

        super().__init__()
    
        history = app_commands.Group(name="history", description="History commands")
        town = app_commands.Group(name="town", description="Get history for a town's attributes", parent=history)
        player = app_commands.Group(name="player", description="Get history for a player's attributes", parent=history)

        allowed_attributes = [
            {"attribute":"nation", "qualitative":True, "formatter":None, "name":None, "parser":None},
            {"attribute":"religion", "qualitative":True, "formatter":None, "name":None, "parser":None},
            {"attribute":"culture", "qualitative":True, "formatter":None, "name":None, "parser":None},
            {"attribute":"mayor", "qualitative":True, "formatter":None, "name":None, "parser":None},
            {"attribute":"resident_count", "qualitative":False, "formatter":None, "name":None, "parser":None},
            {"attribute":"resident_tax", "qualitative":False, "formatter":lambda x: f"{x:,.1f}%", "name":"tax", "parser":None},
            {"attribute":"bank", "qualitative":False, "formatter":lambda x: f"${x:,.2f}", "name":None, "parser":None},
            {"attribute":"public", "qualitative":True, "formatter":None, "name":None, "parser":bool},
            {"attribute":"peaceful", "qualitative":True, "formatter":None, "name":None, "parser":bool},
            {"attribute":"area", "qualitative":False, "formatter":lambda x: f"{x:,} plots", "name":None, "parser":None},
            {"attribute":"duration", "qualitative":False, "formatter":generate_time, "name":"activity", "parser":None}
        ]
        allowed_attributes_player = [
            {"attribute":"duration", "qualitative":False, "formatter":generate_time, "name":"activity", "parser":None}
        ]

        for attribute in allowed_attributes:
            name = attribute.get("name") or attribute.get("attribute")
            command = app_commands.command(name=name, description=f"History for town {name}")(generate_command(self.client, attribute.get("attribute"), attribute.get("qualitative"), attribute.get("formatter") or str, attribute.get("parser"), True, attname=name))
            command.autocomplete("town")(autocompletes.town_autocomplete)
            town.add_command(command)

        for attribute in allowed_attributes_player:
            name = attribute.get("name") or attribute.get("attribute")
            command = app_commands.command(name=name, description=f"History for player {name}")(generate_command(self.client, attribute.get("attribute"), attribute.get("qualitative"), attribute.get("formatter") or str, attribute.get("parser"), is_player=True, attname=name))
            command.autocomplete("player")(autocompletes.player_autocomplete)
            player.add_command(command)

        self.bot.tree.add_command(history)

    

    

async def setup(bot : commands.Bot):
    await bot.add_cog(History(bot, bot.client))



