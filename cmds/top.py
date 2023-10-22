
import discord 

import setup as s
from funcs import paginator, graphs, commands_view

from discord import app_commands
from discord.ext import commands

import db

import client

from matplotlib.pyplot import bar

import datetime

def generate_command(
            cog,
            c : client.Client, 
            attribute : str, 
            formatter = str, 
            parser = None, 
            is_town : bool = False, 
            is_player : bool = False, 
            is_nation=False, 
            is_culture=False,
            is_religion=False,
            attname : str = None, 
            y:str = None, 
            reverse=False, 
            y_formatter = None
):
    async def cmd_uni(interaction : discord.Interaction):

        if is_town:
            rs = await c.towns_table.get_records(attributes=["name", attribute], order=db.CreationOrder(attribute, db.types.OrderAscending))
        elif is_player:
            rs = await c.players_table.get_records(attributes=["name", attribute], order=db.CreationOrder(attribute, db.types.OrderAscending))
        elif is_nation: 
            rs = await c.objects_table.get_records(conditions=[db.CreationCondition("type", "nation")], attributes=["name", attribute], order=db.CreationOrder(attribute, db.types.OrderAscending))
        elif is_culture:
            rs = await c.objects_table.get_records(conditions=[db.CreationCondition("type", "culture")], attributes=["name", attribute], order=db.CreationOrder(attribute, db.types.OrderAscending))
        else: # is religion
            rs = await c.objects_table.get_records(conditions=[db.CreationCondition("type", "religion")], attributes=["name", attribute], order=db.CreationOrder(attribute, db.types.OrderAscending))

        o_type = "nation" if is_nation else "town" if is_town else "player" if is_player else "culture" if is_culture else "religion"
        attnameformat = attname.replace('_', ' ')

        log = ""
        values = {}
        for i, record in enumerate(reversed(rs) if reverse else rs):
            if is_town and record.attribute('name') in s.DEFAULT_TOWNS:
                continue
            r = c.world.get_religion(record.attribute("name"))
            if is_religion and r:
                continue_main = False
                for dt in s.DEFAULT_TOWNS:
                    if dt in [t.name for t in r.towns]:
                        continue_main = True
                if continue_main:
                    continue
            
            parsed = (parser(record.fields[1].value) if parser else record.fields[1].value) or 0
            val = formatter(parsed)

            log =  f"{len(rs)-i}. **{discord.utils.escape_markdown(record.attribute('name'))}**: {val}\n" + log

            values[str(record.attribute('name'))] = int(parsed)
        

        file = graphs.save_graph(dict(list(reversed(list(values.items())))[:s.top_graph_object_count]), f"Top {o_type}s by {attnameformat} ({len(rs)})", o_type.title(), y or "Value", bar, y_formatter=y_formatter)
        graph = discord.File(file, filename="graph.png")

        embed = discord.Embed(title=f"Top {o_type}s by {attnameformat} ({len(rs)})", color=s.embed)
        embed.set_image(url="attachment://graph.png")

        

        cmds = []
        for i, object_name in enumerate(reversed(values.keys())):
            if i >= 25: break 
            cmds.append(commands_view.Command(f"get {o_type}", f"{i+1}. {object_name}", (object_name,), emoji=None))
        

        if attribute == "duration":
            embed.set_footer(text=f" Tracking for {(await interaction.client.client.world.total_tracked).str_no_timestamp()}")

        view = paginator.PaginatorView(embed, log)
        view.add_item(commands_view.CommandSelect(cog, cmds, f"Get {o_type.title()} Info...", 2))
        
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
        cultures = app_commands.Group(name="cultures", description="List the top cultures by an attribute", parent=top)
        religions = app_commands.Group(name="religions", description="List the top religions by an attribute", parent=top)

        

        for attribute in s.top_commands["town"]:
            name = attribute.get("name") or attribute.get("attribute")
            command = app_commands.command(name=name, description=f"Top towns by {name}")(generate_command(self, self.client, attribute.get("attribute"), attribute.get("formatter") or str, attribute.get("parser"), is_town=True, attname=name, y=attribute.get("y"), reverse=attribute.get("reverse"), y_formatter=attribute.get("y_formatter")))
            towns.add_command(command)

        for attribute in s.top_commands["player"]:
            name = attribute.get("name") or attribute.get("attribute")
            command = app_commands.command(name=name, description=f"Top players by {name}")(generate_command(self, self.client, attribute.get("attribute"), attribute.get("formatter") or str, attribute.get("parser"), is_player=True, attname=name, y=attribute.get("y"), y_formatter=attribute.get("y_formatter")))
            players.add_command(command)
        
        for attribute in s.top_commands["nation"]:
            name = attribute.get("name") or attribute.get("attribute")
            command = app_commands.command(name=name, description=f"Top nations by {name}")(generate_command(self, self.client, attribute.get("attribute"), attribute.get("formatter") or str, attribute.get("parser"), is_nation=True, attname=name, y=attribute.get("y"), y_formatter=attribute.get("y_formatter")))
            nations.add_command(command)
        for attribute in s.top_commands["object"]:
            name = attribute.get("name") or attribute.get("attribute")
            command = app_commands.command(name=name, description=f"Top cultures by {name}")(generate_command(self, self.client, attribute.get("attribute"), attribute.get("formatter") or str, attribute.get("parser"), is_culture=True, attname=name, y=attribute.get("y"), y_formatter=attribute.get("y_formatter")))
            cultures.add_command(command)

            name = attribute.get("name") or attribute.get("attribute")
            name = "followers" if name == "residents" else name
            command = app_commands.command(name=name, description=f"Top religions by {name}")(generate_command(self, self.client, attribute.get("attribute"), attribute.get("formatter") or str, attribute.get("parser"), is_religion=True, attname=name, y=attribute.get("y"), y_formatter=attribute.get("y_formatter")))
            religions.add_command(command)

        self.bot.tree.add_command(top)


async def setup(bot : commands.Bot):
    await bot.add_cog(Top(bot, bot.client))
