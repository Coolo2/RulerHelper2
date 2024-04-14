
from datetime import timedelta
from discord import Object
from discord.utils import escape_markdown
from client.funcs import generate_time
from client.image_generator import YTickFormatter
import datetime
import os

"""
Setup file!
-Make sure to clear all images from ./cache if adjusting map settings, otherwise may still show an old image when testing

"""

version = "2.11.0" # Version number displayed on bot status etc 

PRODUCTION_MODE = False # Enables error handling and stuff. Set to False during testing, True during release
debug_mode = True # Prints debug stuff in console
commands = True # Whether to listen for commands

"""Adjust these on first run. They need to be filled with IDs bot has access to"""
mod_guild = Object(id=985589916794765332) # Guild to add mod commands to
alert_channel = 1155439092423733359 # Channel ID to send heavy error messages to
request_channel = 985590035556479017 # Channel ID to send /request stuff
mods = [368071242189897728] # List of User IDs who are "bot moderators". They can accept requests. First member of this list should be bot owner

"""Adjust these when bot is updated"""
refresh_commands = False # Whether to update slash commands. Prefer to keep this at False (unless needed) for faster startup and less likely to get rate limited
MIGRATE_DB = True # Migrates the database using client/funcs/def update_db. Breaks program if enabled and DB isn't created yet

"""These rarely need to be changed"""
DEFAULT_TOWNS = ["RulerSpawn", "Sea", "Unclaimed"] # Ignore these towns in certain commands. Will still be tracked and can still be seen with /get
DEFAULT_TOWNS_SUBSTRING = ["Quarry", "Trading", "Treasure Ship"]
DONT_TRACK_TOWNS = ["Sea", "RulerSpawn", "Unclaimed"] # Ignore these towns while tracking.

IMAGE_DPI_GRAPH = 100 # DPI (image quality) for graphs (bar charts, pie charts, line graphs)
IMAGE_DPI_DRAWING_SMALL = 250 # DPI (image quality) for small maps (eg /get town thumbnail)
IMAGE_DPI_DRAWING = 600 # DPI (image quality) for drawings (maps)

timeline_colors = ["red", "green", "brown", "orange", "purple", "pink"] # Colours for timelines 
compare_emojis = [":red_square:", ":orange_square:", ":yellow_square:", ":green_square:", ":blue_square:"] # Emojis for compare commands
compare_line_colors = ["red", "orange", "yellow", "green", "cyan"]
connection_line_colours = ["red", "orange", "yellow", "green", "blue", "aqua", "purple", "grey", "black", "white", "cyan", "olive", "pink", "chocolate"] 
timeline_colors_bool = ["green", "red"] # True, False bool colours for timeline
bar_color = "#1F1F1F" # Colour of bars in images in commands such as /top
line_color = "silver"
map_bordering_town_fill_colour = "#808080"
map_bordering_town_opacity = 10 # 1-100 opacity for bordering towns on /get town and /get nation maps

face_size = 64

town_continent_description_compass_distance_threshold = 2500 # number of blocks east/west/south/north to show in /get town continent description
get_town_deletion_warning_threshold_days = 15 # Number of days mayor has to have been inactive to show deletion warning in /get twn

earth_svg_path = "earth.svg"
stretch_earth_bg = (1, 1)
earth_svg_width = 1844
show_earth_bg_if_over = 500 # Shows earth background on maps if over this number (blocks) high or wide
CACHE_IMAGES = False

waiting_bg_path = "map_waiting.jpg"
resident_prefix_history = "`[R]` "

DATE_STRFTIME = "%a %d %b %Y"

refresh_map_url = os.getenv("base_url") # Base map URL
default_refresh_period = {"players":5, "map":20} # Duration in seconds to refresh
map_link_zoom = 6 # Zoom level for map links. Eg "Location" in /get player

cull_players_from = timedelta(days=45) # Duration of time to remove players from the database after
cull_objects_after = timedelta(minutes=1) # Duration of time to remove deleted towns/nations from the database after. Does not clear history, just concurrent data used in /top etc

history_abstraction_thresholds = [
    (timedelta(days=45), "1"),
    (timedelta(days=120), "1, 3"),
    (timedelta(days=200), "1, 3, 5"),
    (timedelta(days=365), "1, 2, 3, 4, 5")
] 
cull_insignificant_activity_after = timedelta(days=90)


top_graph_object_count = 40 # Number of towns/players/nations to display in "/top" bar charts
history_skip_if_object_unknown = False # If True and an object (town/player) is not known, ignore it completely in history commands. If False will still display but with diff. format
see_more_footer = True # Show a footer saying "see more with /command..." under certain commands. useful when bot is new for button calls

embed = 0x2B2D31
embedFail = 0xFF0000
embedSuccess = 0x32CD32

compare_attributes = {
    "town": [
        {"attribute":"activity", "qualitative":False, "y_formatter":YTickFormatter.TIME, "history_attribute":"duration", "inline":True},
        {"attribute":"total_visited_players", "qualitative":False, "name":"visited players", "inline":True, "history_attribute":"visited_players", "inline":True},
        {"attribute":"founded_date", "qualitative":False, "formatter":lambda x: f"{(datetime.date.today()-x).days:,} days ({x.strftime(DATE_STRFTIME)})", "parser":lambda x: (datetime.date.today() - x).days, "name":"age", "y":"Age (days)", "no_history":True},
        {"attribute":"bank", "qualitative":False, "formatter":lambda x: f"${x:,.2f}", "name":None, "y":"Bank ($)", "inline":True},
        {"attribute":"resident_count", "qualitative":False, "name":"residents", "inline":False},
        {"attribute":"area", "qualitative":False, "formatter":lambda x: f"{x:,} plots ({x* 64:,}km²)", "name":None, "y":"Area (plots)", "inline":True},
        {"attribute":"population_density", "qualitative":False, "formatter":lambda x: f"{x:,} plots/resident", "name":None, "y":"Density (plots/resident)", "inline":True, "history_attribute":"area/resident_count"},
        {"attribute":"resident_tax", "qualitative":False, "name":"daily_tax", "y":"Tax (%)", "inline":False},
        {"attribute":"mayor", "qualitative":True, "inline":True, "formatter":lambda x: escape_markdown(x.name if hasattr(x, 'name') else x)},
        {"attribute":"nation", "qualitative":True, "formatter":lambda n: n.name_formatted if n else "None", "inline":True},
        {"attribute":"mention_count", "qualitative":False, "inline":True, "history_attribute":"mentions"}
    ],
    "nation":[
        {"attribute":"activity", "qualitative":False, "y_formatter":YTickFormatter.TIME, "history_attribute":"duration"},
        {"attribute":"total_towns", "qualitative":False, "inline":True, "name":"towns", "history_attribute":"towns"},
        {"attribute":"total_residents", "qualitative":False, "name":"residents", "inline":True, "history_attribute":"residents"},
        {"attribute":"total_value", "qualitative":False, "formatter":lambda x: f"${x:,.2f}", "name":None, "y":"Town Value ($)", "inline":False, "history_attribute":"town_balance"},
        {"attribute":"total_area", "qualitative":False, "formatter":lambda x: f"{x:,} plots ({x* 64:,}km²)", "name":None, "y":"Area (plots)", "inline":True, "history_attribute":"area"},
        {"attribute":"population_density", "qualitative":False, "formatter":lambda x: f"{x:,} plots/resident", "name":None, "y":"Density (plots/resident)", "inline":True, "history_attribute":"area/residents"},
        {"attribute":"leader", "qualitative":True, "inline":False, "formatter":lambda x: escape_markdown(x.name if hasattr(x, 'name') else x)},
        {"attribute":"capital", "qualitative":True, "inline":True},
        {"attribute":"average_town_balance", "qualitative":False, "inline":True, "formatter":lambda x: f"${x:,.2f}", "name":None, "y":"Town Value ($)", "history_attribute":"town_balance/towns"},
        {"attribute":"mention_count", "qualitative":False, "inline":True, "history_attribute":"mentions"}
    ],
    "player":[
        {"attribute":"activity", "qualitative":False, "y_formatter":YTickFormatter.TIME, "history_attribute":"duration"},
        {"attribute":"total_visited_towns", "qualitative":False, "name":"visited towns", "inline":True, "history_attribute":"visited_towns"},
        {"attribute":"total_visited_nations", "qualitative":False, "name":"visited nations", "inline":True, "history_attribute":"visited_nations"},
        {"attribute":"location", "qualitative":True, "formatter":lambda x: f"{int(x.x)}, {int(x.y)}, {int(x.z)}", "inline":False},
        {"attribute":"town", "qualitative":True, "inline":True},
        {"attribute":"residence", "qualitative":True, "inline":True},
        {"attribute":"bank", "qualitative":False, "formatter":lambda x: f"${x:,.2f}" if x else '*Unknown (not mayor)*', "name":None, "y":"Bank ($)", "inline":False},
        {"attribute":"message_count", "qualitative":False, "inline":True, "history_attribute":"messages"},
        {"attribute":"mention_count", "qualitative":False, "inline":True, "history_attribute":"mentions"}
        
    ]
}

history_commands = {
    "town":[
            {"attribute":"nation", "qualitative":True, "formatter":None, "name":None, "parser":lambda x: str(x).replace("_", " ")},
            {"attribute":"religion", "qualitative":True, "formatter":None, "name":None, "parser":lambda x: str(x).replace("_", " ")},
            {"attribute":"culture", "qualitative":True, "formatter":None, "name":None, "parser":lambda x: str(x).replace("_", " ")},
            {"attribute":"mayor", "qualitative":True, "formatter":None, "name":None, "parser":None},
            {"attribute":"resident_count", "qualitative":False, "formatter":None, "name":"residents", "parser":None, "y":"Residents"},
            {"attribute":"resident_tax", "qualitative":False, "formatter":lambda x: f"{x:,.1f}%", "name":"tax", "parser":None, "y":"Tax (%)"},
            {"attribute":"bank", "qualitative":False, "formatter":lambda x: f"${x:,.2f}", "name":None, "parser":None, "y":"Bank ($)"},
            {"attribute":"public", "qualitative":True, "formatter":None, "name":None, "parser":bool, "description":"History of whether the town is accessible by teleport"},
            {"attribute":"area", "qualitative":False, "formatter":lambda x: f"{x:,} plots ({x* 64:,}km²)", "name":None, "parser":None, "y":"plots", "description":"History of town's claimed area"},
            {"attribute":"duration", "qualitative":False, "formatter":generate_time, "name":"activity", "y":"Time", "y_formatter":YTickFormatter.TIME, "description":"History of the town's total time with players within claims"},
            {"attribute":"area/resident_count", "qualitative":False, "formatter":lambda x: f"{x:,} plots/resident", "name":"population_density", "parser":None, "y":"Plots per resident", "description":"History of the amount of plots per resident"},
            {"attribute":"visited_players", "qualitative":False, "formatter":None, "name":"visited_player_count", "parser":None, "y":"Players", "description":"History of the number of players who have visited"},
            {"attribute":"current_name", "qualitative":True, "formatter":None, "name":None, "parser":lambda x: str(x).replace("_", " "), "name":"name"},
            {"attribute":"mentions", "qualitative":False, "formatter":lambda x: f"{x:,}", "parser":None, "y":"Mentions", "description":"History of the amount of times mentioned in chat"}
    ],
    "player":[
            {"attribute":"duration", "qualitative":False, "formatter":generate_time, "name":"activity", "y":"Time", "y_formatter":YTickFormatter.TIME, "description":"The player's time online throughout history"},
            {"attribute":"visited_towns", "qualitative":False, "formatter":None, "name":"visited_town_count", "parser":None, "y":"Towns", "description":"Number of towns the player has visited over time"},
            {"attribute":"visited_nations", "qualitative":False, "formatter":None, "name":"visited_nation_count", "parser":None, "y":"Nations", "description":"Number of nations the player has visited since tracking began"},
            {"attribute":"likely_town", "name":"town_residence", "qualitative":True, "formatter":None, "parser":lambda x: str(x).replace("_", " "), "start_at":datetime.date(2023, 11, 20), "description":"History of the player's likely town residence"},
            {"attribute":"likely_nation", "name":"nation_residence", "qualitative":True, "formatter":None, "parser":lambda x: str(x).replace("_", " "), "start_at":datetime.date(2023, 11, 20), "description":"History of the player's likely nation residence"},
            {"attribute":"bank", "qualitative":False, "formatter":lambda x: f"${x:,.2f}", "name":None, "parser":None, "y":"Bank ($)"},
            {"attribute":"messages", "qualitative":False, "formatter":lambda x: f"{x:,}", "parser":None, "y":"Messages", "description":"History of the number of messages a player's sent"},
            {"attribute":"mentions", "qualitative":False, "formatter":lambda x: f"{x:,}", "parser":None, "y":"Mentions", "description":"History of the amount of times a player's mentioned in chat"}
    ],
    "nation":[
            {"attribute":"towns", "qualitative":False, "formatter":None, "name":"towns", "parser":None},
            {"attribute":"town_balance", "qualitative":False, "formatter":lambda x: f"${x:,.2f}", "name":"town_value", "parser":None, "y":"Bank ($)", "description":"History of nation's town balances totalled"},
            {"attribute":"residents", "qualitative":False, "formatter":None, "name":"residents", "parser":None},
            {"attribute":"capital", "qualitative":True, "formatter":None, "name":None, "parser":lambda x: str(x).replace("_", " ")},
            {"attribute":"leader", "qualitative":True, "formatter":None, "name":None, "parser":None},
            {"attribute":"area", "qualitative":False, "formatter":lambda x: f"{x:,} plots ({x* 64:,}km²)", "name":"area", "parser":None, "y":"Area (plots)", "description":"History of nation's claimed area"},
            {"attribute":"duration", "qualitative":False, "formatter":generate_time, "name":"activity", "y":"Time", "y_formatter":YTickFormatter.TIME, "description":"History of the nation's total time with players within claims"},
            {"attribute":"area/residents", "qualitative":False, "formatter":lambda x: f"{x:,} plots/resident", "name":"population_density", "parser":None, "y":"Plots per resident", "description":"History of the amount of plots per resident"},
            {"attribute":"visited_players", "qualitative":False, "formatter":None, "name":"visited_player_count", "parser":None, "y":"Players", "description":"History of the number of players who have visited"},
            {"attribute":"current_name", "qualitative":True, "formatter":None, "name":None, "parser":lambda x: str(x).replace("_", " "), "name":"name"},
            {"attribute":"town_balance/towns", "qualitative":False, "formatter":lambda x: f"${x:.2f}/town", "name":"average_town_balance", "parser":None, "y":"$/town"},
            {"attribute":"mentions", "qualitative":False, "formatter":lambda x: f"{x:,}", "parser":None, "y":"Mentions", "description":"History of the amount of times mentioned in chat"}
    ],
    "object":[ # Religion and Culture
            {"attribute":"towns", "qualitative":False, "formatter":None, "name":"towns", "parser":None},
            {"attribute":"town_balance", "qualitative":False, "formatter":lambda x: f"${x:,.2f}", "name":"town_value", "parser":None, "y":"Bank ($)"},
            {"attribute":"residents", "qualitative":False, "formatter":None, "name":"residents", "parser":None},
            {"attribute":"area", "qualitative":False, "formatter":lambda x: f"{x:,} plots ({x* 64:,}km²)", "name":"area", "parser":None, "y":"Area (plots)"},
            {"attribute":"mentions", "qualitative":False, "formatter":lambda x: f"{x:,}", "parser":None, "y":"Mentions"}
    ],
    "global":[
            {"attribute":"towns", "qualitative":False, "formatter":None, "name":"towns", "parser":None},
            {"attribute":"town_value", "qualitative":False, "formatter":lambda x: f"${x:,.2f}", "name":"town_value", "parser":None, "y":"Bank ($)"},
            {"attribute":"mayor_value", "qualitative":False, "formatter":lambda x: f"${x:,.2f}", "name":"mayor_value", "parser":None, "y":"Bank ($)"},
            {"attribute":"residents", "qualitative":False, "formatter":lambda x: f"{x:,}", "name":"residents", "parser":None},
            {"attribute":"area", "qualitative":False, "formatter":lambda x: f"{x:,} plots ({x* 64:,}km²)", "name":"area", "parser":None, "y":"Area (plots)"},
            {"attribute":"nations", "qualitative":False, "formatter":None, "name":"nations", "parser":None},
            {"attribute":"known_players", "qualitative":False, "formatter":lambda x: f"{x:,}", "name":None, "parser":None},
            {"attribute":"activity", "qualitative":False, "formatter":generate_time, "name":"total_player_activity", "y":"Time", "y_formatter":YTickFormatter.TIME},
            {"attribute":"messages", "qualitative":False, "formatter":lambda x: f"{x:,}", "parser":None, "y":"Messages"},
            {"attribute":"database_size", "qualitative":False, "formatter":lambda x: f"{x:,.2f} MB", "parser":None, "y":"Size (MB)"},
            {"attribute":"online_players", "qualitative":False, "formatter":None, "parser":None, "y":"Online players", "today_only":True},
    ]
}

# Uses history settings 
history_today_commands = {
    "player":["activity", "visited_town_count", "visited_nation_count", "bank"],
    "town":["residents", "tax", "bank", "area", "activity"],
    "nation":["towns", "town_value", "residents", "area", "activity", "visited_player_count"],
    "global":["towns", "town_value", "residents", "area", "nations", "known_players", "total_player_activity", "messages", "online_players"]
}

top_commands = {
    "town":[
        {"attribute":"resident_count", "formatter":None, "name":"residents", "parser":None},
        {"attribute":"resident_tax", "formatter":lambda x: f"{x:,.1f}%", "name":"tax", "parser":None, "y":"Tax (%)", "reverse_notable":True, "reverse":True},
        {"attribute":"bank", "formatter":lambda x: f"${x:,.2f}", "name":None, "parser":None, "y":"Bank ($)"},
        {"attribute":"area", "formatter":lambda x: f"{x:,} plots ({x* 64:,}km²)", "name":None, "parser":None, "y":"Area (plots)"},
        {"attribute":"duration", "formatter":generate_time, "name":"activity", "y":"Time", "y_formatter":YTickFormatter.TIME},
        {"attribute":"founded_date", "formatter":lambda x: f"{x:,} days ({(datetime.date.today()-datetime.timedelta(days=x)).strftime(DATE_STRFTIME)})", "name":"age", "parser":lambda x: (datetime.date.today() - x).days, "y":"Age (days)", "reverse":True, "reverse_notable":True, "not_in_history":True},
        {"attribute":"mayor_inactivity", "description": "Top towns (with 1 resident) by time the mayor has been inactive", "formatter":lambda x: f"{x:,} days ({(datetime.date.today()-datetime.timedelta(days=x)).strftime(DATE_STRFTIME)})", "parser":lambda x: ((datetime.datetime.now() - (x or datetime.datetime.now())).days), "y":"Time (days)", "reverse":True, "reverse_notable":True, "not_in_history":True},
        {"attribute":"area/resident_count", "qualitative":False, "formatter":lambda x: f"{x:,} plots/resident", "name":"population_density", "parser":None, "y":"Plots per resident", "reverse_notable":True, "reverse":True},
        {"attribute":"visited_players", "qualitative":False, "formatter":None, "name":None, "parser":None, "y":"Player count"},
        {"attribute":"mentions", "formatter":lambda x: f"{x:,}", "parser":None},
        {"attribute":"outposts", "formatter":None, "parser":None, "not_in_history":True}
    ],
    "player":[
        {"attribute":"duration", "formatter":generate_time, "name":"activity", "y":"Time", "y_formatter":YTickFormatter.TIME},
        {"attribute":"visited_towns", "qualitative":False, "formatter":None, "name":None, "parser":None, "y":"Town count"},
        {"attribute":"visited_nations", "qualitative":False, "formatter":None, "name":None, "parser":None, "y":"Nation count"},
        {"attribute":"bank", "qualitative":False, "formatter":lambda x: f"${x:,.2f}", "name":None, "parser":None, "y":"Bank ($)"},
        {"attribute":"messages", "formatter":lambda x: f"{x:,}", "parser":None},
        {"attribute":"mentions", "formatter":lambda x: f"{x:,}", "parser":None},
    ],
    "nation":[
        {"attribute":"towns", "formatter":None, "name":"towns", "parser":None},
        {"attribute":"town_balance", "formatter":lambda x: f"${x:,.2f}", "name":"town_value", "parser":None, "y":"Bank ($)"},
        {"attribute":"residents", "formatter":None, "name":"residents", "parser":None},
        {"attribute":"area", "formatter":lambda x: f"{x:,} plots ({x* 64:,}km²)", "name":"area", "parser":None, "y":"Area (plots)"},
        {"attribute":"duration", "formatter":generate_time, "name":"activity", "y":"Time", "y_formatter":YTickFormatter.TIME},
        {"attribute":"area/residents", "qualitative":False, "formatter":lambda x: f"{x:,} plots/resident", "name":"population_density", "parser":None, "y":"Plots per resident", "reverse_notable":True, "reverse":True},
        {"attribute":"town_balance/towns", "qualitative":False, "formatter":lambda x: f"${x:,.2f}/town", "name":"average_town_balance", "parser":None, "y":"$/town"},
        {"attribute":"mentions", "formatter":lambda x: f"{x:,}", "parser":None},
        {"attribute":"visited_players", "qualitative":False, "formatter":None, "name":None, "parser":None, "y":"Player count", "notable":False},
    ],
    "object":[#Culture and Religion
        {"attribute":"towns", "formatter":None, "name":"towns", "parser":None},
        {"attribute":"town_balance", "formatter":lambda x: f"${x:,.2f}", "name":"town_value", "parser":None, "y":"Bank ($)"},
        {"attribute":"residents", "formatter":None, "name":"residents", "parser":None},
        {"attribute":"area", "formatter":lambda x: f"{x:,} plots ({x* 64:,}km²)", "name":"area", "parser":None, "y":"Area (plots)"},
        {"attribute":"mentions", "formatter":lambda x: f"{x:,}", "parser":None}
    ]
}

distribution_commands = {
    "object":[ # Nation, culture religion
        {"attribute":"bank", "formatter":lambda x: f"${x:,.2f}", "name":"town_bank", "parser":None},
        {"attribute":"resident_count", "formatter":None, "name":"residents", "parser":None},
        {"attribute":"area", "formatter":lambda x: f"{x:,} plots ({x* 64:,}km²)", "name":"area", "parser":None},
        {"attribute":"duration", "formatter":lambda x: generate_time(x*60), "name":"activity", "parser":lambda x: x/60},
        {"attribute":"visited_players", "formatter":lambda x: f"{x:,}", "name":None, "parser":None},
    ],
    "nation":[
        {"attribute":"mayor_bank", "formatter":lambda x: f"${x:,.2f}", "name":None, "parser":None},
    ]
}

# Don't change these unless you know what you're doing
flags = { 
    "player":{
        "discord":{"unique":True}
    },
    "nation":{
        "server":{"unique":False}
    }
}

# Template for town descriptions. Needs to be updated ASAP when server updates
template = """
<div><div style="text-align:left"> <img src="
(.*)" /><p><span style="font-size:130%;font-weight:600">&#x1f3f0; 
(.*)</span></p><hr /> <p><span style="font-size:120%;font-weight:600">&#x1f38c; 
(.*)</span></p><hr /> <p><span style="font-size:100%">&#x1f6d0; 
(.*)</span></p> <p><span style="font-size:100%">&#x1f54e; 
(.*)</span></p> <hr /> <p><span style="font-size:120%;font-weight:600">&#x1f451; Ruler:</span></p><img style="border-width:1px;border-style:solid;border-color:#000;width:30px;height:30px" src="
(.*)" /> <span style="font-size:100%">
(.*)</span><hr /> <p><span style="font-size:90%;font-weight:600">&#x1f465; Residents:</span> 
(.*)<br /></p><span style="font-size:88%">
(.*)</span> <p><span style="font-size:90%;font-weight:600">⏳ Founded:</span> 
(.*)<br /></p> <p><span style="font-size:90%;font-weight:600">% Resident Tax:</span> 
(.*)<br /></p> <p><span style="font-size:90%"><span style="font-weight:600">&#x1f4b0; Bank:</span> 
(.*) Dollars <b>Mayor:</b> 
(.*)</span></p> <p><span style="font-size:90%"><span style="font-weight:600">&#x1f6a5; Public Teleport:</span> 
(.*)</span></p>
(.*)</div></div>


""".replace("\n", "").replace(" ", "")