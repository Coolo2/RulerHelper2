
import discord 

import setup as s
from funcs import autocompletes, commands_view, graphs, paginator

from discord import app_commands
from discord.ext import commands

import client
import db 
import numpy as np

from matplotlib.pyplot import bar, plot

class Compare(commands.GroupCog, name="compare", description="Compare two (or more) objects"):

    def __init__(self, bot : commands.Bot, client : client.Client):
        self.bot = bot
        self.client = client

        super().__init__()
    
    @app_commands.command(name="towns", description="Compare attributes for two (or more) towns")
    @app_commands.autocomplete(town_name_1=autocompletes.town_autocomplete, town_name_2=autocompletes.town_autocomplete, town_name_3=autocompletes.town_autocomplete, town_name_4=autocompletes.town_autocomplete, town_name_5=autocompletes.town_autocomplete)
    async def _towns(self, interaction : discord.Interaction, town_name_1 : str, town_name_2 : str, town_name_3 : str = None, town_name_4 : str = None, town_name_5 : str = None):
        
        edit = interaction.extras.get("edit")

        image_generators = []
        town_names = [tn for tn in [town_name_1, town_name_2, town_name_3, town_name_4, town_name_5] if tn != None] # COmbine and remove None
        town_names = list(dict.fromkeys(town_names)) # Remove duplicates
        if len(town_names) == 1:
            raise client.errors.MildError("Cannot compare a town to itself")

        towns : list[client.object.Town] = []
        for i, town_name in enumerate(town_names):
            town = self.client.world.get_town(town_name, True)
            if not town:
                raise client.errors.MildError(f"Couldn't find town {i+1}")
            towns.append(town)
        
        embed = discord.Embed(
            title="Comparison between: ", 
            description="\n".join(f"### {s.compare_emojis[i]} - {t.name_formatted}" for i, t in enumerate(towns)),
            color=s.embed
        )
        if interaction.extras.get("author"): embed._author = interaction.extras.get("author")

        attributes = s.compare_attributes["town"]

        async def im_map(twns : list[client.object.Town]):
            dpi = await self.client.image_generator.generate_area_map(twns, True, False, self.client.image_generator.MapBackground.AUTO, False, None, [], True, (1.25, 0.92+(0.08*len(twns))))
            await self.client.image_generator.layer_spawn_connections(twns)
            return await self.client.image_generator.render_plt(dpi, None)
        image_generators.append((im_map, (towns,)))

        for _, attribute in enumerate(attributes):
            display_name : str = (attribute.get("name") or attribute.get("attribute")).replace("_", " ").title()
            history_name = attribute.get("history_attribute") or attribute.get("attribute")
            formatter = attribute.get("formatter") or str

            desc, total = "", 0
            values = [getattr(t, attribute.get("attribute")) for t in towns]

            for i, value in enumerate(values): # Await coroutines
                try: values[i] = await value 
                except: pass 
            
            graph = self.client.image_generator.LineGraph(self.client.image_generator.XTickFormatter.DATE, attribute.get("y_formatter"))
            for i, (town, value) in enumerate(zip(towns, values)):
                desc += f"{s.compare_emojis[i]} {formatter(value)}\n"

                if not attribute.get('no_history') and not attribute.get('qualitative'):
                    total =  total + value
                    history_r = await self.client.town_history_table.get_records([db.CreationCondition("town", town.name)], order=db.CreationOrder("date", db.types.OrderAscending), attributes=[history_name, "date"])
                    graph.add_line(self.client.image_generator.Line([self.client.image_generator.Vertex(r.attribute("date"), r.attribute(history_name)) for r in history_r], town.name))
            
            if not attribute.get("qualitative"):
                y = attribute.get("y") or display_name
                if not attribute.get("no_history"):
                    async def plot_lines(graph, display_name, y):
                        await self.client.image_generator.plot_linegraph(graph, f"{display_name} Comparison", "Date", y)
                        return await self.client.image_generator.render_plt(s.IMAGE_DPI_GRAPH, pad=True)
                    image_generators.append((plot_lines, (graph,display_name,y)))
            
            total = total if type(total) == int else round(total, 2)
            total_str = f"{total:,}" if type(total) in [int, float] else str(total)
            embed.add_field(name=f"{display_name} {('('+total_str+')') if not attribute.get('no_history') and not attribute.get('qualitative') else ''}", value=desc, inline=attribute.get("inline") or False)

        nations = list(dict.fromkeys([t.nation.name for t in towns if t.nation]))

        view = paginator.PaginatorView(embed, page_image_generators=image_generators, search=False, skip_buttons=False, temp_img_url="attachment://paginator_image.png" if edit else "attachment://map_waiting.jpg", render_image_after=True, index=interaction.extras.get("page"))
        view.add_item(commands_view.CommandButton(self, commands_view.Command("compare players", "Compare Mayors", parameters=[t._mayor_raw for t in towns], emoji="👤", row=2)))
        if len(nations) > 1: view.add_item(commands_view.CommandButton(self, commands_view.Command("compare nations", "Compare Nations", parameters=nations, emoji="🗾", row=2)))
        
        view.add_item(commands_view.RefreshButton(self.client, "compare towns", town_names, row=0))
        
        f = discord.File(s.waiting_bg_path, "map_waiting.jpg")
        await (interaction.response.edit_message(embed=embed, view=view) if edit else interaction.response.send_message(embed=embed, view=view, file=f))

        await view.render_initial_image()

        await interaction.edit_original_response(embed=view.embed, attachments=[view.attachment], view=view)

    @app_commands.command(name="nations", description="Compare attributes for two (or more) nations")
    @app_commands.autocomplete(nation_name_1=autocompletes.nation_autocomplete, nation_name_2=autocompletes.nation_autocomplete, nation_name_3=autocompletes.nation_autocomplete, nation_name_4=autocompletes.nation_autocomplete, nation_name_5=autocompletes.nation_autocomplete)
    async def _nations(self, interaction : discord.Interaction, nation_name_1 : str, nation_name_2 : str, nation_name_3 : str = None, nation_name_4 : str = None, nation_name_5 : str = None):
        
        edit = interaction.extras.get("edit")

        image_generators = []
        nation_names = [tn for tn in [nation_name_1, nation_name_2, nation_name_3, nation_name_4, nation_name_5] if tn != None] # COmbine and remove None
        nation_names = list(dict.fromkeys(nation_names)) # Remove duplicates
        if len(nation_names) == 1:
            raise client.errors.MildError("Cannot compare a nation to itself")
        
        twns : list[client.object.Town] = []
        capitals : list[client.object.Town] = []
        nations : list[client.object.Nation] = []
        for i, nation_name in enumerate(nation_names):
            nation = self.client.world.get_nation(nation_name, True)
            if not nation:
                raise client.errors.MildError(f"Couldn't find nation {i+1}")
            nations.append(nation)
            twns += nation.towns
            capitals.append(nation.capital)
        
        embed = discord.Embed(
            title="Comparison between: ", 
            description="\n".join(f"### {s.compare_emojis[i]} - {n.name_formatted}" for i, n in enumerate(nations)),
            color=s.embed
        )
        if interaction.extras.get("author"): embed._author = interaction.extras.get("author")
        
        async def im_map(twns : list[client.object.Town], capitals : list[client.object.Town]):
            dpi = await self.client.image_generator.generate_area_map(twns, True, False, self.client.image_generator.MapBackground.AUTO, False, None, [], True, (1.25, 0.92+(0.08*len(capitals))))
            await self.client.image_generator.layer_spawn_connections(capitals)
            return await self.client.image_generator.render_plt(dpi, None)
        image_generators.append((im_map, (twns, capitals)))

        attributes = s.compare_attributes["nation"]
        for _, attribute in enumerate(attributes):
            display_name : str = (attribute.get("name") or attribute.get("attribute")).replace("_", " ").title()
            history_name = attribute.get("history_attribute") or attribute.get("attribute")
            formatter = attribute.get("formatter") or str

            desc, total = "", 0
            values = [getattr(t, attribute.get("attribute")) for t in nations]

            for i, value in enumerate(values): # Await coroutines
                try: values[i] = await value 
                except: pass 
            
            graph = self.client.image_generator.LineGraph(self.client.image_generator.XTickFormatter.DATE, attribute.get("y_formatter"))
            for i, (nation, value) in enumerate(zip(nations, values)):
                desc += f"{s.compare_emojis[i]} {formatter(value)}\n"

                if not attribute.get('no_history') and not attribute.get('qualitative'):
                    total += value
                    history_r = await self.client.nation_history_table.get_records([db.CreationCondition("nation", nation.name)], order=db.CreationOrder("date", db.types.OrderAscending), attributes=[history_name, "date"])
                    graph.add_line(self.client.image_generator.Line([self.client.image_generator.Vertex(r.attribute("date"), r.attribute(history_name)) for r in history_r], nation.name))
            
            if not attribute.get("qualitative"):
                y = attribute.get("y") or display_name
                if not attribute.get("no_history"):
                    async def plot_lines(graph, display_name, y):
                        await self.client.image_generator.plot_linegraph(graph, f"{display_name} Comparison", "Date", y)
                        return await self.client.image_generator.render_plt(s.IMAGE_DPI_GRAPH, pad=True)
                    image_generators.append((plot_lines, (graph,display_name,y)))
            
            total = total if type(total) == int else round(total, 2)
            total_str = f"{total:,}" if type(total) in [int, float] else str(total)
            embed.add_field(name=f"{display_name} {('('+total_str+')') if not attribute.get('no_history') and not attribute.get('qualitative') else ''}", value=desc, inline=attribute.get("inline") or False)

        
        view = paginator.PaginatorView(embed, page_image_generators=image_generators, search=False, skip_buttons=False, temp_img_url="attachment://paginator_image.png" if edit else "attachment://map_waiting.jpg", render_image_after=True, index=interaction.extras.get("page"))
        view.add_item(commands_view.CommandButton(self, commands_view.Command("compare players", "Compare Leaders", parameters=[n.capital._mayor_raw for n in nations], emoji="👤", row=2)))
        view.add_item(commands_view.CommandButton(self, commands_view.Command("compare towns", "Compare Capitals", parameters=[n.capital.name for n in nations], emoji="🏛️", row=2)))
        
        view.add_item(commands_view.RefreshButton(self.client, "compare nations", nation_names, row=0))
        
        f = discord.File(s.waiting_bg_path, "map_waiting.jpg")
        await (interaction.response.edit_message(embed=embed, view=view) if edit else interaction.response.send_message(embed=embed, view=view, file=f))

        await view.render_initial_image()

        await interaction.edit_original_response(embed=view.embed, attachments=[view.attachment], view=view)

    @app_commands.command(name="players", description="Compare attributes for two (or more) players")
    @app_commands.autocomplete(player_name_1=autocompletes.player_autocomplete, player_name_2=autocompletes.player_autocomplete, player_name_3=autocompletes.player_autocomplete, player_name_4=autocompletes.player_autocomplete, player_name_5=autocompletes.player_autocomplete)
    async def _players(self, interaction : discord.Interaction, player_name_1 : str, player_name_2 : str, player_name_3 : str = None, player_name_4 : str = None, player_name_5 : str = None):
        
        edit = interaction.extras.get("edit")

        image_generators = []
        player_names = [tn for tn in [player_name_1, player_name_2, player_name_3, player_name_4, player_name_5] if tn != None] # COmbine and remove None
        player_names = list(dict.fromkeys(player_names)) # Remove duplicates
        if len(player_names) == 1:
            raise client.errors.MildError("Cannot compare a player to itself")

        players : list[client.object.Player] = []
        for i, player_name in enumerate(player_names):
            player = self.client.world.get_player(player_name, True)
            if not player:
                raise client.errors.MildError(f"Couldn't find player {i+1}")
            players.append(player)
        
        embed = discord.Embed(
            title="Comparison between: ", 
            description="\n".join(f"### {s.compare_emojis[i]} - {p.name}" for i, p in enumerate(players)),
            color=s.embed
        )
        if interaction.extras.get("author"): embed._author = interaction.extras.get("author")

        async def im_map(players : list[client.object.Player]):
            await self.client.image_generator.init_map()

            await self.client.image_generator.layer_player_locations(players, [], show_background=True, expand_limits_multiplier=(1.4, 0.92+(0.08*len(players))))
            await self.client.image_generator.layer_spawn_connections(players)
            return await self.client.image_generator.render_plt(s.IMAGE_DPI_DRAWING, None)
        image_generators.append((im_map, (players,)))

        attributes = s.compare_attributes["player"]
        for _, attribute in enumerate(attributes):
            display_name : str = (attribute.get("name") or attribute.get("attribute")).replace("_", " ").title()
            history_name = attribute.get("history_attribute") or attribute.get("attribute")
            formatter = attribute.get("formatter") or str

            desc, total = "", 0
            values = [getattr(t, attribute.get("attribute")) for t in players]

            for i, value in enumerate(values): # Await coroutines
                try: values[i] = await value 
                except: pass 
            
            graph = self.client.image_generator.LineGraph(self.client.image_generator.XTickFormatter.DATE, attribute.get("y_formatter"))
            for i, (player, value) in enumerate(zip(players, values)):
                desc += f"{s.compare_emojis[i]} {formatter(value)}\n"

                if not attribute.get('no_history') and not attribute.get('qualitative'):
                    total += value
                    history_r = await self.client.player_history_table.get_records([db.CreationCondition("player", player.name)], order=db.CreationOrder("date", db.types.OrderAscending), attributes=[history_name, "date"])
                    graph.add_line(self.client.image_generator.Line([self.client.image_generator.Vertex(r.attribute("date"), r.attribute(history_name)) for r in history_r], player.name))
            
            if not attribute.get("qualitative"):
                y = attribute.get("y") or display_name
                if not attribute.get("no_history"):
                    async def plot_lines(graph, display_name, y):
                        await self.client.image_generator.plot_linegraph(graph, f"{display_name} Comparison", "Date", y)
                        return await self.client.image_generator.render_plt(s.IMAGE_DPI_GRAPH, pad=True)
                    image_generators.append((plot_lines, (graph,display_name,y)))
            
            total = total if type(total) == int else round(total, 2)
            total_str = f"{total:,}" if type(total) in [int, float] else str(total)
            embed.add_field(name=f"{display_name} {('('+total_str+')') if not attribute.get('no_history') and not attribute.get('qualitative') else ''}", value=desc, inline=attribute.get("inline") or False)
        
        likely_residencies = [i for i in list(dict.fromkeys([(await p.likely_residency).name if (await p.likely_residency) else None for p in players])) if i != None]

        view = paginator.PaginatorView(embed, page_image_generators=image_generators, search=False, skip_buttons=False, temp_img_url="attachment://paginator_image.png" if edit else "attachment://map_waiting.jpg", render_image_after=True, index=interaction.extras.get("page"))
        if len(likely_residencies) > 1: view.add_item(commands_view.CommandButton(self, commands_view.Command("compare towns", "Compare Likely Residencies", parameters=likely_residencies, emoji="🗾", row=2)))
        view.add_item(commands_view.RefreshButton(self.client, "compare players", player_names, row=0))
        
        f = discord.File(s.waiting_bg_path, "map_waiting.jpg")
        await (interaction.response.edit_message(embed=embed, view=view) if edit else interaction.response.send_message(embed=embed, view=view, file=f))

        await view.render_initial_image()

        await interaction.edit_original_response(embed=view.embed, attachments=[view.attachment], view=view)




async def setup(bot : commands.Bot):
    await bot.add_cog(Compare(bot, bot.client))
