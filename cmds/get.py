
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
        notable_statistics = client.funcs.top_rankings_to_text(await player.top_rankings, player.name)

        health = "<:heartfull:1152274373923844196>"*int(player.health//2) + "<:hearthalf:1152274386364145715>"*int(player.health%2) + "<:heartnone:1152275125199179867>"*int((20-player.health)//2)
        armor = "<:armorfull:1152274423898976289>"*int(player.armor//2) + "<:armorhalf:1152274436179898430>"*int(player.armor%2) + "<:armornone:1152274447445790730>"*int((20-player.armor)//2)
        online = f"🟢  {discord.utils.escape_markdown(player.name)} is **online**" if player.online else f"🔴 {discord.utils.escape_markdown(player.name)} is **offline**"

        embed = discord.Embed(title=f"Player: {discord.utils.escape_markdown(player.name)}", description=f"{online}\n\n{health}\n{armor}", color=s.embed)
        
        embed.add_field(name="Location", value=f"[{int(player.location.x)}, {int(player.location.y)}, {int(player.location.z)}]({self.client.url}?x={int(player.location.x)}&z={int(player.location.z)}&zoom={s.map_link_zoom})")
        embed.add_field(name="Town", value=f"{town.name_formatted} {'('+str(town.nation.name_formatted)+')' if town.nation else ''}" if town else "None")
        embed.add_field(name="Likely Residency", value=f"{likely_residency.name_formatted} {'('+likely_residency.nation.name_formatted+')' if likely_residency.nation and likely_residency != town else ''}" if likely_residency else "None")
        embed.add_field(name="Activity", value=str(activity))
        embed.add_field(name="Visited Towns", value=f"{visited_towns_total} ({(visited_towns_total/len(self.client.world.towns))*100:.1f}%)")
        embed.add_field(name="Likely Discord", value=str(dc.mention if dc else "Unknown"))
        embed.add_field(name="Donator?", value="Yes" if player.donator == True else "Unlikely" if player.donator == False else "Unknown")
        embed.add_field(name="Notable Statistics", value=notable_statistics, inline=False)

        embed.set_footer(text=f"Bot has been tracking for {(await self.client.world.total_tracked).str_no_timestamp()}")
        
        embed.set_thumbnail(url=await player.face_url)

        c_view = commands_view.CommandsView(self)
        if town:
            c_view.add_command(commands_view.Command("get town", "Town Info", (town.name,), button_style=discord.ButtonStyle.primary, emoji="ℹ️"))
        if likely_residency and likely_residency != town:
            c_view.add_command(commands_view.Command("get town", "Likely Residency Info", (likely_residency.name,), button_style=discord.ButtonStyle.primary, emoji="ℹ️"))
        c_view.add_command(commands_view.Command("history player activity", "Activity History", (player.name,), button_style=discord.ButtonStyle.secondary, emoji="⏳"))
        if visited_towns_total > 0:
            c_view.add_command(commands_view.Command("history player visited_towns", "Visited Towns", (player.name,), button_style=discord.ButtonStyle.secondary, emoji="📖"))

        return await interaction.response.send_message(embed=embed, view=c_view)

    @app_commands.command(name="town", description="Get information about a town")
    @app_commands.autocomplete(town_name=autocompletes.town_autocomplete)
    async def _town(self, interaction : discord.Interaction, town_name : str):
        
        town = self.client.world.get_town(town_name, True)

        if not town:
            raise client.errors.MildError("Couldn't find town")
        
        borders = town.borders
        area = town.area

        notable_rankings_str = client.funcs.top_rankings_to_text(await town.top_rankings, town.name_formatted)
        notable_statistics = town.notable_statistics
        notable_statistics_str = "- " + "\n- ".join(notable_statistics) if len(notable_statistics) > 0 else ""

        embed = discord.Embed(title=f"Town: {town.name_formatted}", description=town.geography_description, color=s.embed)
        embed.set_thumbnail(url="attachment://graph.png")

        embed.add_field(name="Nation", value=town.nation.name_formatted if town.nation else "None")
        embed.add_field(name="Culture", value=str(town.culture))
        embed.add_field(name="Religion", value=str(town.religion))
        embed.add_field(name="Daily Tax", value=str(town.resident_tax))
        embed.add_field(name="Bank", value=f"${town.bank:,.2f}")
        embed.add_field(name="Mayor", value=discord.utils.escape_markdown(str(town.mayor)))
        embed.add_field(name="Spawnblock", value=f"[{int(town.spawn.x)}, {int(town.spawn.z)}]({self.client.url}?x={int(town.spawn.x)}&z={int(town.spawn.z)}&zoom={s.map_link_zoom})")
        embed.add_field(name="Total Residents", value=f"{town.resident_count:,}")
        embed.add_field(name="Founded", value=town.founded_date.strftime('%b %d %Y'))
        embed.add_field(name="Area", value=f"{area:,} plots ({area * 64:,}km²)")
        embed.add_field(name="Activity", value=str(await town.activity))
        embed.add_field(name="Public", value="Yes" if town.public else "No")
        embed.add_field(name=f"Borders ({len(borders)})", value="`" + ("`, `".join(t.name_formatted for t in borders) + "`") if len(borders) > 0 else "None", inline=False) 
        #embed.add_field(name="Peaceful", value="Yes" if town.peaceful else "No")
        embed.add_field(name="Notable Statistics", value=notable_statistics_str + notable_rankings_str, inline=False)

        embed.set_footer(text=f"Bot has been tracking for {(await self.client.world.total_tracked).str_no_timestamp()}")

        c_view = commands_view.CommandsView(self)

        if type(town.mayor) != str:
            c_view.add_command(commands_view.Command("get player", "Mayor Info", (town.mayor.name,), button_style=discord.ButtonStyle.primary, emoji="👑"))
        if town.nation:
            c_view.add_command(commands_view.Command("get nation", "Nation Info", (town.nation.name,), button_style=discord.ButtonStyle.primary, emoji="🗾"))
        if town.culture:
            c_view.add_command(commands_view.Command("get culture", "Culture Info", (town.culture.name,), button_style=discord.ButtonStyle.primary, emoji="📔"))
        if town.religion:
            c_view.add_command(commands_view.Command("get religion", "Religion Info", (town.religion.name,), button_style=discord.ButtonStyle.primary, emoji="🙏"))
        
        
        button = discord.ui.Button(label="Expand Outposts", emoji="🗺️", row=2, style=discord.ButtonStyle.primary)
        def outposts_button(town : client.object.Town, view : discord.ui.View, borders):
            async def outposts_button_callback(interaction : discord.Interaction):
                for item in view.children:
                    if item.label == "Expand Outposts":
                        item.disabled = True 
                
                graph = discord.File(graphs.plot_towns([town], outposts=True, dimmed_towns=borders), filename="graph_outposts.png")

                interaction.message.embeds[0].set_thumbnail(url=None)
                interaction.message.embeds[0].set_image(url="attachment://graph_outposts.png")
                
                await interaction.response.edit_message(view=view, attachments=[graph], embed=interaction.message.embeds[0])
            return outposts_button_callback
        button.callback = outposts_button(town, c_view, borders)
        if len(town.raw_locs) > 1:
            c_view.add_item(button)
        c_view.add_command(commands_view.Command("history town visited_players", "Visited Players", (town.name,), button_style=discord.ButtonStyle.secondary, emoji="📖", row=2))
        c_view.add_command(commands_view.Command("history town bank", "Bank History", (town.name,), button_style=discord.ButtonStyle.secondary, emoji="💵", row=2))
        c_view.add_command(commands_view.Command("history town residents", "Resident History", (town.name,), button_style=discord.ButtonStyle.secondary, emoji="👤", row=2))
        
        cache_name = f"Town+{town.name}"
        cache_id = town.vertex_count
        
        graph = discord.File(graphs.plot_towns([town], outposts="retain", dimmed_towns=borders, show_earth=False, cache_name=cache_name, cache_id=cache_id), filename="graph.png")

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
        total_residents = nation.total_residents
        area = nation.total_area
        
        borders = nation.borders

        towns.remove(capital)

        notable_rankings_str = client.funcs.top_rankings_to_text(await nation.top_rankings, nation.name_formatted)
        notable_statistics = nation.notable_statistics
        notable_statistics_str = "- " + "\n- ".join(notable_statistics) if len(notable_statistics) > 0 else ""

        religion_make_up = nation.religion_make_up
        culture_make_up = nation.culture_make_up

        embed = discord.Embed(title=f"Nation: {nation.name_formatted}", description=f"[Visit on map]({self.client.url}?x={int(nation.capital.spawn.x)}&z={int(nation.capital.spawn.z)}&zoom={s.map_link_zoom})", color=s.embed)
        embed.set_thumbnail(url=self.client.url + "/" + nation.capital.flag_url)
        
        embed.add_field(name="Leader", value=discord.utils.escape_markdown(str(leader)))
        embed.add_field(name="Capital", value=str(capital))
        embed.add_field(name="Residents", value=f"{total_residents:,}")
        embed.add_field(name="Town Value", value=f"${nation.total_value:,.2f}")
        embed.add_field(name="Area", value=f"{area:,} plots ({area*64:,}km²)")
        embed.add_field(name="Population Density", value=f"{int(nation.total_area/total_residents):,} plots/resident")
        embed.add_field(name="Activity", value=str(await nation.activity))
        embed.add_field(name="Discord", value=flags.get("server") or "None set.")
        embed.add_field(name=f"Borders ({len(borders[0])})", value="`" + ("`, `".join(n.name_formatted for n in borders[0]) + "`") if len(borders[1]) > 0 else "None", inline=False if len(borders[1]) > 0 else True) 
        embed.add_field(name=f"Towns ({len(towns)+1})", value="`" + ("`, `".join(t.name_formatted for t in [capital]+towns)) + "`", inline=False)
        embed.add_field(name="Culture Make Up", value="- " + "\n- ".join([f"{name}: {(residents/total_residents)*100:,.2f}%" for name, residents in culture_make_up.items()][:5]) if len(culture_make_up) > 0 else 'None')
        embed.add_field(name="Religion Make Up", value="- " + "\n- ".join([f"{name}: {(residents/total_residents)*100:,.2f}%" for name, residents in religion_make_up.items()][:5]) if len(religion_make_up) > 0 else 'None')
        embed.add_field(name="Notable Statistics", value=notable_statistics_str + notable_rankings_str, inline=False)

        embed.set_footer(text=f"Bot has been tracking for {(await self.client.world.total_tracked).str_no_timestamp()}")

        c_view = commands_view.CommandsView(self)

        button = discord.ui.Button(label="Expand Outposts", emoji="🗺️", row=2, style=discord.ButtonStyle.primary)
        def outposts_button(nation : client.object.Nation, view : discord.ui.View, borders):
            async def outposts_button_callback(interaction : discord.Interaction):
                for item in view.children:
                    if type(item) == discord.ui.Button and item.label == "Expand Outposts":
                        item.disabled = True 
                
                graph = discord.File(graphs.plot_towns(nation.towns, outposts=True, dimmed_towns=borders[1], plot_spawn=True), filename="graph_outposts.png")

                interaction.message.embeds[0].set_thumbnail(url=None)
                interaction.message.embeds[0].set_image(url="attachment://graph_outposts.png")
                
                await interaction.response.edit_message(view=view, attachments=[graph], embed=interaction.message.embeds[0])
            return outposts_button_callback
        button.callback = outposts_button(nation, c_view, borders)
        if len(nation.raw_locs) > len(towns)+1:
            c_view.add_item(button)

        if type(leader) != str:
            c_view.add_command(commands_view.Command("get player", "Leader Info", (leader.name,), button_style=discord.ButtonStyle.primary, emoji="👑", row=1))
        c_view.add_command(commands_view.Command("history nation residents", "Resident History", (nation.name,), emoji="🧑", row=1))
        c_view.add_command(commands_view.Command("history nation towns", "Town History", (nation.name,), emoji="🗾", row=1))

        if len(towns)+1 > 1:
            c_view.add_command(commands_view.Command("distribution nation residents", "Resident distribution", (nation.name,), emoji="🧑", row=2))
            c_view.add_command(commands_view.Command("distribution nation town_bank", "Balance distr.", (nation.name,), emoji="💵", row=2))
            c_view.add_command(commands_view.Command("distribution nation area", "Area distr.", (nation.name,), emoji="🗾", row=2))

        cmds = []
        for i, town in enumerate([capital]+towns):
            if i >= 25: break 
            cmds.append(commands_view.Command("get town", town.name_formatted, (town.name,), emoji=None))
        c_view.add_item(commands_view.CommandSelect(self, cmds, "Get Town Info...", 3))

        

        # Diagram and send
        cache_name = f"Nation+{nation.name}"
        cache_id = nation.vertex_count
        im = graphs.check_cache(cache_name=cache_name, cache_id=cache_id)
        files=[]
        if im:
            files.append(discord.File(im, "map.png"))
            embed.set_image(url="attachment://map.png")

            return await interaction.response.send_message(embed=embed, files=files, view=c_view)

        elif len(towns) > 3:
            
            files.append(discord.File(s.waiting_bg_path, "map_waiting.jpg"))
            embed.set_image(url="attachment://map_waiting.jpg")

            await interaction.response.send_message(embed=embed, files=files, view=c_view)
        
        graph = discord.File(graphs.plot_towns([capital]+towns, plot_spawn=True, dimmed_towns=borders[1], cache_name=cache_name, cache_id=cache_id, outposts="retain"), filename="map.png")
        embed.set_image(url="attachment://map.png")

        if len(towns) > 3:
            await interaction.edit_original_response(embed=embed, attachments=[graph])
        else:
            await interaction.response.send_message(embed=embed, view=c_view, file=graph)
        
    @app_commands.command(name="culture", description="Get information about a culture")
    @app_commands.autocomplete(culture_name=autocompletes.culture_autocomplete)
    async def _culture(self, interaction : discord.Interaction, culture_name : str):
        
        culture = self.client.world.get_culture(culture_name, True)
        towns = culture.towns
        area = culture.total_area

        if not culture:
            raise client.errors.MildError("Couldn't find culture")
        
        nation_make_up = culture.nation_make_up
        total_residents = culture.total_residents

        embed = discord.Embed(title=f"Culture: {culture.name_formatted}", color=s.embed)
        
        embed.add_field(name="Residents", value=f"{total_residents:,}")
        embed.add_field(name="Area", value=f"{area:,} plots ({area*64:,}km²)")
        embed.add_field(name="Town Value", value=f"${culture.total_value:,.2f}")
        embed.add_field(name="Population Density", value=f"{int(culture.total_area/total_residents):,} plots/resident")
        embed.add_field(name=f"Towns ({len(towns)+1})", value="`" + ("`, `".join(t.name_formatted for t in towns)) + "`", inline=False)
        embed.add_field(name="Nation Make Up", value="- " + "\n- ".join([f"{name}: {(residents/total_residents)*100:,.2f}%" for name, residents in nation_make_up.items()][:5]) if len(nation_make_up) > 0 else 'None')

        c_view = commands_view.CommandsView(self)

        cmds = []
        for i, town in enumerate(towns):
            if i >= 25: break 
            cmds.append(commands_view.Command("get town", town.name_formatted, (town.name,), emoji=None))
        c_view.add_item(commands_view.CommandSelect(self, cmds, "Get Town Info...", 3))
        c_view.add_command(commands_view.Command("history culture towns", "Town History", (culture.name,), button_style=discord.ButtonStyle.secondary, emoji="🗾", row=2))
        c_view.add_command(commands_view.Command("history culture residents", "Resident History", (culture.name,), button_style=discord.ButtonStyle.secondary, emoji="👤", row=2))

        if len(towns) > 3:
            embed.set_image(url="attachment://map_waiting.jpg")

            await interaction.response.send_message(embed=embed, view=c_view, file=discord.File(s.waiting_bg_path, "map_waiting.jpg"))
        
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
        area = religion.total_area

        if not religion:
            raise client.errors.MildError("Couldn't find religion")
        
        nation_make_up = religion.nation_make_up
        total_residents = religion.total_residents

        embed = discord.Embed(title=f"Religion: {religion.name_formatted}", color=s.embed)
        
        embed.add_field(name="Followers", value=f"{total_residents:,}")
        embed.add_field(name="Area", value=f"{area:,} plots ({area*64:,}km²)")
        embed.add_field(name="Town Value", value=f"${religion.total_value:,.2f}")
        embed.add_field(name="Population Density", value=f"{int(religion.total_area/total_residents):,} plots/resident")
        embed.add_field(name=f"Towns ({len(towns)+1})", value="`" + ("`, `".join(t.name_formatted for t in towns)) + "`", inline=False)
        embed.add_field(name="Nation Make Up", value="- " + "\n- ".join([f"{name}: {(residents/total_residents)*100:,.2f}%" for name, residents in nation_make_up.items()][:5]) if len(nation_make_up) > 0 else 'None')

        c_view = commands_view.CommandsView(self)

        cmds = []
        for i, town in enumerate(towns):
            if i >= 25: break 
            cmds.append(commands_view.Command("get town", town.name_formatted, (town.name,), emoji=None))
        c_view.add_item(commands_view.CommandSelect(self, cmds, "Get Town Info...", 3))
        c_view.add_command(commands_view.Command("history religion towns", "Town History", (religion.name,), button_style=discord.ButtonStyle.secondary, emoji="🗾", row=2))
        c_view.add_command(commands_view.Command("history religion followers", "Follower History", (religion.name,), button_style=discord.ButtonStyle.secondary, emoji="👤", row=2))

        if len(towns) > 3:
            embed.set_image(url="attachment://map_waiting.jpg")

            await interaction.response.send_message(embed=embed, view=c_view, file=discord.File(s.waiting_bg_path, "map_waiting.jpg"))
        
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
        area = world.total_area
        total_activity = await world.total_activity
        total_tracked = await world.total_tracked

        embed = discord.Embed(title="RulerCraft Earth", description=f"[View Map]({self.client.url})", color=s.embed)
        
        embed.add_field(name="Towns", value=str(len(world.towns)))
        embed.add_field(name="Nations", value=str(len(world.nations)))
        embed.add_field(name="Cultures", value=str(len(world.cultures)))
        embed.add_field(name="Religions", value=str(len(world.religions)))
        embed.add_field(name="Town Value", value=f"${world.total_value:,.2f}")
        embed.add_field(name="Claimed Area", value=f"{area:,} plots ({area*64:,}km²)")
        embed.add_field(name="Total Residents", value=f"{world.total_residents:,} ({len(world.players):,} known)")
        embed.add_field(name="Average online players", value=f"{total_activity.total/total_tracked.total:,.2f}")

        embed.set_footer(text=f"Bot has been tracking for {total_tracked.str_no_timestamp()}")

        cache_id = f"{len(world.towns)}+{len(world.nations)}"
        im = graphs.check_cache(cache_name="Earth", cache_id=cache_id)
        files=[]
        if im:
            files.append(discord.File(im, "graph.png"))
            embed.set_image(url="attachment://graph.png")
        else:
            files.append(discord.File(s.waiting_bg_path, "map_waiting.jpg"))
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
        cmds = []
        for i, player in enumerate(online_players):
            today = await player.get_activity_today()
            log = f"**{discord.utils.escape_markdown(player.name)}**: [{int(player.location.x)}, {int(player.location.y)}, {int(player.location.z)}]({self.client.url}?x={int(player.location.x)}&z={int(player.location.z)}&zoom={s.map_link_zoom}) ({client.funcs.generate_time(today.total)} today)\n" + log

            if i <= 25: cmds.append(commands_view.Command("get player", player.name, (player.name,), emoji=None))

        embed = discord.Embed(title=f"Online players ({len(online_players)})", color=s.embed)
        embed.set_image(url="attachment://map_waiting.jpg")

        view = paginator.PaginatorView(embed, log, skip_buttons=False)
        if len(cmds) > 0:
            view.add_item(commands_view.CommandSelect(self, list(reversed(cmds))[:25], "Get Player Info...", 2))

        im = graphs.check_cache(cache_name="Earth", cache_id=f"{len(self.client.world.towns)}+{len(self.client.world.nations)}")
        
        await interaction.response.send_message(embed=embed, view=view, file=discord.File(s.waiting_bg_path, "map_waiting.jpg"))

        graph = discord.File(graphs.plot_towns(self.client.world.towns, players=self.client.world.players, plot_spawn=False, whole=True, cache_checked=im, cache_name="Earth", cache_id=f"{len(self.client.world.towns)}+{len(self.client.world.nations)}"), filename="graph.png")
        embed.set_image(url="attachment://graph.png")

        await interaction.edit_original_response(attachments=[graph], embed=embed)


async def setup(bot : commands.Bot):
    await bot.add_cog(Get(bot, bot.client))
