
import discord 

import setup as s
from funcs import autocompletes, commands_view, paginator, graphs

from discord import app_commands
from discord.ext import commands

import db
import client

from matplotlib.pyplot import plot, bar
from client.funcs import generate_time

import datetime

import numpy as np

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
            y_formatter = None,
            start_at : datetime.date = None
):
    async def cmd_uni(interaction : discord.Interaction, town : str = None, player : str = None, nation : str = None, culture : str = None, religion : str = None):

        edit = interaction.extras.get("edit")
        conditions = []

        o_type = "town" if town else "player" if player else "nation" if nation else "culture" if culture else "religion" if religion else "global"
        table_name = "town_history" if town else "player_history" if player else "nation_history" if nation else "object_history" if culture or religion else "global_history"
        name_attribute = "town" if town else "player" if player else "nation" if nation else "object" if culture or religion else None

        if start_at: conditions.append(db.CreationCondition("date", start_at, ">="))

        if town:
            o = c.world.get_town(town, True)
        elif player:
            o = c.world.get_player(player, True)
        elif nation:
            o = c.world.get_nation(nation, True)
        elif culture:
            o = c.world.get_culture(culture, True)
            conditions.append(db.CreationCondition("type", o.object_type))
        elif religion:
            o = c.world.get_religion(religion, True)
            conditions.append(db.CreationCondition("type", o.object_type))
        else:
            o = None
            rs = await c.global_history_table.get_records(attributes=["date", attribute], order=db.CreationOrder("date", db.types.OrderAscending), conditions=conditions)

        table = await c.database.get_table(table_name)

        if o_type != "global":
            if not o: raise client.errors.MildError("Nothing found!")
            conditions.append(db.CreationCondition(name_attribute, o.name))
        
        rs = await table.get_records(
            conditions, 
            ["date", attribute], 
            order=db.CreationOrder("date", db.types.OrderAscending)
        )

        name = o.name_formatted + "'s" if o else 'Global'
        attnameformat = attname.replace('_', ' ')

        log = ""
        last = None
        values = {}
        parsed_values = {}
        for record in rs:
            
            if record.attribute(attribute) == None and not qualitative:
                continue
            
            parsed = parser(record.attribute(attribute)) if parser else record.attribute(attribute)
            if qualitative and last == parsed:
                continue
            
            parsed_values[str(record.attribute('date'))] = parsed

            if not qualitative:
                change = parsed-last if last else None
                change = (("+" if change >= 0 else "-") + formatter(change).replace("-", "")) if change not in [None, 0] else ""
            val = formatter(parsed)
            
            log = f"**{record.attribute('date').strftime('%b %d %Y')}**: {discord.utils.escape_markdown(str(val))}" + (f" (`{change}`)\n" if last and not qualitative and len(change)>0 else "\n") + log
            last = parsed
        
        if not qualitative:

            idx = range(len(parsed_values))
        
        else:
            prev = None 
            idx = []
            for i, (date, parsed) in enumerate(parsed_values.items()):
                if parsed != prev:
                    prev = parsed 
                    idx.append(i)

        for i in idx:
            date, parsed = list(parsed_values.items())[i]
            values[date] = str(parsed) if qualitative else int(parsed)

        td = datetime.date.today().strftime("%Y-%m-%d")
        if td not in values and len(values) > 0 and datetime.datetime.strptime(list(values)[-1], "%Y-%m-%d").date() < datetime.date.today():
            values[td] = values[list(values)[-1]]
        
        if not qualitative:
            file = graphs.save_graph(values, f"{name} {attnameformat} history", "Date", y or "Value", plot, y_formatter = y_formatter, adjust_missing=len(values) < 60)
        else:
            file = graphs.save_timeline(values, f"{name} {attnameformat} history", booly=parser==bool)

        graph = discord.File(file, filename="graph.png")

        embed = discord.Embed(title=f"{name} {attnameformat} history", color=s.embed)
        if interaction.extras.get("author"): embed._author = interaction.extras.get("author")
        embed.set_image(url="attachment://graph.png")

        
        if s.see_more_footer:
            embed.set_footer(text=f"See more with /history {o_type} ... !" + (f" Tracking for {(await interaction.client.client.world.total_tracked).str_no_timestamp()}" if attribute == "duration" else ""))
        elif attribute == "duration":
            embed.set_footer(text=f" Tracking for {(await interaction.client.client.world.total_tracked).str_no_timestamp()}")

        view = paginator.PaginatorView(embed, log, index=interaction.extras.get("page"))
        
        view.add_item(commands_view.RefreshButton(c, f"history {o_type} {attname}", [o.name] if o else [], row=0 if len(view.children) < 5 else 1))
        
        return await (interaction.response.edit_message(embed=embed, view=view, attachments=[graph]) if edit else interaction.response.send_message(embed=embed, view=view, file=graph))

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

def generate_visited_command(cog, c : client.Client, is_town=False, is_player=False):
    async def cmd_uni(interaction : discord.Interaction, town : str = None, player : str = None):

        edit = interaction.extras.get("edit")

        objects : list[client.object.Activity] = []
        if town:
            o = c.world.get_town(town, True)
            if not o: raise client.errors.MildError("Nothing found!")
            objects = await o.visited_players
            total = await c.visited_towns_table.total_column("duration", conditions=[db.CreationCondition("town", o.name)])
            l = [p.name for p in c.world.players]
        elif player:
            o = c.world.get_player(player, True)
            if not o: raise client.errors.MildError("Nothing found!")
            objects = await o.visited_towns
            likely_residency = await o.likely_residency
            total = await c.visited_towns_table.total_column("duration", conditions=[db.CreationCondition("player", o.name)])
            l = [t.name for t in c.world.towns]

        log = ""
        values = {}
        towns = []
        for i, obj in enumerate(reversed(objects)):
            is_known = True if type(obj.town) != str and type(obj.player) != str else False
            name = str(obj.town or obj.player)
            
            prefix = ""
            fmt = ""
            if obj.player and type(obj.player) != str:
                if str(await obj.player.likely_residency) == str(o):
                    prefix = s.likely_residency_prefix_history
            if obj.town and type(obj.town) != str:
                towns.append(obj.town)
                if str(likely_residency) == str(obj.town):
                    prefix = s.likely_residency_prefix_history
            
            if datetime.datetime.now() - obj.last <= datetime.timedelta(seconds=c.refresh_period+5):
                fmt = "**"

            format = fmt if is_known else "`"
            
            if not is_known and s.history_skip_if_object_unknown:
                continue

            perc = (obj.total/total)*100
            
            log = f"{len(objects)-i}. {prefix}{format}{discord.utils.escape_markdown(name) if is_known else name}{format}: {str(obj)} ({perc:,.1f}%)\n" + log

            values[name] = obj.total

        opp = "player" if town else "town"
        
        embed = discord.Embed(title=f"{str(o)} visited history ({len(objects)})", color=s.embed)
        if interaction.extras.get("author"): embed._author = interaction.extras.get("author")
        embed.set_footer(text=f"Bot has been tracking for {(await c.world.total_tracked).str_no_timestamp()}")

        files = []
        if len(objects) > 0:
            file = graphs.save_graph(dict(list(reversed(list(values.items())))[:s.top_graph_object_count]), f"{str(o)}'s visited {opp} history ({len(objects)})", opp.title(), "Time (minutes)", bar, y_formatter=generate_time)
            files.append(discord.File(file, filename="graph.png"))
            embed.set_image(url="attachment://graph.png")

            cmds = []
            added = 0
            for i, object_name in enumerate(reversed(values.keys()) ):
                if object_name.replace(" ", "_") in l and added < 25:
                    added += 1
                    cmds.append(commands_view.Command(f"get {opp}", f"{i+1}. {object_name}", (object_name,), emoji=None))

            view = paginator.PaginatorView(embed, log, skip_buttons=False, index=interaction.extras.get("page"))
            if len(cmds) > 0:
                view.add_item(commands_view.CommandSelect(cog, cmds, f"Get {opp.title()} Info...", 2))
            
            if player:
                button = discord.ui.Button(label="Map", emoji="🗺️", row=0)
                def map_button(towns : list[client.object.Town], view : discord.ui.View):
                    async def map_button_callback(interaction : discord.Interaction):
                        await interaction.response.defer()

                        for item in view.children:
                            if hasattr(item, "label") and item.label == "Map":
                                item.disabled = True 
                        
                        map = discord.File(graphs.plot_towns(towns, plot_spawn=False, whole=True), filename="graph.png")
                        
                        await interaction.followup.edit_message(embed=embed, attachments=[map], message_id=interaction.message.id, view=view)
                    return map_button_callback
                button.callback = map_button(towns, view)
                view.add_item(button)
        else:
            view = discord.ui.View()
            embed.description = "No one has visited."
        view.add_item(commands_view.RefreshButton(c, f"history {'town' if town else 'player'} visited_{opp}s", (o.name,), row=0))
        
        await (interaction.response.edit_message(embed=embed, view=view, attachments=files) if edit else interaction.response.send_message(embed=embed, view=view, files=files))

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
        town = app_commands.Group(name="town", description="Get history for a town's attributes", parent=history)
        player = app_commands.Group(name="player", description="Get history for a player's attributes", parent=history)

        command_types = [
            {"name":"global", "group":app_commands.Group(name="global", description="Get history for global attributes", parent=history), "parameters":[]},
            {"name":"town", "group":town, "parameters":[{"name":"town", "autocomplete":autocompletes.town_autocomplete}]},
            {"name":"player", "group":player, "parameters":[{"name":"player", "autocomplete":autocompletes.player_autocomplete}]},
            {"name":"nation", "group":app_commands.Group(name="nation", description="Get history for a nation's attributes", parent=history), "parameters":[{"name":"nation", "autocomplete":autocompletes.nation_autocomplete}]},
            {"name":"culture", "group":app_commands.Group(name="culture", description="Get history for a culture's attributes", parent=history), "parameters":[{"name":"culture", "autocomplete":autocompletes.culture_autocomplete}], "attributes":s.history_commands["object"]},
            {"name":"religion", "group":app_commands.Group(name="religion", description="Get history for a religion's attributes", parent=history), "parameters":[{"name":"religion", "autocomplete":autocompletes.religion_autocomplete}], "attributes":s.history_commands["object"]},
        ]

        for command_type in command_types:
            for attribute in command_type.get("attributes") or s.history_commands[command_type["name"]]:
                name = attribute.get("name") or attribute.get("attribute")
                cmd_type_name = command_type['name']
                name = "followers" if name == "residents" and cmd_type_name == "religion" else name

                command = app_commands.command(name=name, description=f"History for {cmd_type_name} {name}")(generate_command(
                    self.client, 
                    attribute.get("attribute"), 
                    attribute.get("qualitative"), 
                    attribute.get("formatter") or str, attribute.get("parser"), 
                    is_town=cmd_type_name == "town", is_nation = cmd_type_name == "nation", is_player=cmd_type_name == "player", is_culture=cmd_type_name == "culture", is_religion=cmd_type_name == "religion",
                    attname=name, 
                    y=attribute.get("y"), y_formatter=attribute.get("y_formatter"),
                    start_at=attribute.get("start_at")
                ))
                for parameter in command_type["parameters"]:
                    if parameter.get("autocomplete"):
                        command.autocomplete(parameter["name"])(parameter["autocomplete"])
                command_type["group"].add_command(command)
        
        cmds = [["player", "town", player, autocompletes.player_autocomplete], ["town", "player", town, autocompletes.town_autocomplete]]
        for cmd in cmds:
            command = app_commands.command(name=f"visited_{cmd[1]}s", description=f"History for {cmd[0]}'s visited {cmd[1]}s")(generate_visited_command(self, self.client, is_player=cmd[0] == "player", is_town=cmd[0] == "town"))
            command.autocomplete(cmd[0])(cmd[3])
            cmd[2].add_command(command)

        self.bot.tree.add_command(history)


async def setup(bot : commands.Bot):
    await bot.add_cog(History(bot, bot.client))
