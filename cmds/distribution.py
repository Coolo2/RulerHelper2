
import discord 

import setup as s
from funcs import paginator, graphs, autocompletes

from discord import app_commands
from discord.ext import commands

import db

import client
from client.object import generate_time

from matplotlib.pyplot import pie

def generate_command(c : client.Client, attribute : str, formatter = str, parser = None, is_nation=False, is_culture=False, is_religion=False,attname : str = None):
    async def cmd_uni(interaction : discord.Interaction, nation : str=None, culture : str=None, religion : str=None):

        if nation:
            o = c.world.get_nation(nation, True)
            if not o: raise client.errors.MildError("Nothing found!")
            rs = await c.towns_table.get_records(conditions=[db.CreationCondition("nation", o.name)], attributes=["name", attribute], order=db.CreationOrder(attribute, db.types.OrderAscending))
        elif culture:
            o = c.world.get_culture(culture, True)
            if not o: raise client.errors.MildError("Nothing found!")
            rs = await c.towns_table.get_records(conditions=[db.CreationCondition("culture", o.name)], attributes=["name", attribute], order=db.CreationOrder(attribute, db.types.OrderAscending))
        else: # is religion
            o = c.world.get_religion(religion, True)
            if not o: raise client.errors.MildError("Nothing found!")
            rs = await c.towns_table.get_records(conditions=[db.CreationCondition("religion", o.name)], attributes=["name", attribute], order=db.CreationOrder(attribute, db.types.OrderAscending))

        

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


    if is_nation:
        async def cmd(interaction : discord.Interaction, nation : str):
            await cmd_uni(interaction, nation)
    elif is_culture:
        async def cmd(interaction : discord.Interaction, culture : str):
            await cmd_uni(interaction, culture=culture)
    elif is_religion:
        async def cmd(interaction : discord.Interaction, religion : str):
            await cmd_uni(interaction, religion=religion)
    return cmd

class Distribution(commands.Cog):

    def __init__(self, bot : commands.Bot, client : client.Client):
        self.bot = bot
        self.client = client

        super().__init__()
    
        distribution = app_commands.Group(name="distribution", description="View the distribution of attributes within an object")
        nation = app_commands.Group(name="nation", description="Get nation attribute distributions", parent=distribution)
        culture = app_commands.Group(name="culture", description="Get culture attribute distributions", parent=distribution)
        religion = app_commands.Group(name="religion", description="Get religion attribute distributions", parent=distribution)

        allowed_attributes = [
            {"attribute":"bank", "formatter":lambda x: f"${x:,.2f}", "name":"town_bank", "parser":None},
            {"attribute":"resident_count", "formatter":None, "name":"residents", "parser":None},
            {"attribute":"area", "formatter":lambda x: f"{x:,} plots", "name":"area", "parser":None},
            {"attribute":"duration", "formatter":lambda x: generate_time(x*60), "name":"activity", "parser":lambda x: x/60}
        ]
        
        for attribute in allowed_attributes:
            name = attribute.get("name") or attribute.get("attribute")
            command = app_commands.command(name=name, description=f"History for nation {name}")(generate_command(self.client, attribute.get("attribute"), attribute.get("formatter") or str, attribute.get("parser"), is_nation=True, attname=name))
            command.autocomplete("nation")(autocompletes.nation_autocomplete)
            nation.add_command(command)

            name = attribute.get("name") or attribute.get("attribute")
            command = app_commands.command(name=name, description=f"History for culture {name}")(generate_command(self.client, attribute.get("attribute"), attribute.get("formatter") or str, attribute.get("parser"), is_culture=True, attname=name))
            command.autocomplete("culture")(autocompletes.culture_autocomplete)
            culture.add_command(command)

            name = attribute.get("name") or attribute.get("attribute")
            name = "followers" if name == "residents" else name
            command = app_commands.command(name=name, description=f"History for religion {name}")(generate_command(self.client, attribute.get("attribute"), attribute.get("formatter") or str, attribute.get("parser"), is_religion=True, attname=name))
            command.autocomplete("religion")(autocompletes.religion_autocomplete)
            religion.add_command(command)

        self.bot.tree.add_command(distribution)


async def setup(bot : commands.Bot):
    await bot.add_cog(Distribution(bot, bot.client))
