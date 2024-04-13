

from __future__ import annotations
import typing
if typing.TYPE_CHECKING:
    import client as client_pre

from client import errors

async def merge_objects(c : client_pre.Client, object_type : str, old_object_name : str, new_object_name : str):
        
    if object_type == "player":
        obj = c.world.get_player(new_object_name)
    elif object_type == "town":
        obj = c.world.get_town(new_object_name)
    elif object_type == "nation":
        obj = c.world.get_nation(new_object_name)

    if not obj:
        raise errors.MildError(f"{object_type.title()} not found")

    # ------------------- Merge system. Probably overcomplicated but it works  -------------------

    # Firstly merge activity. Same for all object types
    old_activity_record = await (await c.execute("SELECT duration, last FROM activity WHERE object_type=? AND object_name=?", (object_type, old_object_name))).fetchone()
    await c.execute("DELETE FROM activity WHERE object_type=? AND object_name=?", (object_type, old_object_name))
    if old_activity_record:
        await c.execute("REPLACE INTO activity VALUES (?, ?, ifnull((select duration from activity where object_type=? AND object_name=?), 0)+?, ?)", (object_type, obj.name, object_type, obj.name, old_activity_record[0], old_activity_record[1]))

    if object_type == "player":
        old_duration = (await (await c.execute("SELECT duration FROM player_history WHERE player=? ORDER BY date DESC LIMIT 1", (old_object_name,))).fetchone())[0]

        old_messages_record = await (await c.execute("SELECT amount, last FROM chat_message_counts WHERE player=?", (old_object_name,))).fetchone()
        if old_messages_record:
            await c.execute("REPLACE INTO chat_message_counts VALUES (?, ifnull((select amount from chat_message_counts WHERE player=?), 0)+?, ?)", (obj.name, obj.name, old_messages_record[0], old_messages_record[1]))
        await c.execute("DELETE FROM chat_message_counts WHERE player=?", (old_object_name,))

        old_mentions_record = await (await c.execute("SELECT amount, last FROM chat_mentions WHERE object_type='player' AND object_name=?", (old_object_name,))).fetchone()
        if old_mentions_record:
            await c.execute("REPLACE INTO chat_mentions VALUES ('player', ?, ifnull((select amount from chat_mentions where object_type='player' AND object_name=?), 0)+?, ?)", (obj.name, obj.name, old_mentions_record[0], old_mentions_record[1]))
        await c.execute("DELETE FROM chat_mentions WHERE object_type='player' AND object_name=?", (old_object_name,))

        await c.execute("UPDATE chat_mentions SET object_name=? WHERE object_name=? AND object_type='player'", (obj.name, old_object_name))

        # Update flag table
        await c.execute("DELETE FROM flags WHERE object_type='player' AND object_name=?", (obj.name,)) # Delete items in the table with the new object name to cancel any duplicates
        await c.execute("UPDATE flags SET object_name=? WHERE object_type='player' AND object_name=?", (obj.name, old_object_name))

        # Iterate over old history records. If not under new name, add it. Otherwise, remove old
            # Add to new player records with old duration
        player_history_records_new = await (await c.execute("SELECT date FROM player_history WHERE player=? ORDER BY date ASC", (obj.name,))).fetchall()
        for (date,) in player_history_records_new:
            old_duration_at_point = await (await c.execute("SELECT duration FROM player_history WHERE player=? AND date <=? ORDER BY date DESC LIMIT 1", (old_object_name, date))).fetchone()
            
            if old_duration_at_point: 
                await c.execute("UPDATE player_history SET duration=duration+? WHERE player=? AND date=?", (old_duration_at_point[0], obj.name, date))
        # Iterate over old records. If exists for new player, remove
        player_history_records_old = await (await c.execute("SELECT date FROM player_history WHERE player=? ORDER BY date ASC", (old_object_name,))).fetchall()
        for (date,) in player_history_records_old:
            exists_record = await (await c.execute("SELECT 1 FROM player_history WHERE player=? AND date=?", (obj.name, date))).fetchone()
            if not exists_record:
                await c.execute("UPDATE player_history SET player=? WHERE player=? AND date=?", (obj.name, old_object_name, date))
            else:
                await c.execute("DELETE FROM player_history WHERE player=? AND date=?", (old_object_name, date))
        # if duplicates exist, merge data
        visited_records_old = await (await c.execute("SELECT player, town, duration FROM visited_towns WHERE player=?", (old_object_name,))).fetchall()
        for (player, town, duration) in visited_records_old:
            rec = await (await c.execute("SELECT 1 FROM visited_towns WHERE player=? AND town=?", (obj.name, town))).fetchone()
            if not rec:
                await c.execute("UPDATE visited_towns SET player=? WHERE player=? AND town=?", (obj.name, player, town))
            else:
                await c.execute("DELETE FROM visited_towns WHERE player=? AND town=?", (player, town))
                await c.execute("UPDATE visited_towns SET duration=duration+? WHERE player=? AND town=?", (duration, obj.name, town))

        await c.execute("UPDATE players SET duration=duration+? WHERE name=?", (old_duration, obj.name))

        await c.execute("DELETE FROM players WHERE name=?", (old_object_name,))
        
        await c.execute("UPDATE town_history SET mayor=? WHERE mayor=?", (obj.name, old_object_name))
        await c.execute("UPDATE nation_history SET leader=? WHERE leader=?", (obj.name, old_object_name))
    elif object_type == "town":
        old_duration = (await (await c.execute("SELECT duration FROM town_history WHERE town=? ORDER BY date DESC LIMIT 1", (old_object_name,))).fetchone())[0]

        old_mentions_record = await (await c.execute("SELECT amount, last FROM chat_mentions WHERE object_type='town' AND object_name=?", (old_object_name,))).fetchone()
        if old_mentions_record:
            await c.execute("REPLACE INTO chat_mentions VALUES ('town', ?, ifnull((select amount from chat_mentions where object_type='town' AND object_name=?), 0)+?, ?)", (obj.name, obj.name, old_mentions_record[0], old_mentions_record[1]))
        await c.execute("DELETE FROM chat_mentions WHERE object_type='town' AND object_name=?", (old_object_name,))

        # Update flag table
        await c.execute("DELETE FROM flags WHERE object_type='town' AND object_name=?", (obj.name,)) # Delete items in the table with the new object name to cancel any duplicates
        await c.execute("UPDATE flags SET object_name=? WHERE object_type='town' AND object_name=?", (obj.name, old_object_name))

        # Iterate over old history records. If not under new name, add it. Otherwise, remove old
        town_history_records_new = await (await c.execute("SELECT date FROM town_history WHERE town=? ORDER BY date ASC", (obj.name,))).fetchall()
        for (date,) in town_history_records_new:
            old_duration_at_point = await (await c.execute("SELECT duration FROM town_history WHERE town=? AND date <=? ORDER BY date DESC LIMIT 1", (old_object_name, date))).fetchone()
        
            if old_duration_at_point: 
                await c.execute("UPDATE town_history SET duration=duration+? WHERE town=? AND date=?", (old_duration_at_point[0], obj.name, date))
        # Iterate over old records. If exists for new town, remove
        town_history_records_old = await (await c.execute("SELECT date FROM town_history WHERE town=? ORDER BY date ASC", (old_object_name,))).fetchall()
        for (date,) in town_history_records_old:
            exists_record = await (await c.execute("SELECT 1 FROM town_history WHERE town=? AND date=?", (obj.name, date))).fetchone()
            if not exists_record:
                await c.execute("UPDATE town_history SET town=? WHERE town=? AND date=?", (obj.name, old_object_name, date))
            else:
                await c.execute("DELETE FROM town_history WHERE town=? AND date=?", (old_object_name, date))
        
        # If duplicate exists, merge data
        visited_records_old = await (await c.execute("SELECT player, town, duration FROM visited_towns WHERE town=?", (old_object_name,))).fetchall()
        for (player, town, duration) in visited_records_old:
            rec = await (await c.execute("SELECT 1 FROM visited_towns WHERE town=? AND player=?", (obj.name, town))).fetchone()
            if not rec:
                await c.execute("UPDATE visited_towns SET town=? WHERE player=? AND town=?", (obj.name, player, town))
            else:
                await c.execute("DELETE FROM visited_towns WHERE player=? AND town=?", (player, town))
                await c.execute("UPDATE visited_towns SET duration=duration+? WHERE town=? AND player=?", (duration, obj.name, player))
        
        # Update main record
        await c.execute("DELETE FROM towns WHERE name=?", (old_object_name,))

        await c.execute("UPDATE nation_history SET capital=? WHERE capital=?", (obj.name, old_object_name))
        await c.execute("UPDATE player_history SET likely_town=? WHERE likely_town=?", (obj.name, old_object_name))
    elif object_type == "nation":

        await c.execute("UPDATE notifications SET object_name=? WHERE object_name=?", (obj.name, old_object_name))

        old_mentions_record = await (await c.execute("SELECT amount, last FROM chat_mentions WHERE object_type='nation' AND object_name=?", (old_object_name,))).fetchone()
        if old_mentions_record:
            await c.execute("REPLACE INTO chat_mentions VALUES ('nation', ?, ifnull((select amount from chat_mentions where object_type='nation' AND object_name=?), 0)+?, ?)", (obj.name, obj.name, old_mentions_record[0], old_mentions_record[1]))
        await c.execute("DELETE FROM chat_mentions WHERE object_type='nation' AND object_name=?", (old_object_name,))

        # Update flags: 1. Delete flags if already exist 2. Update old name
        await c.execute("DELETE FROM flags WHERE object_type='nation' AND object_name=?", (obj.name,))
        await c.execute("UPDATE flags SET object_name=? WHERE object_type='nation' AND object_name=?", (obj.name, old_object_name))

        # Iterate over old history records. If not under new name, add it. Otherwise, remove old
        nation_history_records_new = await (await c.execute("SELECT date FROM nation_history WHERE nation=? ORDER BY date ASC", (obj.name,))).fetchall()
        for (date,) in nation_history_records_new:
            old_duration_at_point = await (await c.execute("SELECT duration FROM nation_history WHERE nation=? AND date <=? ORDER BY date DESC LIMIT 1", (old_object_name, date))).fetchone()
        
            if old_duration_at_point: 
                await c.execute("UPDATE nation_history SET duration=duration+? WHERE nation=? AND date=?", (old_duration_at_point[0], obj.name, date))
        # Iterate over old records. If exists for new nation, remove
        nation_history_records_old = await (await c.execute("SELECT date FROM nation_history WHERE nation=? ORDER BY date ASC", (old_object_name,))).fetchall()
        for (date,) in nation_history_records_old:
            exists_record = await (await c.execute("SELECT 1 FROM nation_history WHERE nation=? AND date=?", (obj.name, date))).fetchone()
            if not exists_record:
                await c.execute("UPDATE nation_history SET nation=? WHERE nation=? AND date=?", (obj.name, old_object_name, date))
            else:
                await c.execute("DELETE FROM nation_history WHERE nation=? AND date=?", (old_object_name, date))
        
        # If duplicate exists, merge data
        visited_records_old = await (await c.execute("SELECT player, nation, duration FROM visited_nations WHERE nation=?", (old_object_name,))).fetchall()
        for (player, nation, duration) in visited_records_old:
            rec = await (await c.execute("SELECT 1 FROM visited_nations WHERE nation=? AND player=?", (obj.name, nation))).fetchone()
            if not rec:
                await c.execute("UPDATE visited_nations SET nation=? WHERE player=? AND nation=?", (obj.name, player, nation))
            else:
                await c.execute("DELETE FROM visited_nations WHERE player=? AND nation=?", (player, nation))
                await c.execute("UPDATE visited_nations SET duration=duration+? WHERE nation=? AND player=?", (duration, obj.name, player))
        
        await c.execute("UPDATE town_history SET nation=? WHERE nation=?", (obj.name, old_object_name))
        await c.execute("UPDATE player_history SET likely_nation=? WHERE likely_nation=?", (obj.name, old_object_name))