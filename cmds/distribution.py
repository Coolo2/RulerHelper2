
import discord 

import setup as s
from funcs import paginator, autocompletes, commands_view

from discord import app_commands
from discord.ext import commands

import db

import client

def generate_command(c : client.Client, attribute : str, formatter = str, parser = None, is_nation=False, is_culture=False, is_religion=False,attname : str = None):
    async def cmd_uni(interaction : discord.Interaction, nation : str=None, culture : str=None, religion : str=None):

        edit = interaction.extras.get("edit")

        if nation:
            o = c.world.get_nation(nation, True)
            typeatt = "nation"
            if not o: raise client.errors.MildError("Nothing found!")
        elif culture:
            o = c.world.get_culture(culture, True)
            if not o: raise client.errors.MildError("Nothing found!")
            typeatt = "culture"
        else: # is religion
            o = c.world.get_religion(religion, True)
            typeatt = "religion"
            if not o: raise client.errors.MildError("Nothing found!")

        rs = await c.towns_table.get_records(conditions=[db.CreationCondition(typeatt, o.name)], attributes=["name", attribute], order=db.CreationOrder(attribute, db.types.OrderDescending))
        total = await c.towns_table.total_column(attribute, conditions=[db.CreationCondition(typeatt, o.name)])

        attnameformat = attname.replace('_', ' ')

        log = ""
        values : list[c.image_generator.Vertex] = []
        for i, record in enumerate(rs):
            parsed = parser(record.attribute(attribute)) if parser else record.attribute(attribute)
            name = str(record.attribute('name').replace("_", " "))
            val = formatter(parsed)
            perc = (record.attribute(attribute)/total)*100

            log = log + f"{i+1}. **{discord.utils.escape_markdown(name)}**: {val} ({perc:,.1f}%)\n"

            if int(parsed) > 0:
                values.append(c.image_generator.Vertex(name, int(parsed)))

        await c.image_generator.plot_piechart(
            values[:s.top_graph_object_count], f"{o.name_formatted}'s distribution of {attnameformat} ({len(rs)})"
        )
        graph = discord.File(await c.image_generator.render_plt(s.IMAGE_DPI_GRAPH, pad=True), "graph.png")

        embed = discord.Embed(title=f"{o.name_formatted}'s distribution of {attnameformat} ({len(rs)} towns)", color=s.embed)
        if interaction.extras.get("author"): embed._author = interaction.extras.get("author")
        embed.set_image(url="attachment://graph.png")

        if s.see_more_footer:
            embed.set_footer(text=f"View more with /distribution {typeatt}!" + (f" Tracking for {(await interaction.client.client.world.total_tracked).str_no_timestamp()}" if attribute =="duration" else ""))
        elif attribute == "duration":
            embed.set_footer(text=f" Tracking for {(await interaction.client.client.world.total_tracked).str_no_timestamp()}")

        view = paginator.PaginatorView(embed, log, index=interaction.extras.get("page"))
        view.add_item(commands_view.RefreshButton(c, f"distribution {typeatt} {attname}", (o.name,), row=0 if len(view.children) < 5 else 1))
        
        return await (interaction.response.edit_message(embed=embed, view=view, attachments=[graph]) if edit else interaction.response.send_message(embed=embed, view=view, file=graph))


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
        
        for attribute in s.distribution_commands["object"]:
            name = attribute.get("name") or attribute.get("attribute")
            command = app_commands.command(name=name, description=f"Distribution of nation {name}")(generate_command(self.client, attribute.get("attribute"), attribute.get("formatter") or str, attribute.get("parser"), is_nation=True, attname=name))
            command.autocomplete("nation")(autocompletes.nation_autocomplete)
            nation.add_command(command)

            name = attribute.get("name") or attribute.get("attribute")
            command = app_commands.command(name=name, description=f"Distribution of culture {name}")(generate_command(self.client, attribute.get("attribute"), attribute.get("formatter") or str, attribute.get("parser"), is_culture=True, attname=name))
            command.autocomplete("culture")(autocompletes.culture_autocomplete)
            culture.add_command(command)

            name = attribute.get("name") or attribute.get("attribute")
            name = "followers" if name == "residents" else name
            command = app_commands.command(name=name, description=f"Distribution of religion {name}")(generate_command(self.client, attribute.get("attribute"), attribute.get("formatter") or str, attribute.get("parser"), is_religion=True, attname=name))
            command.autocomplete("religion")(autocompletes.religion_autocomplete)
            religion.add_command(command)
        
        for attribute in s.distribution_commands["nation"]:
            name = attribute.get("name") or attribute.get("attribute")
            command = app_commands.command(name=name, description=f"Distribution of nation {name}")(generate_command(self.client, attribute.get("attribute"), attribute.get("formatter") or str, attribute.get("parser"), is_nation=True, attname=name))
            command.autocomplete("nation")(autocompletes.nation_autocomplete)
            nation.add_command(command)

        self.bot.tree.add_command(distribution)


async def setup(bot : commands.Bot):
    await bot.add_cog(Distribution(bot, bot.client))
