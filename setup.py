
from datetime import timedelta

refresh_commands = False
PRODUCTION_MODE = False


IMAGE_DPI = 200
timeline_colors = ["red", "green", "brown", "orange", "purple", "yellow"]

map_url = "https://map.rulercraft.com" # Base map URL
refresh_period = 30 # Duration in seconds to refresh
map_link_zoom = 10 # Zoom level for map links. Eg "Location" in /get player

cull_history_from = timedelta(days=45)
cull_players_from = timedelta(days=45)
cull_towns_after = timedelta(hours=1)

embed = 0x2F3136
embedFail = 0xFF0000
embedSuccess = 0x32CD32

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