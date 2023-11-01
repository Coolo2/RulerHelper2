
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

        embed.add_field(name="Tracking time", value=f"{(await self.client.world.total_tracked).str_no_timestamp()}")
        embed.add_field(name="Servers", value=str(len(self.bot.guilds)))
        embed.add_field(name="Database size", value=f"{round(os.path.getsize('towny.db')/1000/1000, 2)}MB")
        embed.add_field(name="Last refresh", value=f"<t:{round(self.client.world.last_refreshed.timestamp())}:R>")

        total_linked_accounts = 0

        for player in self.client.world.players:
            if await player.discord:
                total_linked_accounts += 1
        
        embed.add_field(name="Linked Discord accounts", value=str(total_linked_accounts))

        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="changelog", description="Get a changelog of recent versions")
    async def _changelog(self, interaction : discord.Interaction):
        
        embed = discord.Embed(title=f"Bot changelog for {s.version}", description="""
- /history and /top have many more parameters, for example /history global, /history nation
- New /history type: timeline. Displays qualitative data. Eg: /history town mayor
- Visited history commands now show deleted towns 
- /distribution nation added which ranks towns by area, residents, etc
- Bot now tracks nation activity
- /get town
 - Location description is better now. It shows continent rather than general map area
- /get nation
 - Now displays flag
 - Shows world behind map drawing
 - Link to nation spawn map added
- /get player
 - Displays armour/health in a more visual format
 - Displays if player is online
 - Detects donator
- /get culture and /get religion
 - Now display "nation make-up". This shows what nations make up the culture/religion
- /compare
 - Now supports >2 objects as input
 - In a more blunt format
- Map drawings:
 - /get map drawings now show bordering towns in a dim colour
 - Certain map drawings will no longer re-render if already rendered (and not updated in-game since)
 - Higher quality background
 - Shows "generating map" instead of wait
- Request commands
 - You can now request to merge old objects into their new names to restore history. 
 - You can set nation discord links and discords as before, however system is more robust
- /get online now displays "playtime today" for each player
- Notable statistics are now more extensive
- You now no longer need to complete input on command parameters; eg you can type "enderpig" instead of "enderpig992216" if there is no one else with "enderpig" in their name
- Times now format correctly on x and y axis of graphs, if there is a gap it will be shown as a gap
- Performance fixes
- Top commands now allow you to visit a town/nation/culture/player's /get page from a select menu
- Towns and nations will automatically merge on name update
- Paged menus now allow you to skip to end
- History visited towns now has a map
- km² calculations were incorrect. changed to IRL km²
""", color=s.embed)

        await interaction.response.send_message(embed=embed)


async def setup(bot : commands.Bot):
    await bot.add_cog(Get(bot, bot.client))
