
import discord 
import json
import io

import setup as s
from funcs import autocompletes, commands_view

from discord import app_commands
from discord.ext import commands

import db

import client

class Get(commands.GroupCog, name="get", description="All get commands"):

    def __init__(self, bot : commands.Bot, client : client.Client):
        self.bot = bot
        self.client = client

        super().__init__()
    
    @app_commands.command(name="player", description="Get information about a player")
    @app_commands.autocomplete(player_name=autocompletes.player_autocomplete)
    async def _player(self, interaction : discord.Interaction, player_name : str):

        player = self.client.world.get_player(player_name, True)
        activity = await player.activity 

        town = player.town 
        likely_residency = await player.likely_residency
        visited_towns_total = await player.total_visited_towns

        health = "<:heartfull:1152274373923844196>"*int(player.health//2) + "<:hearthalf:1152274386364145715>"*int(player.health%2) + "<:heartnone:1152275125199179867>"*int((20-player.health)//2)
        armor = "<:armorfull:1152274423898976289>"*int(player.armor//2) + "<:armorhalf:1152274436179898430>"*int(player.armor%2) + "<:armornone:1152274447445790730>"*int((20-player.armor)//2)
        online = f"🟢 {player.name} is **online**" if player.online else f"🔴 {player.name} is **offline**"

        embed = discord.Embed(title=f"Player: {player.name}", description=f"{online}\n\n{health}\n{armor}", color=s.embed)
        
        embed.add_field(name="Location", value=f"[{int(player.location.x)}, {int(player.location.y)}, {int(player.location.z)}]({self.client.url}?x={int(player.location.x)}&z={int(player.location.z)}&zoom={s.map_link_zoom})")
        embed.add_field(name="Town", value=f"{town.name} {'('+str(town.nation)+')' if town.nation else ''}" if town else "None")
        embed.add_field(name="Likely Residency", value=f"{likely_residency.name} {'('+str(likely_residency.nation)+')' if likely_residency.nation and likely_residency != town else ''}" if likely_residency else "None")
        embed.add_field(name="Activity", value=str(activity))
        embed.add_field(name="Visited Towns", value=f"{visited_towns_total} ({(visited_towns_total/len(self.client.world.towns))*100:.2f}%)")
        
        embed.set_thumbnail(url=player.avatar_url)


        c_view = commands_view.CommandsView(self)
        if town:
            c_view.add_command(commands_view.Command("get town", "Town Info", (town.name,), button_style=discord.ButtonStyle.primary, emoji="ℹ️"))
        

        return await interaction.response.send_message(embed=embed, view=c_view)

    @app_commands.command(name="town", description="Get information about a town")
    @app_commands.autocomplete(town_name=autocompletes.town_autocomplete)
    async def _town(self, interaction : discord.Interaction, town_name : str):
        
        town = self.client.world.get_town(town_name, True)

        embed = discord.Embed(title=f"Town: {town.name}", color=s.embed)

        embed.add_field(name="Nation", value=town.nation.name if town.nation else "None")
        embed.add_field(name="Daily Tax", value=f"{town.resident_tax:.1f}%")
        embed.add_field(name="Bank", value=f"${town.bank:,.2f}")
        embed.add_field(name="Mayor", value=str(town.mayor))
        embed.add_field(name="Spawnblock", value=f"[{int(town.spawn.x)}, {int(town.spawn.z)}]({self.client.url}?x={int(town.spawn.x)}&z={int(town.spawn.z)}&zoom={s.map_link_zoom})")
        embed.add_field(name="Total Residents", value=f"{town.resident_count:,}")
        embed.add_field(name="Area", value=f"{town.area} plots")
        embed.add_field(name="Activity", value=str(await town.activity))

        return await interaction.response.send_message(embed=embed)

    

    

async def setup(bot : commands.Bot):
    await bot.add_cog(Get(bot, bot.client))



