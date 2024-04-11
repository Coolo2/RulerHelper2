from __future__ import annotations
import typing
if typing.TYPE_CHECKING:
    import client as client_pre

import discord 
from shapely import Point 

import setup as s

from client import funcs

class NotificationChannel():
    def __init__(self):
        self.notification_type : str = None
        self.channel : discord.TextChannel = None 
        self.nation_name : str = None
        self.ignore_if_resident :bool = None
    
    def from_record(client : client_pre.Client, record : tuple):
        nc = NotificationChannel()

        nc.notification_type = record[1]
        nc.channel = client.bot.get_channel(int(record[0]))
        nc.nation_name = record[2]

        ignore_if_resident = record[3]
        nc.ignore_if_resident = True if str(ignore_if_resident) == "1" else False

        return nc

class Notifications():
    def __init__(self, client: client_pre.Client):
        self.client = client

        self._players_ignore : dict[str, dict[str, int]] = {}# "town":{"player":[0, msg]}

    async def set_notification_config(self, channel : discord.TextChannel, notification_type : str, nation_name : str, ignore_if_resident : bool):
        await self.client.execute("REPLACE INTO notifications VALUES (?, ?, ?, ?, ?)", (
            notification_type,channel.guild.id, channel.id,nation_name, int(ignore_if_resident)
        ))

    async def delete_notifications_channel(self, channel : discord.TextChannel, notification_type : str = None):
        statement = "DELETE FROM notifications WHERE channel_id=?"
        bindings = [channel.id]
        if notification_type:
            bindings.append(notification_type)
            statement += " AND notification_type=?"
        await self.client.execute(statement, bindings)

    
    async def get_notification_channels(self, channel : discord.TextChannel = None, notification_type : str = None):
        statement = "SELECT channel_id, notification_type, object_name, ignore_if_resident FROM notifications"
        bindings = []

        if channel:
            statement += " WHERE channel_id=?"
            bindings.append(channel.id)
        if notification_type:
            statement += " AND notification_type=?"
            bindings.append(notification_type)
        
        notification_channels_records : list[tuple] = await (await self.client.execute(statement, bindings)).fetchall()
        
        notification_channels : list[NotificationChannel] = []

        for record in notification_channels_records:
            nc = NotificationChannel.from_record(self.client, record)
            if nc.channel:
                notification_channels.append(nc)
        
        return notification_channels
    
    async def refresh(self):
        channels = await self.client.notifications.get_notification_channels()

        for town_name, players in self.client.world.towns_with_players.items():
            
            town = self.client.world.get_town(town_name, False)
            ignore_players = self._players_ignore.get(town_name) or {}
            if not town:
                continue

            for player in players:
                if player.name in ignore_players:
                    l = [player.location.x, player.location.z]
                    ig = self._players_ignore[town_name][player.name]
                    if len(ig[2]) == 0 or ig[2][-1] != l:
                        ig[2].append(l)
                    ig[0] += self.client.refresh_period["players"]
                    continue

                for channel in channels:
                    if town.nation and channel.notification_type == "territory_enter" and channel.nation_name == town.nation.name:
                        
                        residency_nation = player.residency.nation.name_formatted if player.residency and player.residency.nation else "None"
                        
                        if channel.ignore_if_resident and player.residency and player.residency.nation == town.nation:
                            continue
                            
                        embed = discord.Embed(title=f"Player entered {town.nation.name_formatted} territory", color=s.embed)
                        embed.add_field(name="Player name", value=discord.utils.escape_markdown(player.name))
                        embed.add_field(name="Coordinates", value=f"[{int(player.location.x)}, {int(player.location.y)}, {int(player.location.z)}]({self.client.url}?x={int(player.location.x)}&z={int(player.location.z)}&zoom={s.map_link_zoom})")
                        embed.add_field(name="Town", value=town.name_formatted)
                        embed.add_field(name="Residency (origin)", value=f"{player.residency.name_formatted} ({residency_nation})" if player.residency else "Unknown")
                        embed.add_field(name="Time spent", value="This will be edited when they exit")
                        embed.set_thumbnail(url=await player.face_url)

                        try:
                            msg = await channel.channel.send(embed=embed)
                        except:
                            msg = None

                        if town_name not in self._players_ignore:
                            self._players_ignore[town_name] = {}
                        
                        if player.name not in self._players_ignore[town_name]:
                            self._players_ignore[town_name][player.name] = [self.client.refresh_period["players"], [], [[player.location.x, player.location.z]]]
                        
                        self._players_ignore[town_name][player.name][1].append(msg)      
        
        for town_name, players in self._players_ignore.copy().items():

            for player in players.copy():
                time : int = self._players_ignore[town_name][player][0]
                msgs : list[discord.Message] = self._players_ignore[town_name][player][1]
                journey : list[list[int]] = self._players_ignore[town_name][player][2]
                    
                if not self.client.world.towns_with_players.get(town_name) or player not in self.client.world.towns_with_players[town_name]:

                    t = self.client.world.get_town(town_name, False)
                    if t:
                        a = []
                        for area in t.areas:
                            for point in journey:
                                if area.is_point_in_area(Point(point[0], 64, point[1])) and area not in a:
                                    a.append(area)
                        dpi = await self.client.image_generator.generate_area_map(a, False, False, False, False, None, [])
                        await self.client.image_generator.layer_journey(journey)
                        

                    for msg in msgs:
                        if msg:
                            plt = await self.client.image_generator.render_plt(dpi, None)
                            
                            embed = msg.embeds[0]
                            embed.set_image(url="attachment://journey.png")
                            embed.set_field_at(4, name="Time spent", value=f"In town for {funcs.generate_time(time)}")

                            try:
                                await msg.edit(embed=embed, attachments=[discord.File(plt, "journey.png")] if t else [])
                            except Exception as e:
                                print(e)

                    del self._players_ignore[town_name][player]
            
            if len(self._players_ignore[town_name]) == 0:
                del self._players_ignore[town_name]