
import discord 

import setup as s
from funcs import autocompletes, commands_view, graphs, paginator

from discord import app_commands
from discord.ext import commands

import client

class Get(commands.GroupCog, name="get", description="All get commands"):

    def __init__(self, bot : commands.Bot, client : client.Client):
        self.bot = bot
        self.client = client

        super().__init__()
    
    @app_commands.command(name="player", description="Get information about a player")
    @app_commands.autocomplete(player_name=autocompletes.player_autocomplete)
    async def _player(self, interaction : discord.Interaction, player_name : str):

        player = self.client.world.get_player(player_name, True)
        if not player:
            raise client.errors.MildError("Player not found")
        activity = await player.activity 

        town = player.town 
        likely_residency = await player.likely_residency
        visited_towns_total = await player.total_visited_towns
        dc = await player.discord

        health = "<:heartfull:1152274373923844196>"*int(player.health//2) + "<:hearthalf:1152274386364145715>"*int(player.health%2) + "<:heartnone:1152275125199179867>"*int((20-player.health)//2)
        armor = "<:armorfull:1152274423898976289>"*int(player.armor//2) + "<:armorhalf:1152274436179898430>"*int(player.armor%2) + "<:armornone:1152274447445790730>"*int((20-player.armor)//2)
        online = f"🟢  {discord.utils.escape_markdown(player.name)} is **online**" if player.online else f"🔴 {discord.utils.escape_markdown(player.name)} is **offline**"

        embed = discord.Embed(title=f"Player: {discord.utils.escape_markdown(player.name)}", description=f"{online}\n\n{health}\n{armor}", color=s.embed)
        
        embed.add_field(name="Location", value=f"[{int(player.location.x)}, {int(player.location.y)}, {int(player.location.z)}]({self.client.url}?x={int(player.location.x)}&z={int(player.location.z)}&zoom={s.map_link_zoom})")
        embed.add_field(name="Town", value=f"{town.name} {'('+str(town.nation)+')' if town.nation else ''}" if town else "None")
        embed.add_field(name="Likely Residency", value=f"{likely_residency.name} {'('+str(likely_residency.nation)+')' if likely_residency.nation and likely_residency != town else ''}" if likely_residency else "None")
        embed.add_field(name="Activity", value=str(activity))
        embed.add_field(name="Visited Towns", value=f"{visited_towns_total} ({(visited_towns_total/len(self.client.world.towns))*100:.1f}%)")
        embed.add_field(name="Likely Discord", value=str(dc.mention if dc else "Unknown"))

        embed.set_footer(text=f"Bot has been tracking for {(await self.client.world.total_tracked).str_no_timestamp()}")
        
        embed.set_thumbnail(url=player.avatar_url)

        c_view = commands_view.CommandsView(self)
        if town:
            c_view.add_command(commands_view.Command("get town", "Town Info", (town.name,), button_style=discord.ButtonStyle.primary, emoji="ℹ️"))
        c_view.add_command(commands_view.Command("history player activity", "Activity History", (player.name,), button_style=discord.ButtonStyle.secondary, emoji="⏳"))
        if visited_towns_total > 1:
            c_view.add_command(commands_view.Command("history player visited_towns", "Visited Towns", (player.name,), button_style=discord.ButtonStyle.secondary, emoji="📖"))

        return await interaction.response.send_message(embed=embed, view=c_view)

    @app_commands.command(name="town", description="Get information about a town")
    @app_commands.autocomplete(town_name=autocompletes.town_autocomplete)
    async def _town(self, interaction : discord.Interaction, town_name : str):
        
        town = self.client.world.get_town(town_name, True)

        if not town:
            raise client.errors.MildError("Couldn't find town")
        
        borders = town.borders

        graph = discord.File(graphs.plot_towns([town], outposts=False, dimmed_towns=borders), filename="graph.png")

        embed = discord.Embed(title=f"Town: {town.name_formatted}", color=s.embed)
        embed.set_thumbnail(url="attachment://graph.png")

        embed.add_field(name="Nation", value=town.nation.name_formatted if town.nation else "None")
        embed.add_field(name="Daily Tax", value=f"{town.resident_tax:.1f}%")
        embed.add_field(name="Bank", value=f"${town.bank:,.2f}")
        embed.add_field(name="Mayor", value=discord.utils.escape_markdown(str(town.mayor)))
        embed.add_field(name="Spawnblock", value=f"[{int(town.spawn.x)}, {int(town.spawn.z)}]({self.client.url}?x={int(town.spawn.x)}&z={int(town.spawn.z)}&zoom={s.map_link_zoom})")
        embed.add_field(name="Total Residents", value=f"{town.resident_count:,}")
        embed.add_field(name="Founded", value=str(town.founded_date))
        embed.add_field(name="Area", value=f"{town.area:,} plots")
        embed.add_field(name="Activity", value=str(await town.activity))
        embed.add_field(name="Public", value="Yes" if town.public else "No")
        embed.add_field(name=f"Borders ({len(borders)})", value="`" + ("`, `".join(t.name for t in borders) + "`") if len(borders) > 0 else "None", inline=False) 
        #embed.add_field(name="Peaceful", value="Yes" if town.peaceful else "No")

        embed.set_footer(text=f"Bot has been tracking for {(await self.client.world.total_tracked).str_no_timestamp()}")

        c_view = commands_view.CommandsView(self)

        if type(town.mayor) != str:
            c_view.add_command(commands_view.Command("get player", "Mayor Info", (town.mayor.name,), button_style=discord.ButtonStyle.primary, emoji="👑"))
        if town.nation:
            c_view.add_command(commands_view.Command("get nation", "Nation Info", (town.nation.name,), button_style=discord.ButtonStyle.primary, emoji="🗾"))
        c_view.add_command(commands_view.Command("history town visited_players", "Visited Players", (town.name,), button_style=discord.ButtonStyle.secondary, emoji="📖"))
        
        button = discord.ui.Button(label="View Outposts", emoji="🗺️", row=1)
        def outposts_button(town : client.object.Town, view : discord.ui.View, borders):
            async def outposts_button_callback(interaction : discord.Interaction):
                for item in view.children:
                    if item.label == "View Outposts":
                        item.disabled = True 
                
                graph = discord.File(graphs.plot_towns([town], outposts=True, dimmed_towns=borders), filename="graph_outposts.png")

                interaction.message.embeds[0].set_thumbnail(url=None)
                interaction.message.embeds[0].set_image(url="attachment://graph_outposts.png")
                
                await interaction.response.edit_message(view=view, attachments=[graph], embed=interaction.message.embeds[0])
            return outposts_button_callback
        button.callback = outposts_button(town, c_view, borders)
        if len(town.raw_locs) > 1:
            c_view.add_item(button)

        return await interaction.response.send_message(embed=embed, file=graph, view=c_view)
    
    @app_commands.command(name="nation", description="Get information about a nation")
    @app_commands.autocomplete(nation_name=autocompletes.nation_autocomplete)
    async def _nation(self, interaction : discord.Interaction, nation_name : str):
        
        nation = self.client.world.get_nation(nation_name, True)

        if not nation:
            raise client.errors.MildError("Couldn't find nation")

        towns = nation.towns
        capital = nation.capital
        leader = capital.mayor
        flags = await nation.flags
        
        borders = nation.borders

        towns.remove(capital)

        embed = discord.Embed(title=f"Nation: {nation.name_formatted}", description=f"[Visit on map]({self.client.url}?x={int(nation.capital.spawn.x)}&z={int(nation.capital.spawn.z)}&zoom={s.map_link_zoom})", color=s.embed)
        embed.set_thumbnail(url=self.client.url + "/" + nation.capital.flag_url)
        
        embed.add_field(name="Leader", value=discord.utils.escape_markdown(str(leader)))
        embed.add_field(name="Capital", value=str(capital))
        embed.add_field(name="Residents", value=f"{nation.total_residents:,}")
        embed.add_field(name="Town Value", value=f"${nation.total_value:,.2f}")
        embed.add_field(name="Area", value=f"{nation.total_area:,} plots")
        embed.add_field(name="Population Density", value=f"{int(nation.total_area/nation.total_residents):,} plots/resident")
        embed.add_field(name=f"Borders ({len(borders[0])})", value="`" + ("`, `".join(n.name for n in borders[0]) + "`") if len(borders[1]) > 0 else "None", inline=False) 
        embed.add_field(name=f"Towns ({len(towns)+1})", value="`" + ("`, `".join(t.name_formatted for t in [capital]+towns)) + "`", inline=False)
        embed.add_field(name="Discord", value=flags.get("discord") or "None set.")

        c_view = commands_view.CommandsView(self)
        if type(leader) != str:
            c_view.add_command(commands_view.Command("get player", "Leader Info", (leader.name,), button_style=discord.ButtonStyle.primary, emoji="👑", row=1))
        c_view.add_command(commands_view.Command("history nation residents", "Resident History", (nation.name,), emoji="🧑", row=1))
        c_view.add_command(commands_view.Command("history nation towns", "Town History", (nation.name,), emoji="🗾", row=1))

        if len(towns) > 1:
            c_view.add_command(commands_view.Command("distribution nation residents", "Resident distribution", (nation.name,), emoji="🧑", row=2))
            c_view.add_command(commands_view.Command("distribution nation town_bank", "Balance distr.", (nation.name,), emoji="💵", row=2))
            c_view.add_command(commands_view.Command("distribution nation area", "Area distr.", (nation.name,), emoji="🗾", row=2))

        cmds = []
        for i, town in enumerate([capital]+towns):
            if i >= 25: break 
            cmds.append(commands_view.Command("get town", town.name, (town.name,), emoji=None))
        c_view.add_item(commands_view.CommandSelect(self, cmds, "Get Town Info...", 3))

        if len(towns) > 3:
            embed.set_image(url="attachment://map_waiting.jpg")

            await interaction.response.send_message(embed=embed, view=c_view, file=discord.File("map_waiting.jpg"))
        
        graph = discord.File(graphs.plot_towns([capital]+towns, plot_spawn=False, dimmed_towns=borders[1]), filename="graph.png")
        embed.set_image(url="attachment://graph.png")
        
        if len(towns) > 3:
            await interaction.edit_original_response(attachments=[graph], embed=embed)
        else:
            await interaction.response.send_message(embed=embed, view=c_view, file=graph)
        
    @app_commands.command(name="culture", description="Get information about a culture")
    @app_commands.autocomplete(culture_name=autocompletes.culture_autocomplete)
    async def _culture(self, interaction : discord.Interaction, culture_name : str):
        
        culture = self.client.world.get_culture(culture_name, True)
        towns = culture.towns

        if not culture:
            raise client.errors.MildError("Couldn't find culture")

        embed = discord.Embed(title=f"Culture: {culture.name}", color=s.embed)
        
        embed.add_field(name="Residents", value=f"{culture.total_residents:,}")
        embed.add_field(name="Area", value=f"{culture.total_area:,} plots")
        embed.add_field(name="Town Value", value=f"${culture.total_value:,.2f}")
        embed.add_field(name="Population Density", value=f"{int(culture.total_area/culture.total_residents):,} plots/resident")
        embed.add_field(name=f"Towns ({len(towns)+1})", value="`" + ("`, `".join(t.name_formatted for t in towns)) + "`", inline=False)

        c_view = commands_view.CommandsView(self)

        cmds = []
        for i, town in enumerate(towns):
            if i >= 25: break 
            cmds.append(commands_view.Command("get town", town.name, (town.name,), emoji=None))
        c_view.add_item(commands_view.CommandSelect(self, cmds, "Get Town Info...", 3))

        if len(towns) > 3:
            embed.set_image(url="attachment://map_waiting.jpg")

            await interaction.response.send_message(embed=embed, view=c_view, file=discord.File("map_waiting.jpg"))
        
        graph = discord.File(graphs.plot_towns(towns, plot_spawn=False), filename="graph.png")
        embed.set_image(url="attachment://graph.png")
        
        if len(towns) > 3:
            await interaction.edit_original_response(attachments=[graph], embed=embed)
        else:
            await interaction.response.send_message(embed=embed, view=c_view, file=graph)
    
    @app_commands.command(name="religion", description="Get information about a religion")
    @app_commands.autocomplete(religion_name=autocompletes.religion_autocomplete)
    async def _religion(self, interaction : discord.Interaction, religion_name : str):
        
        religion = self.client.world.get_religion(religion_name, True)
        towns = religion.towns

        if not religion:
            raise client.errors.MildError("Couldn't find religion")

        embed = discord.Embed(title=f"Religion: {religion.name}", color=s.embed)
        
        embed.add_field(name="Followers", value=f"{religion.total_residents:,}")
        embed.add_field(name="Area", value=f"{religion.total_area:,} plots")
        embed.add_field(name="Town Value", value=f"${religion.total_value:,.2f}")
        embed.add_field(name="Population Density", value=f"{int(religion.total_area/religion.total_residents):,} plots/resident")
        embed.add_field(name=f"Towns ({len(towns)+1})", value="`" + ("`, `".join(t.name_formatted for t in towns)) + "`", inline=False)

        c_view = commands_view.CommandsView(self)

        cmds = []
        for i, town in enumerate(towns):
            if i >= 25: break 
            cmds.append(commands_view.Command("get town", town.name, (town.name,), emoji=None))
        c_view.add_item(commands_view.CommandSelect(self, cmds, "Get Town Info...", 3))

        if len(towns) > 3:
            embed.set_image(url="attachment://map_waiting.jpg")

            await interaction.response.send_message(embed=embed, view=c_view, file=discord.File("map_waiting.jpg"))
        
        graph = discord.File(graphs.plot_towns(towns, plot_spawn=False), filename="graph.png")
        embed.set_image(url="attachment://graph.png")
        
        if len(towns) > 3:
            await interaction.edit_original_response(attachments=[graph], embed=embed)
        else:
            await interaction.response.send_message(embed=embed, view=c_view, file=graph)
    
    @app_commands.command(name="world", description="Get information about the world as a whole")
    async def _world(self, interaction : discord.Interaction):
        
        world = self.client.world
        towns = world.towns

        embed = discord.Embed(title="RulerCraft Earth", description=f"[View Map]({self.client.url})", color=s.embed)
        
        embed.add_field(name="Towns", value=str(len(world.towns)))
        embed.add_field(name="Nations", value=str(len(world.nations)))
        embed.add_field(name="Cultures", value=str(len(world.cultures)))
        embed.add_field(name="Religions", value=str(len(world.religions)))
        embed.add_field(name="Town Value", value=f"${world.total_value:,.2f}")
        embed.add_field(name="Claimed Area", value=f"{world.total_area:,} plots")
        embed.add_field(name="Total Residents", value=f"{world.total_residents:,} ({len(world.players):,} known)")

        embed.set_footer(text=f"Bot has been tracking for {(await world.total_tracked).str_no_timestamp()}")

        cache_id = f"{len(world.towns)}+{len(world.nations)}"
        im = graphs.check_cache(cache_name="Earth", cache_id=cache_id)
        files=[]
        if im:
            files.append(discord.File(im, "graph.png"))
            embed.set_image(url="attachment://graph.png")
        else:
            files.append(discord.File("map_waiting.jpg"))
            embed.set_image(url="attachment://map_waiting.jpg")

        await interaction.response.send_message(embed=embed, files=files)

        if not im:
            graph = discord.File(graphs.plot_towns(towns, plot_spawn=False, whole=True, cache_name="Earth", cache_id=cache_id, cache_checked=im), filename="graph.png")
            embed.set_image(url="attachment://graph.png")

            await interaction.edit_original_response(embed=embed, attachments=[graph])

    @app_commands.command(name="online", description="List online players")
    async def _online(self, interaction : discord.Interaction):
        
        online_players = self.client.world.online_players
        log = ""
        for player in online_players:
            today = await player.get_activity_today()
            log = f"**{discord.utils.escape_markdown(player.name)}**: [{int(player.location.x)}, {int(player.location.y)}, {int(player.location.z)}]({self.client.url}?x={int(player.location.x)}&z={int(player.location.z)}&zoom={s.map_link_zoom}) ({client.object.generate_time(today.total)} today)\n" + log

        embed = discord.Embed(title=f"Online players ({len(online_players)})", color=s.embed)
        embed.set_image(url="attachment://map_waiting.jpg")

        view = paginator.PaginatorView(embed, log)

        im = graphs.check_cache(cache_name="Earth", cache_id=f"{len(self.client.world.towns)}+{len(self.client.world.nations)}")
        
        await interaction.response.send_message(embed=embed, view=view, file=discord.File("map_waiting.jpg"))

        graph = discord.File(graphs.plot_towns(self.client.world.towns, players=self.client.world.players, plot_spawn=False, whole=True, cache_checked=im, cache_name="Earth", cache_id=f"{len(self.client.world.towns)}+{len(self.client.world.nations)}"), filename="graph.png")
        embed.set_image(url="attachment://graph.png")

        await interaction.edit_original_response(attachments=[graph], embed=embed)


async def setup(bot : commands.Bot):
    await bot.add_cog(Get(bot, bot.client))
