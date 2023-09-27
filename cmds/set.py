
import discord 

import setup as s
from funcs import autocompletes, commands_view, graphs, paginator

from discord import app_commands
from discord.ext import commands

import client

class Set(commands.GroupCog, name="set", description="Set stuff"):

    def __init__(self, bot : commands.Bot, client : client.Client):
        self.bot = bot
        self.client = client

        super().__init__()
    
    @app_commands.command(name="nation_discord_invite", description="Set nation invite link")
    async def _nation_discord_invite(self, interaction : discord.Interaction, nation_name : str, invite_link : str):

        nation = self.client.world.get_nation(nation_name, True)

        if not nation:
            raise client.errors.MildError("Couldn't find nation")
        
        for player in self.client.world.players:
            if player.discord and player.discord.id == interaction.user.id and player != player.town.nation.capital.mayor:
                raise client.errors.MildError("You are not in-game leader of this nation")
        
        await nation.set_flag("discord", invite_link)

        embed = discord.Embed(title="Successfully set discord invite", description=f"Set discord invite link for **{nation.name_formatted}** to **{invite_link}**", color=s.embedSuccess)
        
        await interaction.response.send_message(embed=embed)
        
           


async def setup(bot : commands.Bot):
    await bot.add_cog(Set(bot, bot.client))
