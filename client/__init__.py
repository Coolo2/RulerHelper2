
import aiohttp
from client import object, funcs, errors
import json

import datetime
import setup as s

import db
from db import wrapper

import discord
from discord.ext import commands




class Client():
    def __init__(self):
        
        self.session : aiohttp.ClientSession= None
        self.database = db.Database("towny.db", auto_commit=False)
        self.bot : commands.Bot = None
        self.url = s.map_url

        self.towns_table : wrapper.Table = []
        self.players_table : wrapper.Table = []
        self.visited_towns_table : wrapper.Table = []

        self.refresh_period = s.refresh_period
        self.world = object.World(self) 
        self.notifications = Notifications(self)

    async def init_db(self):
        await self.database.connect()

        self.global_table = await self.database.create_or_get_table(
            db.CreationTable(
                "global",
                [
                    db.CreationAttribute("name", db.types.String),
                    db.CreationAttribute("value", db.types.Any)
                ]
            )
        )

        self.towns_table = await self.database.create_or_get_table(
            db.CreationTable(
                "towns",
                [
                    db.CreationAttribute("name", db.types.String, primary_key=True),
                    db.CreationAttribute("flag_url", db.types.String),
                    db.CreationAttribute("nation", db.types.String),
                    db.CreationAttribute("religion", db.types.String),
                    db.CreationAttribute("culture", db.types.String),
                    db.CreationAttribute("mayor", db.types.String),
                    db.CreationAttribute("resident_count", db.types.Int),
                    db.CreationAttribute("founded_date", db.types.Date),
                    db.CreationAttribute("resident_tax", db.types.Float),
                    db.CreationAttribute("bank", db.types.Float),
                    db.CreationAttribute("public", db.types.Int),
                    db.CreationAttribute("peaceful", db.types.Int),
                    db.CreationAttribute("area", db.types.Int),
                    db.CreationAttribute("last_seen", db.types.Datetime)
                ]
            )
        )

        self.players_table = await self.database.create_or_get_table(
            db.CreationTable(
                "players",
                [
                    db.CreationAttribute("name", db.types.String, primary_key=True),
                    db.CreationAttribute("location", db.types.String),
                    db.CreationAttribute("town", db.types.String),
                    db.CreationAttribute("armor", db.types.Int),
                    db.CreationAttribute("health", db.types.Int),
                    db.CreationAttribute("duration", db.types.Int),
                    db.CreationAttribute("last", db.types.Datetime)
                ]
            )
        )

        self.objects_table = await self.database.create_or_get_table(
            db.CreationTable(
                "objects",
                [
                    db.CreationAttribute("type", db.types.String),
                    db.CreationAttribute("name", db.types.String),
                    db.CreationAttribute("towns", db.types.Int),
                    db.CreationAttribute("town_balance", db.types.Float),
                    db.CreationAttribute("residents", db.types.Int),
                    db.CreationAttribute("area", db.types.Int),
                    db.CreationAttribute("last", db.types.Datetime)
                ]
            )
        )

        self.visited_towns_table = await self.database.create_or_get_table(
            db.CreationTable(
                "visited_towns",
                [
                    db.CreationAttribute("player", db.types.String),
                    db.CreationAttribute("town", db.types.String),
                    db.CreationAttribute("duration", db.types.Int),
                    db.CreationAttribute("last", db.types.Datetime)
                ]
            )
        )

        self.town_history_table = await self.database.create_or_get_table(
            db.CreationTable(
                "town_history",
                [
                    db.CreationAttribute("town", db.types.String),
                    db.CreationAttribute("date", db.types.Date),
                    db.CreationAttribute("nation", db.types.String),
                    db.CreationAttribute("religion", db.types.String),
                    db.CreationAttribute("culture", db.types.String),
                    db.CreationAttribute("mayor", db.types.String),
                    db.CreationAttribute("resident_count", db.types.Int),
                    db.CreationAttribute("resident_tax", db.types.Float),
                    db.CreationAttribute("bank", db.types.Float),
                    db.CreationAttribute("public", db.types.Int),
                    db.CreationAttribute("peaceful", db.types.Int),
                    db.CreationAttribute("area", db.types.Int),
                    db.CreationAttribute("duration", db.types.Int)
                ]
            )
        )

        self.player_history_table = await self.database.create_or_get_table(
            db.CreationTable(
                "player_history",
                [
                    db.CreationAttribute("player", db.types.String),
                    db.CreationAttribute("date", db.types.Date),
                    db.CreationAttribute("duration", db.types.Int)
                ]
            )
        )

        self.nation_history_table = await self.database.create_or_get_table(
            db.CreationTable(
                "nation_history",
                [
                    db.CreationAttribute("nation", db.types.String),
                    db.CreationAttribute("date", db.types.Date),
                    db.CreationAttribute("towns", db.types.Int),
                    db.CreationAttribute("town_balance", db.types.Float),
                    db.CreationAttribute("residents", db.types.Int),
                    db.CreationAttribute("capital", db.types.String),
                    db.CreationAttribute("leader", db.types.String),
                    db.CreationAttribute("area", db.types.Int)
                ]
            )
        )

        self.global_history_table = await self.database.create_or_get_table(
            db.CreationTable(
                "global_history",
                [
                    db.CreationAttribute("date", db.types.Date),
                    db.CreationAttribute("towns", db.types.Int),
                    db.CreationAttribute("residents", db.types.Int),
                    db.CreationAttribute("nations", db.types.Int),
                    db.CreationAttribute("town_value", db.types.Float),
                    db.CreationAttribute("area", db.types.Int),
                    db.CreationAttribute("known_players", db.types.Int)
                ]
            )
        )

        self.object_history_table = await self.database.create_or_get_table(
            db.CreationTable(
                "object_history",
                [
                    db.CreationAttribute("date", db.types.Date),
                    db.CreationAttribute("type", db.types.String),
                    db.CreationAttribute("object", db.types.String),
                    db.CreationAttribute("towns", db.types.Int),
                    db.CreationAttribute("town_balance", db.types.Float),
                    db.CreationAttribute("residents", db.types.Int),
                    db.CreationAttribute("area", db.types.Int)
                ]
            )
        )

        self.flags_table = await self.database.create_or_get_table(
            db.CreationTable(
                "flags",
                [
                    db.CreationAttribute("object_type", db.types.String),
                    db.CreationAttribute("object_name", db.types.String),
                    db.CreationAttribute("name", db.types.String),
                    db.CreationAttribute("value", db.types.Any)
                ]
            )
        )

        self.notifications_table = await self.database.create_or_get_table(
            db.CreationTable(
                "notifications",
                [
                    db.CreationAttribute("notification_type", db.types.String),
                    db.CreationAttribute("guild_id", db.types.Int),
                    db.CreationAttribute("channel_id", db.types.Int),
                    db.CreationAttribute("object_name", db.types.String),
                    db.CreationAttribute("ignore_if_resident", db.types.Any)
                ]
            )
        )

    async def create_session(self):
        if not self.session:
            self.session = aiohttp.ClientSession()


    async def fetch_world(self):
        

        await self.create_session()

        map = await self.session.get(f"{self.url}/up/world/RulerEarth/0")
        map_data = await self.session.get(f"{self.url}/tiles/_markers_/marker_RulerEarth.json")
        

        await self.world.refresh(map.content, map_data.content)
    
    async def cull_db(self):

        await self.town_history_table.delete_records([db.CreationCondition("date", datetime.date.today()-s.cull_history_from, "<")])
        await self.player_history_table.delete_records([db.CreationCondition("date", datetime.date.today()-s.cull_history_from, "<")])
        await self.global_history_table.delete_records([db.CreationCondition("date", datetime.date.today()-s.cull_history_from, "<")])
        await self.nation_history_table.delete_records([db.CreationCondition("date", datetime.date.today()-s.cull_history_from, "<")])
        await self.visited_towns_table.delete_records([db.CreationCondition("last", datetime.date.today()-s.cull_history_from, "<")])

        await self.players_table.delete_records([db.CreationCondition("last", datetime.datetime.now()-s.cull_players_from, "<")])
        await self.towns_table.delete_records([db.CreationCondition("last_seen", datetime.datetime.now()-s.cull_objects_after, "<")])
        await self.objects_table.delete_records([db.CreationCondition("last", datetime.datetime.now()-s.cull_objects_after, "<")])

        await self.flags_table.delete_records([db.CreationCondition("object_type", "nation"), db.CreationField.external_query(self.objects_table, "object_name", db.CreationCondition("type", "nation"), operator="NOT IN")])

        for player in self.world.players.copy():
            if not await player.exists_in_db:
                self.world._remove_player(player.name)
        for town in self.world.towns.copy():
            if not await town.exists_in_db:
                await self.bot.get_channel(s.alert_channel).send(f"Removed town {town.name}")
                self.world._remove_town(town.name)
        for nation in self.world.nations.copy():
            
            if not nation.capital:
                await self.bot.get_channel(s.alert_channel).send(f"Removed nation {nation.name}")
                self.world._remove_nation(nation.name)
    
class NotificationChannel():
    def __init__(self):
        self.notification_type : str = None
        self.channel : discord.TextChannel = None 
        self.nation_name : str = None
        self.ignore_if_resident :bool = None
    
    def from_record(client : Client, record : wrapper.Record):
        nc = NotificationChannel()

        nc.notification_type = record.attribute("notification_type")
        nc.channel = client.bot.get_channel(int(record.attribute("channel_id")))
        nc.nation_name = record.attribute("object_name")

        ignore_if_resident = record.attribute("ignore_if_resident")
        nc.ignore_if_resident = True if ignore_if_resident == 1 else False

        return nc

class Notifications():
    def __init__(self, client: Client):
        self.client = client

        self._players_ignore : dict[str, list[object.Player]] = {}# "town":Player, Player

    async def add_notification_channel(self, channel : discord.TextChannel, notification_type : str, nation_name : str, ignore_if_resident : bool):
        await self.client.notifications_table.add_record(
            [
                notification_type,
                channel.guild.id,
                channel.id,
                nation_name,
                int(ignore_if_resident)
            ]
        )
    
    async def update_notifications_channel(self, channel : discord.TextChannel, notification_type : str, nation_name : str, ignore_if_resident : bool):
        await self.client.notifications_table.update_record(
            [db.CreationCondition("channel_id", channel.id), db.CreationCondition("notification_type", notification_type)],
            *[
                notification_type,
                channel.guild.id,
                channel.id,
                nation_name,
                int(ignore_if_resident)
            ]
        )
    
    async def does_notification_channel_exist(self, channel : discord.TextChannel, notification_type : str):
        return await self.client.notifications_table.record_exists(*[db.CreationCondition("channel_id", channel.id), db.CreationCondition("notification_type", notification_type)])

    async def delete_notifications_channel(self, channel : discord.TextChannel = None, notification_type : str = None):
        c = []
        if notification_type:
            c.append(db.CreationCondition("notification_type", notification_type))
        if channel:
            c.append(db.CreationCondition("channel_id", channel.id))
        return await self.client.notifications_table.delete_records(*c)

    
    async def get_notification_channels(self, channel : discord.TextChannel = None, notification_type : str = None):
        c = []
        if notification_type:
            c.append(db.CreationCondition("notification_type", notification_type))
        if channel:
            c.append(db.CreationCondition("channel_id", channel.id))
        
        notification_channels_records = await self.client.notifications_table.get_records(
            conditions=c
        )

        
        notification_channels : list[NotificationChannel] = []

        for record in notification_channels_records:
            nc = NotificationChannel.from_record(self.client, record)
            if nc.channel:
                notification_channels.append(nc)
        
        return notification_channels
    
    async def refresh(self):
        channels = await self.client.notifications.get_notification_channels()

        for town_name, players in self.client.world.towns_with_players.items():
            
            town = self.client.world.get_town(town_name)
            ignore_players = self._players_ignore.get(town_name) or []

            for channel in channels:
                if town.nation and channel.notification_type == "territory_enter" and channel.nation_name == town.nation.name:
                    for player in players:
                        if player in ignore_players:
                            continue
                
                        likely_residency = await player.likely_residency
                        likely_residency_nation = likely_residency.nation if likely_residency else "None"

                        if channel.ignore_if_resident and likely_residency == town:
                            continue
                            
                        embed = discord.Embed(title="Player entered territory", color=s.embed)
                        embed.add_field(name="Player name", value=player.name)
                        embed.add_field(name="Coordinates", value=f"[{int(player.location.x)}, {int(player.location.y)}, {int(player.location.z)}]({self.client.url}?x={int(player.location.x)}&z={int(player.location.z)}&zoom={s.map_link_zoom})")
                        embed.add_field(name="Town", value=town.name_formatted)
                        embed.add_field(name="Likely residency", value=f"{likely_residency} ({likely_residency_nation})" if likely_residency else "Unknown")
                        embed.set_thumbnail(url=player.avatar_url)

                        try:
                            await channel.channel.send(embed=embed)
                        except:
                            pass

                        

                        if town_name not in self._players_ignore:
                            self._players_ignore[town_name] = []
                        
                        if player not in self._players_ignore[town_name]:
                            self._players_ignore[town_name].append(player)
        
        for town_name, players in self._players_ignore.copy().items():
            if town_name not in self.client.world.towns_with_players:
                del self._players_ignore[town_name]
            else:
                for player in players:
                    if player not in self.client.world.towns_with_players[town_name]:
                        self._players_ignore[town_name].remove(player)


def top_rankings_to_text(rankings : dict, object_name : str, notable_only = True) -> str:
    notable_statistics = ""
    for (leaderboard), (value, ranking, notable) in rankings.items():
        if notable: notable_statistics += f"\n- {object_name} is **#{ranking}** on the **{leaderboard.replace('_', ' ')}** ranking"
    if not notable_only or notable_statistics == "": notable_statistics = "None"

    return notable_statistics