
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
    
    def as_select_option(self):
        return discord.SelectOption(label=self.label, emoji=self.emoji, value=f"{self.command}{self.label}")

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
        try:
            await (self.get_command_callback(interaction.client.tree))(cog, interaction, *self.parameters)
        except TypeError:
            await (self.get_command_callback(interaction.client.tree))(interaction, *self.parameters)

class CommandSelect(discord.ui.Select):
    def __init__(self, cog, commands : list[Command], placeholder : str = "Select an option...", row : int = 1):
        self.cog = cog
        self.commands = commands 

        super().__init__(options=[c.as_select_option() for c in commands], placeholder=placeholder, row=row)
    
    async def callback(self, interaction : discord.Interaction):
        for command in self.commands:
            if self.values[0] == f"{command.command}{command.label}":
                await command.execute(self.cog, interaction)


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
            

        
    
