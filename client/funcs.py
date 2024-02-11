
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

        tables = [['players','messages','integer','0',[db.CreationAttribute('name',db.types.String,primary_key=True),db.CreationAttribute('location',db.types.String),db.CreationAttribute('town',db.types.String),db.CreationAttribute('armor',db.types.Int),db.CreationAttribute('health',db.types.Int),db.CreationAttribute('visited_towns',db.types.Int),db.CreationAttribute('donator',db.types.Int),db.CreationAttribute('messages',db.types.Int),db.CreationAttribute('duration',db.types.Int),db.CreationAttribute('last',db.types.Datetime)],['name','location','town','armor','health','visited_towns','donator','duration','last'],None],['players','mentions','integer','0',[db.CreationAttribute('name',db.types.String,primary_key=True),db.CreationAttribute('location',db.types.String),db.CreationAttribute('town',db.types.String),db.CreationAttribute('armor',db.types.Int),db.CreationAttribute('health',db.types.Int),db.CreationAttribute('visited_towns',db.types.Int),db.CreationAttribute('donator',db.types.Int),db.CreationAttribute('messages',db.types.Int),db.CreationAttribute('mentions',db.types.Int),db.CreationAttribute('duration',db.types.Int),db.CreationAttribute('last',db.types.Datetime)],['name','location','town','armor','health','visited_towns','donator','messages','duration','last'],None],['player_history','messages','integer','NULL',[db.CreationAttribute('player',db.types.String),db.CreationAttribute('date',db.types.Date),db.CreationAttribute('duration',db.types.Int),db.CreationAttribute('visited_towns',db.types.Int),db.CreationAttribute('likely_town',db.types.String),db.CreationAttribute('likely_nation',db.types.String),db.CreationAttribute('messages',db.types.Int)],['player','date','duration','visited_towns','likely_town','likely_nation'],None],['player_history','mentions','integer','NULL',[db.CreationAttribute('player',db.types.String),db.CreationAttribute('date',db.types.Date),db.CreationAttribute('duration',db.types.Int),db.CreationAttribute('visited_towns',db.types.Int),db.CreationAttribute('likely_town',db.types.String),db.CreationAttribute('likely_nation',db.types.String),db.CreationAttribute('messages',db.types.Int),db.CreationAttribute('mentions',db.types.Int)],['player','date','duration','visited_towns','likely_town','likely_nation','messages'],None],['towns','mentions','integer','0',[db.CreationAttribute('name',db.types.String,primary_key=True),db.CreationAttribute('nation',db.types.String),db.CreationAttribute('religion',db.types.String),db.CreationAttribute('culture',db.types.String),db.CreationAttribute('mayor',db.types.String),db.CreationAttribute('resident_count',db.types.Int),db.CreationAttribute('founded_date',db.types.Date),db.CreationAttribute('resident_tax',db.types.Float),db.CreationAttribute('bank',db.types.Float),db.CreationAttribute('public',db.types.Int),db.CreationAttribute('peaceful',db.types.Int),db.CreationAttribute('area',db.types.Int),db.CreationAttribute('mentions',db.types.Int),db.CreationAttribute('visited_players',db.types.Int),db.CreationAttribute('duration',db.types.Int),db.CreationAttribute('last_seen',db.types.Datetime)],['name','nation','religion','culture','mayor','resident_count','founded_date','resident_tax','bank','public','peaceful','area','visited_players','duration','last_seen'],None],['town_history','mentions','integer','NULL',[db.CreationAttribute('town',db.types.String),db.CreationAttribute('date',db.types.Date),db.CreationAttribute('nation',db.types.String),db.CreationAttribute('religion',db.types.String),db.CreationAttribute('culture',db.types.String),db.CreationAttribute('mayor',db.types.String),db.CreationAttribute('resident_count',db.types.Int),db.CreationAttribute('resident_tax',db.types.Float),db.CreationAttribute('bank',db.types.Float),db.CreationAttribute('public',db.types.Int),db.CreationAttribute('peaceful',db.types.Int),db.CreationAttribute('area',db.types.Int),db.CreationAttribute('duration',db.types.Int),db.CreationAttribute('visited_players',db.types.Int),db.CreationAttribute('current_name',db.types.String),db.CreationAttribute('mentions',db.types.Int)],['town','date','nation','religion','culture','mayor','resident_count','resident_tax','bank','public','peaceful','area','duration','visited_players','current_name'],None],['objects','mentions','integer','0',[db.CreationAttribute('type',db.types.String),db.CreationAttribute('name',db.types.String),db.CreationAttribute('towns',db.types.Int),db.CreationAttribute('town_balance',db.types.Float),db.CreationAttribute('residents',db.types.Int),db.CreationAttribute('area',db.types.Int),db.CreationAttribute('mentions',db.types.Int),db.CreationAttribute('duration',db.types.Int),db.CreationAttribute('last',db.types.Datetime)],['type','name','towns','town_balance','residents','area','duration','last'],None],['object_history','mentions','integer','NULL',[db.CreationAttribute('date',db.types.Date),db.CreationAttribute('type',db.types.String),db.CreationAttribute('object',db.types.String),db.CreationAttribute('towns',db.types.Int),db.CreationAttribute('town_balance',db.types.Float),db.CreationAttribute('residents',db.types.Int),db.CreationAttribute('area',db.types.Int),db.CreationAttribute('mentions',db.types.Int)],['date','type','object','towns','town_balance','residents','area'],None],['nation_history','mentions','integer','NULL',[db.CreationAttribute('nation',db.types.String),db.CreationAttribute('date',db.types.Date),db.CreationAttribute('towns',db.types.Int),db.CreationAttribute('town_balance',db.types.Float),db.CreationAttribute('residents',db.types.Int),db.CreationAttribute('capital',db.types.String),db.CreationAttribute('leader',db.types.String),db.CreationAttribute('area',db.types.Int),db.CreationAttribute('duration',db.types.Int),db.CreationAttribute('current_name',db.types.String),db.CreationAttribute('mentions',db.types.Int)],['nation','date','towns','town_balance','residents','capital','leader','area','duration','current_name'],None],['global_history','messages','integer','NULL',[db.CreationAttribute('date',db.types.Date),db.CreationAttribute('towns',db.types.Int),db.CreationAttribute('residents',db.types.Int),db.CreationAttribute('nations',db.types.Int),db.CreationAttribute('town_value',db.types.Float),db.CreationAttribute('area',db.types.Int),db.CreationAttribute('known_players',db.types.Int),db.CreationAttribute('activity',db.types.Int),db.CreationAttribute('messages',db.types.Int)],['date','towns','residents','nations','town_value','area','known_players','activity'],None],['global_history','database_size','real','NULL',[db.CreationAttribute('date',db.types.Date),db.CreationAttribute('towns',db.types.Int),db.CreationAttribute('residents',db.types.Int),db.CreationAttribute('nations',db.types.Int),db.CreationAttribute('town_value',db.types.Float),db.CreationAttribute('area',db.types.Int),db.CreationAttribute('known_players',db.types.Int),db.CreationAttribute('activity',db.types.Int),db.CreationAttribute('messages',db.types.Int),db.CreationAttribute('database_size',db.types.Float)],['date','towns','residents','nations','town_value','area','known_players','activity','messages'],None],['global_day_history','messages','integer','NULL',[db.CreationAttribute('time',db.types.Datetime),db.CreationAttribute('towns',db.types.Int),db.CreationAttribute('residents',db.types.Int),db.CreationAttribute('nations',db.types.Int),db.CreationAttribute('town_value',db.types.Float),db.CreationAttribute('area',db.types.Int),db.CreationAttribute('known_players',db.types.Int),db.CreationAttribute('activity',db.types.Int),db.CreationAttribute('messages',db.types.Int)],['time','towns','residents','nations','town_value','area','known_players','activity'],None],['towns','outposts','integer','0',[db.CreationAttribute('name',db.types.String,primary_key=True),db.CreationAttribute('nation',db.types.String),db.CreationAttribute('religion',db.types.String),db.CreationAttribute('culture',db.types.String),db.CreationAttribute('mayor',db.types.String),db.CreationAttribute('resident_count',db.types.Int),db.CreationAttribute('founded_date',db.types.Date),db.CreationAttribute('resident_tax',db.types.Float),db.CreationAttribute('bank',db.types.Float),db.CreationAttribute('public',db.types.Int),db.CreationAttribute('peaceful',db.types.Int),db.CreationAttribute('area',db.types.Int),db.CreationAttribute('mentions',db.types.Int),db.CreationAttribute('outposts',db.types.Int),db.CreationAttribute('visited_players',db.types.Int),db.CreationAttribute('duration',db.types.Int),db.CreationAttribute('last_seen',db.types.Datetime)],['name','nation','religion','culture','mayor','resident_count','founded_date','resident_tax','bank','peaceful','area','mentions','visited_players','duration','last_seen'],None],['global_day_history','online_players','integer','NULL',[db.CreationAttribute('time',db.types.Datetime),db.CreationAttribute('towns',db.types.Int),db.CreationAttribute('residents',db.types.Int),db.CreationAttribute('nations',db.types.Int),db.CreationAttribute('town_value',db.types.Float),db.CreationAttribute('area',db.types.Int),db.CreationAttribute('known_players',db.types.Int),db.CreationAttribute('activity',db.types.Int),db.CreationAttribute('messages',db.types.Int),db.CreationAttribute('online_players',db.types.Int)],['time','towns','residents','nations','town_value','area','known_players','activity','messages'],None]]
        
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