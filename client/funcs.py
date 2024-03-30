
import db
import datetime
import discord

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
        if notable: notable_statistics += f"\n- {discord.utils.escape_markdown(object_name)} is **#{ranking}** on the **{leaderboard.replace('_', ' ')}** ranking"
    if not notable_only or notable_statistics == "": notable_statistics = "None"

    return notable_statistics

async def update_db(c):

        tables = [['players','bank','real','NULL',[db.CreationAttribute('name',db.types.String,primary_key=True),db.CreationAttribute('location',db.types.String),db.CreationAttribute('town',db.types.String),db.CreationAttribute('armor',db.types.Int),db.CreationAttribute('health',db.types.Int),db.CreationAttribute('visited_towns',db.types.Int),db.CreationAttribute('donator',db.types.Int),db.CreationAttribute('bank',db.types.Float),db.CreationAttribute('messages',db.types.Int),db.CreationAttribute('mentions',db.types.Int),db.CreationAttribute('duration',db.types.Int),db.CreationAttribute('last',db.types.Datetime)],['name','location','town','armor','health','visited_towns','donator','messages','mentions','duration','last'],None],['player_history','bank','real','NULL',[db.CreationAttribute('player',db.types.String),db.CreationAttribute('date',db.types.Date),db.CreationAttribute('duration',db.types.Int),db.CreationAttribute('visited_towns',db.types.Int),db.CreationAttribute('likely_town',db.types.String),db.CreationAttribute('likely_nation',db.types.String),db.CreationAttribute('bank',db.types.Float),db.CreationAttribute('messages',db.types.Int),db.CreationAttribute('mentions',db.types.Int)],['player','date','duration','visited_towns','likely_town','likely_nation','messages','mentions'],None],['player_day_history','bank','real','NULL',[db.CreationAttribute('player',db.types.String),db.CreationAttribute('time',db.types.Datetime),db.CreationAttribute('duration',db.types.Int),db.CreationAttribute('bank',db.types.Float),db.CreationAttribute('visited_towns',db.types.Int)],['player','time','duration','visited_towns'],None],['global_history','mayor_value','real','NULL',[db.CreationAttribute('date',db.types.Date),db.CreationAttribute('towns',db.types.Int),db.CreationAttribute('residents',db.types.Int),db.CreationAttribute('nations',db.types.Int),db.CreationAttribute('town_value',db.types.Float),db.CreationAttribute('mayor_value',db.types.Float),db.CreationAttribute('area',db.types.Int),db.CreationAttribute('known_players',db.types.Int),db.CreationAttribute('activity',db.types.Int),db.CreationAttribute('messages',db.types.Int),db.CreationAttribute('database_size',db.types.Float)],['date','towns','residents','nations','town_value','area','known_players','activity','messages','database_size'],None]]
        
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