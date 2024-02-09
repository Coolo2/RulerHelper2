
import discord 

import setup as s
import os

from discord import app_commands
from discord.ext import commands

from funcs import paginator, commands_view

import client

class Get(commands.GroupCog, name="bot", description="Commands relating to the bot"):

    def __init__(self, bot : commands.Bot, client : client.Client):
        self.bot = bot
        self.client = client

        super().__init__()

    @app_commands.command(name="info", description="Get information on the bot")
    async def _info(self, interaction : discord.Interaction):

        send = interaction.response.edit_message if interaction.extras.get("edit") else interaction.response.send_message
        
        embed = discord.Embed(title="Bot information", description=f"{self.client.bot.user.display_name} is a bot managed by <@{s.mods[0]}> which provides towny stats.", color=s.embed)

        embed.add_field(name="Tracking time", value=f"{(await self.client.world.total_tracked).str_no_timestamp()}")
        embed.add_field(name="Servers", value=str(len(self.bot.guilds)))
        embed.add_field(name="Database size", value=f"{self.client.world.database_size}MB")
        embed.add_field(name="Last refresh", value=f"<t:{round(self.client.world.last_refreshed.timestamp())}:R>")
        embed.add_field(name="Linked discord accounts", value=str(len(await self.client.world.linked_discords)))
        embed.add_field(name="Current refresh time", value=f"{self.client.refresh_period}s")

        view = discord.ui.View()
        view.add_item(commands_view.RefreshButton(self.client, "bot info", []))

        await send(embed=embed, view=view)
    
    @app_commands.command(name="changelog", description="Get a changelog of recent versions")
    async def _changelog(self, interaction : discord.Interaction):
        
        embed = discord.Embed(title=f"Bot changelog up to {s.version}", color=s.embed)

        with open("changelog.txt", encoding="utf-8") as f:
            changelog = f.read()
        
        embed = discord.Embed(title=f"Changelog up to v{s.version}", color=s.embed)
        view = paginator.PaginatorView(embed, changelog, "newpage", 1, search=False)

        await interaction.response.send_message(embed=view.embed, view=view)


async def setup(bot : commands.Bot):
    await bot.add_cog(Get(bot, bot.client))
