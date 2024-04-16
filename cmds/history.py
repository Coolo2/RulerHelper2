
import discord 

import setup as s
from funcs import autocompletes, commands_view, paginator

from discord import app_commands
from discord.ext import commands

import client

import datetime
import typing

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
    async def cmd_uni(
                interaction : discord.Interaction, 
                before : str = None,
                after : str = None,
                town : str = None, 
                player : str = None, 
                nation : str = None, 
                culture : str = None, 
                religion : str = None
    ):
        
        before_date, after_date = None, None
        edit = interaction.extras.get("edit")
        conditions = []
        bindings = []

        if before:
            try:
                before_date = datetime.datetime.strptime(before, s.DATE_STRFTIME).date()
            except ValueError:
                raise c.errors.MildError("Not a valid 'before' date")
            
        if after:
            try:
                after_date = datetime.datetime.strptime(after, s.DATE_STRFTIME).date()
            except ValueError:
                raise c.errors.MildError("Not a valid 'after' date")
        
        # Swap before and after if in wrong order
        if before_date and after_date and after_date > before_date:
            after_date_copy = after_date
            after_date = before_date
            before_date = after_date_copy 
        
        if start_at: 
            conditions.append("date >= ?")
            bindings.append(start_at)
        if after: 
            conditions.append("date >= ?")
            bindings.append(after_date)
        if before: 
            conditions.append("date <= ?")
            bindings.append(before_date)

        o_type = "town" if town else "player" if player else "nation" if nation else "culture" if culture else "religion" if religion else "global"
        table_name = "town_history" if town else "player_history" if player else "nation_history" if nation else "object_history" if culture or religion else "global_history"
        name_attribute = "town" if town else "player" if player else "nation" if nation else "object" if culture or religion else None

        if town:
            o = c.world.get_town(town, True)
            conditions.append("date >= ?")
            bindings.append(o.founded_date)
        elif player:
            o = c.world.get_player(player, True)
        elif nation:
            o = c.world.get_nation(nation, True)
        elif culture:
            o = c.world.get_culture(culture, True)
            conditions.append("type = ?")
            bindings.append(o.object_type)
        elif religion:
            o = c.world.get_religion(religion, True)
            conditions.append("type = ?")
            bindings.append(o.object_type)
        else:
            o = None

        if o_type != "global":
            if not o: raise client.errors.MildError("Nothing found!")
            conditions.append(f"{name_attribute} = ?")
            bindings.append(o.name)
        
        statement = f"SELECT date, {attribute} FROM {table_name}{' WHERE ' if len(conditions) > 0 else ''}{' AND '.join(conditions)} ORDER BY date ASC"

        rs = await (await c.execute(statement, bindings)).fetchall()

        name = o.name_formatted + "'s" if o else 'Global'
        attnameformat = attname.replace('_', ' ')

        log = ""
        last = None
        values = {}
        parsed_values = {}
        timeline_points = []
        for (date, value) in rs:
            
            if value == None and not qualitative:
                continue
            
            parsed = parser(value) if parser else value
            if qualitative and last == parsed:
                continue
            
            if not qualitative:
                parsed_values[str(date)] = parsed
            else:
                timeline_points.append(c.image_generator.Vertex(date, parsed))

            if not qualitative:
                change = parsed-last if last else None
                change = (("+" if change >= 0 else "-") + formatter(change).replace("-", "")) if change not in [None, 0] else ""
            val = formatter(parsed)
            
            log = f"**{date.strftime(s.DATE_STRFTIME)}**: {discord.utils.escape_markdown(str(val))}" + (f" (`{change}`)\n" if last and not qualitative and len(change)>0 else "\n") + log
            last = parsed
        
        if not qualitative:

            idx = range(len(parsed_values))

            for i in idx:
                date, parsed = list(parsed_values.items())[i]
                values[date] = str(parsed) if qualitative else int(parsed)

        td = datetime.date.today().strftime("%Y-%m-%d")
        if td not in values and len(values) > 0 and datetime.datetime.strptime(list(values)[-1], "%Y-%m-%d").date() < datetime.date.today():
            values[td] = values[list(values)[-1]]
        
        if not qualitative:
            lg = c.image_generator.LineGraph(c.image_generator.XTickFormatter.DATE, y_formatter)
            lg.add_line(c.image_generator.Line([c.image_generator.Vertex(r[0], r[1]) for r in rs], add_point_before=True))
            
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

        if attribute=="bank" and is_player:
            embed.set_footer(text="Bank balance is only tracked for town mayors")
        elif s.see_more_footer:
            embed.set_footer(text=f"See more with /history {o_type} ... !" + (f" Tracking for {(await interaction.client.client.world.total_tracked).str_no_timestamp()}" if attribute == "duration" else ""))
        elif attribute == "duration":
            embed.set_footer(text=f" Tracking for {(await interaction.client.client.world.total_tracked).str_no_timestamp()}")

        view = paginator.PaginatorView(embed, log, index=interaction.extras.get("page"))
        
        view.add_item(commands_view.RefreshButton(c, f"history {o_type} {attname}", ((o.name,) if o else ()) + (before, after), row=0 if len(view.children) < 5 else 1))
        
        return await (interaction.response.edit_message(embed=embed, view=view, attachments=[graph]) if edit else interaction.response.send_message(embed=embed, view=view, file=graph))

    if is_town:
        async def cmd(interaction : discord.Interaction, town : str, before : str = None, after : str = None):
            await cmd_uni(interaction, town=town, before=before, after=after)
    elif is_player:
        async def cmd(interaction : discord.Interaction, player : str, before : str = None, after : str = None):
            await cmd_uni(interaction, player=player, before=before, after=after)
    elif is_nation:
        async def cmd(interaction : discord.Interaction, nation : str, before : str = None, after : str = None):
            await cmd_uni(interaction, nation=nation, before=before, after=after)
    elif is_culture:
        async def cmd(interaction : discord.Interaction, culture : str, before : str = None, after : str = None):
            await cmd_uni(interaction, culture=culture, before=before, after=after)
    elif is_religion:
        async def cmd(interaction : discord.Interaction, religion : str, before : str = None, after : str = None):
            await cmd_uni(interaction, religion=religion, before=before, after=after)
    else:
        async def cmd(interaction : discord.Interaction, before : str = None, after : str = None):
            await cmd_uni(interaction, before=before, after=after)
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
        bindings = []

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

        if o_type != "global":
            if not o: raise client.errors.MildError("Nothing found!")
            conditions.append(f"{name_attribute}=?" )
            bindings.append(o.name)
        
        rs = await (await c.execute(f"SELECT time, {attribute} FROM {table_name}{' WHERE ' if len(conditions) > 0 else ''}{' AND '.join(conditions)} ORDER BY time ASC", bindings)).fetchall()

        if len(rs) == 0:
            raise client.errors.MildError(f"No data to show yet! Wait until some is available (max 20 minutes)")

        name = o.name_formatted + "'s" if o else 'Global'
        attnameformat = attname.replace('_', ' ')

        log = ""
        last = None
        values = {}
        parsed_values = {}
        for (time, value) in rs:
            if value == None:
                continue
            
            parsed = parser(value) if parser else value
            
            parsed_values[str(time)] = parsed

            change = parsed-last if last else None
            change = (("+" if change >= 0 else "-") + formatter(change).replace("-", "")) if change not in [None, 0] else ""
            val = formatter(parsed)
            
            log = f"**<t:{int(time.timestamp())}:f>**: {discord.utils.escape_markdown(str(val))}" + (f" (`{change}`)\n" if last and len(change)>0 else "\n") + log
            last = parsed
        
            values[str(time)] = int(parsed)
        
        lg = c.image_generator.LineGraph(c.image_generator.XTickFormatter.DATETIME, y_formatter)
        lg.add_line(c.image_generator.Line([c.image_generator.Vertex(r[0], r[1]) for r in rs]))
        await c.image_generator.plot_linegraph(
            lg, f"{name} {attnameformat} history today", "Time (GMT)", y or "Value"
        )
        file = await c.image_generator.render_plt(s.IMAGE_DPI_GRAPH, pad=True)
        graph = discord.File(file, filename="graph.png")

        embed = discord.Embed(title=f"{name} {attnameformat} history today", color=s.embed)
        if interaction.extras.get("author"): embed._author = interaction.extras.get("author")
        embed.set_image(url="attachment://graph.png")

        if attribute=="bank" and is_player:
            embed.set_footer(text="Bank balance is only tracked for town mayors")
        elif s.see_more_footer:
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

def generate_visited_command(cog, c : client.Client, table_type : typing.Literal["town", "nation"], is_town=False, is_player=False, is_nation=False):
    async def cmd_uni(interaction : discord.Interaction, town : str = None, player : str = None, nation : str = None):
        
        # table_type is either 'town' or 'nation'

        edit = interaction.extras.get("edit")

        objects : list[client.objects.Activity] = []
        if town or nation:
            if town:
                o = c.world.get_town(town, True)
            elif nation:
                o = c.world.get_nation(nation, True)
            if not o: raise client.errors.MildError("Nothing found!")
            objects = await o.visited_players
            total = (await (await c.execute(f"SELECT SUM(duration) FROM visited_{table_type}s WHERE {table_type}=?", (o.name,))).fetchone())[0]
            l = {p.name for p in c.world.players}
        elif player:
            o = c.world.get_player(player, True)
            if not o: raise client.errors.MildError("Nothing found!")
            objects = (await o.visited_towns) if table_type == "town" else (await o.visited_nations)
            total = (await (await c.execute(f"SELECT SUM(duration) FROM visited_{table_type}s WHERE player=?", (o.name,))).fetchone())[0]
            l = {t.name for t in c.world.towns} if table_type == "town" else ([n.name for n in c.world.nations])

        log = ""
        values : list[c.image_generator.Vertex] = []
        towns = []
        for i, obj in enumerate(objects):
            is_known = True if type(obj.town) != str and type(obj.player) != str and type(obj.nation) != str else False
            name = str(obj.town or obj.player or obj.nation)

            if not is_known and s.history_skip_if_object_unknown:
                continue
            
            perc = (obj.total/total)*100

            prefix = ""
            fmt = ""
            
            if table_type == "town":
                if obj.player and str(obj.player) in o._resident_names:
                    prefix = s.resident_prefix_history
                if obj.town and type(obj.town) != str:
                    towns.append(obj.town)
                    if str(o.residence) == str(obj.town):
                        prefix = s.resident_prefix_history
            
            if datetime.datetime.now() - obj.last <= datetime.timedelta(seconds=c.refresh_period["map"]+5):
                fmt = "**"

            format = fmt if is_known else "`"

            log = log + f"{i+1}. {prefix}{format}{discord.utils.escape_markdown(name) if is_known else name}{format}: {str(obj)} ({perc:,.1f}%)\n"
            values.append(c.image_generator.Vertex(name, obj.total))

        opp = "player" if town or nation else "town" if table_type == "town" and player else "nation"
        
        embed = discord.Embed(title=f"{discord.utils.escape_markdown(str(o))} visited {opp} history ({len(objects)})", color=s.embed)
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
                view.add_item(commands_view.CommandSelect(cog, cmds, f"Get {opp.title()} Info...", -1))
            
            if player and table_type == "town":
                button = discord.ui.Button(label="Map", emoji="🗺️", row=1)
                def map_button(towns : list[client.objects.Town], view : discord.ui.View):
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
            embed.description = f"No visited {opp}s."
        view.add_item(commands_view.RefreshButton(c, f"history {'town' if town else 'player' if player else 'nation'} visited_{opp}s", (o.name,), row=1))

        if table_type == "nation":
            embed.set_footer(text=f"Tracking nation visited players for {(await c.world.total_tracked_nation_visited).str_no_timestamp()}")
        
        await (interaction.response.edit_message(embed=embed, view=view, attachments=files) if edit else interaction.response.send_message(embed=embed, view=view, files=files))

    if is_town:
        async def cmd(interaction : discord.Interaction, town : str):
            await cmd_uni(interaction, town=town)
    elif is_player:
        async def cmd(interaction : discord.Interaction, player : str):
            await cmd_uni(interaction, player=player)
    elif is_nation:
        async def cmd(interaction : discord.Interaction, nation : str):
            await cmd_uni(interaction, nation=nation)

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
        nation = app_commands.Group(name="nation", description="Get history for a nation's attributes", parent=history)
        

        command_types = [
            {"name":"global", "group":app_commands.Group(name="global", description="Get history for global attributes", parent=history), 
                "group_today":app_commands.Group(name="global", description="Get history for global attributes today", parent=today), "parameters":[]},
            {"name":"town", "group":town, 
                "group_today":app_commands.Group(name="town", description="Get history for a town's attributes today", parent=today), "parameters":[{"name":"town", "autocomplete":autocompletes.town_autocomplete}]},
            {"name":"player", "group":player, 
                "group_today":app_commands.Group(name="player", description="Get history for a player's attributes today", parent=today), "parameters":[{"name":"player", "autocomplete":autocompletes.player_autocomplete}]},
            {"name":"nation", "group":nation, 
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
                        y=attribute.get("y"), y_formatter=attribute.get("y_formatter") or attribute.get("formatter"),
                        start_at=attribute.get("start_at"),
                    ))
                    for parameter in command_type["parameters"]:
                        if parameter.get("autocomplete"):
                            command.autocomplete(parameter["name"])(parameter["autocomplete"])
                    command_type["group"].add_command(command)
                    command.autocomplete("after")(autocompletes.history_date_autocomplete_wrapper("object" if cmd_type_name in ["culture", "religion"] else cmd_type_name))
                    command.autocomplete("before")(autocompletes.history_date_autocomplete_wrapper("object" if cmd_type_name in ["culture", "religion"] else cmd_type_name))

                if command_type.get("group_today") and name in s.history_today_commands[command_type["name"]]:
                    command_day = app_commands.command(name=name, description=attribute.get("description") or f"Today's history for {cmd_type_name} {name}")(generate_command_today(
                        self.client, 
                        attribute.get("attribute"), 
                        attribute.get("formatter") or str, attribute.get("parser"), 
                        is_town=cmd_type_name == "town", is_nation = cmd_type_name == "nation", is_player=cmd_type_name == "player",
                        attname=name, 
                        y=attribute.get("y"), y_formatter=attribute.get("y_formatter") or attribute.get("formatter")
                    ))
                    for parameter in command_type["parameters"]:
                        if parameter.get("autocomplete"):
                            command_day.autocomplete(parameter["name"])(parameter["autocomplete"] if parameter["autocomplete"] != autocompletes.player_autocomplete else autocompletes.players_today_autocomplete)
                    command_type["group_today"].add_command(command_day)
        
        cmds = [["player", "town", player, autocompletes.player_autocomplete, "town"], ["player", "nation", player, autocompletes.player_autocomplete, "nation"], ["town", "player", town, autocompletes.town_autocomplete, "town"], ["nation", "player", nation, autocompletes.nation_autocomplete, "nation"]]
        for cmd in cmds:
            command = app_commands.command(name=f"visited_{cmd[1]}s", description=f"History for {cmd[0]}'s visited {cmd[1]}s")(generate_visited_command(self, self.client, cmd[4], is_player=cmd[0] == "player", is_town=cmd[0] == "town", is_nation=cmd[0] == "nation"))
            command.autocomplete(cmd[0])(cmd[3])
            cmd[2].add_command(command)

        self.bot.tree.add_command(history)
        self.bot.tree.add_command(today)


async def setup(bot : commands.Bot):
    await bot.add_cog(History(bot, bot.client))
