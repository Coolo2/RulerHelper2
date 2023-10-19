
import discord 
import json
import io

import setup as s
from funcs import autocompletes, commands_view, paginator, graphs

from discord import app_commands
from discord.ext import commands

import db

import client

from matplotlib.pyplot import plot, bar
from client.funcs import generate_time


import datetime

def generate_command(
            c : client.Client, 
            attribute : str, 
            qualitative=False, 
            formatter = str, 
            parser = None, 
            is_town : bool = False, 
            is_player : bool = False, 
            is_nation=False, 
            is_culture=False, 
            is_religion=False, 
            attname : str = None, 
            y : str = None, 
            y_formatter = None
):
    async def cmd_uni(interaction : discord.Interaction, town : str = None, player : str = None, nation : str = None, culture : str = None, religion : str = None):

        
        if town:
            o = c.world.get_town(town, True)
            if not o: raise client.errors.MildError("Nothing found!")
            rs = await c.town_history_table.get_records([db.CreationCondition("town", o.name)], ["date", attribute], order=db.CreationOrder("date", db.types.OrderAscending))
        elif player:
            o = c.world.get_player(player, True)
            if not o: raise client.errors.MildError("Nothing found!")
            rs = await c.player_history_table.get_records([db.CreationCondition("player", o.name)], ["date", attribute], order=db.CreationOrder("date", db.types.OrderAscending))
        elif nation:
            o = c.world.get_nation(nation, True)
            if not o: raise client.errors.MildError("Nothing found!")
            rs = await c.nation_history_table.get_records([db.CreationCondition("nation", o.name)], ["date", attribute], order=db.CreationOrder("date", db.types.OrderAscending))
        elif culture:
            o = c.world.get_culture(culture, True)
            if not o: raise client.errors.MildError("Nothing found!")
            rs = await c.object_history_table.get_records([db.CreationCondition("object", o.name), db.CreationCondition("type", o.object_type)], ["date", attribute], order=db.CreationOrder("date", db.types.OrderAscending))
        elif religion:
            o = c.world.get_religion(religion, True)
            if not o: raise client.errors.MildError("Nothing found!")
            rs = await c.object_history_table.get_records([db.CreationCondition("object", o.name), db.CreationCondition("type", o.object_type)], ["date", attribute], order=db.CreationOrder("date", db.types.OrderAscending))
        else:
            o = None
            rs = await c.global_history_table.get_records(attributes=["date", attribute], order=db.CreationOrder("date", db.types.OrderAscending))

        name = o.name_formatted + "'s" if o else 'Global'
        attnameformat = attname.replace('_', ' ')

        log = ""
        last = None
        values = {}
        for record in rs:
            parsed = parser(record.attribute(attribute)) if parser else record.attribute(attribute)
            val = formatter(parsed)
            if qualitative and last == val:
                continue
            log = f"**{record.attribute('date')}**: {discord.utils.escape_markdown(str(val))}\n" + log
            last = val

            values[str(record.attribute('date'))] = str(parsed) if qualitative else int(parsed)

        td = datetime.date.today().strftime("%Y-%m-%d")
        if td not in values:
            values[td] = values[list(values)[-1]]

        if not qualitative:
            file = graphs.save_graph(values, f"{name} {attnameformat} history", "Date", y or "Value", plot, y_formatter = y_formatter)
        else:
            file = graphs.save_timeline(values, f"{name} {attnameformat} history", booly=parser==bool)
        graph = discord.File(file, filename="graph.png")

        embed = discord.Embed(title=f"{name} {attnameformat} history", color=s.embed)
        embed.set_image(url="attachment://graph.png")

        if s.see_more_footer:
            embed.set_footer(text=f"See more with /history {'town' if town else 'nation' if nation else 'player' if player else ''} ... !" + (f" Tracking for {(await interaction.client.client.world.total_tracked).str_no_timestamp()}" if attribute == "duration" else ""))
        elif attribute == "duration":
            embed.set_footer(text=f" Tracking for {(await interaction.client.client.world.total_tracked).str_no_timestamp()}")

        view = paginator.PaginatorView(embed, log)
        
        return await interaction.response.send_message(embed=embed, view=view, file=graph)

    if is_town:
        async def cmd(interaction : discord.Interaction, town : str):
            await cmd_uni(interaction, town=town)
    elif is_player:
        async def cmd(interaction : discord.Interaction, player : str):
            await cmd_uni(interaction, player=player)
    elif is_nation:
        async def cmd(interaction : discord.Interaction, nation : str):
            await cmd_uni(interaction, nation=nation)
    elif is_culture:
        async def cmd(interaction : discord.Interaction, culture : str):
            await cmd_uni(interaction, culture=culture)
    elif is_religion:
        async def cmd(interaction : discord.Interaction, religion : str):
            await cmd_uni(interaction, religion=religion)
    else:
        async def cmd(interaction : discord.Interaction):
            await cmd_uni(interaction)
    return cmd

def generate_visited_command(c : client.Client, is_town=False, is_player=False):
    async def cmd_uni(interaction : discord.Interaction, town : str = None, player : str = None):

        objects : list[client.object.Activity] = []
        if town:
            o = c.world.get_town(town, True)
            if not o: raise client.errors.MildError("Nothing found!")
            objects = await o.visited_players
        elif player:
            o = c.world.get_player(player, True)
            if not o: raise client.errors.MildError("Nothing found!")
            objects = await o.visited_towns
            likely_residency = await o.likely_residency

        log = ""
        values = {}
        for i, obj in enumerate(reversed(objects)):
            is_known = True if type(obj.town) != str and type(obj.player) != str else False
            name = discord.utils.escape_markdown(str(obj.town or obj.player))
            
            prefix = ""
            fmt = ""
            if obj.player and type(obj.player) != str:
                if str(await obj.player.likely_residency) == str(o):
                    prefix = s.likely_residency_prefix_history
            if obj.town and type(obj.town) != str:
                if str(likely_residency) == str(obj.town):
                    prefix = s.likely_residency_prefix_history
            
            if datetime.datetime.now() - obj.last <= datetime.timedelta(seconds=s.refresh_period+5):
                fmt = "**"

            format = fmt if is_known else "`"
            
            if not is_known and s.history_skip_if_object_unknown:
                continue
            
            log = f"{len(objects)-i}. {prefix}{format}{name}{format}: {str(obj)}\n" + log

            values[name] = obj.total

        opp = "player" if town else "pown"
        file = graphs.save_graph(dict(list(reversed(list(values.items())))[:s.top_graph_object_count]), f"{str(o)}'s visited {opp} history ({len(objects)})", opp.title(), "Time (minutes)", bar, y_formatter=generate_time)
        graph = discord.File(file, filename="graph.png")

        embed = discord.Embed(title=f"{str(o)} visited history ({len(objects)})", color=s.embed)
        embed.set_image(url="attachment://graph.png")
        
        embed.set_footer(text=f"Bot has been tracking for {(await interaction.client.client.world.total_tracked).str_no_timestamp()}")

        view = paginator.PaginatorView(embed, log)
        
        return await interaction.response.send_message(embed=embed, view=view, file=graph)

    if is_town:
        async def cmd(interaction : discord.Interaction, town : str):
            await cmd_uni(interaction, town=town)
    elif is_player:
        async def cmd(interaction : discord.Interaction, player : str):
            await cmd_uni(interaction, player=player)

    return cmd


class History(commands.Cog):

    def __init__(self, bot : commands.Bot, client : client.Client):
        self.bot = bot
        self.client = client

        super().__init__()
    
        history = app_commands.Group(name="history", description="History commands")
        global_ = app_commands.Group(name="global", description="Get history for global attributes", parent=history)
        town = app_commands.Group(name="town", description="Get history for a town's attributes", parent=history)
        player = app_commands.Group(name="player", description="Get history for a player's attributes", parent=history)
        nation = app_commands.Group(name="nation", description="Get history for a nation's attributes", parent=history)
        culture = app_commands.Group(name="culture", description="Get history for a culture's attributes", parent=history)
        religion = app_commands.Group(name="religion", description="Get history for a religion's attributes", parent=history)


        for attribute in s.history_commands["town"]:
            name = attribute.get("name") or attribute.get("attribute")
            command = app_commands.command(name=name, description=f"History for town {name}")(generate_command(self.client, attribute.get("attribute"), attribute.get("qualitative"), attribute.get("formatter") or str, attribute.get("parser"), True, attname=name, y=attribute.get("y"), y_formatter=attribute.get("y_formatter")))
            command.autocomplete("town")(autocompletes.town_autocomplete)
            town.add_command(command)

        for attribute in s.history_commands["player"]:
            name = attribute.get("name") or attribute.get("attribute")
            command = app_commands.command(name=name, description=f"History for player {name}")(generate_command(self.client, attribute.get("attribute"), attribute.get("qualitative"), attribute.get("formatter") or str, attribute.get("parser"), is_player=True, attname=name, y=attribute.get("y"), y_formatter=attribute.get("y_formatter")))
            command.autocomplete("player")(autocompletes.player_autocomplete)
            player.add_command(command)
        
        for attribute in s.history_commands["nation"]:
            name = attribute.get("name") or attribute.get("attribute")
            command = app_commands.command(name=name, description=f"History for nation {name}")(generate_command(self.client, attribute.get("attribute"), attribute.get("qualitative"), attribute.get("formatter") or str, attribute.get("parser"), is_nation=True, attname=name, y=attribute.get("y"), y_formatter=attribute.get("y_formatter")))
            command.autocomplete("nation")(autocompletes.nation_autocomplete)
            nation.add_command(command)
        
        for attribute in s.history_commands["global"]:
            name = attribute.get("name") or attribute.get("attribute")
            command = app_commands.command(name=name, description=f"History for global {name}")(generate_command(self.client, attribute.get("attribute"), attribute.get("qualitative"), attribute.get("formatter") or str, attribute.get("parser"), attname=name, y=attribute.get("y"), y_formatter=attribute.get("y_formatter")))
            global_.add_command(command)
        
        for attribute in s.history_commands["object"]:
            name = attribute.get("name") or attribute.get("attribute")
            command = app_commands.command(name=name, description=f"History for culture {name}")(generate_command(self.client, attribute.get("attribute"), attribute.get("qualitative"), attribute.get("formatter") or str, attribute.get("parser"), is_culture=True, attname=name, y=attribute.get("y"), y_formatter=attribute.get("y_formatter")))
            command.autocomplete("culture")(autocompletes.culture_autocomplete)
            culture.add_command(command)
            name = attribute.get("name") or attribute.get("attribute")
            name = "followers" if name == "residents" else name
            command = app_commands.command(name=name, description=f"History for religion {name}")(generate_command(self.client, attribute.get("attribute"), attribute.get("qualitative"), attribute.get("formatter") or str, attribute.get("parser"), is_religion=True, attname=name, y=attribute.get("y"), y_formatter=attribute.get("y_formatter")))
            command.autocomplete("religion")(autocompletes.religion_autocomplete)
            religion.add_command(command)
        
        command = app_commands.command(name="visited_towns", description="History for player's visited towns")(generate_visited_command(self.client, is_player=True))
        command.autocomplete("player")(autocompletes.player_autocomplete)
        player.add_command(command)

        command = app_commands.command(name="visited_players", description="History for town's visited players")(generate_visited_command(self.client, is_town=True))
        command.autocomplete("town")(autocompletes.town_autocomplete)
        town.add_command(command)

        self.bot.tree.add_command(history)


async def setup(bot : commands.Bot):
    await bot.add_cog(History(bot, bot.client))
