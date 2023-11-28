
import aiohttp
from client import object, funcs, errors
import json

import datetime
import setup as s

import db
from db import wrapper

import discord
from discord.ext import commands

import shutil
import os

class Client():
    def __init__(self):

        self.refresh_no : int = 0
        
        self.session : aiohttp.ClientSession= None
        self.database = db.Database("towny.db", auto_commit=False)
        self.bot : commands.Bot = None
        self.url = s.map_url

        self.towns_table : wrapper.Table = []
        self.players_table : wrapper.Table = []
        self.visited_towns_table : wrapper.Table = []

        self.refresh_period = s.default_refresh_period
        self.last_refreshed : datetime.datetime = None
        self.world = object.World(self) 
        self.notifications = Notifications(self)

    async def init_db(self, update_coro = None):
        await self.database.connect()
        await self.database.connection.execute("PRAGMA auto_vacuum = FULL")

        if update_coro:
            await update_coro

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
                    db.CreationAttribute("visited_players", db.types.Int),
                    db.CreationAttribute("duration", db.types.Int),
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
                    db.CreationAttribute("visited_towns", db.types.Int),
                    db.CreationAttribute("donator", db.types.Int),
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
                    db.CreationAttribute("duration", db.types.Int),
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
                    db.CreationAttribute("duration", db.types.Int),
                    db.CreationAttribute("visited_players", db.types.Int),
                    db.CreationAttribute("current_name", db.types.String)
                ]
            )
        )

        self.town_day_history_table = await self.database.create_or_get_table(
            db.CreationTable(
                "town_day_history",
                [
                    db.CreationAttribute("town", db.types.String),
                    db.CreationAttribute("time", db.types.Datetime),
                    db.CreationAttribute("resident_count", db.types.Int),
                    db.CreationAttribute("resident_tax", db.types.Float),
                    db.CreationAttribute("bank", db.types.Float),
                    db.CreationAttribute("area", db.types.Int),
                    db.CreationAttribute("duration", db.types.Int),
                    db.CreationAttribute("visited_players", db.types.Int)
                ]
            )
        )

        self.player_history_table = await self.database.create_or_get_table(
            db.CreationTable(
                "player_history",
                [
                    db.CreationAttribute("player", db.types.String),
                    db.CreationAttribute("date", db.types.Date),
                    db.CreationAttribute("duration", db.types.Int),
                    db.CreationAttribute("visited_towns", db.types.Int),
                    db.CreationAttribute("likely_town", db.types.String),
                    db.CreationAttribute("likely_nation", db.types.String),
                ]
            )
        )

        self.player_day_history_table = await self.database.create_or_get_table(
            db.CreationTable(
                "player_day_history",
                [
                    db.CreationAttribute("player", db.types.String),
                    db.CreationAttribute("time", db.types.Datetime),
                    db.CreationAttribute("duration", db.types.Int),
                    db.CreationAttribute("visited_towns", db.types.Int)
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
                    db.CreationAttribute("area", db.types.Int),
                    db.CreationAttribute("duration", db.types.Int),
                    db.CreationAttribute("current_name", db.types.String)
                ]
            )
        )

        self.nation_day_history_table = await self.database.create_or_get_table(
            db.CreationTable(
                "nation_day_history",
                [
                    db.CreationAttribute("nation", db.types.String),
                    db.CreationAttribute("time", db.types.Datetime),
                    db.CreationAttribute("towns", db.types.Int),
                    db.CreationAttribute("town_balance", db.types.Float),
                    db.CreationAttribute("residents", db.types.Int),
                    db.CreationAttribute("area", db.types.Int),
                    db.CreationAttribute("duration", db.types.Int),
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
                    db.CreationAttribute("known_players", db.types.Int),
                    db.CreationAttribute("activity", db.types.Int)
                ]
            )
        )

        self.global_day_history_table = await self.database.create_or_get_table(
            db.CreationTable(
                "global_day_history",
                [
                    db.CreationAttribute("time", db.types.Datetime),
                    db.CreationAttribute("towns", db.types.Int),
                    db.CreationAttribute("residents", db.types.Int),
                    db.CreationAttribute("nations", db.types.Int),
                    db.CreationAttribute("town_value", db.types.Float),
                    db.CreationAttribute("area", db.types.Int),
                    db.CreationAttribute("known_players", db.types.Int),
                    db.CreationAttribute("activity", db.types.Int)
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

        self.activity_table = await self.database.create_or_get_table(
            db.CreationTable(
                "activity",
                [
                    db.CreationAttribute("object_type", db.types.String),
                    db.CreationAttribute("object_name", db.types.String),
                    db.CreationAttribute("duration", db.types.Int),
                    db.CreationAttribute("last", db.types.Datetime)
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

        #await self.database.connection.execute('PRAGMA synchronous = OFF')
        await self.database.connection.execute('PRAGMA journal_mode = WAL')
        

    async def create_session(self):
        if not self.session:
            self.session = aiohttp.ClientSession()


    async def fetch_world(self):
        

        await self.create_session()

        map = await self.session.get(f"{self.url}/up/world/RulerEarth/0")
        map_data = await self.session.get(f"{self.url}/tiles/_markers_/marker_RulerEarth.json")

        if map.status == 502 or map_data.status == 502:
            return False
        

        await self.world.refresh(map.content, map_data.content)
    
    async def cull_db(self):

        await self.player_day_history_table.delete_records([db.CreationCondition("time", datetime.datetime.now()-datetime.timedelta(days=1), "<")])
        await self.town_day_history_table.delete_records([db.CreationCondition("time", datetime.datetime.now()-datetime.timedelta(days=1), "<")])
        await self.nation_day_history_table.delete_records([db.CreationCondition("time", datetime.datetime.now()-datetime.timedelta(days=1), "<")])
        await self.global_day_history_table.delete_records([db.CreationCondition("time", datetime.datetime.now()-datetime.timedelta(days=1), "<")])

        await self.players_table.delete_records([db.CreationCondition("last", datetime.datetime.now()-s.cull_players_from, "<")])
        await self.towns_table.delete_records([db.CreationCondition("last_seen", datetime.datetime.now()-s.cull_objects_after, "<")])
        

        await self.flags_table.delete_records([db.CreationCondition("object_type", "nation"), db.CreationField.external_query(self.objects_table, "object_name", db.CreationCondition("type", "nation"), operator="NOT IN")])

        sent = 0

        for player in self.world.players.copy():
            if not await player.exists_in_db:
                self.world._remove_player(player.name)
        for town in self.world.towns.copy():
            if not await town.exists_in_db:
                await self.bot.get_channel(s.alert_channel).send(f"Removed town {town.name}")
                self.world._remove_town(town.name)
                for t in self.world.towns:
                    if t.spawn.x == town.spawn.x and t.spawn.z == town.spawn.z:
                        sent += 1
                        if sent <= 10: await self.bot.get_channel(s.alert_channel).send(f"Is this town the same as  {t.name}?")
                        await self.merge_objects("town", town.name, t.name)
                
                
        for nation in self.world.nations.copy():
            
            if not nation.capital:
                nation_info = await self.nation_history_table.get_record([db.CreationCondition("nation", nation.name)], order=db.CreationOrder("date", db.types.OrderDescending))
                if not nation_info:
                    nation_info = await self.objects_table.get_record([db.CreationCondition("name", nation.name), db.CreationCondition("type", "nation")])
                self.world._remove_nation(nation.name)
                sent += 1
                if sent <= 10:
                    if not nation_info:
                        return await self.bot.get_channel(s.alert_channel).send(f"Removed nation {nation.name}. Couldn't find history info")
                    await self.bot.get_channel(s.alert_channel).send(f"Removed nation {nation.name} {nation_info.attribute('towns')} {nation_info.attribute('residents')}")
                
                for n in self.world.nations:
                    if len(n.towns) == nation_info.attribute("towns") and n.total_residents == nation_info.attribute("residents") and n.capital and (n.capital.name == nation_info.attribute("capital") or n.total_area == nation_info.attribute("area")):
                        sent += 1
                        if sent <= 10: await self.bot.get_channel(s.alert_channel).send(f"Is this nation the same as  {n.name}?")
                        await self.merge_objects("nation", nation.name, n.name)
                        break
        
        if sent > 10:
            await self.bot.get_channel(s.alert_channel).send("... + more")

        # Must be done after because accesssed in cull
        await self.objects_table.delete_records([db.CreationCondition("last", datetime.datetime.now()-s.cull_objects_after, "<")])
    
    async def test(self):

        for i in range(15):
            num = (i+1)*35
            await self.database.connection.execute(f"INSERT INTO town_history(town, date, nation, religion, culture, mayor, resident_count, resident_tax, bank, public, peaceful, area, duration, visited_players, current_name) SELECT town, DATE(date, '+{num} days'), nation, religion, culture, mayor, resident_count, resident_tax, bank, public, peaceful, area, duration, visited_players, current_name FROM town_history WHERE date <= ?", (datetime.date.today(),))
    
    async def backup_db_if_not(self):
        epoch = datetime.date(2022, 1, 1)
        td = datetime.date.today()
        backup_name = f"backups/towny_{(td-epoch).days}_{td.year}_{td.month}_{td.day}.db"
        if not os.path.exists(backup_name):
            shutil.copyfile("towny.db", backup_name)
    
    async def merge_objects(self, object_type : str, old_object_name : str, new_object_name : str):
        
        if object_type == "player":
            obj = self.world.get_player(new_object_name)
        elif object_type == "town":
            obj = self.world.get_town(new_object_name)
        elif object_type == "nation":
            obj = self.world.get_nation(new_object_name)

        if not obj:
            raise errors.MildError(f"{object_type.title()} not found")

        # Merge system. Probably overcomplicated but it works 

        # Firstly merge activity. Same for all so can be reused
        old_activity = await self.activity_table.get_record([db.CreationCondition("object_type", object_type), db.CreationCondition("object_name", old_object_name)], ["duration", "last"]) 
        await self.activity_table.delete_records([db.CreationCondition("object_type", object_type), db.CreationCondition("object_name", old_object_name)]) 
        in_new = self.activity_table.record_exists(*[db.CreationCondition("object_type", object_type), db.CreationCondition("object_name", obj.name)])
        if in_new:
            await self.activity_table.update_records([db.CreationCondition("object_type", object_type), db.CreationCondition("object_name", obj.name)], [object_type, obj.name, db.CreationField.add("duration", old_activity.attribute("duration")), db.CreationField("last", old_activity.attribute("last"))])
        else:
            await self.activity_table.add_record([object_type, obj.name, old_activity.attribute("total"), old_activity.attribute("last")])

        if object_type == "player":
            old_duration = (await self.player_history_table.get_record([db.CreationCondition("player", old_object_name)], [self.player_history_table.attribute("duration")], order=db.CreationOrder("date", db.types.OrderDescending))).attribute("duration")

            # Update flag table
            await self.flags_table.delete_records([db.CreationCondition("object_type", "player"), db.CreationCondition("object_name", obj.name)]) 
            await self.flags_table.update_records([db.CreationCondition("object_type", "player"), db.CreationCondition("object_name", old_object_name)], [db.CreationField(self.flags_table.attribute("object_name"), new_object_name)])

            # Iterate over old history records. If not under new name, add it. Otherwise, remove old
                # Add to new player records with old duration
            for record in await self.player_history_table.get_records([db.CreationCondition("player", obj.name)], order=db.CreationOrder("date", db.types.OrderAscending)):
                old_duration_at_point = await self.player_history_table.get_record([db.CreationCondition("player", old_object_name), db.CreationCondition("date", record.attribute("date"), "<=")], order=db.CreationOrder("date", db.types.OrderDescending))
                #if old_duration_at_point: await record.update(db.CreationField.add("duration", old_duration_at_point.attribute("duration")))
                if old_duration_at_point: await self.player_history_table.update_records([db.CreationCondition("player", obj.name), db.CreationCondition("date", record.attribute("date"))], [db.CreationField.add("duration", old_duration_at_point.attribute("duration"))])
            # Iterate over old records. If exists for new player, remove
            for record in await self.player_history_table.get_records([db.CreationCondition("player", old_object_name)], order=db.CreationOrder("date", db.types.OrderAscending)):
                if not await self.player_history_table.record_exists(db.CreationCondition("player", obj.name), db.CreationCondition("date", record.attribute("date"))):
                    await self.player_history_table.update_records([db.CreationCondition("player", old_object_name), db.CreationCondition("date", record.attribute("date"))], [db.CreationField("player", obj.name)]) 
                else:
                    await record.delete()
            # if duplicates exist, merge data
            for record in await self.visited_towns_table.get_records([db.CreationCondition("player", old_object_name)]):
                rec = await self.visited_towns_table.get_record([db.CreationCondition("player", obj.name), db.CreationCondition("town", record.attribute("town"))])
                if not rec:
                    await record.update([db.CreationField("player", obj.name)]) 
                else:
                    dur = record.attribute("duration")
                    await record.delete()
                    await rec.update(db.CreationField.add("duration", dur))

            await self.players_table.update_records([db.CreationCondition("name", obj.name)], [db.CreationField.add("duration", old_duration)])

            await self.players_table.delete_records([db.CreationCondition("name", old_object_name)])

            await self.town_history_table.update_records([db.CreationCondition("mayor", old_object_name)], db.CreationField("mayor", obj.name))
            await self.nation_history_table.update_records([db.CreationCondition("leader", old_object_name)], db.CreationField("leader", obj.name))
        elif object_type == "town":
            old_duration = (await self.town_history_table.get_record([db.CreationCondition("town", old_object_name)], [self.town_history_table.attribute("duration")], order=db.CreationOrder("date", db.types.OrderDescending))).attribute("duration")

            # Update flag table
            await self.flags_table.delete_records([db.CreationCondition("object_type", "town"), db.CreationCondition("object_name", obj.name)]) 
            await self.flags_table.update_records([db.CreationCondition("object_type", "town"), db.CreationCondition("object_name", old_object_name)], [db.CreationField(self.flags_table.attribute("object_name"), new_object_name)])

            # Iterate over old history records. If not under new name, add it. Otherwise, remove old
            for record in await self.town_history_table.get_records([db.CreationCondition("town", obj.name)], order=db.CreationOrder("date", db.types.OrderAscending)):
                old_duration_at_point = await self.town_history_table.get_record([db.CreationCondition("town", old_object_name), db.CreationCondition("date", record.attribute("date"), "<=")], order=db.CreationOrder("date", db.types.OrderDescending))
                #if old_duration_at_point: await record.update(db.CreationField.add("duration", old_duration_at_point.attribute("duration")))
                if old_duration_at_point: await self.town_history_table.update_records([db.CreationCondition("town", obj.name), db.CreationCondition("date", record.attribute("date"))], [db.CreationField.add("duration", old_duration_at_point.attribute("duration"))])
                # Iterate over old records. If exists for new town, remove
            for record in await self.town_history_table.get_records([db.CreationCondition("town", old_object_name)]):
                if not await self.town_history_table.record_exists(db.CreationCondition("town", obj.name), db.CreationCondition("date", record.attribute("date"))):
                    await self.town_history_table.update_records([db.CreationCondition("town", old_object_name), db.CreationCondition("date", record.attribute("date"))], [db.CreationField("town", obj.name)]) 
                else:
                    await record.delete()
            
            # If duplicate exists, merge data
            for record in await self.visited_towns_table.get_records([db.CreationCondition("town", old_object_name)]):
                rec = await self.visited_towns_table.get_record([db.CreationCondition("town", obj.name), db.CreationCondition("player", record.attribute("player"))])
                if not rec:
                    await record.update([db.CreationField("town", obj.name)]) 
                else:
                    dur = record.attribute("duration")
                    await record.delete()
                    await rec.update(db.CreationField.add("duration", dur))
            
            # Update main record
            await self.towns_table.delete_records([db.CreationCondition("name", old_object_name)])

            await self.nation_history_table.update_records([db.CreationCondition("capital", old_object_name)], db.CreationField("capital", obj.name))
            await self.player_history_table.update_records([db.CreationCondition("likely_town", old_object_name)], db.CreationField("likely_town", obj.name))
        elif object_type == "nation":

            # Update flags: 1. Delete flags if already exist 2. Update old name
            await self.flags_table.delete_records([db.CreationCondition("object_type", "nation"), db.CreationCondition("object_name", obj.name)]) 
            await self.flags_table.update_records([db.CreationCondition("object_type", "nation"), db.CreationCondition("object_name", old_object_name)], [db.CreationField(self.flags_table.attribute("object_name"), new_object_name)])
            
            # Iterate over old history records. If not under new name, add it. Otherwise, remove old
            for record in await self.nation_history_table.get_records([db.CreationCondition("nation", obj.name)], order=db.CreationOrder("date", db.types.OrderAscending)):
                old_duration_at_point = await self.nation_history_table.get_record([db.CreationCondition("nation", old_object_name), db.CreationCondition("date", record.attribute("date"), "<=")], order=db.CreationOrder("date", db.types.OrderDescending))
                #await record.update(db.CreationField.add("duration", old_duration_at_point.attribute("duration")))
                if old_duration_at_point: await self.nation_history_table.update_records([db.CreationCondition("nation", obj.name), db.CreationCondition("date", record.attribute("date"))], [db.CreationField.add("duration", old_duration_at_point.attribute("duration"))])
            # Iterate over old records. If exists for new nation, remove
            for record in await self.nation_history_table.get_records([db.CreationCondition("nation", old_object_name)]):
                if not await self.nation_history_table.record_exists(db.CreationCondition("nation", obj.name), db.CreationCondition("date", record.attribute("date"))):
                    await self.nation_history_table.update_records([db.CreationCondition("nation", old_object_name), db.CreationCondition("date", record.attribute("date"))], [db.CreationField("nation", obj.name)]) 
                else:
                    await record.delete()
            
            await self.town_history_table.update_records([db.CreationCondition("nation", old_object_name)], db.CreationField("nation", obj.name))
            await self.player_history_table.update_records([db.CreationCondition("likely_nation", old_object_name)], db.CreationField("likely_nation", obj.name))

    
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
        nc.ignore_if_resident = True if str(ignore_if_resident) == "1" else False

        return nc

class Notifications():
    def __init__(self, client: Client):
        self.client = client

        self._players_ignore : dict[str, dict[str, int]] = {}# "town":{"player":[0, msg]}

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
            ignore_players = self._players_ignore.get(town_name) or {}
            if not town:
                continue

            for channel in channels:
                if town.nation and channel.notification_type == "territory_enter" and channel.nation_name == town.nation.name:
                    for player in players:
                        if player.name in ignore_players:
                            continue
                
                        likely_residency = await player.likely_residency
                        likely_residency_nation = likely_residency.nation.name_formatted if likely_residency and likely_residency.nation else "None"

                        
                        if channel.ignore_if_resident and likely_residency and likely_residency.nation == town.nation:
                            continue
                            
                        embed = discord.Embed(title="Player entered territory", color=s.embed)
                        embed.add_field(name="Player name", value=discord.utils.escape_markdown(player.name))
                        embed.add_field(name="Coordinates", value=f"[{int(player.location.x)}, {int(player.location.y)}, {int(player.location.z)}]({self.client.url}?x={int(player.location.x)}&z={int(player.location.z)}&zoom={s.map_link_zoom})")
                        embed.add_field(name="Town", value=town.name_formatted)
                        embed.add_field(name="Likely residency", value=f"{likely_residency} ({likely_residency_nation})" if likely_residency else "Unknown")
                        embed.add_field(name="Time spent", value="This will be edited when they exit")
                        embed.set_thumbnail(url=await player.face_url)

                        try:
                            msg = await channel.channel.send(embed=embed)
                        except:
                            msg = None

                        if town_name not in self._players_ignore:
                            self._players_ignore[town_name] = {}
                        
                        if player.name not in self._players_ignore[town_name]:
                            self._players_ignore[town_name][player.name] = [0, msg]
                        
                        self._players_ignore[town_name][player.name][0] += self.client.refresh_period
        
        for town_name, players in self._players_ignore.copy().items():

            for player in players.copy():
                time : int = self._players_ignore[town_name][player][0]
                msg : discord.Message = self._players_ignore[town_name][player][1]
                    
                if not self.client.world.towns_with_players.get(town_name) or player not in self.client.world.towns_with_players[town_name]:
                    if msg:
                        embed = msg.embeds[0]
                        embed.set_field_at(4, name="Time spent", value=f"In town for {funcs.generate_time(time)}")
                        try:
                            await msg.edit(embed=embed)
                        except Exception as e:
                            print(e)

                    del self._players_ignore[town_name][player]
            
            if len(self._players_ignore[town_name]) == 0:
                del self._players_ignore[town_name]
            





