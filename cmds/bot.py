
import discord 

import setup as s
import os

from discord import app_commands
from discord.ext import commands

import client

class Get(commands.GroupCog, name="bot", description="Commands relating to the bot"):

    def __init__(self, bot : commands.Bot, client : client.Client):
        self.bot = bot
        self.client = client

        super().__init__()

    @app_commands.command(name="info", description="Get information on the bot")
    async def _info(self, interaction : discord.Interaction):
        
        embed = discord.Embed(title="Bot information", description=f"{self.client.bot.user.display_name} is a bot managed by <@{s.mods[0]}> which provides towny stats.", color=s.embed)

        embed.add_field(name="Tracking time", value=f"{int((await self.client.world.total_tracked).total/3600/24)}d")
        embed.add_field(name="Servers", value=str(len(self.bot.guilds)))
        embed.add_field(name="Database size", value=f"{round(os.path.getsize('towny.db')/1000/1000, 2)}MB")
        embed.add_field(name="Last refresh", value=f"<t:{round(self.client.world.last_refreshed.timestamp())}:R>")

        total_linked_accounts = 0

        for player in self.client.world.players:
            if await player.discord:
                total_linked_accounts += 1
        
        embed.add_field(name="Linked Discord accounts", value=str(total_linked_accounts))

        await interaction.response.send_message(embed=embed)


async def setup(bot : commands.Bot):
    await bot.add_cog(Get(bot, bot.client))
