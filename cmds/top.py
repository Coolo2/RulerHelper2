
import discord 

import setup as s
from funcs import paginator, commands_view, autocompletes

from discord import app_commands
from discord.ext import commands

import db

import client

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
            y_formatter = None,
            not_in_history : bool = None
):
    async def cmd_uni(interaction : discord.Interaction, on : str = None, highlight : str = None):

        edit = interaction.extras.get("edit")

        on_date = datetime.datetime.strptime(on, s.DATE_STRFTIME).date() if on and not not_in_history else datetime.date.today()

        if is_town:
            if not_in_history:
                rs = await c.towns_table.get_records(attributes=["name", attribute], order=db.CreationOrder(attribute, db.types.OrderDescending))
                total = await c.towns_table.total_column(attribute)
            else:
                rs = await c.town_history_table.get_records(attributes=["town AS name", attribute], order=db.CreationOrder(attribute, db.types.OrderDescending), conditions=[db.CreationCondition("date", on_date)])
                total = await c.town_history_table.total_column(attribute, conditions=[db.CreationCondition("date", on_date)])
            l = [t.name for t in c.world.towns]
        elif is_player:
            rs = await c.player_history_table.get_records(
                attributes=["player AS name", f"MAX({attribute}) AS {attribute}"], 
                order=db.CreationOrder(attribute, db.types.OrderDescending),
                conditions=[db.CreationCondition("date", on_date, "<=")],
                group=["player"]
            )
            total = 0
            for r in rs: 
                attr = r.attribute(attribute)
                total += (attr if type(attr) != str else None) or 0
            l = [p.name for p in c.world.players]
        else: # is nation
            rs = await c.nation_history_table.get_records(conditions=[db.CreationCondition("date", on_date)], attributes=["nation AS name", attribute], order=db.CreationOrder(attribute, db.types.OrderDescending))
            total = await c.nation_history_table.total_column(attribute, conditions=[db.CreationCondition("date", on_date)])
            l = [n.name for n in c.world.nations]

        o_type = "nation" if is_nation else "town" if is_town else "player" if is_player else "culture" if is_culture else "religion"
        attnameformat = attname.replace('_', ' ')

        if is_culture or is_religion:
            rs = await c.object_history_table.get_records(conditions=[db.CreationCondition("type", o_type), db.CreationCondition("date", on_date)], attributes=["object AS name", attribute], order=db.CreationOrder(attribute, db.types.OrderDescending))
            total = await c.object_history_table.total_column(attribute, conditions=[db.CreationCondition("type", o_type), db.CreationCondition("date", on_date)])
            l = [o.name for o in c.world._objects[o_type + "s"]]

        log = ""
        values : list[c.image_generator.Vertex] = []
        i = -1
        for record in (reversed(rs) if reverse else rs):
            r_name = record.attribute("name")
            if is_town and (r_name in s.DEFAULT_TOWNS or True in [l in r_name for l in s.DEFAULT_TOWNS_SUBSTRING]):
                continue
            if is_religion and "Production" in r_name:
                continue
            if r_name not in l and on_date == datetime.date.today():
                continue

            attval = record.attribute(attribute) or 0
            if is_player and attribute=="bank" and (not attval or type(attval) == str):
                continue
            i += 1
            
            parsed = (parser(record.fields[1].value) if parser else record.fields[1].value) or 0
            val = formatter(parsed)
            
            if total > 0:
                perc = (attval/total)*100 if type(attval) != datetime.date else (parsed/total)*100
            else:
                perc = 0
            perc_str = f" ({perc:,.1f}%)" if type(attval) != datetime.date else ""
            name = str(r_name).replace("_", " ") if not is_player else str(r_name)
            fmt = "**" if r_name in l else "`"

            log =  log + f"{i}. {fmt}{discord.utils.escape_markdown(name)}{fmt}: {val}{perc_str}\n"

            values.append(c.image_generator.Vertex(name, parsed))
        
        title = f"Top {o_type}s by {attnameformat} " + (f"on {on} " if on else "") + f"({i:,})"

        await c.image_generator.plot_barchart(
            values[0:s.top_graph_object_count], title, o_type.title(), y or "Value", y_formatter, highlight=highlight
        )
        graph = discord.File(await c.image_generator.render_plt(s.IMAGE_DPI_GRAPH, pad=True), "graph.png")

        embed = discord.Embed(title=title, color=s.embed)
        if interaction.extras.get("author"): embed._author = interaction.extras.get("author")
        embed.set_image(url="attachment://graph.png")

        cmds = []
        added = 0
        for i, object in enumerate(values):
            if i >= 25: continue 
            if object.x.replace(" ", "_") in l and added < 25:
                added += 1
                cmds.append(commands_view.Command(f"get {o_type}", f"{i+1}. {object.x}", (object.x,), emoji=None))
        
        if attribute in ["duration"]:
            embed.set_footer(text=f" Tracking for {(await interaction.client.client.world.total_tracked).str_no_timestamp()}")
        elif attribute in ["messages", "mentions"]:
            embed.set_footer(text=f" Tracking chat for {(await interaction.client.client.world.total_tracked_chat).str_no_timestamp()}")
        if attribute == "bank" and is_player:
            embed.set_footer(text="Bank balance is only known for town mayors")

        view = paginator.PaginatorView(embed, log, index=interaction.extras.get("page"))
        view.add_item(commands_view.RefreshButton(c, f"top {o_type}s {attname}", (), 3))
        view.add_item(commands_view.CommandSelect(cog, cmds, f"Get {o_type.title()} Info...", 2))
        
        return await (interaction.response.edit_message(embed=embed, view=view, attachments=[graph]) if edit else interaction.response.send_message(embed=embed, view=view, file=graph))


    return cmd_uni

class Top(commands.Cog):

    def __init__(self, bot : commands.Bot, client : client.Client):
        self.bot = bot
        self.client = client

        super().__init__()
    
        top = app_commands.Group(name="top", description="Rank objects")

        command_types = [
            {"name":"town", "group":app_commands.Group(name="towns", description="List the top towns by an attribute", parent=top), "parameters":[{"name":"highlight", "autocomplete":autocompletes.town_autocomplete}]},
            {"name":"player", "group":app_commands.Group(name="players", description="List the top nations by an attribute", parent=top), "parameters":[{"name":"highlight", "autocomplete":autocompletes.player_autocomplete}]},
            {"name":"nation", "group":app_commands.Group(name="nations", description="List the top nations by an attribute", parent=top), "parameters":[{"name":"highlight", "autocomplete":autocompletes.nation_autocomplete}]},
            {"name":"culture", "group":app_commands.Group(name="cultures", description="List the top cultures by an attribute", parent=top), "parameters":[{"name":"highlight", "autocomplete":autocompletes.culture_autocomplete}], "attributes":s.top_commands["object"]},
            {"name":"religion", "group":app_commands.Group(name="religions", description="List the top religions by an attribute", parent=top), "parameters":[{"name":"highlight", "autocomplete":autocompletes.religion_autocomplete}], "attributes":s.top_commands["object"]},
        ]

        for command_type in command_types:
            for attribute in command_type.get("attributes") or s.top_commands[command_type["name"]]:
                name = attribute.get("name") or attribute.get("attribute")
                cmd_type_name = command_type['name']
                name = "followers" if name == "residents" and cmd_type_name == "religion" else name

                command = app_commands.command(name=name, description=f"Top {cmd_type_name}s by {name}")(generate_command(
                    self, 
                    self.client, 
                    attribute.get("attribute"), 
                    attribute.get("formatter") or str, 
                    attribute.get("parser"), 
                    is_town=cmd_type_name == "town", is_nation = cmd_type_name == "nation", is_player=cmd_type_name == "player", is_culture=cmd_type_name == "culture", is_religion=cmd_type_name == "religion",
                    attname=name, 
                    y=attribute.get("y"), 
                    reverse=attribute.get("reverse"), 
                    y_formatter=attribute.get("y_formatter"), 
                    not_in_history=attribute.get("not_in_history")
                ))
                command.autocomplete("on")(autocompletes.history_date_autocomplete_wrapper("object" if cmd_type_name in ["culture", "religion"] else cmd_type_name))
                for parameter in command_type["parameters"]:
                    if parameter.get("autocomplete"):
                        command.autocomplete(parameter["name"])(parameter["autocomplete"])
                command_type["group"].add_command(command)

        self.bot.tree.add_command(top)

async def setup(bot : commands.Bot):
    await bot.add_cog(Top(bot, bot.client))
