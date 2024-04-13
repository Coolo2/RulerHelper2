

import discord 

from discord.ext import commands
from funcs import commands_view

import client

class Events(commands.Cog):

    def __init__(self, bot : commands.Bot, client : client.Client):
        self.bot = bot
        self.client = client

    @commands.Cog.listener()
    async def on_interaction(self, interaction : discord.Interaction):

        try:

            custom_id : str = interaction.data.get("custom_id")

            if interaction.data.get("component_type") == 3:
                custom_id = interaction.data["values"][0]

            if custom_id and (custom_id.startswith("refresh") or custom_id.startswith("command")):

                if custom_id.startswith("refresh"):
                    command_string = custom_id.replace("refresh_", "")

                    interaction.extras["edit"] = True

                    if len(interaction.message.embeds) > 0:
                        interaction.extras["author"] = interaction.message.embeds[0]._author if interaction.message.embeds[0].author else None

                        if "Page" in str(interaction.message.embeds[0].footer.text):
                            page_no = interaction.message.embeds[0].footer.text.split("Page")[1].split("/")[0].split(" ")[-1].strip()
                            if page_no.isnumeric():
                                interaction.extras["page"] = int(page_no)-1
                        
                else:
                    # Don't check if refresh button
                    if interaction.guild:
                        can_send_messages = interaction.channel.permissions_for(interaction.guild.get_member(interaction.user.id)).send_messages
                        if not can_send_messages:
                            raise client.errors.MildError("You do not have permissions to send here!")
                    
                    command_string = custom_id.replace("command_", "")
                    interaction.extras["author"] = {
                        "name":f"Requested by {interaction.user.display_name}",
                        "icon_url":interaction.user.display_avatar.url if interaction.user.display_avatar else None
                    }
                
                command_name, parameters = command_string.split("+") 
                parameters : list[str] = parameters.split("_&_")
                for i in range(len(parameters)):
                    if parameters[i] == "":
                        parameters[i] = None
                if len(parameters) == 1 and parameters[0] == None:
                    parameters = []
                
                callback = commands_view.get_command_callback(self.bot.tree, command_name)
                
                await commands_view.execute_callback_with_interaction(callback, self, interaction, parameters)
        
        except Exception as e:
            await self.bot.tree.on_error(interaction, e)

async def setup(bot : commands.Bot):
    await bot.add_cog(Events(bot, bot.client))
