
import discord 

import setup as s
from funcs import paginator, graphs

from discord import app_commands
from discord.ext import commands

import db

import client
from client.object import generate_time

from matplotlib.pyplot import bar

import datetime

def generate_command(c : client.Client, attribute : str, formatter = str, parser = None, is_town : bool = False, is_player : bool = False, is_nation=False, attname : str = None, y:str = None, reverse=False):
    async def cmd_uni(interaction : discord.Interaction):

        
        if is_town:
            rs = await c.towns_table.get_records(attributes=["name", attribute], order=db.CreationOrder(attribute, db.types.OrderAscending))
        elif is_player:
            rs = await c.players_table.get_records(attributes=["name", attribute], order=db.CreationOrder(attribute, db.types.OrderAscending))
        else: # is_nation
            rs = await c.objects_table.get_records(conditions=[db.CreationCondition("type", "nation")], attributes=["name", attribute], order=db.CreationOrder(attribute, db.types.OrderAscending))

        o_type = "nation" if is_nation else "town" if is_town else "player"
        attnameformat = attname.replace('_', ' ')

        log = ""
        values = {}
        for i, record in enumerate(reversed(rs) if reverse else rs):
            if is_town and record.attribute('name') in s.DEFAULT_TOWNS:
                continue
            
            parsed = parser(record.attribute(attribute)) if parser else record.attribute(attribute)
            val = formatter(parsed)

            log =  f"{len(rs)-i}. **{record.attribute('name')}**: {val}\n" + log

            values[str(record.attribute('name'))] = int(parsed)
        

        file = graphs.save_graph(dict(list(reversed(list(values.items())))[:s.top_graph_object_count]), f"Top {o_type}s by {attnameformat}", o_type.title(), y or "Value", bar)
        graph = discord.File(file, filename="graph.png")

        embed = discord.Embed(title=f"Top {o_type}s by {attnameformat}", color=s.embed)
        embed.set_image(url="attachment://graph.png")

        if attribute == "duration":
            embed.set_footer(text=f" Tracking for {(await interaction.client.client.world.total_tracked).str_no_timestamp()}")

        view = paginator.PaginatorView(embed, log)
        
        return await interaction.response.send_message(embed=embed, view=view, file=graph)


    async def cmd(interaction : discord.Interaction):
        await cmd_uni(interaction)
    return cmd

class Top(commands.Cog):

    def __init__(self, bot : commands.Bot, client : client.Client):
        self.bot = bot
        self.client = client

        super().__init__()
    
        top = app_commands.Group(name="top", description="Rank objects")
        towns = app_commands.Group(name="towns", description="List the top towns by an attribute", parent=top)
        players = app_commands.Group(name="players", description="List the top nations by an attribute", parent=top)
        nations = app_commands.Group(name="nations", description="List the top nations by an attribute", parent=top)

        allowed_attributes = [
            {"attribute":"resident_count", "formatter":None, "name":"residents", "parser":None},
            {"attribute":"resident_tax", "formatter":lambda x: f"{x:,.1f}%", "name":"tax", "parser":None, "y":"Tax (%)"},
            {"attribute":"bank", "formatter":lambda x: f"${x:,.2f}", "name":None, "parser":None, "y":"Bank ($)"},
            {"attribute":"area", "formatter":lambda x: f"{x:,} plots", "name":None, "parser":None, "y":"Area (plots)"},
            {"attribute":"duration", "formatter":lambda x: generate_time(x*60), "name":"activity", "parser":lambda x: x/60, "y":"Time (minutes)"},
            {"attribute":"founded_date", "formatter":lambda x: f"{x:,} days ({datetime.date.today()-datetime.timedelta(days=x)})", "name":"age", "parser":lambda x: (datetime.date.today() - x).days, "y":"Age (days)", "reverse":True}
        ]
        allowed_attributes_player = [
            {"attribute":"duration", "formatter":lambda x: generate_time(x*60), "name":"activity", "parser":lambda x: x/60, "y":"Time (minutes)"}
        ]
        allowed_attributes_nation = [
            {"attribute":"towns", "formatter":None, "name":"towns", "parser":None},
            {"attribute":"town_balance", "formatter":lambda x: f"${x:,.2f}", "name":"town_value", "parser":None, "y":"Bank ($)"},
            {"attribute":"residents", "formatter":None, "name":"residents", "parser":None},
            {"attribute":"area", "formatter":lambda x: f"{x:,} plots", "name":"area", "parser":None, "y":"Area (plots)"}
        ]

        for attribute in allowed_attributes:
            name = attribute.get("name") or attribute.get("attribute")
            command = app_commands.command(name=name, description=f"History for town {name}")(generate_command(self.client, attribute.get("attribute"), attribute.get("formatter") or str, attribute.get("parser"), is_town=True, attname=name, y=attribute.get("y"), reverse=attribute.get("reverse")))
            towns.add_command(command)

        for attribute in allowed_attributes_player:
            name = attribute.get("name") or attribute.get("attribute")
            command = app_commands.command(name=name, description=f"History for player {name}")(generate_command(self.client, attribute.get("attribute"), attribute.get("formatter") or str, attribute.get("parser"), is_player=True, attname=name, y=attribute.get("y")))
            players.add_command(command)
        
        for attribute in allowed_attributes_nation:
            name = attribute.get("name") or attribute.get("attribute")
            command = app_commands.command(name=name, description=f"History for nation {name}")(generate_command(self.client, attribute.get("attribute"), attribute.get("formatter") or str, attribute.get("parser"), is_nation=True, attname=name, y=attribute.get("y")))
            nations.add_command(command)

        self.bot.tree.add_command(top)


async def setup(bot : commands.Bot):
    await bot.add_cog(Top(bot, bot.client))
