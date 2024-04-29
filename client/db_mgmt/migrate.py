from __future__ import annotations
import typing
if typing.TYPE_CHECKING:
    import client as client_pre

import setup as s

class Migration:
    # Class for a single migration 
    def __init__(self, table_name : str, new_table_attributes_with_types : str, old_attributes_to_migrate : str, sql_statement_after_run : str = None):
        self.table_name = table_name
        self.new_table_attributes_with_types = new_table_attributes_with_types if type(new_table_attributes_with_types) == str else ", ".join(new_table_attributes_with_types)
        self.old_attributes_to_migrate = old_attributes_to_migrate
        self.sql_statement_after_run = sql_statement_after_run
    
    async def execute_migration(self, c : client_pre.Client):
        # Adds a new attribute to a table
        # Firstly it creates a new table with the new column added
        # Next it migrates over old rows which are wanted
        # After this it executes a custom sql statement if provided
        # Finally it deletes the original table and renames the temp one back
        
        print("migrating")

        await c.execute(f"CREATE TABLE temp{self.table_name} ({self.new_table_attributes_with_types});")
        await c.execute(f"INSERT INTO temp{self.table_name} ({', '.join(self.old_attributes_to_migrate)}) SELECT {', '.join(self.old_attributes_to_migrate)} FROM {self.table_name};")
        if self.sql_statement_after_run: await c.execute(self.sql_statement_after_run)
        await c.execute(f"DROP TABLE {self.table_name};")
        await c.execute(f"ALTER TABLE temp{self.table_name} RENAME TO {self.table_name};")

async def upgrade_db(c : client_pre.Client):
     

    version_migrations : dict[str, list[Migration]] = {
        "10":[
            Migration("players", "name string PRIMARY KEY, location string, town string, armor integer, health integer, visited_towns integer, visited_nations integer, nickname string DEAFULT NULL, bank real, messages integer, mentions integer, duration integer, last timestamp", ["name", "location", "town", "armor", "health", "visited_towns", "bank", "messages", "mentions", "duration", "last"]),
            Migration("town_history", ["town STRING","date DATE","nation STRING","religion STRING","culture STRING","mayor STRING","resident_count INTEGER","resident_tax REAL","bank REAL","public INTEGER","peaceful INTEGER","area INTEGER","duration INTEGER","visited_players INTEGER","current_name STRING","mentions INTEGER","PRIMARY KEY (town, date)"], ["town", "date", "nation", "religion", "culture", "mayor", "resident_count", "resident_tax", "bank", "public", "peaceful", "area", "duration", "visited_players", "current_name", "mentions"]),
            Migration("player_history", ["player STRING","date DATE","duration INTEGER","visited_towns INTEGER","visited_nations INTEGER","likely_town STRING","likely_nation STRING","bank REAL","messages INTEGER","mentions INTEGER","PRIMARY KEY (player, date)"], ["player", "date", "duration", "visited_towns", "likely_town", "likely_nation", "bank", "messages", "mentions"]),
            Migration("activity", ["object_type STRING","object_name STRING","duration INTEGER","last TIMESTAMP","PRIMARY KEY (object_type, object_name)"], ["object_type", "object_name", "duration", "last"]),
            Migration("town_day_history", ["town STRING","time TIMESTAMP","resident_count INTEGER","resident_tax REAL","bank REAL","area INTEGER","duration INTEGER","visited_players INTEGER","PRIMARY KEY (town, time)"], ["town", "time", "resident_count", "resident_tax", "bank", "area", "duration", "visited_players"]),
            Migration("objects", ["type STRING","name STRING","towns INTEGER","town_balance REAL","residents INTEGER","area INTEGER","mentions INTEGER","duration INTEGER","last TIMESTAMP","PRIMARY KEY(type, name)"], ["type", "name", "towns", "town_balance", "residents", "area", "mentions", "duration", "last"]),
            Migration("object_history", ["date DATE","type STRING","object STRING","towns INTEGER","town_balance REAL","residents INTEGER","area INTEGER","mentions INTEGER","PRIMARY KEY(date, type, object)"], ["date", "type", "object", "towns", "town_balance", "residents", "area", "mentions"]),
            Migration("nation_history", ["nation STRING","date DATE","towns INTEGER","town_balance REAL","residents INTEGER","capital STRING","leader STRING","area INTEGER","duration INTEGER","visited_players INTEGER","current_name STRING","mentions INTEGER","PRIMARY KEY(nation, date)"], ["nation", "date", "towns", "town_balance", "residents", "capital", "leader", "area", "duration", "current_name", "mentions"]),
            Migration("nation_day_history", ["nation STRING", "time TIMESTAMP", "towns INTEGER", "town_balance REAL", "residents INTEGER", "visited_players INTEGER","area INTEGER", "duration INTEGER", "PRIMARY KEY(nation, time)"], ["nation", "time", "towns", "town_balance", "residents", "area", "duration"]),
            Migration("global", ["name STRING PRIMARY KEY","value"], ["name", "value"]),
            Migration("global_history", ["date DATE PRIMARY KEY","towns INTEGER","residents INTEGER","nations INTEGER","town_value REAL","mayor_value REAL","area INTEGER","known_players INTEGER","activity INTEGER","messages INTEGER","database_size REAL"], ["date", "towns", "residents", "nations", "town_value", "mayor_value", "area", "known_players", "activity", "messages", "database_size"]),
            Migration("chat_message_counts", ["player STRING PRIMARY KEY","amount INTEGER","last TIMESTAMP"], ["player", "amount", "last"]),
            Migration("chat_mentions", ["object_type STRING","object_name STRING","amount INTEGER","last TIMESTAMP", "PRIMARY KEY(object_type, object_name)"], ["object_type", "object_name", "amount", "last"]),
            Migration("visited_towns", ["player STRING","town STRING","duration INTEGER","last TIMESTAMP","PRIMARY KEY(player, town)"], ["player", "town", "duration", "last"]),
            Migration("player_day_history", ["player STRING","time TIMESTAMP","duration INTEGER","bank REAL","visited_towns INTEGER","visited_nations INTEGER","PRIMARY KEY(player, time)"], ["player", "time", "duration", "bank", "visited_towns"]),
            Migration("flags", ["object_type STRING","object_name STRING","name STRING","value","PRIMARY KEY(object_type, object_name, name)"], ["object_type", "object_name", "name", "value"]),
            Migration("notifications", ["notification_type STRING","guild_id INTEGER","channel_id INTEGER","object_name STRING","ignore_if_resident INTEGER","PRIMARY KEY(notification_type, channel_id, object_name)"], ["notification_type", "guild_id", "channel_id", "object_name", "ignore_if_resident"]),
            Migration("towns", ["name STRING PRIMARY KEY","nation STRING","religion STRING","culture STRING","mayor STRING","resident_count INTEGER","founded_date DATE","resident_tax REAL","bank REAL","mayor_bank REAL","public INTEGER","peaceful INTEGER","area INTEGER","mentions INTEGER","outposts INTEGER","visited_players INTEGER","mayor_inactivity TIMESTAMP","duration INTEGER","last_seen TIMESTAMP"], ["name", "nation", "religion", "culture", "mayor", "resident_count", "founded_date", "resident_tax", "bank", "mayor_bank", "public", "peaceful", "area", "mentions", "outposts", "visited_players", "duration", "last_seen"])
        ]
    }

    version = int(list(version_migrations)[-1])
    if s.MIGRATE_DB:

        current_db_version = await c.db_version
        tracked = await c.world.total_tracked
        if tracked and (tracked).total > 0:
            for version, migrations in version_migrations.items():
                if not current_db_version or int(version) > current_db_version:
                    for migration in migrations:
                        await migration.execute_migration(c)
    
    if not current_db_version:
        await c.execute("INSERT INTO global VALUES (?, ?)", ("db_version", int(version)))
    else:
        await c.execute("UPDATE global SET value=? WHERE name=?", (int(version), "db_version"))
        
            

