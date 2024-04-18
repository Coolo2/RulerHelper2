
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

        embed.add_field(name="Version", value=f"v{s.version}")
        embed.add_field(name="Servers", value=str(len(self.bot.guilds)))
        embed.add_field(name="Database Size", value=f"{self.client.world.database_size}MB")
        embed.add_field(name="Linked Discord Accounts", value=str(len(await self.client.world.linked_discords)))
        embed.add_field(name="Last Refresh", value="\n".join(f"{k.title()}: <t:{round(t.timestamp())}:R>" for k, t in self.client.last_refreshed.items()))
        embed.add_field(name="Current Refresh Time", value="\n".join(f"{k.title()}: {round(t)}s" for k, t in self.client.refresh_period.items()))

        embed.set_footer(text=await self.client.tracking_footer + f", nation visitors for {(await self.client.world.total_tracked_nation_visited).str_no_timestamp(False)}")

        view = discord.ui.View()
        view.add_item(commands_view.RefreshButton(self.client, "bot info", []))
        view.add_item(commands_view.CommandButton(self, commands_view.Command("bot changelog", "Changelogs", parameters=(), emoji="📜", row=1)))
        view.add_item(commands_view.CommandButton(self, commands_view.Command("history global database_size", "Database Size History", parameters=(), emoji="📁", row=1)))

        await send(embed=embed, view=view)
    
    @app_commands.command(name="help", description="Get a list of commands for the bot")
    async def _help(self, interaction : discord.Interaction):

        desc = ""
        for command in self.bot.tree.walk_commands():
            if not command.parent:
                desc += f"# /{command.qualified_name}"

                if type(command) == app_commands.Group:
                    for sub_command in command.commands:
                        desc += f"\n- /{sub_command.qualified_name}" + (f" - {sub_command.description}" if sub_command.description else "")

                        if type(sub_command) == app_commands.Group:
                            for sub_sub_command in sub_command.commands:
                                desc += f"\n - /{sub_sub_command.qualified_name}"
                desc += "newpage"

        embed = discord.Embed(title="Bot command list", color=s.embed)
        view = paginator.PaginatorView(embed, desc, "newpage", 1, search=False)

        await interaction.response.send_message(embed=view.embed, view=view)

    
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
