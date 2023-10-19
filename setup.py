
from datetime import timedelta
from discord import Object
from client.funcs import generate_time
import datetime

"""
Setup file!
-Make sure to clear all images from ./cache if adjusting map settings, otherwise may still show an old image when testing

"""

version = "2.0.0"

refresh_commands = False # Whether to update slash commands. Prefer to keep this at False (unless needed) for faster startup and less likely to get rate limited
PRODUCTION_MODE = False # Enables error handling and stuff. Set to False during testing, True during release

commands = True # Whether to listen for commands

mod_guild = Object(id=985589916794765332) # Guild to add mod commands to
alert_channel = 1155439092423733359 # Channel ID to send heavy error messages to
request_channel = 985590035556479017 # Channel ID to send /request stuff
mods = [368071242189897728] # List of User IDs who are "bot moderators". They can accept requests. First member of this list should be bot owner

DEFAULT_TOWNS = ["RulerSpawn", "Sea", "Unclaimed", "Europe_Quarry", "North_America_Quarry", "Asia-Pacific_Quarry", "South_America_Quarry", "Africa_Quarry"] # Ignore these towns in certain commands. Will still be tracked and can still be seen with /get
DONT_TRACK_TOWNS = ["Sea", "RulerSpawn", "Unclaimed"] # Ignore these towns while tracking.

IMAGE_DPI_GRAPH = 100 # DPI (image quality) for graphs (bar charts, pie charts, line graphs)
IMAGE_DPI_DRAWING = 300 # DPI (image quality) for drawings (maps)
timeline_colors = ["red", "green", "brown", "orange", "purple", "yellow"] # Colours for timelines 
timeline_colors_bool = ["green", "red"] # True, False bool colours for timeline
bar_color = "#1F1F1F" # Colour of bars in images in commands such as /top
line_color = "silver"
map_bordering_town_fill_colour = "#808080"
map_bordering_town_opacity = 10 # 1-100 opacity for bordering towns on /get town and /get nation maps

earth_bg_path = "earth.png"
likely_residency_prefix_history = "`[R]` "

map_url = "https://map.rulercraft.com" # Base map URL
refresh_period = 30 # Duration in seconds to refresh
map_link_zoom = 10 # Zoom level for map links. Eg "Location" in /get player

cull_history_from = timedelta(days=45) # Duration of time to remove history from the database after
cull_players_from = timedelta(days=45) # Duration of time to remove players from the database after
cull_objects_after = timedelta(minutes=1) # Duration of time to remove deleted towns/nations from the database after. Does not clear history, just concurrent data used in /top etc

top_graph_object_count = 25 # Number of towns/players/nations to display in "/top" bar charts
history_skip_if_object_unknown = False # If True and an object (town/player) is not known, ignore it completely in history commands. If False will still display but with diff. format
see_more_footer = True # Show a footer saying "see more with /command..." under certain commands. useful when bot is new for button calls

show_earth_bg_if_over = 2000 # Shows earth background on maps if over this number (blocks) high or wide

embed = 0x2F3136
embedFail = 0xFF0000
embedSuccess = 0x32CD32

history_commands = {
    "town":[
            {"attribute":"nation", "qualitative":True, "formatter":None, "name":None, "parser":None},
            {"attribute":"religion", "qualitative":True, "formatter":None, "name":None, "parser":None},
            {"attribute":"culture", "qualitative":True, "formatter":None, "name":None, "parser":None},
            {"attribute":"mayor", "qualitative":True, "formatter":None, "name":None, "parser":None},
            {"attribute":"resident_count", "qualitative":False, "formatter":None, "name":None, "parser":None, "y":"Residents"},
            {"attribute":"resident_tax", "qualitative":False, "formatter":lambda x: f"{x:,.1f}%", "name":"tax", "parser":None, "y":"Tax (%)"},
            {"attribute":"bank", "qualitative":False, "formatter":lambda x: f"${x:,.2f}", "name":None, "parser":None, "y":"Bank ($)"},
            {"attribute":"public", "qualitative":True, "formatter":None, "name":None, "parser":bool},
            #{"attribute":"peaceful", "qualitative":True, "formatter":None, "name":None, "parser":bool},
            {"attribute":"area", "qualitative":False, "formatter":lambda x: f"{x:,} plots", "name":None, "parser":None, "y":"plots"},
            {"attribute":"duration", "qualitative":False, "formatter":generate_time, "name":"activity", "y":"Time", "y_formatter":generate_time},
            {"attribute":"area/resident_count", "qualitative":False, "formatter":lambda x: f"{x:,} plots/resident", "name":"population_density", "parser":None, "y":"Plots per resident"},
    ],
    "player":[
            {"attribute":"duration", "qualitative":False, "formatter":generate_time, "name":"activity", "y":"Time", "y_formatter":generate_time}
    ],
    "nation":[
            {"attribute":"towns", "qualitative":False, "formatter":None, "name":"towns", "parser":None},
            {"attribute":"town_balance", "qualitative":False, "formatter":lambda x: f"${x:,.2f}", "name":"town_value", "parser":None, "y":"Bank ($)"},
            {"attribute":"residents", "qualitative":False, "formatter":None, "name":"residents", "parser":None},
            {"attribute":"capital", "qualitative":True, "formatter":None, "name":None, "parser":None},
            {"attribute":"leader", "qualitative":True, "formatter":None, "name":None, "parser":None},
            {"attribute":"area", "qualitative":False, "formatter":lambda x: f"{x:,} plots", "name":"area", "parser":None, "y":"Area (plots)"},
            {"attribute":"area/residents", "qualitative":False, "formatter":lambda x: f"{x:,} plots/resident", "name":"population_density", "parser":None, "y":"Plots per resident"},
    ],
    "object":[ # Religion and Culture
            {"attribute":"towns", "qualitative":False, "formatter":None, "name":"towns", "parser":None},
            {"attribute":"town_balance", "qualitative":False, "formatter":lambda x: f"${x:,.2f}", "name":"town_value", "parser":None, "y":"Bank ($)"},
            {"attribute":"residents", "qualitative":False, "formatter":None, "name":"residents", "parser":None},
            {"attribute":"area", "qualitative":False, "formatter":lambda x: f"{x:,} plots", "name":"area", "parser":None, "y":"Area (plots)"}
    ],
    "global":[
            {"attribute":"towns", "qualitative":False, "formatter":None, "name":"towns", "parser":None},
            {"attribute":"town_value", "qualitative":False, "formatter":lambda x: f"${x:,.2f}", "name":"town_value", "parser":None, "y":"Bank ($)"},
            {"attribute":"residents", "qualitative":False, "formatter":lambda x: f"{x:,}", "name":"residents", "parser":None},
            {"attribute":"area", "qualitative":False, "formatter":lambda x: f"{x:,} plots", "name":"area", "parser":None, "y":"Area (plots)"},
            {"attribute":"nations", "qualitative":False, "formatter":None, "name":"nations", "parser":None},
            {"attribute":"known_players", "qualitative":False, "formatter":lambda x: f"{x:,}", "name":None, "parser":None}
    ]
}

top_commands = {
    "town":[
        {"attribute":"resident_count", "formatter":None, "name":"residents", "parser":None},
        {"attribute":"resident_tax", "formatter":lambda x: f"{x:,.1f}%", "name":"tax", "parser":None, "y":"Tax (%)"},
        {"attribute":"bank", "formatter":lambda x: f"${x:,.2f}", "name":None, "parser":None, "y":"Bank ($)"},
        {"attribute":"area", "formatter":lambda x: f"{x:,} plots", "name":None, "parser":None, "y":"Area (plots)"},
        {"attribute":"duration", "formatter":generate_time, "name":"activity", "y":"Time", "y_formatter":generate_time},
        {"attribute":"founded_date", "formatter":lambda x: f"{x:,} days ({datetime.date.today()-datetime.timedelta(days=x)})", "name":"age", "parser":lambda x: (datetime.date.today() - x).days, "y":"Age (days)", "reverse":True},
        {"attribute":"area/resident_count", "qualitative":False, "formatter":lambda x: f"{x:,} plots/resident", "name":"population_density", "parser":None, "y":"Plots per resident"},
    ],
    "player":[
        {"attribute":"duration", "formatter":generate_time, "name":"activity", "y":"Time", "y_formatter":generate_time}
    ],
    "nation":[
        {"attribute":"towns", "formatter":None, "name":"towns", "parser":None},
        {"attribute":"town_balance", "formatter":lambda x: f"${x:,.2f}", "name":"town_value", "parser":None, "y":"Bank ($)"},
        {"attribute":"residents", "formatter":None, "name":"residents", "parser":None},
        {"attribute":"area", "formatter":lambda x: f"{x:,} plots", "name":"area", "parser":None, "y":"Area (plots)"},
        {"attribute":"area/residents", "qualitative":False, "formatter":lambda x: f"{x:,} plots/resident", "name":"population_density", "parser":None, "y":"Plots per resident"},
    ],
    "object":[#Culture and Religion
        {"attribute":"towns", "formatter":None, "name":"towns", "parser":None},
        {"attribute":"town_balance", "formatter":lambda x: f"${x:,.2f}", "name":"town_value", "parser":None, "y":"Bank ($)"},
        {"attribute":"residents", "formatter":None, "name":"residents", "parser":None},
        {"attribute":"area", "formatter":lambda x: f"{x:,} plots", "name":"area", "parser":None, "y":"Area (plots)"}
    ]
}

distribution_commands = {
    "object":[ # Nation, culture religion
        {"attribute":"bank", "formatter":lambda x: f"${x:,.2f}", "name":"town_bank", "parser":None},
        {"attribute":"resident_count", "formatter":None, "name":"residents", "parser":None},
        {"attribute":"area", "formatter":lambda x: f"{x:,} plots", "name":"area", "parser":None},
        {"attribute":"duration", "formatter":lambda x: generate_time(x*60), "name":"activity", "parser":lambda x: x/60}
    ]
}

flags = { # Don't change these unless you know what you're doing
    "player":{
        "discord":{"unique":True}
    },
    "nation":{
        "server":{"unique":False}
    }
}


# Template for town descriptions. Needs to be updated ASAP when server updates
template = """<div><div style="text-align:left"> <img src="
(.*)" /><p><span style="font-size:130%;font-weight:600">
&#x1f3f0; (.*)</span></p> <hr /> <p><span style="font-size:120%;font-weight:600">&#x1f38c; (.*)</span></p> <hr /> <p><span style="font-size:100%">
&#x1f6d0; (.*)</span></p> <p><span style="font-size:100%">
&#x1f54e; (.*)</span></p> <hr /> <p><span style="font-size:120%;font-weight:600">&#x1f451; 
Ruler:</span></p> <span style="font-size:100%">(.*)</span> <img style="border-width:1px;border-style:solid;border-color:#000;width:30px;height:30px" src="
(.*)" /> <hr /> <p><span style="font-size:90%;font-weight:600">&#x1f465; 
Residents:</span> (.*)<br /></p> <p><span style="font-size:90%;font-weight:600">
⏳ Founded:</span> (.*)<br /></p> <p><span style="font-size:90%;font-weight:600">
% Resident Tax:</span> (.*)<br /></p> <p><span style="font-size:90%"><span style="font-weight:600">
&#x1f4b0; Bank:</span> (.*) Dollars</span></p> <p><span style="font-size:90%"><span style="font-weight:600">
&#x1f6a5; Public:</span> (.*)</span></p> </div></div>""".replace("\n", "")