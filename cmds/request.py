
import discord 

from discord import app_commands
from discord.ext import commands

import client

import setup as s

from funcs import autocompletes

class AcceptView(discord.ui.View):

    def __init__(self, client : client.Client, flag_name : str, flag_value, object : client.objects.Object):

        self.client = client

        self.flag_name = flag_name 
        self.flag_value = flag_value 
        self.object = object
        super().__init__()

        self.timeout = None
    
    @discord.ui.button(style=discord.ButtonStyle.green, label="Accept")
    async def _accept_button(self, interaction : discord.Interaction, button : discord.ui.Button):

        if interaction.user.id not in s.mods:
            raise client.errors.MildError("You are not a Bot Moderator!")
        
        await self.object.set_flag(self.flag_name, self.flag_value)

        if self.flag_name == "discord" and type(self.object) == client.objects.Player:
            try:
                await self.client.bot.get_user(int(self.flag_value)).send(f"Your request has been accepted! You are now linked to {self.object.name}")
            except:
                await self.client.bot.get_channel(s.alert_channel).send(f"Couldn't dm <@{self.flag_value}>. They are now linked to {self.object.name}")
            
        button.disabled = True
            
        await interaction.response.edit_message(content=f"Accepted request! **{self.object.name}**'s {self.flag_name} is now **{self.flag_value}**", view=self)



class Request(commands.GroupCog, name="request", description="Request something from the Bot Moderators"):

    def __init__(self, bot : commands.Bot, client : client.Client):
        self.bot = bot
        self.client = client
    
    @app_commands.command(name="link_discord", description="Link your discord to your minecraft officially. Allows you to run certain commands easier")
    @app_commands.autocomplete(minecraft_name=autocompletes.player_autocomplete)
    async def _link_discord(self, interaction : discord.Interaction, minecraft_name : str):

        player = self.client.world.get_player(minecraft_name, True)
        if not player:
            raise client.errors.MildError("Player not found! They have to have joined the server recently to be added.")
        
        channel : discord.TextChannel = self.client.bot.get_channel(s.request_channel)

        view = AcceptView(self.client, "discord", interaction.user.id, player)

        await channel.send(
            f"/mod set_flag object_type:player object_name:{player.name} flag_name:discord flag_value:{interaction.user.id}",
            embed=discord.Embed(
                title="Discord Account link request", 
                description=f"{interaction.user.mention} has requested for their account to be linked to **{minecraft_name}**.",
                color=s.embed
            ),
            view=view
        )

        await interaction.response.send_message(f"Request sent! Please wait for it to be reviewed... You'll get a DM if approved")
    
    @app_commands.command(name="update_nickname", description="Update your nickname to retain history")
    @app_commands.autocomplete(new_minecraft_name=autocompletes.player_autocomplete, old_minecraft_name=autocompletes.offline_players_autocomplete)
    async def _update_nickname(self, interaction : discord.Interaction, old_minecraft_name : str, new_minecraft_name : str):

        player = self.client.world.get_player(new_minecraft_name, True)
        if not player:
            raise client.errors.MildError("New player not found! You may need to join the server on the new username.")
        
        channel : discord.TextChannel = self.client.bot.get_channel(s.request_channel)

        await channel.send(
            f"/mod update object_type:player old_object_name:{old_minecraft_name} new_object_name:{player.name} discord_id:{interaction.user.id}",
            embed=discord.Embed(
                title="IGN update request", 
                description=f"{interaction.user.mention} has requested for their old IGN **{old_minecraft_name}** to be updated into **{player.name}**.",
                color=s.embed
            )
        )

        await interaction.response.send_message(f"Request sent! Please wait for it to be reviewed... You'll get a DM if approved")
    
    @app_commands.command(name="update_town_name", description="Update a town name to retain history")
    @app_commands.autocomplete(new_town_name=autocompletes.town_autocomplete, old_town_name=autocompletes.deleted_towns_autocomplete)
    async def _update_town_name(self, interaction : discord.Interaction, old_town_name : str, new_town_name : str):

        town = self.client.world.get_town(new_town_name, True)
        if not town:
            raise client.errors.MildError("New town not found.")
        
        channel : discord.TextChannel = self.client.bot.get_channel(s.request_channel)

        await channel.send(
            f"/mod update object_type:town old_object_name:{old_town_name} new_object_name:{town.name} discord_id:{interaction.user.id}",
            embed=discord.Embed(
                title="Town name update request", 
                description=f"{interaction.user.mention} has requested for old town named **{old_town_name}** to be updated into **{town.name}**.",
                color=s.embed
            )
        )

        await interaction.response.send_message(f"Request sent! Please wait for it to be reviewed... You'll get a DM if approved")
    
    @app_commands.command(name="update_nation_name", description="Update a nation name to retain history")
    @app_commands.autocomplete(new_nation_name=autocompletes.nation_autocomplete, old_nation_name=autocompletes.deleted_nations_autocomplete)
    async def _update_nation_name(self, interaction : discord.Interaction, old_nation_name : str, new_nation_name : str):

        nation = self.client.world.get_nation(new_nation_name, True)
        if not nation:
            raise client.errors.MildError("New nation not found.")
        
        channel : discord.TextChannel = self.client.bot.get_channel(s.request_channel)

        await channel.send(
            f"/mod update object_type:nation old_object_name:{old_nation_name} new_object_name:{nation.name} discord_id:{interaction.user.id}",
            embed=discord.Embed(
                title="Nation name update request", 
                description=f"{interaction.user.mention} has requested for old nation named **{old_nation_name}** to be updated into **{nation.name}**.",
                color=s.embed
            )
        )

        await interaction.response.send_message(f"Request sent! Please wait for it to be reviewed... You'll get a DM if approved")
    
# Fix None for likely_residency
# Make view respond

class Mod(commands.Cog):

    def __init__(self, bot : commands.Bot, client : client.Client):
        self.bot = bot
        self.client = client
    
    mod = app_commands.Group(name="mod", description="Moderator action commands. Guild only.", default_permissions=discord.Permissions(administrator=True), guild_ids=[s.mod_guild.id])

    flags = []
    for f_l in s.flags.values():
        for f in f_l:
            flags.append(f)

    @app_commands.default_permissions(administrator=True)
    @mod.command(name="set_flag", description="Set the likely residency for a user.")
    @app_commands.choices(object_type=[app_commands.Choice(name=c, value=c) for c in s.flags], flag_name=[app_commands.Choice(name=c, value=c) for c in flags])
    async def _set_flag(self, interaction : discord.Interaction, object_type : str, object_name : str, flag_name : str, flag_value : str = None):

        if interaction.user.id not in s.mods:
            raise client.errors.MildError("You are not a Bot Moderator!")
        
        if object_type == "player":
            obj = self.client.world.get_player(object_name)
        elif object_type == "town":
            obj = self.client.world.get_town(object_name)
        elif object_type == "nation":
            obj = self.client.world.get_nation(object_name)

        if not obj:
            raise client.errors.MildError(f"{object_type.title()} not found")

        await obj.set_flag(flag_name, flag_value)
        
        await interaction.response.send_message(
            embed=discord.Embed(
                title=f"Successfully flag for the {object_type}",
                description=f"Successfully set {flag_name} flag for **{object_name}** to **{flag_value}**.",
                color=s.embedSuccess
            )
        )

        if flag_name == "discord" and object_type == "player":
            try:
                await self.client.bot.get_user(int(flag_value)).send(f"Your request has been accepted! You are now linked to {object_name}")
            except:
                await self.client.bot.get_channel(s.alert_channel).send(f"Couldn't dm <@{flag_value}>. They are now linked to {object_name}")
    
    @app_commands.default_permissions(administrator=True)
    @mod.command(name="update", description="Update an old object into a new one")
    @app_commands.choices(object_type=[app_commands.Choice(name="player", value="player"), app_commands.Choice(name="town", value="town"), app_commands.Choice(name="nation", value="nation")])
    async def _update(self, interaction : discord.Interaction, object_type : str, old_object_name : str, new_object_name : str, discord_id : str = None):

        if interaction.user.id not in s.mods:
            raise client.errors.MildError("You are not a Bot Moderator!")
        
        await self.client.merge_objects(object_type, old_object_name, new_object_name)


        await interaction.response.send_message(
            embed=discord.Embed(
                title=f"Successfully updated",
                description=f"Successfully updated old {object_type} name from {old_object_name} into {new_object_name}.",
                color=s.embedSuccess
            )
        )

        if discord_id:
            try:
                await self.client.bot.get_user(int(discord_id)).send(f"Your request has been accepted! The old {object_type} named {old_object_name} has been updated into {new_object_name}")
            except:
                await self.client.bot.get_channel(s.alert_channel).send(f"Couldn't dm <@{discord_id}>. The old {object_type} named {old_object_name} has been updated into {new_object_name}")

class Set(commands.GroupCog, name="set", description="Set stuff"):

    def __init__(self, bot : commands.Bot, client : client.Client):
        self.bot = bot
        self.client = client

        super().__init__()
    
    @app_commands.command(name="nation_discord_invite", description="Set nation invite link")
    @app_commands.autocomplete(nation_name=autocompletes.nation_autocomplete)
    async def _nation_discord_invite(self, interaction : discord.Interaction, nation_name : str, invite_link : str):

        nation = self.client.world.get_nation(nation_name, True)

        if not nation:
            raise client.errors.MildError("Couldn't find nation")
        
        found = False
        for player in self.client.world.players:
            flags = await player.flags
            if flags.get("discord") == str(interaction.user.id):
                if player != nation.capital.mayor:
                    raise client.errors.MildError("You are not in-game leader of this nation")
                else:
                    found = True 
        if not found:
            raise client.errors.MildError("You must link your discord manually to run this command. Do so with **/request link_discord**")
            
        
        await nation.set_flag("server", invite_link)

        embed = discord.Embed(title="Successfully set discord invite", description=f"Set discord invite link for **{nation.name_formatted}** to **{invite_link}**", color=s.embedSuccess)
        
        await interaction.response.send_message(embed=embed)

async def setup(bot : commands.Bot):
    await bot.add_cog(Request(bot, bot.client))
    await bot.add_cog(Mod(bot, bot.client), guild=s.mod_guild)
    await bot.add_cog(Set(bot, bot.client))





