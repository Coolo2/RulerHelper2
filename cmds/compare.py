
import discord 

import setup as s
from funcs import autocompletes, commands_view, graphs, paginator

from discord import app_commands
from discord.ext import commands

import client

from matplotlib.pyplot import bar

class Compare(commands.GroupCog, name="compare", description="Compare two (or more) objects"):

    def __init__(self, bot : commands.Bot, client : client.Client):
        self.bot = bot
        self.client = client

        super().__init__()
    
    @app_commands.command(name="towns", description="Compare attributes for two (or more) towns")
    @app_commands.autocomplete(town_name_1=autocompletes.town_autocomplete, town_name_2=autocompletes.town_autocomplete, town_name_3=autocompletes.town_autocomplete, town_name_4=autocompletes.town_autocomplete, town_name_5=autocompletes.town_autocomplete)
    async def _towns(self, interaction : discord.Interaction, town_name_1 : str, town_name_2 : str, town_name_3 : str = None, town_name_4 : str = None, town_name_5 : str = None):
        
        await interaction.response.defer()

        image_generators = []
        town_names = [tn for tn in [town_name_1, town_name_2, town_name_3, town_name_4, town_name_5] if tn != None] # COmbine and remove None
        

        towns : list[client.object.Town] = []
        for i, town_name in enumerate(town_names):
            town = self.client.world.get_town(town_name, True)
            if not town:
                raise client.errors.MildError(f"Couldn't find town {i+1}")
            towns.append(town)
        
        embed = discord.Embed(
            title="Comparison between: ", 
            description="\n".join(f"### {s.compare_emojis[i]} - {t.name}" for i, t in enumerate(towns)),
            color=s.embed
        )

        attributes = s.compare_attributes["town"]
        image_generators.append((graphs.plot_towns, (towns, False, "auto", True, 5, False, None, None, None, None, [], towns)))
        for _, attribute in enumerate(attributes):
            display_name : str = (attribute.get("name") or attribute.get("attribute")).replace("_", " ").title()
            formatter = attribute.get("formatter") or str
            values = [getattr(t, attribute.get("attribute")) for t in towns]
            for i, value in enumerate(values): # Await what needs to be
                try:
                    values[i] = await value 
                except:
                    pass 
            
            desc = ""
            vals = {}
            for i, (town, value) in enumerate(zip(towns, values)):
                vals[town.name_formatted] = value
                desc += f"{s.compare_emojis[i]} {formatter(value)}\n"
            embed.add_field(name=display_name, value=desc, inline=attribute.get("inline") or False)
        
            if not attribute.get("qualitative"):
                y = attribute.get("y") or display_name
                parser = attribute.get("parser") or int
                image_generators.append((graphs.save_graph, ({t:parser(v) for t, v in vals.items()}, f"{display_name} Comparison", "Town", y, bar, None, attribute.get("y_formatter"))))
        
        view = paginator.PaginatorView(embed, page_image_generators=image_generators, search=False, skip_buttons=False)
        
        return await interaction.followup.send(embed=embed, view=view, file=view.attachment)

    @app_commands.command(name="nations", description="Compare attributes for two (or more) nations")
    @app_commands.autocomplete(nation_name_1=autocompletes.nation_autocomplete, nation_name_2=autocompletes.nation_autocomplete, nation_name_3=autocompletes.nation_autocomplete, nation_name_4=autocompletes.nation_autocomplete, nation_name_5=autocompletes.nation_autocomplete)
    async def _nations(self, interaction : discord.Interaction, nation_name_1 : str, nation_name_2 : str, nation_name_3 : str = None, nation_name_4 : str = None, nation_name_5 : str = None):
        
        await interaction.response.defer()

        image_generators = []
        nation_names = [tn for tn in [nation_name_1, nation_name_2, nation_name_3, nation_name_4, nation_name_5] if tn != None] # COmbine and remove None
        
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
            description="\n".join(f"### {s.compare_emojis[i]} - {n.name}" for i, n in enumerate(nations)),
            color=s.embed
        )

        attributes = s.compare_attributes["nation"]
        image_generators.append((graphs.plot_towns, (twns, False, "auto", True, 5, False, None, None, None, None, [], capitals)))
        for _, attribute in enumerate(attributes):
            display_name : str = (attribute.get("name") or attribute.get("attribute")).replace("_", " ").title()
            formatter = attribute.get("formatter") or str
            values = [getattr(n, attribute.get("attribute")) for n in nations]
            for i, value in enumerate(values): # Await what needs to be
                try:
                    values[i] = await value 
                except:
                    pass 
            
            desc = ""
            vals = {}
            for i, (nation, value) in enumerate(zip(nations, values)):
                vals[nation.name_formatted] = value
                desc += f"{s.compare_emojis[i]} {formatter(value)}\n"
            embed.add_field(name=display_name, value=desc, inline=attribute.get("inline") or False)
        
            if not attribute.get("qualitative"):
                y = attribute.get("y") or display_name
                parser = attribute.get("parser") or int
                image_generators.append((graphs.save_graph, ({t:parser(v) for t, v in vals.items()}, f"{display_name} Comparison", "Nation", y, bar, None, attribute.get("y_formatter"))))
        
        view = paginator.PaginatorView(embed, page_image_generators=image_generators, search=False, skip_buttons=False)
        
        return await interaction.followup.send(embed=embed, view=view, file=view.attachment)

    @app_commands.command(name="players", description="Compare attributes for two (or more) players")
    @app_commands.autocomplete(player_name_1=autocompletes.player_autocomplete, player_name_2=autocompletes.player_autocomplete, player_name_3=autocompletes.player_autocomplete, player_name_4=autocompletes.player_autocomplete, player_name_5=autocompletes.player_autocomplete)
    async def _players(self, interaction : discord.Interaction, player_name_1 : str, player_name_2 : str, player_name_3 : str = None, player_name_4 : str = None, player_name_5 : str = None):
        
        await interaction.response.defer()

        image_generators = []
        player_names = [tn for tn in [player_name_1, player_name_2, player_name_3, player_name_4, player_name_5] if tn != None] # COmbine and remove None
        

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

        attributes = s.compare_attributes["player"]
        image_generators.append((graphs.plot_towns, ([], False, "auto", True, 5, False, players, None, None, None, [], players)))
        for _, attribute in enumerate(attributes):
            display_name : str = (attribute.get("name") or attribute.get("attribute")).replace("_", " ").title()
            formatter = attribute.get("formatter") or str
            values = [getattr(t, attribute.get("attribute")) for t in players]
            for i, value in enumerate(values): # Await what needs to be
                try:
                    values[i] = await value 
                except:
                    pass 
            
            desc = ""
            vals = {}
            for i, (player, value) in enumerate(zip(players, values)):
                vals[player.name] = value
                desc += f"{s.compare_emojis[i]} {formatter(value)}\n"
            embed.add_field(name=display_name, value=desc, inline=attribute.get("inline") or False)
        
            if not attribute.get("qualitative"):
                y = attribute.get("y") or display_name
                parser = attribute.get("parser") or int
                image_generators.append((graphs.save_graph, ({t:parser(v) for t, v in vals.items()}, f"{display_name} Comparison", "Player", y, bar, None, attribute.get("y_formatter"))))
        
        view = paginator.PaginatorView(embed, page_image_generators=image_generators, search=False, skip_buttons=False)
        
        return await interaction.followup.send(embed=embed, view=view, file=view.attachment)
    




async def setup(bot : commands.Bot):
    await bot.add_cog(Compare(bot, bot.client))
