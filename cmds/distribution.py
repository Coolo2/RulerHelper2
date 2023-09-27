
import discord 

import setup as s
from funcs import paginator, graphs, autocompletes

from discord import app_commands
from discord.ext import commands

import db

import client
from client.object import generate_time

from matplotlib.pyplot import pie

def generate_command(c : client.Client, attribute : str, formatter = str, parser = None, is_nation=False, attname : str = None):
    async def cmd_uni(interaction : discord.Interaction, nation : str ):

        o = c.world.get_nation(nation, True)
        if not o: raise client.errors.MildError("Nothing found!")
        rs = await c.towns_table.get_records(conditions=[db.CreationCondition("nation", o.name)], attributes=["name", attribute], order=db.CreationOrder(attribute, db.types.OrderAscending))

        attnameformat = attname.replace('_', ' ')

        log = ""
        values = {}
        for record in rs:
            parsed = parser(record.attribute(attribute)) if parser else record.attribute(attribute)
            val = formatter(parsed)

            log = f"**{record.attribute('name')}**: {val}\n" + log

            if int(parsed) > 0:
                values[str(record.attribute('name'))] = int(parsed)
        

        file = graphs.save_graph(dict(list(reversed(list(values.items())))[:s.top_graph_object_count]), f"{o.name_formatted}'s distribution of {attnameformat}", "", "", pie)
        graph = discord.File(file, filename="graph.png")

        embed = discord.Embed(title=f"{o.name_formatted}'s distribution of {attnameformat}", color=s.embed)
        embed.set_image(url="attachment://graph.png")

        if s.see_more_footer:
            embed.set_footer(text="View more with /distribution nation!" + (f" Tracking for {(await interaction.client.client.world.total_tracked).str_no_timestamp()}" if attribute =="duration" else ""))
        elif attribute == "duration":
            embed.set_footer(text=f" Tracking for {(await interaction.client.client.world.total_tracked).str_no_timestamp()}")

        view = paginator.PaginatorView(embed, log)
        
        return await interaction.response.send_message(embed=embed, view=view, file=graph)


    async def cmd(interaction : discord.Interaction, nation : str):
        await cmd_uni(interaction, nation)
    return cmd

class Distribution(commands.Cog):

    def __init__(self, bot : commands.Bot, client : client.Client):
        self.bot = bot
        self.client = client

        super().__init__()
    
        distribution = app_commands.Group(name="distribution", description="View the distribution of attributes within an object")
        nation = app_commands.Group(name="nation", description="Get nation attribute distributions", parent=distribution)


        allowed_attributes_nation = [
            {"attribute":"bank", "formatter":lambda x: f"${x:,.2f}", "name":"town_bank", "parser":None},
            {"attribute":"resident_count", "formatter":None, "name":"residents", "parser":None},
            {"attribute":"area", "formatter":lambda x: f"{x:,} plots", "name":"area", "parser":None},
            {"attribute":"duration", "formatter":lambda x: generate_time(x*60), "name":"activity", "parser":lambda x: x/60}
        ]
        
        for attribute in allowed_attributes_nation:
            name = attribute.get("name") or attribute.get("attribute")
            command = app_commands.command(name=name, description=f"History for nation {name}")(generate_command(self.client, attribute.get("attribute"), attribute.get("formatter") or str, attribute.get("parser"), is_nation=True, attname=name))
            command.autocomplete("nation")(autocompletes.nation_autocomplete)
            nation.add_command(command)

        self.bot.tree.add_command(distribution)


async def setup(bot : commands.Bot):
    await bot.add_cog(Distribution(bot, bot.client))
