
from client import Client
import json

async def activity_to_json(client : Client):

    a = {"towns":{}, "players":{}}

    for town in client.world.towns:
        a["towns"][town.name] = (await town.activity).total
    for player in client.world.players:
        a["players"][player.name] = (await player.activity).total 
    
    with open("activity.json", "w") as f:
        f.write(json.dumps(a, indent=4))
