
import aiohttp
from client import errors, image_generator, notifications, migrate, objects, funcs, refresh
from client.continents import continents

import datetime
from client.objects import properties
import setup as s

import db
from db import wrapper

from discord.ext import commands

import shutil
import os

import asyncio 

class Client():
    def __init__(self):

        self.refresh_no : int = 0
        self.dynmap_update_timestamp = 0
        self.messages_sent = 0
        
        self.session : aiohttp.ClientSession= None
        self.database = db.Database("towny.db", auto_commit=False)
        self.bot : commands.Bot = None
        self.url = "https://map.rulercraft.com"

        self.towns_table : wrapper.Table = []
        self.players_table : wrapper.Table = []
        self.visited_towns_table : wrapper.Table = []

        self.refresh_period : dict[str, int] = s.default_refresh_period
        self.last_refreshed : dict[str, datetime.datetime] = {k:None for k in s.default_refresh_period}
        self.world = objects.World(self) 
        self.notifications = notifications.Notifications(self)

        self.image_generator = image_generator.ImageGenerator(self)
    
    errors = errors
    objects = objects 
    continents = continents
    funcs = funcs

    async def init_db(self, update_coro = None):
        await self.database.connect()
        await self.database.connection.execute("PRAGMA auto_vacuum = FULL")

        await self.database.connection.execute('PRAGMA journal_mode = WAL')
        await self.database.connection.execute('PRAGMA synchronous = 1')
        await self.database.connection.execute('PRAGMA cache_size = -64000')
        

        self.global_table = await self.database.create_or_get_table(
            db.CreationTable(
                "global",
                [
                    "name STRING PRIMARY KEY",
                    "value"
                ]
            )
        )

        self.towns_table = await self.database.create_or_get_table(
            db.CreationTable(
                "towns",
                [
                    "name STRING PRIMARY KEY",
                    "nation STRING",
                    "religion STRING",
                    "culture STRING",
                    "mayor STRING",
                    "resident_count INTEGER",
                    "founded_date DATE",
                    "resident_tax REAL",
                    "bank REAL",
                    "mayor_bank REAL",
                    "public INTEGER",
                    "peaceful INTEGER",
                    "area INTEGER",
                    "mentions INTEGER",
                    "outposts INTEGER",
                    "visited_players INTEGER",
                    "duration INTEGER",
                    "last_seen TIMESTAMP"
                ]
            )
        )

        self.players_table = await self.database.create_or_get_table(
            db.CreationTable(
                "players",
                [
                    "name STRING PRIMARY KEY",
                    "location STRING",
                    "town STRING",
                    "armor INTEGER",
                    "health INTEGER",
                    "visited_towns INTEGER",
                    "nickname STRING",
                    "bank REAL",
                    "messages INTEGER",
                    "mentions INTEGER",
                    "duration INTEGER",
                    "last TIMESTAMP"
                ]
            )
        )

        self.objects_table = await self.database.create_or_get_table(
            db.CreationTable(
                "objects",
                [
                    "type STRING",
                    "name STRING",
                    "towns INTEGER",
                    "town_balance REAL",
                    "residents INTEGER",
                    "area INTEGER",
                    "mentions INTEGER",
                    "duration INTEGER",
                    "last TIMESTAMP",
                    "PRIMARY KEY(type, name)"
                ]
            )
        )

        self.visited_towns_table = await self.database.create_or_get_table(
            db.CreationTable(
                "visited_towns",
                [
                    "player STRING",
                    "town STRING",
                    "duration INTEGER",
                    "last TIMESTAMP",
                    "PRIMARY KEY(player, town)"
                ]
            )
        )

        self.town_history_table = await self.database.create_or_get_table(
            db.CreationTable(
                "town_history",
                [
                    "town STRING",
                    "date DATE",
                    "nation STRING",
                    "religion STRING",
                    "culture STRING",
                    "mayor STRING",
                    "resident_count INTEGER",
                    "resident_tax REAL",
                    "bank REAL",
                    "public INTEGER",
                    "peaceful INTEGER",
                    "area INTEGER",
                    "duration INTEGER",
                    "visited_players INTEGER",
                    "current_name STRING",
                    "mentions INTEGER",
                    "PRIMARY KEY (town, date)"
                ]
            )
        )

        self.town_day_history_table = await self.database.create_or_get_table(
            db.CreationTable(
                "town_day_history",
                [
                    "town STRING",
                    "time TIMESTAMP",
                    "resident_count INTEGER",
                    "resident_tax REAL",
                    "bank REAL",
                    "area INTEGER",
                    "duration INTEGER",
                    "visited_players INTEGER",
                    "PRIMARY KEY (town, time)"
                ]
            )
        )

        self.player_history_table = await self.database.create_or_get_table(
            db.CreationTable(
                "player_history",
                [
                    "player STRING",
                    "date DATE",
                    "duration INTEGER",
                    "visited_towns INTEGER",
                    "likely_town STRING",
                    "likely_nation STRING",
                    "bank REAL",
                    "messages INTEGER",
                    "mentions INTEGER",
                    "PRIMARY KEY (player, date)"
                ]
            )
        )

        self.player_day_history_table = await self.database.create_or_get_table(
            db.CreationTable(
                "player_day_history",
                [
                    "player STRING",
                    "time TIMESTAMP",
                    "duration INTEGER",
                    "bank REAL",
                    "visited_towns INTEGER",
                    "PRIMARY KEY(player, time)"
                ]
            )
        )

        self.nation_history_table = await self.database.create_or_get_table(
            db.CreationTable(
                "nation_history",
                [
                    "nation STRING",
                    "date STRING",
                    "towns INTEGER",
                    "town_balance REAL",
                    "residents INTEGER",
                    "capital STRING",
                    "leader STRING",
                    "area INTEGER",
                    "duration INTEGER",
                    "current_name STRING",
                    "mentions INTEGER",
                    "PRIMARY KEY(nation, date)"
                ]
            )
        )

        self.nation_day_history_table = await self.database.create_or_get_table(
            db.CreationTable(
                "nation_day_history",
                [
                    "nation STRING",
                    "time TIMESTAMP",
                    "towns INTEGER",
                    "town_balance REAL",
                    "residents INTEGER",
                    "area INTEGER",
                    "duration INTEGER",
                    "PRIMARY KEY(nation, time)"
                ]
            )
        )

        self.global_history_table = await self.database.create_or_get_table(
            db.CreationTable(
                "global_history",
                [
                    "date DATE PRIMARY KEY",
                    "towns INTEGER",
                    "residents INTEGER",
                    "nations INTEGER",
                    "town_value REAL",
                    "mayor_value REAL",
                    "area INTEGER",
                    "known_players INTEGER",
                    "activity INTEGER",
                    "messages INTEGER",
                    "database_size REAL"
                ]
            )
        )

        self.global_day_history_table = await self.database.create_or_get_table(
            db.CreationTable(
                "global_day_history",
                [
                    "time TIMESTAMP PRIMARY KEY",
                    "towns INTEGER",
                    "residents INTEGER",
                    "nations INTEGER",
                    "town_value REAL",
                    "area INTEGER",
                    "known_players INTEGER",
                    "activity INTEGER",
                    "messages INTEGER",
                    "online_players INTEGER"
                ],
            )
        )

        self.object_history_table = await self.database.create_or_get_table(
            db.CreationTable(
                "object_history",
                [
                    "date DATE",
                    "type STRING",
                    "object STRING",
                    "towns INTEGER",
                    "town_balance REAL",
                    "residents INTEGER",
                    "area INTEGER",
                    "mentions INTEGER",
                    "PRIMARY KEY(date, type, object)"
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
                    "object_type STRING",
                    "object_name STRING",
                    "duration INTEGER DEFAULT 0",
                    "last TIMESTAMP",
                    "PRIMARY KEY (object_type, object_name)"
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

        self.chat_message_counts_table = await self.database.create_or_get_table(
            db.CreationTable(
                "chat_message_counts",
                [
                    "player STRING PRIMARY KEY",
                    "amount INTEGER",
                    "last TIMESTAMP"
                ]
            )
        )

        self.chat_mentions_table = await self.database.create_or_get_table(
            db.CreationTable(
                "chat_mentions",
                [
                    "object_type STRING",
                    "object_name STRING",
                    "amount INTEGER",
                    "last TIMESTAMP",
                    "PRIMARY KEY(object_type, object_name)"
                ]
            )
        )

        if update_coro:
            await update_coro

        
        #await self.database.connection.execute('PRAGMA synchronous = OFF')
        
        
    @property 
    async def tracking_footer(self):
        return f"Tracked: game for {(await self.world.total_tracked).str_no_timestamp()}, chat for {(await self.world.total_tracked_chat).str_no_timestamp()}"
    
    @property 
    async def db_version(self) -> int:

        val = await (await self.database.connection.execute("SELECT value FROM global WHERE name='db_version'")).fetchone()
        return val[0] if val else 0

    

    async def create_session(self):
        if not self.session:
            self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5))



    async def fetch_world(self):

        await self.create_session()

        map_data = await self.session.get(f"{s.refresh_map_url}/tiles/_markers_/marker_RulerEarth.json")

        if map_data.status == 502:
            return False
        
        await refresh.main_refresh(self.world, map_data.content)
    
    async def fetch_short(self):
        
        # Mentions

        r = await self.session.get(f"{s.refresh_map_url}/up/world/RulerEarth/{self.dynmap_update_timestamp+1}")

        if r.status == 502:
            return False

        await refresh.refresh_short(self.world, r.content)
        
                            
        

    async def cull_db(self):

        await self.player_day_history_table.delete_records([db.CreationCondition("time", datetime.datetime.now()-datetime.timedelta(days=1), "<")])
        await self.town_day_history_table.delete_records([db.CreationCondition("time", datetime.datetime.now()-datetime.timedelta(days=1), "<")])
        await self.nation_day_history_table.delete_records([db.CreationCondition("time", datetime.datetime.now()-datetime.timedelta(days=1), "<")])
        await self.global_day_history_table.delete_records([db.CreationCondition("time", datetime.datetime.now()-datetime.timedelta(days=1), "<")])

        await self.players_table.delete_records([db.CreationCondition("last", datetime.datetime.now()-s.cull_players_from, "<")])
        await self.towns_table.delete_records([db.CreationCondition("last_seen", datetime.datetime.now()-s.cull_objects_after, "<")])

        await self.database.connection.execute("DELETE FROM visited_towns WHERE player IN (SELECT visited_towns.player FROM visited_towns LEFT JOIN players ON visited_towns.player=players.name WHERE players.name IS NULL) AND duration < 300;")
        await self.database.connection.execute("DELETE FROM player_history WHERE player IN (SELECT player_history.player FROM player_history LEFT JOIN players ON player_history.player=players.name JOIN activity ON activity.object_name=player_history.player WHERE players.name IS NULL AND activity.duration < 1000);")
        
        # Abstract history tables, remove some old data which is not needed anymore
        for object_type in ["player", "town", "nation", "object"]:
            for threshold_time, days_of_6 in s.history_abstraction_thresholds:
                await self.database.connection.execute(f"DELETE FROM {object_type}_history WHERE (julianday(date)-julianday('2021-10-29')) % 6 IN ({days_of_6}) AND date<?", (datetime.datetime.now()-threshold_time,))
        

        await self.flags_table.delete_records([db.CreationCondition("object_type", "nation"), db.CreationField.external_query(self.objects_table, "object_name", db.CreationCondition("type", "nation"), operator="NOT IN")])

        sent = 0

        for player in self.world.players.copy():
            if not await player.exists_in_db:
                self.world._remove_player(player.name)
        for town in self.world.towns.copy():
            if not await town.exists_in_db:
                sent += 1
                if sent <= 10: await self.bot.get_channel(s.alert_channel).send(f"Removed town {town.name}")
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

            await self.database.connection.execute("UPDATE chat_message_counts SET player=? WHERE player=?", (obj.name, old_object_name))
            await self.database.connection.execute("UPDATE chat_mentions SET object_name=? WHERE object_name=? AND object_type='player'", (obj.name, old_object_name))

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

            await self.database.connection.execute("UPDATE chat_mentions SET object_name=? WHERE object_name=? AND object_type='town'", (obj.name, old_object_name))

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

            await self.database.connection.execute("UPDATE notifications SET object_name=? WHERE object_name=?", (obj.name, old_object_name))

            await self.database.connection.execute("UPDATE chat_mentions SET object_name=? WHERE object_name=? AND object_type='nation'", (obj.name, old_object_name))

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

    

            





