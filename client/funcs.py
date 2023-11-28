
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
                "town_history",
                "current_name",
                "string",
                "NULL",
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
                ],
                ["town", "date", "nation", "religion", "culture", "mayor", "resident_count", "resident_tax", "bank", "public", "peaceful", "area", "duration", "visited_players"],
                "UPDATE temptown_history SET current_name=town" #None if don't want
            ],
            [
                "nation_history",
                "current_name",
                "string",
                "NULL",
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
                ],
                ["nation", "date", "towns", "town_balance", "residents", "capital", "leader", "area", "duration"],
                "UPDATE tempnation_history SET current_name=nation" #None if don't want
            ],
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

def validate_datetime(date_text, format):
    try:
        if date_text != datetime.datetime.strptime(date_text, format).strftime(format):
            raise ValueError
        return True
    except ValueError:
        return False