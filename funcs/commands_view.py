
import discord 
from discord import app_commands 

import typing

from client import Client

def get_command_callback(tree : app_commands.CommandTree, cmd) -> typing.Coroutine:
    if type(cmd) != str:
        return cmd 
    
    command = None 
    
    for item in cmd.split(" "):
        if not command:
            command = tree.get_command(item)
        else:
            command = command.get_command(item)
            
    return command.callback

async def execute_callback_with_interaction(callback, cog, interaction : discord.Interaction, parameters):
    try:
        await callback(cog, interaction, *parameters)
    except (TypeError, AttributeError) as e :
        try:
            await callback(interaction, *parameters)
        except Exception as e:
            await interaction.client.tree.on_error(interaction, e)

class Command():
    def __init__(self, command : typing.Union[str, typing.Coroutine], label : str, parameters : tuple, button_style : discord.ButtonStyle = discord.ButtonStyle.secondary, emoji : str = "💬", row=1):
        self.command = command 
        self.label = label 
        self.parameters = parameters 
        self.button_style = button_style
        self.row = row
        self.emoji = emoji

        self.custom_id = f"command_{command}+{'_&_'.join(parameters)}"
    
    def as_select_option(self):
        return discord.SelectOption(label=self.label, emoji=self.emoji, value=self.custom_id)
    
    async def execute(self, cog, interaction : discord.Interaction):
        await execute_callback_with_interaction(get_command_callback(cog.bot.tree, self.command), cog, interaction, self.parameters)

class CommandButton(discord.ui.Button):
    def __init__(self, cog, command : Command):
        self.cog = cog 
        self.command = command 

        super().__init__(style=command.button_style, label=command.label, emoji=command.emoji, row=command.row, custom_id=self.command.custom_id)

class CommandSelect(discord.ui.Select):
    def __init__(self, cog, commands : list[Command], placeholder : str = "Select an option...", row : int = 1):
        self.cog = cog
        self.commands = commands 

        super().__init__(options=[c.as_select_option() for c in commands], placeholder=placeholder, row=row)

class CommandsView(discord.ui.View):

    def __init__(self, cog, commands : typing.List[Command] = []):
        super().__init__(timeout=3600)
        self.cog = cog

        for command in commands:
            self.add_command(command)
    
    def add_command(self, command : Command):
        button = discord.ui.Button(style=command.button_style, label=command.label, emoji=command.emoji, row=command.row, custom_id=command.custom_id)

        self.add_item(button)

class RefreshButton(discord.ui.Button):
    def __init__(self, client : Client, command_name : str, command_params : tuple, row : int = 1):
        self._custom_id = f"refresh_{command_name}+{'_&_'.join(command_params)}"
        super().__init__(emoji="🔃", row=row, custom_id=self._custom_id)

        self.client = client 
