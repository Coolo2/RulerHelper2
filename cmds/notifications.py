import discord 
import json

from discord import app_commands
from discord.ext import commands

import client

import setup as s
from funcs import autocompletes

Choice = app_commands.Choice

notification_settings = {
    "territory_enter":["ignore_if_resident"]
}

@app_commands.default_permissions(manage_guild=True)
@app_commands.guild_only()
class Notifications(commands.GroupCog, name="notifications", description="Setup nation notifications in a channel in your server"):

    def __init__(self, bot : commands.Bot, client : client.Client):
        self.bot = bot
        self.client = client
    
    @app_commands.command(name="territory_enter", description="Set up territory enter notifications in a specific channel")
    #@app_commands.choices(notification_type=[Choice(name=n.replace("_", " ").title(), value=n) for n in notification_settings.keys()])
    @app_commands.describe(
                channel="The text channel to set up notifications in",
                enabled="Whether to enable or disable this notification type in this channel",
                nation_name="The nation that you want notifications for",
                ignore_if_resident="To be used for territory_enter notificaitons. Doesn't send a notification if they a resident of the nation"
    )
    @app_commands.autocomplete(nation_name=autocompletes.nation_autocomplete)
    async def _territory_enter(
                self, 
                interaction : discord.Interaction, 
                channel : discord.TextChannel, 
                enabled : bool,
                nation_name : str,
                ignore_if_resident : bool,
    ):  
        
        nation = self.client.world.get_nation(nation_name, True)

        if not nation:
            raise client.errors.MildError("Couldn't find nation")

        channels = await self.client.notifications.get_notification_channels(channel, "territory_enter")

        if len(channels) > 0:
            if enabled:
                if channels[0].ignore_if_resident == ignore_if_resident and channels[0].nation_name == nation.name:
                    raise client.errors.MildError("Channel already exists with this config")
                else:
                    await self.client.notifications.set_notification_config(channel, "territory_enter", nation_name, ignore_if_resident)     
                    return await interaction.response.send_message(embed=discord.Embed(title="Updated", description="Updated notifications in this channel!", color=s.embedSuccess))   
            else:
                await self.client.notifications.delete_notifications_channel(channel=channel, notification_type="territory_enter")
                return await interaction.response.send_message(embed=discord.Embed(title="Deleted", description="Deleted notification channel", color=s.embedSuccess))   
        else:
            if enabled:
                await self.client.notifications.set_notification_config(channel, "territory_enter", nation_name, ignore_if_resident)    
                try:
                    await channel.send("> Notifications have been enabled in this channel. See config with `/notifications config view`")
                    return await interaction.response.send_message(embed=discord.Embed(title="Enabled", description="Enabled notifications there!", color=s.embedSuccess))  
                except:
                    return await interaction.response.send_message(embed=discord.Embed(title="Partially enabled", description="Enabled in this channel, however I don't seem to have access to send messages. Please give me access to send messages there!", color=s.embedSuccess)) 
            else:
                raise client.errors.MildError("Notifications aren't set up here...")
    
    @app_commands.command(name="disable", description="Remove all notification channels in a text channel")
    async def _disable(
                self, 
                interaction : discord.Interaction,
                channel : discord.TextChannel
    ):  
        channels = await self.client.notifications.get_notification_channels(channel)
        if len(channels) > 0:
            await self.client.notifications.delete_notifications_channel(channel=channel)
            return await interaction.response.send_message(embed=discord.Embed(title="Disabled", description="Successfully disabled notifications in this channel", color=s.embed)) 
        
        raise client.errors.MildError("No notifications set up there...")
    
        


async def setup(bot : commands.Bot):
    await bot.add_cog(Notifications(bot, bot.client))