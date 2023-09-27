from __future__ import annotations
import typing
import asyncio
if typing.TYPE_CHECKING:
    import client as client_pre

import datetime
from shapely.geometry import MultiPolygon, Polygon, Point
import re

import setup 
import db
from db.wrapper import Record
from io import BytesIO

from aiohttp import StreamReader
import ijson.backends.python as ijson

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

class Money(float):
    def __init__(self, value : float):
        self.value = value 

    def format(self):
        return f"${self.value:,.2f}"

class Activity():
    def __init__(self, total : int = 0, last : datetime.datetime = datetime.datetime.now(), town : client_pre.object.Town|str = None, player : client_pre.object.Player|str = None):
        self.total = total 
        self.last = last

        self.town = town
        self.player = player
    
    def from_record(record : Record, town : client_pre.object.Town = None):
        a = Activity()
        a.total = record.attribute("duration")
        a.last = record.attribute("last")
        a.town = town

        return a
    
    def str_no_timestamp(self):
        return generate_time(self.total)

    def __radd__(self, other):
        return Activity(self.total + other.total, max(self.last, other.last), self.town)

    def __str__(self):
        return f"{generate_time(self.total)}" + (f" <t:{round(self.last.timestamp())}:R>" if self.total > 0 else '')

class Object():
    def __init__(self, world : client_pre.object.World, name : str, object_type : str):
        self.name = name 
        self.world = world
        self.object_type = object_type

        if self.name not in world._objects[self.object_type + "s"]:
            world._objects[self.object_type + "s"].append(self)
    
    @property 
    def name_formatted(self):
        return self.name.replace("_", " ").title()
    
    def __total(self, arr : list, attr : str):
        t = 0
        for o in arr:
            t += getattr(o, attr)
        return t

    def to_record(self):
        return [self.object_type, self.name, len(self.towns), self.total_value, self.total_residents, self.total_area, datetime.datetime.now()]

    @property 
    def total_residents(self) -> int: return self.__total(self.towns, "resident_count")
    @property 
    def total_area(self) -> int: return self.__total(self.towns, "area")
    @property 
    def total_value(self) -> float: return self.__total(self.towns, "bank")

    async def set_flag(self, flag_name : str, flag_value):
        cond = [db.CreationCondition("object_type", self.object_type), db.CreationCondition("object_name", self.name)]
        val = [self.object_type, self.name, flag_name, flag_value]
        a = await self.world.client.flags_table.add_record_if_not_exists(val, cond)
        if not a:
            await self.world.client.flags_table.update_record(cond, *val)
    
    @property
    async def flags(self) -> dict:
        rs = await self.world.client.flags_table.get_records([db.CreationCondition("object_type", self.object_type), db.CreationCondition("object_name", self.name)], ["name", "value"])
        d = {}
        for r in rs:
            d[r.attribute("name")] = r.attribute("value")
        return d

    @property 
    async def exists_in_db(self):
        return await self.world.client.objects_table.record_exists([db.CreationCondition("type", self.object_type), db.CreationCondition("name", self.name)])

    def __str__(self):
        return self.name
    
    def __eq__(self, other):
        return self.name == (other.name if hasattr(other, "name") else other)

class Nation(Object):
    def __init__(self, world, name : str):
        super().__init__(world, name, "nation")
    
    @property 
    def towns(self) -> list[Town]:
        return [t for t in self.world.towns if t.nation == self]

    @property 
    def capital(self) -> Town:
        for town in self.towns:
            if town.icon == "king":
                return town 

    def to_record_history(self):
        return [self.name, datetime.date.today(), len(self.towns), self.total_value, self.total_residents, str(self.capital), str(self.capital.mayor), self.total_area]

class Culture(Object):
    def __init__(self, world, name : str):
        super().__init__(world, name, "culture")
    
    @property 
    def towns(self) -> Town:
        return [t for t in self.world.towns if t.culture == self]

class Religion(Object):
    def __init__(self, world, name : str):
        super().__init__(world, name, "religion")
    
    @property 
    def towns(self) -> Town:
        return [t for t in self.world.towns if t.religion == self]


class Town():
    def __init__(self, world : client_pre.object.World):
        self.__world = world
        self.__locs = {}
        self.__built = False
        self.__desc = None

        self.spawn : Point = None
        self.name : str = None 
        self.icon : str = None

        self.flag_url : str = None 
        self.nation : Nation = None
        self.religion : Religion = None 
        self.culture : Culture = None 
        self.__mayor : str = None 
        self.resident_count : int = None 
        self.founded_date : datetime.date = None 
        self.resident_tax : float = None 
        self.bank : float = None 
        self.public : bool = None 
        self.peaceful : bool = False # Currently not on map. Defaults to false

        self.border_color : str = None 
        self.fill_color : str = None

    def is_coordinate_in_town(self, point : Point) -> bool:
        return self.locations.contains(Point(point.x, point.z))

    @property 
    def raw_locs(self):
        return self.__locs

    @property 
    def name_formatted(self):
        return self.name.replace("_", " ").title()

    @property 
    def _mayor_raw(self):
        return self.__mayor 

    @property 
    def mayor(self) -> typing.Union[Player, str]:
        return self.__world.get_player(self.__mayor) or self.__mayor

    @property 
    def area(self) -> int:
        return round((self.locations.area)/256)
    
    @property 
    async def likely_residents(self) -> list[Player]:
        pls = []
        for player in self.__world.players:
            if await player.likely_residency == self:
                pls.append(player)
        return pls

    @property 
    async def activity(self) -> Activity:
        return Activity.from_record(await self.__world.client.towns_table.get_record([db.CreationCondition("name", self.name)], ["duration", "last"]))
    
    @property 
    def locations(self):
        return MultiPolygon([Polygon(p) for p in list(self.__locs.values())])
    
    @property 
    async def visited_players(self) -> list[Activity]:
        rs = await self.__world.client.visited_towns_table.get_records(
            [db.CreationCondition("town", self.name)], 
            ["player", "duration", "last"], group=["player"], order=db.CreationOrder("duration", db.types.OrderDescending)
        )
        return [Activity(r.attribute("duration"), r.attribute("last"), player=self.__world.get_player(r.attribute("player")) or r.attribute("player")) for r in rs]

    @property 
    async def exists_in_db(self):
        return await self.__world.client.towns_table.record_exists([db.CreationCondition("name", self.name)])

    def to_record(self) -> list:

        return [
            self.name, 
            self.flag_url, 
            str(self.nation), 
            str(self.religion), 
            str(self.culture), 
            str(self.mayor), 
            self.resident_count, 
            self.founded_date, 
            self.resident_tax, 
            self.bank, 
            int(self.public), 
            int(self.peaceful), 
            self.area,
            datetime.datetime.now(),
            0,
            datetime.datetime.now()
        ]
    
    def to_record_update_last(self) -> list:
        r = self.to_record()
        r[-2] = db.CreationField.add("duration", 0)
        r.pop()
        return r
    
    def to_record_update_player(self, players : list[Player]) -> list:
        r = self.to_record()
        r[-2] = db.CreationField.add("duration", self.__world.client.refresh_period*len(players))
        return r
    
    def to_record_history(self) -> list:
        return [
            self.name, 
            datetime.date.today(), 
            self.nation.name if self.nation else None, 
            self.religion.name if self.religion else None, 
            self.culture.name if self.culture else None, 
            self.__mayor,
            self.resident_count,
            self.resident_tax,
            self.bank,
            self.public,
            self.peaceful,
            self.area,
            db.CreationField.external_query(self.__world.client.towns_table, "duration", db.CreationCondition("name", self.name))
        ]
    
    async def parse_desc(self, desc : str):
        if not desc:
            return
        
        if desc != self.__desc and "Siege" not in desc:
            r = re.match(setup.template, desc)
            if not r:
                await (await self.__world.client.bot.fetch_channel(setup.alert_channel)).send(f"Could not extract from desc.\n\n```{desc}```")
                raise
            groups = r.groups()
            self.flag_url = groups[0]
            self.nation = Nation(self.__world, groups[2]) if groups[2].strip() != "" else None
            self.religion = Religion(self.__world, groups[3].replace("Town Religion - ", "")) if "Select your" not in groups[3] else None
            self.culture = Culture(self.__world, groups[4].replace("Culture - ", "")) if groups[4] != "Culture - " else None
            self.__mayor = groups[5]
            self.resident_count  = int(groups[7])

            try:
                self.founded_date = datetime.datetime.strptime(groups[8], "%b %d %Y").date()
            except ValueError:
                self.founded_date = datetime.date.today()

            self.resident_tax = float(groups[9][:-1])
            self.bank = float(groups[10].replace(",", ""))
            self.public = True if "true" in groups[11] else False
            #self.peaceful = True if "true" in groups[12] else False

        self.__desc = desc

    async def add_update(self, data : dict):
        

        if not self.__built:
            self.name = data["label"]
        
            self.__built = True

            await self.parse_desc(data["desc"])
        
        if "__home" in data["id"]:
            self.spawn = Point(data["x"], data["y"], data["z"])
            self.icon = data["icon"]
            
        else:
            self.border_color = data["color"]
            self.fill_color = data["fillcolor"]

            locs = []
            
            for x, z in zip(data["x"], data["z"]):
                locs.append((x, z))
            
            if self.__locs.get(data["id"]) != locs:
                self.__locs[data["id"]] = locs
    
    def __eq__(self, other):
        return self.name == (other.name if hasattr(other, "name") else other)

    def __str__(self):
        return str(self.name_formatted)

class Player():
    def __init__(self, world : client_pre.object.World):
        self.__world = world 

        self.name : str = None
        self.location = None
        self.armor : int = None
        self.health : int = None
        self.online = False

        self._town_cache = None

    async def activity_in(self, town : Town) -> Activity:
        return Activity.from_record(
            await self.__world.client.visited_towns_table.get_record([db.CreationCondition("player", self.name), db.CreationCondition("town", town.name)], ["duration", "last"])
        )
    
    @property 
    def discord(self):
        for guild in self.__world.client.bot.guilds:
            for member in guild.members:
                if self.name.lower().replace("_", " ") in member.name.lower().replace("_", " ") + member.global_name.lower().replace("_", " ") + member.display_name.lower().replace("_", " "):
                    return member 
         

    @property 
    def name_formatted(self):
        """Helper"""
        return self.name

    @property 
    def town(self) -> Town:
        nearby_town = None

        for town in self.__world.towns:
            if town.is_coordinate_in_town(self.location):
                nearby_town = town

        self._town_cache = nearby_town
        return nearby_town

    @property 
    async def activity(self) -> Activity:
        return Activity.from_record(await self.__world.client.players_table.get_record([db.CreationCondition("name", self.name)], ["duration", "last"]))

    @property 
    def avatar_url(self) -> str:
        return f"{self.__world.client.url}/tiles/faces/32x32/{self.name}.png"
    
    @property 
    async def visited_towns(self) -> list[Activity]:
        rs = await self.__world.client.visited_towns_table.get_records(
            [db.CreationCondition("player", self.name)], 
            ["town", "duration", "last"], group=["town"], order=db.CreationOrder("duration", db.types.OrderDescending)
        )
        return [Activity(r.attribute("duration"), r.attribute("last"), self.__world.get_town(r.attribute("town")) or r.attribute("town")) for r in rs]
        
    
    @property 
    async def total_visited_towns(self) -> list[Town]:
        return await self.__world.client.visited_towns_table.count_rows([db.CreationCondition("player", self.name)])
    
    @property 
    async def likely_residency(self) -> Town:
        visited_towns = await self.visited_towns

        for town in self.__world.towns:
            if town._mayor_raw == self.name:
                return town 
        
        if len(visited_towns) > 0:
            for activity in visited_towns:
                if type(activity.town) != str and activity.town :
                    return activity.town
    
    @property 
    async def exists_in_db(self):
        return await self.__world.client.players_table.record_exists([db.CreationCondition("name", self.name)])
    
    
    async def get_activity_today(self, activity : Activity = None):
        twodays = (await self.__world.client.player_history_table.get_records([db.CreationCondition("player", self.name)], attributes=["duration"], order=db.CreationOrder("duration", db.types.OrderDescending), limit=2))
        
        a = activity
        if not activity:
            a = await self.activity
        if len(twodays) == 1:
            return a
        yesterday = twodays[1]
        return Activity(a.total - yesterday.attribute("duration"), last=a.last)
        


    def update(self, data : dict):

        self.name : str = data["account"]
        self.location = Point((data["x"], data["y"], data["z"]))
        self.armor : int = data["armor"]
        self.health : int = data["health"]
        self.online = True
    
    def to_record(self) -> list:
        town = self.town
        return [self.name, ",".join([str(self.location.x), str(self.location.y), str(self.location.z)]), town.name if town else None, self.armor, self.health, self.__world.client.refresh_period, datetime.datetime.now()]

    def to_record_update(self) -> list:
        r = self.to_record()
        r[-2] = db.CreationField.add("duration", self.__world.client.refresh_period)
        return r
    
    def to_record_history(self) -> list:
        return [self.name, datetime.date.today(), db.CreationField.external_query(self.__world.client.players_table, "duration", db.CreationCondition("name", self.name))]

    def __eq__(self, other):
        return self.name == (other.name if hasattr(other, "name") else other)

    def __str__(self):
        return self.name

class World():
    def __init__(self, client : client_pre.Client):

        self.client = client

        self.__towns : dict[str, Town] = {}
        self.__players : dict[str, Player] = {}
        self._objects : dict[str, list[Object]] = {
            "nations":[],
            "cultures":[],
            "religions":[]
        }

        self.player_count : int = None 
        self.is_stormy : bool = None
        

    def get_object(self, array : list, name : str, search=False, multiple=False, max=25):
        multi = []

        for i, o in enumerate(array):
            if (not search and str(o) == name) or (search and name.replace(" ", "_").lower() in str(o).replace(" ", "_").lower() ):
                if not multiple:
                    return o 
                
                multi.append(o)
                if i >= max-1:
                    break
        if multiple:
            return multi

    def get_town(self, town_name : str, search=False, multiple=False, max=25) -> Town:
        if not search:
            return self.__towns.get(town_name)
        
        multi = []
    
        for i, town in enumerate(self.__towns):
            if town_name.replace(" ", "_").lower() in str(town).replace(" ", "_").lower():
                if not multiple:
                    return self.__towns[town]
                multi.append(self.__towns[town])
                if i >= max-1:
                    break
        
        if multiple:
            return multi

    def get_player(self, player_name : str, search=True, multiple=False, max=25) -> Player:
        if not search:
            return self.__players.get(player_name)
        
        multi = []

        for i, player in enumerate(self.__players):
            if player_name.replace(" ", "_").lower() in str(player).replace(" ", "_").lower():
                if not multiple:
                    return self.__players[player]
                multi.append(self.__players[player])
                if i >= max-1:
                    break

        if multiple:
            return multi

    def get_nation(self, nation_name : str, search=False, multiple=False, max=25) -> Nation:
        return self.get_object(self.nations, nation_name, search, multiple, max)
    
    def get_culture(self, culture_name : str, search=False, multiple=False, max=25) -> Nation:
        return self.get_object(self.cultures, culture_name, search, multiple, max)
    
    def get_religion(self, religion_name : str, search=False, multiple=False, max=25) -> Nation:
        return self.get_object(self.religions, religion_name, search, multiple, max)
    
    def search(self, get_func : callable, query : str, max : int = 25) -> list:
        return get_func(query, True, True, max)
    
    def search_player(self, player_name : str, max : int = 25) -> list[Player]: return self.search(self.get_player, player_name, max)
    def search_town(self, town_name : str, max : int = 25) -> list[Town]: return self.search(self.get_town, town_name, max)
    def search_nation(self, nation_name : str, max : int = 25) -> list[Nation]: return self.search(self.get_nation, nation_name, max)

    def to_record_history(self) -> list:
        return [datetime.date.today(), len(self.towns), self.total_residents, len(self.nations), self.total_value, self.total_area, len(self.players)]

    @property 
    def towns(self) -> list[Town]:
        return list(self.__towns.values())
    @property 
    def players(self) -> list[Player]:
        return list(self.__players.values() )
    @property 
    def nations(self) -> list[Nation]:
        return self._objects["nations"]
    @property 
    def cultures(self) -> list[Culture]:
        return self._objects["cultures"]
    @property 
    def religions(self) -> list[Religion]:
        return self._objects["religions"]
    
    @property 
    def online_players(self) -> list[Player]:
        ps = []
        for p in self.players:
            if p.online:
                ps.append(p)
        return ps
    
    def __total(self, arr : list, attr : str):
        t = 0
        for o in arr:
            t += getattr(o, attr)
        return t

    @property 
    def total_residents(self) -> int: return self.__total(self.towns, "resident_count")
    @property 
    def total_area(self) -> int: return self.__total(self.towns, "area")
    @property 
    def total_value(self) -> float: return self.__total(self.towns, "bank")

    @property 
    async def total_tracked(self):
        return Activity((await self.client.global_table.get_record([db.CreationCondition("name", "total_tracked")], ["value"])).attribute("value"))

    def _remove_player(self, player_name : str):
        del self.__players[player_name]
    def _remove_town(self, town_name : str):
        del self.__towns[town_name]
    def _remove_nation(self, nation_name : str):
        self._objects["nations"].remove(nation_name)

    async def refresh(self, r : StreamReader):

        objects = ijson.kvitems_async(r, "", use_float=True)
        towns_with_players : typing.Dict[str, typing.List[Player]] = None
        
        async for o in objects:
            if o[0] == "currentcount":
                self.player_count = o[1] or 0
            if o[0] == "hasStorm":
                self.is_stormy = o[1] or False
            if o[0] == "players":
                towns_with_players = await self.__update_player_list(o[1])
            if o[0] == "updates":
                await self.__update_town_list(o[1], towns_with_players)
        
        await self.__update_global()
        await self.__update_nations()
        await self.__update_objects()

    async def __update_objects(self):
        new_records = []

        for object_type, objects in self._objects.items():
            for object in objects:
                cond = [db.CreationCondition("type", object.object_type), db.CreationCondition("name", object.name)]
                exists = await self.client.objects_table.record_exists(cond)

                if not exists:
                    new_records.append(object.to_record())
                else:
                    await self.client.objects_table.update_record(cond, *object.to_record())
        
        if len(new_records) > 0:
            await self.client.objects_table.add_record(new_records)

    async def __update_nations(self):
        add_nation_history = []
        

        for nation in self.nations:
            cond2 = [db.CreationCondition("nation", nation.name), db.CreationCondition("date", datetime.date.today())]
            exists = await self.client.nation_history_table.record_exists(cond2)
            try:
                if not exists:
                    add_nation_history.append(nation.to_record_history())
                else:
                    await self.client.nation_history_table.update_record(cond2, *nation.to_record_history())
            except Exception as e:
                # Nation needs to be removed! Should be removed on next pass from Client.cull_db()
                await (await self.client.bot.fetch_channel(setup.alert_channel)).send(f"{nation.name} Nation Tracking Update Error! `{e}`")

        if len(add_nation_history) > 0:
            await self.client.nation_history_table.add_record(add_nation_history)

    async def __update_global(self):

        if not await self.client.global_table.record_exists(db.CreationCondition("name", "total_tracked")):
            await self.client.global_table.add_record(["total_tracked", 0])
        await self.client.global_table.update_record(db.CreationCondition("name", "total_tracked"), db.CreationField.add("value", self.client.refresh_period))

        cond = [db.CreationCondition("date", datetime.date.today())]
        exists = await self.client.global_history_table.record_exists(cond)
        if not exists:
            await self.client.global_history_table.add_record(self.to_record_history())
        else:
            await self.client.global_history_table.update_record(cond, *self.to_record_history())

    async def __update_town_list(self, updates : list[dict], towns_with_players : dict[str, list[Player]]):
        for update in updates:
            if update["type"] == "component" and update["set"] != "offline_players" and update.get("icon") != "fire":
                if update["label"] in setup.DONT_TRACK_TOWNS:
                    continue 

                if update["label"] not in self.__towns:
                    t = Town(self)
                    self.__towns[update["label"]] = t
                    
                    await t.add_update(update)
                else:
                    t = self.get_town(update["label"])
                    await t.add_update(update)
                await asyncio.sleep(0.0001) # Allow "parallel" processing

        new_records = []
        add_town_history = []
        for town in self.towns:
            cond = db.CreationCondition(self.client.towns_table.primary_key, town.name)
            exists = await self.client.towns_table.record_exists(cond)

            if not exists:
                new_records.append(town.to_record())
            else:
                if town.name in towns_with_players:
                    up = town.to_record_update_player(towns_with_players[town.name])
                else:
                    up = town.to_record_update_last()
                await self.client.towns_table.update_record([cond], *up)
            
            # Add town history
            cond2 = [db.CreationCondition("town", town.name), db.CreationCondition("date", datetime.date.today())]
            exists = await self.client.town_history_table.record_exists(cond2)
            if not exists:
                add_town_history.append(town.to_record_history())
            else:
                await self.client.town_history_table.update_record(cond2, *town.to_record_history())

        if len(new_records) > 0:
            await self.client.towns_table.add_record(new_records)
        if len(add_town_history) > 0:
                await self.client.town_history_table.add_record(add_town_history)
        
        
    
    async def initialise_player_list(self):
        players = await self.client.players_table.get_records()

        for player in players:
            p = Player(self)

            p.name : str = player.attribute("name")
            p.location = Point(float(c) for c in player.attribute("location").split(","))
            p.armor : int = player.attribute("armor")
            p.health : int = player.attribute("health")

            self.__players[p.name] = p

    async def __update_player_list(self, players : list[dict]):
        add_players = []
        add_visited_towns = []
        add_player_history = []
        online_players : list[str] = []

        towns_with_players : dict[str, list[Player]] = {}

        for player_data in players:
            await asyncio.sleep(0.0001) # Allow "parallel" processing

            online_players.append(player_data["account"])

            p = self.get_player(player_data["account"])

            if not p:
                p = Player(self)
                self.__players[p.name] = p
            p.update(player_data)

            cond = db.CreationCondition(self.client.players_table.primary_key, p.name)
            exists = await self.client.players_table.record_exists(cond)

            if not exists:
                add_players.append(p.to_record())
            else:
                await self.client.players_table.update_record([cond], *p.to_record_update())
            
            # Add player history
            cond2 = [db.CreationCondition("player", p.name), db.CreationCondition("date", datetime.date.today())]
            exists = await self.client.player_history_table.record_exists(cond2)
            if not exists:
                add_player_history.append(p.to_record_history())
            else:
                await self.client.player_history_table.update_record(cond2, *p.to_record_history())

            town = p._town_cache
            if town:
                if town.name not in towns_with_players:
                    towns_with_players[town.name] = []
                towns_with_players[town.name].append(p)

                conds = [db.CreationCondition(self.client.visited_towns_table.attribute("player"), p.name), db.CreationCondition(self.client.visited_towns_table.attribute("town"), town.name)]
                exists = await self.client.visited_towns_table.record_exists(conds)

                if not exists:
                    add_visited_towns.append([p.name, town.name, 20, datetime.datetime.now()])
                else:
                    await self.client.visited_towns_table.update_record(conds, *[p.name, town.name, db.CreationField.add("duration", self.client.refresh_period), datetime.datetime.now()])

        
        if len(add_players) > 0:
            await self.client.players_table.add_record(add_players)
        if len(add_visited_towns) > 0:
            await self.client.visited_towns_table.add_record(add_visited_towns)

        if len(add_player_history) > 0:
            await self.client.player_history_table.add_record(add_player_history)
        
        for player in self.players:
            if player.online and player.name not in online_players:
                player.online = False
        
        return towns_with_players
    
    


        
