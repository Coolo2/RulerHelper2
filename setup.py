
from datetime import timedelta

refresh_commands = False
PRODUCTION_MODE = False

DEFAULT_TOWNS = ["RulerSpawn"] # Ignore these towns in certain commands. Will still be tracked and can still be seen with /get
DONT_TRACK_TOWNS = ["Sea", "RulerSpawn", "Unclaimed"] # Ignore these towns while tracking.

IMAGE_DPI_GRAPH = 100 # DPI (image quality) for graphs (bar charts, pie charts, line graphs)
IMAGE_DPI_DRAWING = 300 # DPI (image quality) for drawings (maps)
timeline_colors = ["red", "green", "brown", "orange", "purple", "yellow"] # Colours for timelines 
bar_color = "#1F1F1F" # Colour of bars in images in commands such as /top

map_url = "https://map.rulercraft.com" # Base map URL
refresh_period = 30 # Duration in seconds to refresh
map_link_zoom = 10 # Zoom level for map links. Eg "Location" in /get player

cull_history_from = timedelta(days=45) # Duration of time to remove history from the database after
cull_players_from = timedelta(days=45) # Duration of time to remove players from the database after
cull_objects_after = timedelta(hours=2) # Duration of time to remove deleted towns/nations from the database after

top_graph_object_count = 25 # Number of towns/players/nations to display in "/top" bar charts
history_skip_if_object_unknown = False # If True and an object (town/player) is not known, ignore it completely in history commands. If False will display "UNKOWN"
see_more_footer = True # Show a footer saying "see more with /command..." under certain commands. useful when bot is new for button calls

embed = 0x2F3136
embedFail = 0xFF0000
embedSuccess = 0x32CD32

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
&#x1f6a5; Public:</span> (.*)</span></p> <p><span style="font-size:90%"><span style="font-weight:600">
&#x1f308; Peaceful:</span> (.*)</span></p></div></div>""".replace("\n", "")