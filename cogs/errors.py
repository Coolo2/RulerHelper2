
import discord 

from discord.ext import commands 
from discord import app_commands 

import setup as s 

import client as c

from funcs import commands_view

class ErrorHandling(commands.Cog):
    def __init__(self, bot : commands.Bot, client : c.Client):
        self.client = client 
    
        @bot.tree.error 
        async def on_error(interaction : discord.Interaction, error : app_commands.CommandInvokeError|Exception):
            error_original = error.original if hasattr(error, "original") else error 

            embed = discord.Embed(
                title="You've run into an unknown error",
                description=f"```{error}```\n\nMessage <@{s.mods[0]}> for support",
                color=s.embedFail
            )
            known = False

            if isinstance(error, app_commands.errors.CommandNotFound):
                return

            if isinstance(error_original, c.errors.MildError):
                embed = discord.Embed(
                    title=error_original.title,
                    description=f"{error_original.description}\n\nMessage <@{s.mods[0]}> for support",
                    color=s.embedFail
                )
                known = True

            if known or s.PRODUCTION_MODE:
                view = discord.ui.View()
                
                if hasattr(error, "command") and not hasattr(error.command, "type"):
                    view.add_item(commands_view.CommandButton(self, commands_view.Command(error.command.qualified_name, "Retry Command", parameters=list(interaction.namespace.__dict__.values()), emoji="🔃", row=1)))

                try:
                    return await interaction.response.send_message(embed=embed, ephemeral=True, view=view)
                except:
                    return await interaction.followup.send(embed=embed, ephemeral=True, view=view)
            
            raise error

async def setup(bot : commands.Bot):
    await bot.add_cog(ErrorHandling(bot, bot.client))