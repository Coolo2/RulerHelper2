
import discord 

import setup as s
from funcs import autocompletes, commands_view, paginator

from discord import app_commands
from discord.ext import commands

import client

class Get(commands.GroupCog, name="get", description="All get commands"):

    def __init__(self, bot : commands.Bot, client : client.Client):
        self.bot = bot
        self.client = client

        super().__init__()

        @self.bot.tree.context_menu(name="Find user")
        async def _get_user(interaction : discord.Interaction, user : discord.User):
            discords = await client.world.linked_discords

            for d in discords:
                if d[1] == user:
                    return await self._player.callback(self, interaction, d[0].name)
            
            raise self.client.errors.MildError("Could not find player's in-game account")

    
    @app_commands.command(name="player", description="Get information about a player")
    @app_commands.autocomplete(player_name=autocompletes.player_autocomplete)
    async def _player(self, interaction : discord.Interaction, player_name : str):

        response_coro = interaction.response.edit_message if interaction.extras.get("edit") else interaction.response.send_message

        player = self.client.world.get_player(player_name, True)
        if not player:
            raise client.errors.MildError("Player not found")
        activity = await player.activity 

        town = player.town 
        visited_towns_total = await player.total_visited_towns
        dc = await player.discord
        notable_statistics = client.funcs.top_rankings_to_text(await player.top_rankings, player.name)
        total_mentions, last_mention = await player.total_mentions
        total_messages, last_message = await player.total_messages

        health = "<:heartfull:1152274373923844196>"*int(player.health//2) + "<:hearthalf:1152274386364145715>"*int(player.health%2) + "<:heartnone:1152275125199179867>"*int((20-player.health)//2)
        armor = "<:armorfull:1152274423898976289>"*int(player.armor//2) + "<:armorhalf:1152274436179898430>"*int(player.armor%2) + "<:armornone:1152274447445790730>"*int((20-player.armor)//2)
        online = f"🟢  {discord.utils.escape_markdown(player.name)} is **online**" if player.online else f"🔴 {discord.utils.escape_markdown(player.name)} is **offline**"

        embed = discord.Embed(title=f"Player: {discord.utils.escape_markdown(player.name)}", description=f"{online}\n\n{health}\n{armor}", color=s.embed)
        if interaction.extras.get("author"): embed._author = interaction.extras.get("author")
        
        embed.add_field(name="Residency", value=f"{player.residency.name_formatted} {'('+player.residency.nation.name_formatted+')' if player.residency.nation and player.residency != town else ''}" if player.residency else "None")
        embed.add_field(name="Location", value=f"[{int(player.location.x)}, {int(player.location.y)}, {int(player.location.z)}]({self.client.url}?x={int(player.location.x)}&z={int(player.location.z)}&zoom={s.map_link_zoom})")
        embed.add_field(name="Activity", value=str(activity))
        embed.add_field(name="Bank Balance", value=f"${player.bank:,.2f}" if player.bank else "Unknown *(not mayor)*")
        embed.add_field(name="Current Town", value=f"{town.name_formatted} {'('+str(town.nation.name_formatted)+')' if town.nation else ''}" if town else "None")
        embed.add_field(name="Visited Towns", value=f"{visited_towns_total} ({(visited_towns_total/len(self.client.world.towns))*100:.1f}%)")
        embed.add_field(name="Likely Discord", value=str(dc.mention if dc else "Unknown"))
        embed.add_field(name="Donator?", value="Yes" if player.donator == True else "Unlikely" if player.donator == False else "Unknown")
        embed.add_field(name="Nickname", value=player.nickname_no_tags if player.nickname_no_tags != player.name else "None")
        embed.add_field(name="Notable Statistics", value=notable_statistics, inline=False)
        embed.add_field(name="Sent messages", value=f"{total_messages:,}" + (f" <t:{int(last_message.timestamp())}:R>" if total_messages != 0 else ""))
        embed.add_field(name="Total mentions", value=f"{total_mentions:,}" + (f" <t:{int(last_mention.timestamp())}:R>" if total_mentions != 0 else ""))

        embed.set_footer(text=await self.client.tracking_footer)
        embed.set_thumbnail(url=await player.face_url)

        c_view = commands_view.CommandsView(self)
        c_view.add_item(commands_view.RefreshButton(self.client, "get player", (player.name,)))

        button = discord.ui.Button(label="Full Skin", emoji="🧍", row=1, style=discord.ButtonStyle.primary)
        def full_skin(player : client.objects.Player, view : discord.ui.View):
            async def full_skin_callback(interaction : discord.Interaction):
                for item in view.children:
                    if item.label == "Full Skin":
                        item.disabled = True 
                
                interaction.message.embeds[0].set_image(url=await player.body_url)
                
                await interaction.response.edit_message(view=view, embed=interaction.message.embeds[0])
            return full_skin_callback
        button.callback = full_skin(player, c_view)
        c_view.add_item(button)

        if town:
            c_view.add_command(commands_view.Command("get town", "Town Info", (town.name,), button_style=discord.ButtonStyle.primary, emoji="ℹ️"))
        if player.residency and player.residency != town:
            c_view.add_command(commands_view.Command("get town", "Residency Info", (player.residency.name,), button_style=discord.ButtonStyle.primary, emoji="ℹ️"))
        c_view.add_command(commands_view.Command("history player activity", "Activity History", (player.name,), button_style=discord.ButtonStyle.secondary, emoji="⏳", row=2))
        if visited_towns_total > 0:
            c_view.add_command(commands_view.Command("history player visited_towns", "Visited Towns", (player.name,), button_style=discord.ButtonStyle.secondary, emoji="📖", row=2))

        return await response_coro(embed=embed, view=c_view)

    @app_commands.command(name="town", description="Get information about a town")
    @app_commands.autocomplete(town_name=autocompletes.town_autocomplete)
    async def _town(self, interaction : discord.Interaction, town_name : str):

        edit = interaction.extras.get("edit")
        
        town = self.client.world.get_town(town_name, True)

        if not town:
            raise client.errors.MildError("Couldn't find town")
        
        borders = town.borders
        area = town.area
        visited_players_total = await town.total_visited_players
        previous_names = await town.previous_names
        total_mentions, last_mention = await town.total_mentions

        notable_rankings_str = client.funcs.top_rankings_to_text(await town.top_rankings, town.name_formatted)
        notable_statistics = town.notable_statistics
        notable_statistics_str = "- " + "\n- ".join(notable_statistics) if len(notable_statistics) > 0 else ""

        embed = discord.Embed(title=f"Town: {town.name_formatted}", description=town.geography_description, color=s.embed)
        if interaction.extras.get("author"): embed._author = interaction.extras.get("author")

        embed.add_field(name="Mayor", value=discord.utils.escape_markdown(str(town.mayor)))
        embed.add_field(name="Bank", value=f"${town.bank:,.2f}")
        embed.add_field(name="Founded", value=town.founded_date.strftime(s.DATE_STRFTIME))
        embed.add_field(name="Nation", value=town.nation.name_formatted if town.nation else "None")
        embed.add_field(name="Culture", value=str(town.culture))
        embed.add_field(name="Religion", value=str(town.religion))
        embed.add_field(name="Area", value=f"{area:,} plots ({area * 64:,}km²)")
        embed.add_field(name="Daily Tax", value=str(town.resident_tax))
        embed.add_field(name="Spawnblock", value=f"[{int(town.spawn.x)}, {int(town.spawn.z)}]({self.client.url}?x={int(town.spawn.x)}&z={int(town.spawn.z)}&zoom={s.map_link_zoom})")
        embed.add_field(name="Activity", value=str(await town.activity))
        embed.add_field(name="Visited Players", value=f"{visited_players_total} ({(visited_players_total/len(self.client.world.players))*100:.1f}%)")
        embed.add_field(name="Outposts", value=str(len(town.outpost_spawns)))
        embed.add_field(name="Public", value="Yes" if town.public else "No")
        embed.add_field(name="Previous names", value=", ".join(previous_names) if len(previous_names) > 0 else "None")
        embed.add_field(name="Total mentions", value=f"{total_mentions:,}" + (f" <t:{int(last_mention.timestamp())}:R>" if total_mentions != 0 else ""))

        embed.add_field(name=f"Residents ({town.resident_count})", value="`" + ("`, `".join(town._resident_names) + "`") if len(town.residents) > 0 else "None", inline=False) 
        embed.add_field(name=f"Bordering Towns ({len(borders)})", value="`" + ("`, `".join(t.name_formatted for t in borders) + "`") if len(borders) > 0 else "None", inline=False) 
        #embed.add_field(name="Peaceful", value="Yes" if town.peaceful else "No")
        embed.add_field(name="Notable Statistics", value=notable_statistics_str + notable_rankings_str, inline=False)

        embed.set_footer(text=await self.client.tracking_footer)

        c_view = commands_view.CommandsView(self)

        c_view.add_item(commands_view.RefreshButton(self.client, "get town", (town.name,)))

        if type(town.mayor) != str:
            c_view.add_command(commands_view.Command("get player", "Mayor Info", (town.mayor.name,), button_style=discord.ButtonStyle.primary, emoji="👑"))
        if town.nation:
            c_view.add_command(commands_view.Command("get nation", "Nation Info", (town.nation.name,), button_style=discord.ButtonStyle.primary, emoji="🗾"))
        if town.culture:
            c_view.add_command(commands_view.Command("get culture", "Culture Info", (town.culture.name,), button_style=discord.ButtonStyle.primary, emoji="📔"))
        if town.religion:
            c_view.add_command(commands_view.Command("get religion", "Religion Info", (town.religion.name,), button_style=discord.ButtonStyle.primary, emoji="🙏"))
        
        outposts = True if len(town.outpost_spawns) > 0 and len(town.areas) > 1 else False
        button = discord.ui.Button(label="Expand Outposts" if outposts else "Expand Map", emoji="🗺️", row=2, style=discord.ButtonStyle.primary)
        def outposts_button(town : client.objects.Town, view : discord.ui.View, borders, outposts : bool):
            async def outposts_button_callback(interaction : discord.Interaction):
                for item in view.children:
                    if hasattr(item, "label") and item.label in ("Expand Outposts", "Expand Map"):
                        item.disabled = True 
                
                c = self.client.image_generator.town_cache_item(f"TownOutposts+{town.name}", [town]).check_cache()
                dpi = await self.client.image_generator.generate_area_map([town], True, True, self.client.image_generator.MapBackground.AUTO, False, c, borders)
                file = discord.File(await self.client.image_generator.render_plt(dpi, c), "town_outpost_map.png")

                interaction.message.embeds[0].set_thumbnail(url=None)
                interaction.message.embeds[0].set_image(url="attachment://town_outpost_map.png")
                
                await interaction.response.edit_message(view=view, attachments=[file], embed=interaction.message.embeds[0])
            return outposts_button_callback
        
        button.callback = outposts_button(town, c_view, borders, outposts)
        c_view.add_item(button)
        c_view.add_command(commands_view.Command("history town visited_players", "Visited Players", (town.name,), button_style=discord.ButtonStyle.secondary, emoji="📖", row=2))
        c_view.add_command(commands_view.Command("history town bank", "Bank History", (town.name,), button_style=discord.ButtonStyle.secondary, emoji="💵", row=2))
        c_view.add_command(commands_view.Command("history town residents", "Resident History", (town.name,), button_style=discord.ButtonStyle.secondary, emoji="👤", row=2))
        
        cmds = []
        i = 0
        for player in town.residents:
            if player == town.mayor or i >= 25: continue 
            cmds.append(commands_view.Command("get player", player.name, (player.name,), emoji=None))
            i += 1
        if len(cmds) > 0:
            c_view.add_item(commands_view.CommandSelect(self, cmds, "Get Resident Info...", 3))

        c = self.client.image_generator.town_cache_item(f"Town+{town.name}", [town]).check_cache()
        dpi = await self.client.image_generator.generate_area_map([town], True, False, self.client.image_generator.MapBackground.OFF, False, c, borders, False)
        file = discord.File(await self.client.image_generator.render_plt(dpi, c), "town_map.png")
        embed.set_thumbnail(url="attachment://town_map.png")

        return await interaction.response.edit_message(embed=embed, attachments=[file], view=c_view) if edit else await interaction.response.send_message(embed=embed, file=file, view=c_view)
    
    @app_commands.command(name="nation", description="Get information about a nation")
    @app_commands.autocomplete(nation_name=autocompletes.nation_autocomplete)
    async def _nation(self, interaction : discord.Interaction, nation_name : str):

        edit = interaction.extras.get("edit")
        
        nation = self.client.world.get_nation(nation_name, True)

        if not nation:
            raise client.errors.MildError("Couldn't find nation")

        towns = list(sorted(nation.towns, key=lambda t: t.resident_count, reverse=True))
        capital = nation.capital
        leader = capital.mayor
        flags = await nation.flags
        total_residents = nation.total_residents
        area = nation.total_area
        previous_names = await nation.previous_names
        total_mentions, last_mention = await nation.total_mentions
        total_outposts = nation.total_outposts
        
        borders = nation.borders

        towns.remove(capital)

        notable_rankings_str = client.funcs.top_rankings_to_text(await nation.top_rankings, nation.name_formatted)
        notable_statistics = nation.notable_statistics
        notable_statistics_str = "- " + "\n- ".join(notable_statistics) if len(notable_statistics) > 0 else ""

        religion_make_up = nation.religion_make_up
        culture_make_up = nation.culture_make_up

        embed = discord.Embed(title=f"Nation: {nation.name_formatted}", description=f"[Visit on map]({self.client.url}?x={int(nation.capital.spawn.x)}&z={int(nation.capital.spawn.z)}&zoom={s.map_link_zoom})", color=s.embed)
        if interaction.extras.get("author"): embed._author = interaction.extras.get("author")
        embed.set_thumbnail(url=self.client.url + "/" + nation.capital.flag_url)
        
        embed.add_field(name="Leader", value=discord.utils.escape_markdown(str(leader)))
        embed.add_field(name="Capital", value=str(capital))
        embed.add_field(name="Residents", value=f"{total_residents:,}")
        embed.add_field(name="Area", value=f"{area:,} plots ({area*64:,}km²)")
        embed.add_field(name="Population Density", value=f"{int(nation.total_area/total_residents):,} plots/resident")
        embed.add_field(name="Activity", value=str(await nation.activity))
        embed.add_field(name="Total Outposts", value=f"{total_outposts:,}")
        embed.add_field(name="Town Value", value=f"${nation.total_value:,.2f}")
        embed.add_field(name="Previous names", value=", ".join(previous_names) if len(previous_names) > 0 else "None")
        embed.add_field(name="Discord", value=flags.get("server") or "None set.")
        embed.add_field(name="Total mentions", value=f"{total_mentions:,}" + (f" <t:{int(last_mention.timestamp())}:R>" if total_mentions != 0 else ""))

        embed.add_field(name=f"Borders ({len(borders[0])})", value="`" + ("`, `".join(n.name_formatted for n in borders[0]) + "`") if len(borders[1]) > 0 else "None", inline=False if len(borders[1]) > 0 else True) 
        embed.add_field(name=f"Towns ({len(towns)+1})", value="`" + ("`, `".join(t.name_formatted for t in [capital]+towns)) + "`", inline=False)
        embed.add_field(name="Culture Make Up", value="- " + "\n- ".join([f"{name}: {(residents/total_residents)*100:,.2f}%" for name, residents in culture_make_up.items()][:5]) if len(culture_make_up) > 0 else 'None')
        embed.add_field(name="Religion Make Up", value="- " + "\n- ".join([f"{name}: {(residents/total_residents)*100:,.2f}%" for name, residents in religion_make_up.items()][:5]) if len(religion_make_up) > 0 else 'None')
        embed.add_field(name="Notable Statistics", value=notable_statistics_str + notable_rankings_str, inline=False)

        embed.set_footer(text=await self.client.tracking_footer)

        c_view = commands_view.CommandsView(self)
        c_view.add_item(commands_view.RefreshButton(self.client, "get nation", (nation.name,)))

        button = discord.ui.Button(label="Expand Outposts", emoji="🗺️", row=2, style=discord.ButtonStyle.primary)
        def outposts_button(nation : client.objects.Nation, view : discord.ui.View, borders):
            async def outposts_button_callback(interaction : discord.Interaction):
                await interaction.response.defer()
                for item in view.children:
                    if type(item) == discord.ui.Button and item.label == "Expand Outposts":
                        item.disabled = True 
                    else:
                        item.disabled = False

                c = self.client.image_generator.town_cache_item(f"NationOutposts+{nation.name}", nation.towns).check_cache()
                dpi = await self.client.image_generator.generate_area_map(nation.towns, True, True, self.client.image_generator.MapBackground.AUTO, False, c, nation.borders[1])
                file = discord.File(await self.client.image_generator.render_plt(dpi, c), "nation_map_outposts.png")

                interaction.message.embeds[0].set_thumbnail(url=None)
                interaction.message.embeds[0].set_image(url="attachment://nation_map_outposts.png")
                
                await interaction.followup.edit_message(view=view, attachments=[file], embed=interaction.message.embeds[0], message_id=interaction.message.id)
            return outposts_button_callback
        button.callback = outposts_button(nation, c_view, borders)
        if len(nation.outpost_spawns) > 0:
            c_view.add_item(button)
        
        button = discord.ui.Button(label="Show Claim Radius", emoji="🗺️", row=2, style=discord.ButtonStyle.primary)
        def claims_button(nation : client.objects.Nation, view : discord.ui.View, capital : client.objects.Town):
            async def claims_button_callback(interaction : discord.Interaction):
                await interaction.response.defer()
                for item in view.children:
                    if type(item) == discord.ui.Button and item.label == "Show Claim Radius":
                        item.disabled = True 

                    else:
                        item.disabled = False

                c = self.client.image_generator.town_cache_item(f"NationClaimRadius+{nation.name}", nation.towns).check_cache()
                dpi = await self.client.image_generator.generate_area_map(nation.towns, True, True, self.client.image_generator.MapBackground.ON, True, c, self.client.world.towns)
                if not c.valid:
                    await self.client.image_generator.layer_claim_circle([capital.spawn.x, capital.spawn.z], 12430)
                file = discord.File(await self.client.image_generator.render_plt(dpi, c), "nation_map_claim.png")

                interaction.message.embeds[0].set_thumbnail(url=None)
                interaction.message.embeds[0].set_image(url="attachment://nation_map_claim.png")
                
                await interaction.followup.edit_message(view=view, attachments=[file], embed=interaction.message.embeds[0], message_id=interaction.message.id)
            return claims_button_callback
        button.callback = claims_button(nation, c_view, nation.capital)
        c_view.add_item(button)

        if type(leader) != str:
            c_view.add_command(commands_view.Command("get player", "Leader Info", (leader.name,), button_style=discord.ButtonStyle.primary, emoji="👑", row=1))
        c_view.add_command(commands_view.Command("history nation residents", "Resident History", (nation.name,), emoji="🧑", row=1))
        c_view.add_command(commands_view.Command("history nation towns", "Town History", (nation.name,), emoji="🗾", row=1))

        if len(towns)+1 > 1:
            c_view.add_command(commands_view.Command("distribution nation residents", "Res. distribution", (nation.name,), emoji="🧑", row=2))
            c_view.add_command(commands_view.Command("distribution nation town_bank", "Balance distr.", (nation.name,), emoji="💵", row=2))

        cmds = []
        for i, town in enumerate([capital]+towns):
            if i >= 25: break 
            cmds.append(commands_view.Command("get town", town.name_formatted, (town.name,), emoji=None))
        c_view.add_item(commands_view.CommandSelect(self, cmds, "Get Town Info...", 3))

        c = self.client.image_generator.town_cache_item(f"Nation+{nation.name}", nation.towns).check_cache()
        if not c.valid and not edit:
            embed.set_image(url="attachment://map_waiting.jpg")
            await interaction.response.send_message(embed=embed, view=c_view, file=discord.File(s.waiting_bg_path, "map_waiting.jpg"))
        elif not c.valid:
            embed.set_image(url="attachment://nation_map.png")
            await interaction.response.edit_message(embed=embed, view=c_view)
        dpi = await self.client.image_generator.generate_area_map(nation.towns, True, False, self.client.image_generator.MapBackground.AUTO, False, c, nation.borders[1])
        file = discord.File(await self.client.image_generator.render_plt(dpi, c), "nation_map.png")
        embed.set_image(url="attachment://nation_map.png")
        if c.valid and not edit:
            await interaction.response.send_message(embed=embed, view=c_view, file=file)
        elif c.valid:
            await interaction.response.edit_message(embed=embed, view=c_view, attachments=[file])
        else:
            await interaction.edit_original_response(embed=embed, view=c_view, attachments=[file])

    @app_commands.command(name="culture", description="Get information about a culture")
    @app_commands.autocomplete(culture_name=autocompletes.culture_autocomplete)
    async def _culture(self, interaction : discord.Interaction, culture_name : str):

        edit = interaction.extras.get("edit")
        
        culture = self.client.world.get_culture(culture_name, True)
        towns = culture.towns
        area = culture.total_area
        total_mentions, last_mention = await culture.total_mentions

        if not culture:
            raise client.errors.MildError("Couldn't find culture")
        
        nation_make_up = culture.nation_make_up
        total_residents = culture.total_residents

        embed = discord.Embed(title=f"Culture: {culture.name_formatted}", color=s.embed)
        if interaction.extras.get("author"): embed._author = interaction.extras.get("author")
        
        embed.add_field(name="Residents", value=f"{total_residents:,}")
        embed.add_field(name="Area", value=f"{area:,} plots ({area*64:,}km²)")
        embed.add_field(name="Town Value", value=f"${culture.total_value:,.2f}")
        embed.add_field(name="Population Density", value=f"{int(culture.total_area/total_residents):,} plots/resident")
        embed.add_field(name="Total mentions", value=f"{total_mentions:,}" + (f" <t:{int(last_mention.timestamp())}:R>" if total_mentions != 0 else ""))
        embed.add_field(name=f"Towns ({len(towns)+1})", value="`" + ("`, `".join(t.name_formatted for t in towns)) + "`", inline=False)
        embed.add_field(name="Nation Make Up", value="- " + "\n- ".join([f"{name}: {(residents/total_residents)*100:,.2f}%" for name, residents in nation_make_up.items()][:5]) if len(nation_make_up) > 0 else 'None')

        c_view = commands_view.CommandsView(self)
        c_view.add_item(commands_view.RefreshButton(self.client, "get culture", (culture.name,), row=2))

        cmds = []
        for i, town in enumerate(towns):
            if i >= 25: break 
            cmds.append(commands_view.Command("get town", town.name_formatted, (town.name,), emoji=None))
        c_view.add_item(commands_view.CommandSelect(self, cmds, "Get Town Info...", 3))
        c_view.add_command(commands_view.Command("history culture towns", "Town History", (culture.name,), button_style=discord.ButtonStyle.secondary, emoji="🗾", row=2))
        c_view.add_command(commands_view.Command("history culture residents", "Resident History", (culture.name,), button_style=discord.ButtonStyle.secondary, emoji="👤", row=2))
        
        c = self.client.image_generator.town_cache_item(f"Culture+{culture.name}", culture.towns).check_cache()
        if not c.valid and not edit:
            embed.set_image(url="attachment://map_waiting.jpg")
            await interaction.response.send_message(embed=embed, view=c_view, file=discord.File(s.waiting_bg_path, "map_waiting.jpg"))
        elif not c.valid:
            embed.set_image(url="attachment://culture_map.png")
            await interaction.response.edit_message(embed=embed, view=c_view)
        dpi = await self.client.image_generator.generate_area_map(culture.towns, False, True, self.client.image_generator.MapBackground.AUTO, False, c)
        file = discord.File(await self.client.image_generator.render_plt(dpi, c), "culture_map.png")
        embed.set_image(url="attachment://culture_map.png")
        if c.valid and not edit:
            await interaction.response.send_message(embed=embed, view=c_view, file=file)
        elif c.valid:
            await interaction.response.edit_message(embed=embed, view=c_view, attachments=[file])
        else:
            await interaction.edit_original_response(embed=embed, view=c_view, attachments=[file])
    
    @app_commands.command(name="religion", description="Get information about a religion")
    @app_commands.autocomplete(religion_name=autocompletes.religion_autocomplete)
    async def _religion(self, interaction : discord.Interaction, religion_name : str):

        edit = interaction.extras.get("edit")
        
        religion = self.client.world.get_religion(religion_name, True)
        towns = religion.towns
        area = religion.total_area
        total_mentions, last_mention = await religion.total_mentions

        if not religion:
            raise client.errors.MildError("Couldn't find religion")
        
        nation_make_up = religion.nation_make_up
        total_residents = religion.total_residents

        embed = discord.Embed(title=f"Religion: {religion.name_formatted}", color=s.embed)
        if interaction.extras.get("author"): embed._author = interaction.extras.get("author")
        
        embed.add_field(name="Followers", value=f"{total_residents:,}")
        embed.add_field(name="Area", value=f"{area:,} plots ({area*64:,}km²)")
        embed.add_field(name="Town Value", value=f"${religion.total_value:,.2f}")
        embed.add_field(name="Population Density", value=f"{int(religion.total_area/total_residents):,} plots/resident")
        embed.add_field(name="Total mentions", value=f"{total_mentions:,}" + (f" <t:{int(last_mention.timestamp())}:R>" if total_mentions != 0 else ""))
        embed.add_field(name=f"Towns ({len(towns)+1})", value="`" + ("`, `".join(t.name_formatted for t in towns)) + "`", inline=False)
        embed.add_field(name="Nation Make Up", value="- " + "\n- ".join([f"{name}: {(residents/total_residents)*100:,.2f}%" for name, residents in nation_make_up.items()][:5]) if len(nation_make_up) > 0 else 'None')

        c_view = commands_view.CommandsView(self)
        c_view.add_item(commands_view.RefreshButton(self.client, "get religion", (religion.name,), row=2))

        cmds = []
        for i, town in enumerate(towns):
            if i >= 25: break 
            cmds.append(commands_view.Command("get town", town.name_formatted, (town.name,), emoji=None))
        c_view.add_item(commands_view.CommandSelect(self, cmds, "Get Town Info...", 3))
        c_view.add_command(commands_view.Command("history religion towns", "Town History", (religion.name,), button_style=discord.ButtonStyle.secondary, emoji="🗾", row=2))
        c_view.add_command(commands_view.Command("history religion followers", "Follower History", (religion.name,), button_style=discord.ButtonStyle.secondary, emoji="👤", row=2))
        
        c = self.client.image_generator.town_cache_item(f"Religion+{religion.name}", religion.towns).check_cache()
        if not c.valid and not edit:
            embed.set_image(url="attachment://map_waiting.jpg")
            await interaction.response.send_message(embed=embed, view=c_view, file=discord.File(s.waiting_bg_path, "map_waiting.jpg"))
        elif not c.valid:
            embed.set_image(url="attachment://religion_map.png")
            await interaction.response.edit_message(embed=embed, view=c_view)
        dpi = await self.client.image_generator.generate_area_map(religion.towns, False, True, self.client.image_generator.MapBackground.AUTO, False, c)
        file = discord.File(await self.client.image_generator.render_plt(dpi, c), "religion_map.png")
        embed.set_image(url="attachment://religion_map.png")
        if c.valid and not edit:
            await interaction.response.send_message(embed=embed, view=c_view, file=file)
        elif c.valid:
            await interaction.response.edit_message(embed=embed, view=c_view, attachments=[file])
        else:
            await interaction.edit_original_response(embed=embed, view=c_view, attachments=[file])
    
    @app_commands.command(name="world", description="Get information about the world as a whole")
    async def _world(self, interaction : discord.Interaction):

        edit = interaction.extras.get("edit")
        
        world = self.client.world
        towns = world.towns
        area = world.total_area
        total_activity = await world.total_activity
        total_tracked = await world.total_tracked

        embed = discord.Embed(title="RulerCraft Earth", description=f"[View Map]({self.client.url})", color=s.embed)
        if interaction.extras.get("author"): embed._author = interaction.extras.get("author")
        
        embed.add_field(name="Towns", value=str(len(world.towns)))
        embed.add_field(name="Nations", value=str(len(world.nations)))
        embed.add_field(name="Cultures", value=str(len(world.cultures)))
        embed.add_field(name="Religions", value=str(len(world.religions)))
        embed.add_field(name="Town Bank Value", value=f"${world.total_value:,.2f}")
        embed.add_field(name="Mayor Bank Value", value=f"${world.total_mayor_value:,.2f}")
        embed.add_field(name="Claimed Area", value=f"{area:,} plots ({area*64:,}km²)")
        embed.add_field(name="Total Residents", value=f"{world.total_residents:,} ({len(world.players):,} known)")
        embed.add_field(name="Total player activity", value=total_activity.str_no_timestamp())
        embed.add_field(name="Average online players", value=f"{total_activity.total/total_tracked.total:,.2f}")
        embed.add_field(name="Total sent messages", value=f"{await world.total_messages:,}")

        embed.set_footer(text=await self.client.tracking_footer)

        c_view = commands_view.CommandsView(self)
        c_view.add_item(commands_view.RefreshButton(self.client, "get world", [], 2))
        c_view.add_command(commands_view.Command("history global towns", "Town History", (), button_style=discord.ButtonStyle.secondary, emoji="🗾", row=2))
        c_view.add_command(commands_view.Command("history global residents", "Resident History", (), button_style=discord.ButtonStyle.secondary, emoji="👤", row=2))
        c_view.add_command(commands_view.Command("history global nations", "Nation History", (), button_style=discord.ButtonStyle.secondary, emoji="👑", row=2))
        c_view.add_command(commands_view.Command("history global town_value", "Town Value History", (), button_style=discord.ButtonStyle.primary, emoji="💵", row=3))
        c_view.add_command(commands_view.Command("history global mayor_value", "Mayor Value History", (), button_style=discord.ButtonStyle.primary, emoji="💵", row=3))

        c = self.client.image_generator.town_cache_item(f"Global", world.towns).check_cache()
        
        if not c.valid and not edit:
            embed.set_image(url="attachment://map_waiting.jpg")
            await interaction.response.send_message(embed=embed, file=discord.File(s.waiting_bg_path, "map_waiting.jpg"), view=c_view)
        elif edit:
            embed.set_image(url="attachment://earth_map.png")
            await interaction.response.edit_message(embed=embed, view=c_view)
        
        embed.set_image(url="attachment://earth_map.png")
        dpi = await self.client.image_generator.generate_area_map(world.towns, False, True, self.client.image_generator.MapBackground.ON, True, c)
        file = discord.File(await self.client.image_generator.render_plt(dpi, c), "earth_map.png")

        if edit or not c.valid:
            await interaction.edit_original_response(embed=embed, view=c_view, attachments=[file])
        else:
            await interaction.response.send_message(embed=embed, view=c_view, file=file)

    @app_commands.command(name="online", description="List online players")
    async def _online(self, interaction : discord.Interaction):

        edit = interaction.extras.get("edit")
        log = ""
        cmds = []
        
        # Sort online players
        online_players = self.client.world.online_players
        for player in online_players: player.today = await player.get_activity_today()
        online_players = sorted(online_players, key=lambda x: x.today.total)

        for i, player in enumerate(online_players):
            log = f"**{discord.utils.escape_markdown(player.name)}**: [{int(player.location.x)}, {int(player.location.y)}, {int(player.location.z)}]({self.client.url}?x={int(player.location.x)}&z={int(player.location.z)}&zoom={s.map_link_zoom}) ({client.funcs.generate_time(player.today.total)} today)\n" + log

            cmds.append(commands_view.Command("get player", player.name, (player.name,), emoji=None))

        embed = discord.Embed(title=f"Online players ({len(online_players)})", color=s.embed)
        if interaction.extras.get("author"): embed._author = interaction.extras.get("author")
        embed.set_image(url="attachment://map_waiting.jpg")

        view = paginator.PaginatorView(embed, log, skip_buttons=False, index=interaction.extras.get("page"))
        view.add_item(commands_view.RefreshButton(self.client, "get online", [], 0))
        if len(cmds) > 0:
            view.add_item(commands_view.CommandSelect(self, list(reversed(cmds))[:25], "Get Player Info...", 2))

        button = discord.ui.Button(label="Show offline players", emoji="🧍", row=1, style=discord.ButtonStyle.primary)
        def off_players(world : client.objects.World, view : discord.ui.View, embed : discord.Embed):
            async def off_players_callback(interaction : discord.Interaction):
                for item in view.children:
                    if hasattr(item, "label") and item.label == "Show offline players":
                        item.disabled = True 
                
                await interaction.response.defer()

                embed.set_image(url="attachment://earth_map.png")
                c = self.client.image_generator.town_cache_item(f"Global", world.towns).check_cache()
                dpi = await self.client.image_generator.generate_area_map(world.towns, False, True, self.client.image_generator.MapBackground.ON, True, c)
                if not c.valid: await self.client.image_generator.render_plt(dpi, c)
                await self.client.image_generator.layer_player_locations(world.online_players, world.offline_players)
                file = discord.File(await self.client.image_generator.render_plt(dpi, c), "earth_map.png")

                return await interaction.followup.edit_message(embed=embed, attachments=[file], view=view, message_id=interaction.message.id)

            return off_players_callback
        button.callback = off_players(self.client.world, view, embed)
        view.add_item(button)


        c = self.client.image_generator.town_cache_item(f"Global", self.client.world.towns).check_cache()
        
        if not edit:
            embed.set_image(url="attachment://map_waiting.jpg")
            await interaction.response.send_message(embed=embed, file=discord.File(s.waiting_bg_path, "map_waiting.jpg"), view=view)
        elif edit:
            embed.set_image(url="attachment://earth_map.png")
            await interaction.response.edit_message(embed=embed, view=view)
        
        embed.set_image(url="attachment://earth_map.png")
        dpi = await self.client.image_generator.generate_area_map(self.client.world.towns, False, True, self.client.image_generator.MapBackground.ON, True, c)
        if not c.valid:
            await self.client.image_generator.render_plt(dpi, c)

        await self.client.image_generator.layer_player_locations(online_players, [])
        file = discord.File(await self.client.image_generator.render_plt(dpi), "earth_map.png")

        
        await interaction.edit_original_response(embed=embed, view=view, attachments=[file])



async def setup(bot : commands.Bot):
    await bot.add_cog(Get(bot, bot.client))
