
import discord 

import setup as s
from funcs import autocompletes, commands_view, graphs, paginator

from discord import app_commands
from discord.ext import commands

import client

class Render(commands.GroupCog, name="render", description="Render an object on a map"):

    def __init__(self, bot : commands.Bot, client : client.Client):
        self.bot = bot
        self.client = client

        super().__init__()
    
    """
    @app_commands.command(name="town", description="Render town claims")
    @app_commands.describe(
            town_name="The town to draw",
            draw_town="Whether to draw town plots or just image. Defaults to True",
            line_width="Line width on the plots. Can be anything below 10. Defaults to 0.5",
            spawn_size="Spawn dot size. Can be any positive integer. Defaults to 10",
            fill_opacity="Opacity of the town map fill. Defaults to 32",
            bordering_town_opacity="Opacity of bordering towns. Defaults to 32",
            show_outposts="Show outposts of towns. Defaults to True"
    )
    @app_commands.autocomplete(town_name=autocompletes.town_autocomplete)
    async def _town(
                self, 
                interaction : discord.Interaction, 
                town_name : str,
                draw_town : bool = None,
                line_width : float = None,
                spawn_size : int = None,
                fill_opacity : int = None,
                bordering_town_opacity : int = None,
                show_outposts : bool = None
    ):
        
        if draw_town == None: draw_town = True 
        if line_width == None: line_width = 0.5
        if spawn_size == None: spawn_size = 10
        if fill_opacity == None: fill_opacity = 32
        if bordering_town_opacity == None: bordering_town_opacity = 32
        if show_outposts == None: show_outposts = True

        await interaction.response.defer()

        town = self.client.world.get_town(town_name, True)
        if not town:
            raise client.errors.MildError("Couldn't find town")
        dimmed_towns = town.borders

        

        await interaction.followup.send(file=discord.File(await graphs.render_towns(
            self.client, [town], dimmed_towns, draw_town, fill_opacity, line_width, bordering_town_opacity, spawn_size, show_outposts
        ), "graph.png"))
    
    @app_commands.command(name="nation", description="Render nation claims")
    @app_commands.describe(
            nation_name="The nation to draw",
            draw_town="Whether to draw town plots or just image. Defaults to True",
            line_width="Line width on the plots. Can be anything below 10. Defaults to 0.5",
            spawn_size="Spawn dot size. Can be any positive integer. Defaults to 10",
            fill_opacity="Opacity of the town map fill. Defaults to 32",
            bordering_town_opacity="Opacity of bordering towns. Defaults to 32",
            show_outposts="Show outposts of towns. Defaults to True"
    )
    @app_commands.autocomplete(nation_name=autocompletes.nation_autocomplete)
    async def _nation(
                self, 
                interaction : discord.Interaction, 
                nation_name : str,
                draw_town : bool = None,
                line_width : float = None,
                spawn_size : int = None,
                fill_opacity : int = None,
                bordering_town_opacity : int = None,
                show_outposts : bool = None
    ):
        
        if draw_town == None: draw_town = True 
        if line_width == None: line_width = 0.5
        if spawn_size == None: spawn_size = 10
        if fill_opacity == None: fill_opacity = 32
        if bordering_town_opacity == None: bordering_town_opacity = 32
        if show_outposts == None: show_outposts = True

        await interaction.response.defer()

        nation = self.client.world.get_nation(nation_name, True)
        if not nation:
            raise client.errors.MildError("Couldn't find nation")
        dimmed_towns = nation.borders[1]

        

        await interaction.followup.send(file=discord.File(await graphs.render_towns(
            self.client, nation.towns, dimmed_towns, draw_town, fill_opacity, line_width, bordering_town_opacity, spawn_size, show_outposts
        ), "graph.png"))"""
    # Maybe another time




async def setup(bot : commands.Bot):
    await bot.add_cog(Render(bot, bot.client))
