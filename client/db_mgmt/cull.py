
from __future__ import annotations
import typing
if typing.TYPE_CHECKING:
    import client as client_pre

import setup as s
import datetime

async def cull_db(c : client_pre.Client):
        
    # If almost all of the towns are to be deleted, something's gone wrong. Therefore don't continue the cull
    remaining_town_rows = await (await c.execute("SELECT COUNT(*) FROM towns WHERE last_seen >= ?", (datetime.datetime.now()-s.cull_objects_after,))).fetchone()
    if remaining_town_rows[0] < 2: 
        return False

    # -------------------- Cull --------------------------

    # Remove records from day_history tables over a day old
    for day_history_type in s.history_today_commands.keys():
        await c.execute(f"DELETE FROM {day_history_type}_day_history WHERE time < ?", (datetime.datetime.now()-datetime.timedelta(days=1),))

    # Delete players that are no longer in the towny database (after 45d)
    await c.execute("DELETE FROM players WHERE last < ?", (datetime.datetime.now()-s.cull_players_from,))

    # Delete towns that aren't on the map anymore (haven't been seen for cull_objects_after)
    await c.execute("DELETE FROM towns WHERE last_seen < ?", (datetime.datetime.now()-s.cull_objects_after,))

    # Delete from visited_towns where player doens't exist and their time in town is insignificant
    await c.execute("DELETE FROM visited_towns WHERE player IN (SELECT visited_towns.player FROM visited_towns LEFT JOIN players ON visited_towns.player=players.name WHERE players.name IS NULL) AND duration < 300;")
    # Delete from visited_towns where town and player don't exist
    await c.execute("DELETE FROM visited_towns WHERE player IN (SELECT visited_towns.player FROM visited_towns LEFT JOIN players ON visited_towns.player=players.name WHERE players.name IS NULL) AND town IN (SELECT visited_towns.town FROM visited_towns LEFT JOIN towns ON visited_towns.town=towns.name WHERE towns.name IS NULL);")
    # Delete from player_history if player doesn't exist and their activity was insignificant
    await c.execute("DELETE FROM player_history WHERE player IN (SELECT player_history.player FROM player_history LEFT JOIN players ON player_history.player=players.name JOIN activity ON activity.object_name=player_history.player WHERE players.name IS NULL AND activity.duration < 1000);")
    
    # Delete from activity where the object's activity is under 10 minutes and hasn't been seen for over cull_insignificant_activity_after time
    await c.execute("DELETE FROM activity WHERE last <? AND duration < 600", (datetime.datetime.now()-s.cull_insignificant_activity_after,))

    # Abstract history tables. This removes certain days (eg 1 day out of every 3) from old history data to abstract it over time. Thresholds are defined in setup.py
    for object_type in ["player", "town", "nation", "object"]:
        for threshold_time, days_of_6 in s.history_abstraction_thresholds:
            await c.execute(f"DELETE FROM {object_type}_history WHERE (julianday(date)-julianday('2021-10-29')) % 6 IN ({days_of_6}) AND date<?", (datetime.datetime.now()-threshold_time,))
    

    await c.execute("DELETE FROM flags WHERE object_type='nation' AND object_name NOT IN (SELECT object_name FROM objects WHERE type='nation')")

    sent = 0 # A quick counter for messages sent to alert channel to limit spam and keep bot running

    towns_in_db : list[str] = [r[0] for r in await (await c.execute("SELECT name FROM towns")).fetchall()]
    players_in_db : list[str] = [r[0] for r in await (await c.execute("SELECT name FROM players")).fetchall()]

    for player in c.world.players.copy():
        if player.name not in players_in_db:
            c.world._remove_player(player.name)
    for town in c.world.towns.copy():
        if town.name not in towns_in_db:
            sent += 1
            if sent <= 10: await c.bot.get_channel(s.alert_channel).send(f"Removed town {town.name}")
            c.world._remove_town(town.name)
            for t in c.world.towns:
                if t.spawn.x == town.spawn.x and t.spawn.z == town.spawn.z:
                    sent += 1
                    if sent <= 10: await c.bot.get_channel(s.alert_channel).send(f"Is this town the same as  {t.name}?")
                    await c.merge_objects("town", town.name, t.name)
            
            
    for nation in c.world.nations.copy():
        
        if not nation.capital:

            nation_info_record = await (await c.execute("SELECT towns, residents, area, capital FROM nation_history WHERE nation=? ORDER BY date DESC", (nation.name,))).fetchone()
            if not nation_info_record:
                nation_info_record = await (await c.execute("SELECT towns, residents, area FROM objects WHERE type='nation' AND name=?", (nation.name,))).fetchone()
            c.world._remove_nation(nation.name)
            sent += 1
            if nation_info_record:
                if sent <= 10:
                    await c.bot.get_channel(s.alert_channel).send(f"Removed nation {nation.name} {nation_info_record[0]} {nation_info_record[1]}")
                
                for n in c.world.nations:
                    if len(n.towns) == nation_info_record[0] and n.total_residents == nation_info_record[1] and n.capital and ((len(nation_info_record) == 4 and n.capital.name == nation_info_record[3]) or n.total_area == nation_info_record[2]):
                        sent += 1
                        if sent <= 10: await c.bot.get_channel(s.alert_channel).send(f"Is this nation the same as  {n.name}?")
                        await c.merge_objects("nation", nation.name, n.name)
                        break
            else:
                await c.bot.get_channel(s.alert_channel).send(f"Removed nation {nation.name}. Couldn't find history info")
    
    if sent > 10:
        await c.bot.get_channel(s.alert_channel).send("... + more")

    # Must be done after because accesssed in cull
    await c.execute("DELETE FROM objects WHERE last < ?", (datetime.datetime.now()-s.cull_objects_after,))