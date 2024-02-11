
import discord 

import setup as s
from funcs import autocompletes, commands_view, paginator

from discord import app_commands
from discord.ext import commands

import db
import client

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
            conditions.append(db.CreationCondition("date", o.founded_date, ">="))
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
            #rs = await c.global_history_table.get_records(attributes=["date", attribute], order=db.CreationOrder("date", db.types.OrderAscending), conditions=conditions)

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
        timeline_points = []
        for record in rs:
            
            if record.attribute(attribute) == None and not qualitative:
                continue
            
            parsed = parser(record.attribute(attribute)) if parser else record.attribute(attribute)
            if qualitative and last == parsed:
                continue
            
            if not qualitative:
                parsed_values[str(record.attribute('date'))] = parsed
            else:
                timeline_points.append(c.image_generator.Vertex(record.attribute('date'), parsed))

            if not qualitative:
                change = parsed-last if last else None
                change = (("+" if change >= 0 else "-") + formatter(change).replace("-", "")) if change not in [None, 0] else ""
            val = formatter(parsed)
            
            log = f"**{record.attribute('date').strftime('%b %d %Y')}**: {discord.utils.escape_markdown(str(val))}" + (f" (`{change}`)\n" if last and not qualitative and len(change)>0 else "\n") + log
            last = parsed
        
        if not qualitative:

            idx = range(len(parsed_values))
        
        #else:
        #    prev = None 
        #    idx = []
        #    for i, (point) in enumerate(timeline_points):
        #        if point.y != prev:
        #            prev = parsed 
        #            idx.append(i)

            for i in idx:
                date, parsed = list(parsed_values.items())[i]
                values[date] = str(parsed) if qualitative else int(parsed)

        td = datetime.date.today().strftime("%Y-%m-%d")
        if td not in values and len(values) > 0 and datetime.datetime.strptime(list(values)[-1], "%Y-%m-%d").date() < datetime.date.today():
            values[td] = values[list(values)[-1]]
        
        if not qualitative:
            lg = c.image_generator.LineGraph(c.image_generator.XTickFormatter.DATE, y_formatter)
            lg.add_line(c.image_generator.Line([c.image_generator.Vertex(r.fields[0].value, r.fields[1].value) for r in rs]))
            await c.image_generator.plot_linegraph(
                lg, f"{name} {attnameformat} history", "Date", y or "Value"
            )
            file = await c.image_generator.render_plt(s.IMAGE_DPI_GRAPH, pad=True)
        else:
            await c.image_generator.plot_timeline(timeline_points, f"{name} {attnameformat} history", boolean_values=parser==bool)
            file = await c.image_generator.render_plt(s.IMAGE_DPI_GRAPH, pad=True)

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


def generate_command_today(
            c : client.Client, 
            attribute : str, 
            formatter = str, 
            parser = None, 
            is_town : bool = False, 
            is_player : bool = False, 
            is_nation=False, 
            attname : str = None, 
            y : str = None, 
            y_formatter = None
):
    async def cmd_uni(interaction : discord.Interaction, town : str = None, player : str = None, nation : str = None, culture : str = None, religion : str = None):

        edit = interaction.extras.get("edit")
        conditions = []

        o_type = "town" if town else "player" if player else "nation" if nation else "global"
        table_name = "town_day_history" if town else "player_day_history" if player else "nation_day_history" if nation else "global_day_history"
        name_attribute = "town" if town else "player" if player else "nation" if nation else None

        if town:
            o = c.world.get_town(town, True)
        elif player:
            o = c.world.get_player(player, True)
        elif nation:
            o = c.world.get_nation(nation, True)
        else:
            o = None

        table = await c.database.get_table(table_name)

        if o_type != "global":
            if not o: raise client.errors.MildError("Nothing found!")
            conditions.append(db.CreationCondition(name_attribute, o.name))
        
        rs = await table.get_records(
            conditions, 
            ["time", attribute], 
            order=db.CreationOrder("time", db.types.OrderAscending)
        )

        if len(rs) == 0:
            raise client.errors.MildError(f"No data to show yet! Wait until some is available (max 20 minutes)")

        name = o.name_formatted + "'s" if o else 'Global'
        attnameformat = attname.replace('_', ' ')

        log = ""
        last = None
        values = {}
        parsed_values = {}
        for record in rs:
            
            if record.attribute(attribute) == None:
                continue
            
            parsed = parser(record.attribute(attribute)) if parser else record.attribute(attribute)
            
            parsed_values[str(record.attribute('time'))] = parsed

            change = parsed-last if last else None
            change = (("+" if change >= 0 else "-") + formatter(change).replace("-", "")) if change not in [None, 0] else ""
            val = formatter(parsed)
            
            log = f"**<t:{int(record.attribute('time').timestamp())}:f>**: {discord.utils.escape_markdown(str(val))}" + (f" (`{change}`)\n" if last and len(change)>0 else "\n") + log
            last = parsed
        
            values[str(record.attribute('time'))] = int(parsed)
        
        lg = c.image_generator.LineGraph(c.image_generator.XTickFormatter.DATETIME, y_formatter)
        lg.add_line(c.image_generator.Line([c.image_generator.Vertex(r.fields[0].value, r.fields[1].value) for r in rs]))
        await c.image_generator.plot_linegraph(
            lg, f"{name} {attnameformat} history today", "Time (GMT)", y or "Value"
        )
        file = await c.image_generator.render_plt(s.IMAGE_DPI_GRAPH, pad=True)
        graph = discord.File(file, filename="graph.png")

        embed = discord.Embed(title=f"{name} {attnameformat} history today", color=s.embed)
        if interaction.extras.get("author"): embed._author = interaction.extras.get("author")
        embed.set_image(url="attachment://graph.png")

        if s.see_more_footer:
            embed.set_footer(text=f"See more with /history_today {o_type} ... !")

        view = paginator.PaginatorView(embed, log, index=interaction.extras.get("page"))
        
        view.add_item(commands_view.RefreshButton(c, f"history_today {o_type} {attname}", [o.name] if o else [], row=0 if len(view.children) < 5 else 1))
        
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
        values : list[c.image_generator.Vertex] = []
        towns = []
        for i, obj in enumerate(objects):
            is_known = True if type(obj.town) != str and type(obj.player) != str else False
            name = str(obj.town or obj.player)

            if not is_known and s.history_skip_if_object_unknown:
                continue
            
            perc = (obj.total/total)*100

            prefix = ""
            fmt = ""
            if (total < 100 or perc >= 0.2) and obj.player and type(obj.player) != str:
                if str(await obj.player.likely_residency) == str(o):
                    prefix = s.likely_residency_prefix_history
            if obj.town and type(obj.town) != str:
                towns.append(obj.town)
                if str(likely_residency) == str(obj.town):
                    prefix = s.likely_residency_prefix_history
            
            if datetime.datetime.now() - obj.last <= datetime.timedelta(seconds=c.refresh_period+5):
                fmt = "**"

            format = fmt if is_known else "`"

            log = log + f"{i+1}. {prefix}{format}{discord.utils.escape_markdown(name) if is_known else name}{format}: {str(obj)} ({perc:,.1f}%)\n"
            values.append(c.image_generator.Vertex(name, obj.total))

        opp = "player" if town else "town"
        
        embed = discord.Embed(title=f"{str(o)} visited history ({len(objects)})", color=s.embed)
        if interaction.extras.get("author"): embed._author = interaction.extras.get("author")
        embed.set_footer(text=await c.tracking_footer)

        files = []
        if len(objects) > 0:
            await c.image_generator.plot_barchart(
                values[0:s.top_graph_object_count], f"{str(o)}'s visited {opp} history ({len(objects)})", opp.title(), "Time (minutes)", y_formatter=c.image_generator.YTickFormatter.TIME
            )
            file = await c.image_generator.render_plt(s.IMAGE_DPI_GRAPH, pad=True)
            files.append(discord.File(file, filename="graph.png"))
            embed.set_image(url="attachment://graph.png")

            cmds = []
            added = 0
            for i, object in enumerate(values ):
                if object.x.replace(" ", "_") in l and added < 25:
                    added += 1
                    cmds.append(commands_view.Command(f"get {opp}", f"{i+1}. {object.x}", (object.x,), emoji=None))

            view = paginator.PaginatorView(embed, log, skip_buttons=True, index=interaction.extras.get("page"))
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

                        dpi = await c.image_generator.generate_area_map(towns, True, True, True, True, None, [])
                        map = discord.File(await c.image_generator.render_plt(dpi, None), "graph.png")
                        
                        await interaction.followup.edit_message(embed=embed, attachments=[map], message_id=interaction.message.id, view=view)
                    return map_button_callback
                button.callback = map_button(towns, view)
                view.add_item(button)
        else:
            view = discord.ui.View()
            embed.description = "No one has visited."
        view.add_item(commands_view.RefreshButton(c, f"history {'town' if town else 'player'} visited_{opp}s", (o.name,), row=3))
        
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
        today = app_commands.Group(name="history_today", description="History for just today")

        town = app_commands.Group(name="town", description="Get history for a town's attributes", parent=history)
        player = app_commands.Group(name="player", description="Get history for a player's attributes", parent=history)
        

        command_types = [
            {"name":"global", "group":app_commands.Group(name="global", description="Get history for global attributes", parent=history), 
                "group_today":app_commands.Group(name="global", description="Get history for global attributes today", parent=today), "parameters":[]},
            {"name":"town", "group":town, 
                "group_today":app_commands.Group(name="town", description="Get history for a town's attributes today", parent=today), "parameters":[{"name":"town", "autocomplete":autocompletes.town_autocomplete}]},
            {"name":"player", "group":player, 
                "group_today":app_commands.Group(name="player", description="Get history for a player's attributes today", parent=today), "parameters":[{"name":"player", "autocomplete":autocompletes.player_autocomplete}]},
            {"name":"nation", "group":app_commands.Group(name="nation", description="Get history for a nation's attributes", parent=history), 
                "group_today":app_commands.Group(name="nation", description="Get history for a nation's attributes today", parent=today), "parameters":[{"name":"nation", "autocomplete":autocompletes.nation_autocomplete}]},
            {"name":"culture", "group":app_commands.Group(name="culture", description="Get history for a culture's attributes", parent=history), "parameters":[{"name":"culture", "autocomplete":autocompletes.culture_autocomplete}], "attributes":s.history_commands["object"]},
            {"name":"religion", "group":app_commands.Group(name="religion", description="Get history for a religion's attributes", parent=history), "parameters":[{"name":"religion", "autocomplete":autocompletes.religion_autocomplete}], "attributes":s.history_commands["object"]},
        ]

        for command_type in command_types:
            for attribute in command_type.get("attributes") or s.history_commands[command_type["name"]]:
                name = attribute.get("name") or attribute.get("attribute")
                cmd_type_name = command_type['name']
                name = "followers" if name == "residents" and cmd_type_name == "religion" else name

                if not attribute.get("today_only"):
                    command = app_commands.command(name=name, description=attribute.get("description") or f"History for {cmd_type_name} {name}")(generate_command(
                        self.client, 
                        attribute.get("attribute"), 
                        attribute.get("qualitative"), 
                        attribute.get("formatter") or str, attribute.get("parser"), 
                        is_town=cmd_type_name == "town", is_nation = cmd_type_name == "nation", is_player=cmd_type_name == "player", is_culture=cmd_type_name == "culture", is_religion=cmd_type_name == "religion",
                        attname=name, 
                        y=attribute.get("y"), y_formatter=attribute.get("y_formatter"),
                        start_at=attribute.get("start_at"),
                    ))
                    for parameter in command_type["parameters"]:
                        if parameter.get("autocomplete"):
                            command.autocomplete(parameter["name"])(parameter["autocomplete"])
                    command_type["group"].add_command(command)

                if command_type.get("group_today") and name in s.history_today_commands[command_type["name"]]:
                    command_day = app_commands.command(name=name, description=attribute.get("description") or f"Today's history for {cmd_type_name} {name}")(generate_command_today(
                        self.client, 
                        attribute.get("attribute"), 
                        attribute.get("formatter") or str, attribute.get("parser"), 
                        is_town=cmd_type_name == "town", is_nation = cmd_type_name == "nation", is_player=cmd_type_name == "player",
                        attname=name, 
                        y=attribute.get("y"), y_formatter=attribute.get("y_formatter")
                    ))
                    for parameter in command_type["parameters"]:
                        if parameter.get("autocomplete"):
                            command_day.autocomplete(parameter["name"])(parameter["autocomplete"] if parameter["autocomplete"] != autocompletes.player_autocomplete else autocompletes.players_today_autocomplete)
                    command_type["group_today"].add_command(command_day)
        
        cmds = [["player", "town", player, autocompletes.player_autocomplete], ["town", "player", town, autocompletes.town_autocomplete]]
        for cmd in cmds:
            command = app_commands.command(name=f"visited_{cmd[1]}s", description=f"History for {cmd[0]}'s visited {cmd[1]}s")(generate_visited_command(self, self.client, is_player=cmd[0] == "player", is_town=cmd[0] == "town"))
            command.autocomplete(cmd[0])(cmd[3])
            cmd[2].add_command(command)

        self.bot.tree.add_command(history)
        self.bot.tree.add_command(today)


async def setup(bot : commands.Bot):
    await bot.add_cog(History(bot, bot.client))
