
import discord 
from discord import app_commands 

import typing

class Command():
    def __init__(self, command : typing.Union[str, typing.Coroutine], label : str, parameters : tuple, button_style : discord.ButtonStyle = discord.ButtonStyle.secondary, emoji : str = "💬", row=1):
        self.command = command 
        self.label = label 
        self.parameters = parameters 
        self.button_style = button_style
        self.row = row
        self.emoji = emoji
    
    def get_command_callback(self, tree : app_commands.CommandTree) -> typing.Coroutine:
        if type(self.command) != str:
            return self.command 
        
        command = None 
        
        for item in self.command.split(" "):
            if not command:
                command = tree.get_command(item)
            else:
                command = command.get_command(item)
        return command.callback
    
    
    async def execute(self, cog, interaction : discord.Interaction):
        await (self.get_command_callback(interaction.client.tree))(cog, interaction, *self.parameters)

class CommandsView(discord.ui.View):

    def __init__(self, cog, commands : typing.List[Command] = []):
        super().__init__(timeout=3600)
        self.cog = cog

        for command in commands:
            self.add_command(command)

    
    def add_command(self, command : Command):
        button = discord.ui.Button(style=command.button_style, label=command.label, emoji=command.emoji, row=command.row)

        def command_callback_runner(cmd):
            async def callback(interaction : discord.Interaction):
                await cmd.execute(self.cog, interaction)
            return callback

        button.callback = command_callback_runner(command) 

        self.add_item(button)
            

        
    
