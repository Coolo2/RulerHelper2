
import db
import datetime

def generate_time(time):
    timeSeconds = time
    day = timeSeconds // (24 * 3600)
    timeSeconds = timeSeconds % (24 * 3600)
    hour = timeSeconds // 3600
    timeSeconds %= 3600
    minutes = timeSeconds // 60
    timeSeconds %= 60
    seconds = timeSeconds

    day = f" {round(day)}d" if day != 0 else ""
    hour = f" {round(hour)}h" if hour != 0 else ""
    minutes = f" {round(minutes)}m" if minutes != 0 else ""

    if day == "" and hour == "" and minutes == "":
        return f"{round(seconds)}s"
    
    return f"{day}{hour}{minutes}".lstrip()

def top_rankings_to_text(rankings : dict, object_name : str, notable_only = True) -> str:
    notable_statistics = ""
    for (leaderboard), (value, ranking, notable) in rankings.items():
        if notable: notable_statistics += f"\n- {object_name} is **#{ranking}** on the **{leaderboard.replace('_', ' ')}** ranking"
    if not notable_only or notable_statistics == "": notable_statistics = "None"

    return notable_statistics

async def update_db(c):
        
        d = datetime.date.today()

        tables = [
            [
                "players",
                "visited_towns",
                "integer",
                "0",
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
                ],
                ["name", "location", "town", "armor", "health", "duration", "last", "donator"],
                "UPDATE tempplayers SET visited_towns=(SELECT COUNT(*) FROM visited_towns WHERE visited_towns.player = name)" #None if don't want
            ],
            [
                "player_history",
                "visited_towns",
                "integer",
                "NULL",
                [
                    db.CreationAttribute("player", db.types.String),
                    db.CreationAttribute("date", db.types.Date),
                    db.CreationAttribute("duration", db.types.Int),
                    db.CreationAttribute("visited_towns", db.types.Int),
                ],
                ["player", "date", "duration"],
                f'UPDATE tempplayer_history SET visited_towns=(SELECT COUNT(*) FROM visited_towns WHERE visited_towns.player = tempplayer_history.player) WHERE date="{d.year}-{str(d.month).zfill(2)}-{str(d.day).zfill(2)}"' #None if don't want
            ]
        ]
        
        for table in tables:
            table_name = table[0]
            att_name = table[1]
            att_type = table[2]
            default = table[3] # if str include ''
            new_attributes = table[4]
            original_attributes_string = table[5]
            custom = table[6] #None if don't want
            
            info = await (await c.database.connection.execute(f"PRAGMA table_info({table_name})")).fetchall()
            if att_name not in[c[1] for c in info]:
                print("not in!")
                coldef = f"{att_name} {att_type} DEFAULT {default}"

                await c.database.connection.execute(f"CREATE TABLE temp{table_name} ({', '.join([a.for_table() if a.name != att_name else coldef for a in new_attributes])});")
                await c.database.connection.execute(f"INSERT INTO temp{table_name} ({', '.join(original_attributes_string)}) SELECT {', '.join(original_attributes_string)} FROM {table_name};")
                if custom: await c.database.connection.execute(custom)
                await c.database.connection.execute(f"DROP TABLE {table_name};")
                await c.database.connection.execute(f"ALTER TABLE temp{table_name} RENAME TO {table_name};")