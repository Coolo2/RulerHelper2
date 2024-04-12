
import aiosqlite 
import sqlite3 

class RawDatabase():

    tables = {
        "global":[
            "name STRING PRIMARY KEY",
            "value"
        ],
        "towns":[
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
            "mayor_inactivity TIMESTAMP",
            "duration INTEGER",
            "last_seen TIMESTAMP"
        ],
        "players":[
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
        ],
        "objects": [
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
        ],
        "visited_towns":[
            "player STRING",
            "town STRING",
            "duration INTEGER",
            "last TIMESTAMP",
            "PRIMARY KEY(player, town)"
        ],
        "town_history":[
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
        ],
        "town_day_history": [
            "town STRING",
            "time TIMESTAMP",
            "resident_count INTEGER",
            "resident_tax REAL",
            "bank REAL",
            "area INTEGER",
            "duration INTEGER",
            "visited_players INTEGER",
            "PRIMARY KEY (town, time)"
        ],
        'player_history':[
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
        ],
        "player_day_history":[
            "player STRING",
            "time TIMESTAMP",
            "duration INTEGER",
            "bank REAL",
            "visited_towns INTEGER",
            "PRIMARY KEY(player, time)"
        ],
        "nation_history":[
            "nation STRING",
            "date DATE",
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
        ],
        "nation_day_history":[
            "nation STRING",
            "time TIMESTAMP",
            "towns INTEGER",
            "town_balance REAL",
            "residents INTEGER",
            "area INTEGER",
            "duration INTEGER",
            "PRIMARY KEY(nation, time)"
        ],
        "global_history":[
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
        ],
        "global_day_history":[
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
        "object_history":[
            "date DATE",
            "type STRING",
            "object STRING",
            "towns INTEGER",
            "town_balance REAL",
            "residents INTEGER",
            "area INTEGER",
            "mentions INTEGER",
            "PRIMARY KEY(date, type, object)"
        ],
        "flags":[
            "object_type STRING",
            "object_name STRING",
            "name STRING",
            "value",
            "PRIMARY KEY(object_type, object_name, name)"
        ],
        "activity":[
            "object_type STRING",
            "object_name STRING",
            "duration INTEGER DEFAULT 0",
            "last TIMESTAMP",
            "PRIMARY KEY (object_type, object_name)"
        ],
        "notifications":[
            "notification_type STRING",
            "guild_id INTEGER",
            "channel_id INTEGER",
            "object_name STRING",
            "ignore_if_resident INTEGER",
            "PRIMARY KEY(notification_type, channel_id, object_name)"
        ],
        "chat_message_counts":[
            "player STRING PRIMARY KEY",
            "amount INTEGER",
            "last TIMESTAMP"
        ],
        "chat_mentions":[
            "object_type STRING",
            "object_name STRING",
            "amount INTEGER",
            "last TIMESTAMP",
            "PRIMARY KEY(object_type, object_name)"
        ]
    }

    def __init__(self, client, path : str):
        self.path = path 
        self.client = client

        self.__connection_store : aiosqlite.Connection = None

    async def connect(self):
        self.__connection_store = await aiosqlite.connect(self.path, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES, check_same_thread=False) 
        return self.__connection_store
    
    @property 
    def connection(self):
        return self.__connection_store
    
    async def initialise(self, update_coro = None):
        await self.connect()
        self.client.add_execute()

        await self.connection.execute("PRAGMA auto_vacuum = FULL")

        await self.connection.execute('PRAGMA journal_mode = WAL')
        await self.connection.execute('PRAGMA synchronous = 1')
        await self.connection.execute('PRAGMA cache_size = -64000')

        for table_name, attributes in self.tables.items():
            await self.connection.execute(f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(attributes)})")
        




        if update_coro:
            await update_coro
