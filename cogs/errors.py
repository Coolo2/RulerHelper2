
import discord 

from discord.ext import commands 
from discord import app_commands 

import setup as s 

import client as c

class ErrorHandling(commands.Cog):
    def __init__(self, bot : commands.Bot, client : c.Client):
        self.client = client 
    


        @bot.tree.error 
        async def on_error(interaction : discord.Interaction, error : app_commands.AppCommandError):
            embed = discord.Embed(
                title="You've run into an unknown error",
                description=f"```{error}```\n\nMessage <@368071242189897728> for support",
                color=s.embedFail
            )

            if isinstance(error, app_commands.errors.CommandNotFound):
                return

            if isinstance(error.original, c.errors.MildError):
                embed = discord.Embed(
                    title=error.original.title,
                    description=f"{error.original.description}\n\nMessage <@368071242189897728> for support",
                    color=s.embedFail
                )

            try:
                await interaction.response.send_message(embed=embed, ephemeral=True)
            except:
                await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot : commands.Bot):
    await bot.add_cog(ErrorHandling(bot, bot.client))