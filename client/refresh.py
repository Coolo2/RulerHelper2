from __future__ import annotations
import typing
if typing.TYPE_CHECKING:
    import client as client_pre

from aiohttp import StreamReader
import ijson.backends.yajl2_c as ijson

import setup as s 
import traceback 
from shapely.geometry import Point
import datetime 
import discord
import sqlite3
import asyncio

class SQLStatement():
    def __init__(self, statement : str):
        self.statement = statement 

        self.bindings = []

    def add_binding_set(self, bindings : tuple):
        self.bindings.append(bindings)
    
    async def execute(self, connection : sqlite3.Connection):

        # Slightly slower (0.4s) to not use executemany, however doens't block. 
        for binding in self.bindings:
            await asyncio.sleep(0.001)
            try:
                await connection.execute(self.statement, binding)
            except sqlite3.IntegrityError as e:
                print("INtegrityError:", str(e))


async def main_refresh(world : client_pre.objects.World, map_data : StreamReader):
    await update_town_list(world, map_data)
    await update_tracking(world)
    

async def update_town_list(world : client_pre.objects.World, map_data):
    
    objects_map_data = ijson.items_async(map_data, "sets.towny.markerset", use_float=True)
    areas = {}
    markers = {}
    async for o in objects_map_data:
        await asyncio.sleep(0)
        areas = o['areas']
        markers = o['markers']

    outposts = {}

    for marker_id, marker_data in markers.items():
        if "_Outpost_" in marker_id:
            town_name = marker_id.split("_Outpost_")[0]
            if town_name not in outposts:
                outposts[town_name] = []
            outposts[town_name].append(Point(marker_data["x"], marker_data["y"], marker_data["z"]))
    
    for town in world.towns:
        town.clear_areas()
    
    for area_name, area in areas.items():
        if area.get("set") != "siegewar.markerset":
            
            
            try:
                
                if area["label"] in s.DONT_TRACK_TOWNS:
                    continue 

                if True in [su in area["label"] for su in s.DEFAULT_TOWNS_SUBSTRING]:
                    continue
                
                t = world.get_town(area["label"], False)
                if not t :
                    
                    t = world.client.objects.Town(world)
                    await t.add_area(area_name, area)
                    
                    if markers.get(f"{t.name}__home"):
                        world.set_town(area["label"], t)
                else:
                    await t.add_area(area_name, area)
                
                if markers.get(f"{t.name}__home"):
                    await t.set_marker(markers[f"{t.name}__home"])

                if t.name in outposts:
                    await t.set_outposts(outposts[t.name])
                
            except Exception as e:
                # Error with town add. Town may need to be removed!
                await world.client.bot.get_channel(s.alert_channel).send(f"{area.get('label')} Town Update Error! `{e}`"[:2000])

async def update_tracking(world : client_pre.objects.World):
    world.client.database.connection.isolation_level = None
    cursor = await world.client.database.connection.cursor()

    n = datetime.datetime.now()
    time_rounded = datetime.datetime(minute=n.minute + 29 - (n.minute%30), hour=n.hour, day=n.day, month=n.month, year=n.year)

    # ------ Global Table ----------

    update_global_statement = SQLStatement("""REPLACE INTO global VALUES (?, ifnull((select value from global where name=?), 0)+?)""")

    update_global_statement.add_binding_set(('total_tracked', 'total_tracked', world.client.refresh_period["map"]))
    update_global_statement.add_binding_set(('total_tracked_chat', 'total_tracked_chat', world.client.refresh_period["map"]))
    update_global_statement.add_binding_set(('total_tracked_nation_visited', 'total_tracked_nation_visited', world.client.refresh_period["map"]))

    
    await cursor.execute("""REPLACE INTO global_history VALUES (?, ?, ?, ?, ?, ?, ?, ?, 
                (SELECT SUM(duration) FROM activity WHERE object_type='player'), (SELECT SUM(amount) FROM chat_message_counts), ?)""", (datetime.date.today(), len(world.towns), world.total_residents, len(world.nations), world.total_value, 
                world.total_mayor_value, world.total_area, len(world.players), world.database_size))
    
    await cursor.execute("""REPLACE INTO global_day_history VALUES (?, ?, ?, ?, ?, ?, ?, 
                (SELECT SUM(duration) FROM activity WHERE object_type='player'), (SELECT SUM(amount) FROM chat_message_counts), ?)""", (time_rounded, len(world.towns), world.total_residents, len(world.nations), world.total_value, 
                world.total_area, len(world.players), len(world.online_players)))
    
    await update_global_statement.execute(cursor)
    
    # --------------- Other Objects ----------------------

    object_statement = SQLStatement("""REPLACE INTO objects VALUES (?, ?, ?, ?, ?, ?, (SELECT amount FROM chat_mentions WHERE object_type = ? AND object_name = ?),
                (SELECT duration FROM activity WHERE object_type = ? AND object_name = ?), ?)""")
    
    object_history_statement = SQLStatement("""REPLACE INTO object_history VALUES (?, ?, ?, ?, ?, ?, ?, (SELECT amount FROM chat_mentions WHERE object_type = ? AND object_name = ?))""")
    
    for object_type, objects in world._objects.items():
        for object in objects:
            object.reset_town_cache()

            if object_type == "nations" and not object.capital:
                continue 

            _rescount = object.search_boost = object.total_residents

            town_count = len(object.towns)

            object_statement.add_binding_set((
                object.object_type, object.name, town_count, object.total_value, _rescount, object.total_area,object.object_type,object.name,object.object_type,object.name,datetime.datetime.now()
            ))

            if object_type in ["cultures", "religions"]: # Culture/religion history
                try:
                    object_history_statement.add_binding_set((
                        datetime.date.today(), object.object_type, object.name, len(object.towns), object.total_value, _rescount, object.total_area, object.object_type, object.name
                    ))
                except Exception as e:
                    # Nation needs to be removed! Should be removed on next pass from Client.cull_db()
                    await world.client.bot.get_channel(s.alert_channel).send(f"{object.name} Object Tracking Update Error! `{e}`"[:2000])

    await object_statement.execute(cursor)
    await object_history_statement.execute(cursor)
    
    # ------ Town Tracking ---------
    
    town_history_statement = SQLStatement("""REPLACE INTO town_history VALUES(
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, (SELECT duration FROM activity WHERE object_type = 'town' AND object_name = ?), 
                (SELECT COUNT(*) FROM visited_towns WHERE town = ?), ?, (SELECT amount FROM chat_mentions WHERE object_type = 'town' AND object_name = ?))""")
    
    activity_statement = SQLStatement("""REPLACE INTO activity VALUES (?, ?, ifnull((select duration from activity where object_type=? AND object_name=?), 0)+?, ?)""")

    town_statement = SQLStatement("""REPLACE INTO towns VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, (SELECT amount FROM chat_mentions WHERE object_type = 'town' AND object_name = ?), ?, 
                (SELECT COUNT(*) FROM visited_towns WHERE town = ?), 
                (CASE WHEN ifnull((select resident_count from towns where name=?), 0) == 1 THEN (SELECT last FROM activity WHERE object_type='player' AND object_name=?) END),(SELECT duration FROM activity WHERE object_type = 'town' AND object_name = ?), ?)""")
    
    town_day_history_statement = SQLStatement("""REPLACE INTO town_day_history VALUES(?, ?, ?, ?, ?, ?,
                (SELECT duration FROM activity WHERE object_type = 'town' AND object_name = ?), (SELECT COUNT(*) FROM visited_towns WHERE town = ?))""")

    
    
    for town in world.towns:
        try:
            town.search_boost = town.area

            # Add town activity
            players_in_town = world.towns_with_players.get(town.name) or []
            if len(players_in_town) > 0:
                activity_statement.add_binding_set(("town",town.name,"town",town.name,world.client.refresh_period["map"]*len(players_in_town), datetime.datetime.now()))

            # Add to towns table
            town_statement.add_binding_set((town.name, town.nation.name if town.nation else None, str(town.religion), str(town.culture), str(town.mayor), town.resident_count, town.founded_date, 
                town.resident_tax.for_record(), town.bank, town.mayor_bank, int(town.public), int(town.peaceful), town.area, town.name, len(town.outposts), town.name, town.name, str(town.mayor), town.name, town.last_updated)
            )
        
            # Add town history
            town_history_statement.add_binding_set((town.name, datetime.date.today(), town.nation.name if town.nation else None, town.religion.name if town.religion else None,
                    town.culture.name if town.culture else None,town._mayor_raw, town.resident_count, town.resident_tax.for_record(), town.bank, town.public, town.peaceful, town.area, town.name, town.name, town.name, town.name)
            )
            
            if n.minute == 29 or n.minute == 59:
                town_day_history_statement.add_binding_set((town.name, time_rounded, town.resident_count, town.resident_tax.for_record(), town.bank, town.area, town.name, town.name))
            
        except Exception as e:
            # Error with town add. Town may need to be removed!
            await world.client.bot.get_channel(s.alert_channel).send(f"{town.name} Town Tracking Update Error! `{e}` {discord.utils.escape_markdown(traceback.format_exc())}"[:2000])

    await town_history_statement.execute(cursor)
    await town_statement.execute(cursor)
    await town_day_history_statement.execute(cursor)
    
    
    # -------- Nation Tracking ---------

    nation_history_statement = SQLStatement("""REPLACE INTO nation_history VALUES (?, ?, ?, ?, ?, ?, ?, ?, (SELECT duration FROM activity WHERE object_type = 'nation' AND object_name = ?), 
                (SELECT COUNT(*) FROM visited_nations WHERE nation = ?), ?, (SELECT amount FROM chat_mentions WHERE object_type = 'nation' AND object_name = ?))""")
    
    nation_day_history_statement = SQLStatement("""REPLACE INTO nation_day_history VALUES (?, ?, ?, ?, ?, 
                (SELECT COUNT(*) FROM visited_nations WHERE nation = ?), ?, (SELECT duration FROM activity WHERE object_type = 'nation' AND object_name = ?))""")

    for nation in world.nations:
        # Add nation activity
        players_in_nation = 0
        for town_name, players in world.towns_with_players.items():
            if town_name in nation.towns:
                players_in_nation += len(players)
        if players_in_nation > 0:
            activity_statement.add_binding_set(("nation",nation.name,"nation",nation.name,world.client.refresh_period["map"]*players_in_nation, datetime.datetime.now()))

        try:
            nation_history_statement.add_binding_set((nation.name, datetime.date.today(), len(nation.towns), nation.total_value, nation.total_residents, str(nation.capital) if nation.capital else None, str(nation.capital.mayor) if nation.capital else None, nation.total_area, nation.name, nation.name, nation.name, nation.name))
            if n.minute == 29 or n.minute == 59:
                nation_day_history_statement.add_binding_set((nation.name, time_rounded, len(nation.towns), nation.total_value, nation.total_residents, nation.name, nation.total_area, nation.name))
        except Exception as e:
            # Nation needs to be removed! Should be removed on next pass from Client.cull_db()
            await world.client.bot.get_channel(s.alert_channel).send(f"{nation.name} Nation Tracking Update Error! `{e}`"[:2000])
    
    await nation_history_statement.execute(cursor)
    await nation_day_history_statement.execute(cursor)

    await activity_statement.execute(cursor)




async def refresh_short(world : client_pre.objects.World, data : StreamReader):
    mentions = {}
    for town in world.towns: 
        mentions[town.name.lower()] = ("town", town.name)
    for object_type in world._objects: 
        for object in world._objects[object_type]: mentions[object.name.lower()] = (object_type[:-1], object.name) 
    for player in world.players:
        mentions[player.name.lower()] = ("player", player.name)
    
    dynmap_parts = ijson.kvitems_async(data, "", use_float=True)
    player_list = None

    chat_message_statemenet = SQLStatement("""REPLACE INTO chat_message_counts VALUES (?, ifnull((select amount from chat_message_counts where player=?), 0)+1, ?)""")
    chat_mention_statemenet = SQLStatement("""REPLACE INTO chat_mentions VALUES (?, ?, ifnull((select amount from chat_mentions where object_type=? AND object_name=?), 0)+1, ?)""")

    async for key, updates in dynmap_parts:
        if key == "updates":
            for update in updates:
                if update["type"] == "chat":
                    world.client.dynmap_update_timestamp = update["timestamp"]

                    sender = world.get_player(update["account"], False)
                    message : str = update['message']

                    for word in message.split(" "):
                        if word.lower() in mentions:
                            mention = mentions[word.lower()]

                            chat_mention_statemenet.add_binding_set((mention[0], mention[1], mention[0], mention[1], datetime.datetime.now()))

                    if sender:
                        chat_message_statemenet.add_binding_set((sender.name, sender.name, datetime.datetime.now()))
        # Players
        if key == "currentcount":
            world.player_count = updates or 0
        elif key == "hasStorm":
            world.is_stormy = updates or False
        elif key  == "players":
            player_list = updates
        else:
            continue
    
    await chat_message_statemenet.execute(world.client.database.connection)
    await chat_mention_statemenet.execute(world.client.database.connection)
    
    world.towns_with_players = await short_refresh_tracking_update(world, player_list)
    

async def short_refresh_tracking_update(world : client_pre.objects.World, players : list[dict]):
    if not players:
        return {}
    
    n = datetime.datetime.now()
    time_rounded = datetime.datetime(minute=n.minute + 29 - (n.minute%30), hour=n.hour, day=n.day, month=n.month, year=n.year)
    
    online_players : list[str] = []

    towns_with_players : dict[str, list[client_pre.objects.Player]] = {}

    activity_statement = SQLStatement("""REPLACE INTO activity VALUES ('player', ?, ifnull((select duration from activity where object_type='player' AND object_name=?), 0)+?, ?)""")
    players_statement = SQLStatement("""REPLACE INTO players VALUES (?, ?, ?, ?, ?, (SELECT COUNT(*) FROM visited_towns WHERE player = ?), (SELECT COUNT(*) FROM visited_nations WHERE player = ?),?, ?, 
                (SELECT amount FROM chat_message_counts WHERE player = ?), (SELECT amount FROM chat_mentions WHERE object_type = 'player' AND object_name = ?), 
                (select duration from activity where object_type='player' AND object_name=?), ?)""")

    player_history_statement = SQLStatement("""REPLACE INTO player_history VALUES (?, ?, (select duration from activity where object_type='player' AND object_name=?), 
                (SELECT COUNT(*) FROM visited_towns WHERE player = ?), (SELECT COUNT(*) FROM visited_nations WHERE player = ?), ?, ?, ?,
                (SELECT amount FROM chat_message_counts WHERE player = ?), (SELECT amount FROM chat_mentions WHERE object_type = 'player' AND object_name = ?))""")
    
    player_day_history_statement = SQLStatement("""REPLACE INTO player_day_history VALUES (?, ?, (select duration from activity where object_type='player' AND object_name=?), 
                ?, (SELECT COUNT(*) FROM visited_towns WHERE player = ?), (SELECT COUNT(*) FROM visited_nations WHERE player = ?)) """)
    
    visited_towns_statement = SQLStatement("""REPLACE INTO visited_towns VALUES (?, ?, ifnull((select duration from visited_towns WHERE player=? AND town=?), 0)+?, ?)""")
    visited_nations_statement = SQLStatement("""REPLACE INTO visited_nations VALUES (?, ?, ifnull((select duration from visited_nations WHERE player=? AND nation=?), 0)+?, ?)""")

    for player_data in players:
        await asyncio.sleep(0.001) # Allow "parallel" processing

        # Add player to player list (in memory) if not already there
        online_players.append(player_data["account"])
        p = world.get_player(player_data["account"], False)
        if not p:
            p = world.client.objects.Player(world)
            world.set_player(player_data["account"], p)
            p.search_boost=-1 # Send player to bottom of autocomplete list as they're new
        p.update(player_data)

        # Add to activity table
        activity_statement.add_binding_set((p.name, p.name, world.client.refresh_period["players"], datetime.datetime.now()))
        
        # Add player history
        player_history_statement.add_binding_set((p.name, datetime.date.today(), p.name, p.name, p.name, p.residence.name if p.residence else None,
            p.residence.nation.name if p.residence and p.residence.nation else None, p.bank, p.name, p.name))
        
        player_day_history_statement.add_binding_set((p.name, time_rounded, p.name, p.bank, p.name, p.name))
        
        # Add to visited town table
        town = p.town
        if town:
            if town.name not in towns_with_players:
                towns_with_players[town.name] = []
            towns_with_players[town.name].append(p)

            visited_towns_statement.add_binding_set((p.name, town.name, p.name, town.name, world.client.refresh_period["players"], datetime.datetime.now()))
            if town.nation:
                visited_nations_statement.add_binding_set((p.name, town.nation.name, p.name, town.nation.name, world.client.refresh_period["players"], datetime.datetime.now()))

        # Add to players table
        players_statement.add_binding_set((p.name, ",".join([str(p.location.x), str(p.location.y), str(p.location.z)]), p.town.name if p.town else None, p.armor, p.health, p.name, p.name, p.nickname,p.bank, p.name, p.name, p.name, datetime.datetime.now()))

    # Execute statements
    for statement in [activity_statement, players_statement, player_history_statement, player_day_history_statement, visited_towns_statement, visited_nations_statement]:
        await statement.execute(world.client.database.connection)
    
    for player in world.players:
        if player.online and player.name not in online_players:
            player.online = False
    
    return towns_with_players