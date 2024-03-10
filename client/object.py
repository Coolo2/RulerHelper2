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

from aiohttp import StreamReader
import ijson.backends.yajl2_c as ijson

import discord
from client import funcs
import traceback

import random
import os

class Area():
    def __init__(self, town : client_pre.object.Town, verticies : list, name : str = None):
        self.__town = town 
        self.__verticies = verticies
        self.__name = name

        self.__polygon_cache = None
    
    @property 
    def name(self):
        return self.__name
    
    @property 
    def town(self):
        return self.__town

    @property 
    def raw_verticies(self) -> list[float]:
        return self.__verticies
    
    def set_verticies(self, verticies : list[tuple[float]]):
        self.__verticies = verticies

    @property 
    def polygon(self):
        if not self.__polygon_cache:
            self.__polygon_cache = Polygon(self.__verticies)
        return self.__polygon_cache
    
    @property 
    def outpost_spawn(self) -> Point:

        for outpost_spawn in self.__town.outpost_spawns:
            if self.polygon.contains(Point(outpost_spawn.x, outpost_spawn.z)):
                return self.polygon
        
        return None 

    @property 
    def is_outpost(self) -> bool:
        if not self.outpost_spawn or len(self.town.areas) == 1:
            return False 
        return True

    @property 
    def is_mainland(self) -> bool:
        return not self.is_outpost

    def is_point_in_area(self, point : Point) -> bool:
        try:
            return self.polygon.contains(Point(point.x, point.z))
        except:
            return False
    
    @property 
    def fill_color(self):
        return self.__town.fill_color
    
    @property 
    def border_color(self):
        return self.__town.border_color
     
    def __eq__(self, other):
        if type(other) == Area and other.name == self.__name:
            return True 
        return False


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
        return funcs.generate_time(self.total)

    def __add__(self, other):
        return Activity(self.total + (other.total if hasattr(other, "total") else other), max(self.last, (other.last if hasattr(other, "last") else datetime.datetime(2000, 1, 1))), self.town)

    __radd__ = __add__

    def __str__(self):
        return f"{funcs.generate_time(self.total)}" + (f" <t:{round(self.last.timestamp())}:R>" if self.total > 0 else '')
    
    def __int__(self):
        return self.total 

    def __float__(self):
        return float(self.total)
    
    def __round__(self, *args):
        return self

class Object():
    def __init__(self, world : client_pre.object.World, name : str, object_type : str):
        self.name = name 
        self.world = world
        self.object_type = object_type
        self.last_seen = datetime.datetime.now() 
        self.search_boost = 0

        if self.name not in world._objects[self.object_type + "s"]:
            world._objects[self.object_type + "s"].append(self)
        else:
            for o in world._objects[self.object_type + "s"]:
                if o == self.name:
                    o.last_seen = datetime.datetime.now()
    
    @property 
    def total_towns(self) -> int:
        return len(self.towns)

    @property 
    def name_formatted(self):
        return self.name.replace("_", " ")
    
    def __total(self, arr : list, attr : str):
        t = 0
        for o in arr:
            t += getattr(o, attr) or 0
        return t

    def to_record(self):
        res_count = self.total_residents
        self.search_boost = res_count
        return [
            self.object_type, 
            self.name, 
            len(self.towns), 
            self.total_value, 
            res_count, 
            self.total_area,
            db.CreationField.external_query(
                self.world.client.chat_mentions_table, "mentions", [db.CreationCondition("object_type", self.object_type), db.CreationCondition("object_name", self.name)], query_attribute="amount"
            ), 
            db.CreationField.external_query(
                    self.world.client.activity_table, 
                    "duration", 
                    [db.CreationCondition("object_type", self.object_type), db.CreationCondition("object_name", self.name)]
            ), 
            datetime.datetime.now()
        ]
    
    @property 
    async def total_mentions(self) -> tuple[int, datetime.datetime]: 
        r = await self.world.client.chat_mentions_table.get_record([db.CreationCondition("object_type", self.object_type), db.CreationCondition("object_name", self.name)], ["amount", "last"])

        if r:
            return r.attribute("amount"), r.attribute("last")
        return 0, None
    @property
    async def mention_count(self): return (await self.total_mentions)[0]

    @property 
    def total_residents(self) -> int: return self.__total(self.towns, "resident_count")
    @property 
    def total_area(self) -> int: return self.__total(self.towns, "area")
    @property 
    def total_value(self) -> float: return self.__total(self.towns, "bank")
    @property 
    def total_detached_area(self) -> int: return self.__total(self.towns, "detached_area")
    @property
    def vertex_count(self) -> int:
        return self.__total(self.towns, "vertex_count")
    
    @property 
    def outpost_spawns(self) -> list[tuple[float]]:
        t = []
        for town in self.towns:
            t += town.outpost_spawns 
        return t

    async def set_flag(self, flag_name : str, flag_value):
        cond = [db.CreationCondition("object_type", self.object_type), db.CreationCondition("object_name", self.name)]
        val = [self.object_type, self.name, flag_name, flag_value]

        if setup.flags[self.object_type][flag_name].get("unique"):
            await self.world.client.flags_table.delete_records([db.CreationCondition("object_type", self.object_type), db.CreationCondition("name", flag_name), db.CreationCondition("value", flag_value)])

        a = await self.world.client.flags_table.add_record_if_not_exists(val, cond)
        if not a:
            await self.world.client.flags_table.update_record(cond, *val)
    
    @property
    async def flags(self) -> dict:
        rs = await self.world.client.flags_table.get_records([db.CreationCondition("object_type", self.object_type), db.CreationCondition("object_name", self.name)], ["name", "value"])
        d = {}
        for r in rs:
            if r.attribute("value"):
                d[r.attribute("name")] = r.attribute("value")
        return d
    
    @property 
    def areas(self):
        l = []
        for town in self.towns:
            l += town.areas
        return l
    

    @property 
    async def exists_in_db(self):
        return await self.world.client.objects_table.record_exists([db.CreationCondition("type", self.object_type), db.CreationCondition("name", self.name)])
    
    def to_record_history(self) -> list:
        return [
            datetime.date.today(), 
            self.object_type,
            self.name, 
            len(self.towns),
            self.total_value,
            self.total_residents,
            self.total_area,
            db.CreationField.external_query(
                self.world.client.chat_mentions_table, "mentions", [db.CreationCondition("object_type", self.object_type), db.CreationCondition("object_name", self.name)], query_attribute="amount"
            )
        ]

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
            if town.icon == "ruler":
                return town 
    
    @property 
    def leader(self) -> Player:
        return self.capital.mayor

    @property 
    def borders(self) -> tuple[list[client_pre.object.Nation]|list[client_pre.object.Town]]:
        borders_towns = []
        borders_nations = []

        multi = MultiPolygon()
        for nation_town in self.towns:
            multi = multi.union(nation_town.locations)
        
        for town in self.world.towns:
            nation = town.nation 

            if nation and nation != self and town not in borders_towns:
                if multi.intersects(town.locations):
                    borders_towns.append(town)
        
        for town in borders_towns:
            if town.nation not in borders_nations:
                borders_nations.append(town.nation)
        
        return [borders_nations, borders_towns]
    
    @property 
    async def top_rankings(self) -> dict[str, list[int, int]]:
        rankings = {}
        for command in setup.top_commands["nation"]:
            value = (await self.world.client.objects_table.get_record(conditions=[db.CreationCondition("type", "nation"), db.CreationCondition("name", self.name)], attributes=[command["attribute"]])).attribute(command["attribute"])
            if value:
                ranking = await self.world.client.objects_table.count_rows(conditions=[db.CreationCondition("type", "nation"), db.CreationCondition(command["attribute"], value, ">")])
                if command.get("reverse_notable"): ranking = len(self.world.nations)-ranking-1
                notable = True if ranking <= len(self.world.nations)/2 else False
                rankings[command.get("name") or command.get("attribute")] = [value, ranking+1, notable]
        
        return dict(sorted(rankings.items(), key=lambda x: x[1][1]))
    
    @property 
    def religion_make_up(self) -> typing.Dict[str, int]:
        d = {}
        for town in self.towns:
            if town.religion and "Produces" not in town.religion.name:
                if town.religion.name not in d:
                    d[town.religion.name] = 0
                d[town.religion.name] += town.resident_count
        d = dict(sorted(d.items(), key=lambda x: x[1], reverse=True))
        return d
    
    @property 
    def culture_make_up(self) -> typing.Dict[str, int]:
        d = {}
        for town in self.towns:
            if town.culture:
                if town.culture.name not in d:
                    d[town.culture.name] = 0
                d[town.culture.name] += town.resident_count
        d = dict(sorted(d.items(), key=lambda x: x[1], reverse=True))
        return d
    
    @property 
    def notable_statistics(self) -> list[str]:
        stats = []
        detached_area_perc = (self.total_detached_area / self.total_area) * 100
        if detached_area_perc > 0:
            stats.append(f"Detached territories make up **{detached_area_perc:,.2f}%** of {discord.utils.escape_markdown(self.name_formatted)}'s claims")
            stats.append(f"The average town balance in {discord.utils.escape_markdown(self.name_formatted)} is **${self.average_town_balance:,.2f}**")
        return stats
    
    @property
    def average_town_balance(self) -> float:
        return self.total_value/self.total_towns

    @property 
    async def activity(self) -> Activity:
        return Activity.from_record(await self.world.client.activity_table.get_record([db.CreationCondition("object_type", "nation"), db.CreationCondition("object_name", self.name)], ["duration", "last"]))

    @property 
    async def previous_names(self) -> list[str]:
        rs = await self.world.client.nation_history_table.get_records([db.CreationCondition("nation", self.name), db.CreationCondition("current_name", self.name, "!=")], ["current_name"], group=["current_name"], order=db.CreationOrder("date", db.types.OrderDescending))
        return [r.attribute("current_name") for r in rs]

    def to_record_history(self):
        cond_objects = [db.CreationCondition("type", "nation"), db.CreationCondition("name", self.name)]

        return [
            self.name, 
            datetime.date.today(), 
            db.CreationField.external_query(self.world.client.objects_table, "towns", cond_objects),
            db.CreationField.external_query(self.world.client.objects_table, "town_balance", cond_objects),
            db.CreationField.external_query(self.world.client.objects_table, "residents", cond_objects),
            str(self.capital), 
            str(self.capital.mayor), 
            db.CreationField.external_query(self.world.client.objects_table, "area", cond_objects),
            db.CreationField.external_query(
                    self.world.client.activity_table, 
                    "duration", 
                    [db.CreationCondition("object_type", "nation"), db.CreationCondition("object_name", self.name)]
            ),
            self.name,
            db.CreationField.external_query(
                self.world.client.chat_mentions_table, "mentions", [db.CreationCondition("object_type", self.object_type), db.CreationCondition("object_name", self.name)], query_attribute="amount"
            )
        ]
    
    def to_record_day_history(self):
        r = self.to_record_history()
        return [r[0], datetime.datetime.now(), r[2], r[3], r[4], r[7], r[8]]
    
    def to_record_activity(self) -> list:
        return ["nation", self.name, 0, datetime.datetime.now()]

    def to_record_activity_update(self, visited_towns : dict[str, list[Player]]) -> list:
        players_in = 0
        for town_name, players in visited_towns.items():
            if town_name in self.towns:
                players_in += len(players)
        
        r = self.to_record_activity()
        r[-2] = db.CreationField.add("duration", self.world.client.refresh_period*players_in)
        if players_in == 0:
            r.pop()
        return r

class Culture(Object):
    def __init__(self, world, name : str):
        super().__init__(world, name, "culture")
    
    @property 
    def towns(self) -> list[Town]:
        return [t for t in self.world.towns if t.culture == self]
    
    @property 
    def nation_make_up(self) -> typing.Dict[str, int]:
        d = {}
        for town in self.towns:
            if town.nation:
                if town.nation.name_formatted not in d:
                    d[town.nation.name_formatted] = 0
                d[town.nation.name_formatted] += town.resident_count
        d = dict(sorted(d.items(), key=lambda x: x[1], reverse=True))
        return d

class Religion(Object):
    def __init__(self, world, name : str):
        super().__init__(world, name, "religion")
    
    @property 
    def towns(self) -> list[Town]:
        return [t for t in self.world.towns if t.religion == self]
    
    @property 
    def nation_make_up(self) -> typing.Dict[str, int]:
        d = {}
        for town in self.towns:
            if town.nation:
                if town.nation.name_formatted not in d:
                    d[town.nation.name_formatted] = 0
                d[town.nation.name_formatted] += town.resident_count
        d = dict(sorted(d.items(), key=lambda x: x[1], reverse=True))
        return d

class Tax():
    def __init__(self, amount : float, tax_type : str):
        self.amount = amount 
        self.tax_type = tax_type 
    
    def __float__(self):
        return float(self.amount)

    def __int__(self):
        return int(self.amount)
    
    def __add__(self, other):
        return Tax(self.amount + (other.amount if hasattr(other, "amount") else other), self.tax_type)
    
    def __round__(self, *args):
        return self

    __radd__ = __add__

    def __str__(self):
        if self.tax_type == "%":
            return f"{self.amount:,.2f}%"
        return f"${self.amount:,.2f}"

    def for_record(self):
        return self.amount if self.tax_type == "%" else 0

class Town():
    def __init__(self, world : client_pre.object.World):
        self.__world = world
        self.__built = False
        self.__desc = None

        self.outpost_spawns : list[Point] = []
        self.__areas : list[Area] = []

        self.search_boost = 0

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
        self.resident_tax : Tax = None 
        self.bank : float = None 
        self.public : bool = None 
        self.peaceful : bool = False # Currently not on map. Defaults to false

        self.border_color : str = None 
        self.fill_color : str = None

        self.last_updated : datetime.datetime = None

    def is_point_in_town(self, point : Point) -> bool:
        try:
            return self.locations.contains(Point(point.x, point.z))
        except:
            return False
    
    @property
    def vertex_count(self) -> int:
        total = 0
        for area in self.__areas:
            total += len(area.raw_verticies)
        return total

    @property 
    def name_formatted(self):
        return self.name.replace("_", " ")

    @property 
    def _mayor_raw(self):
        return self.__mayor 

    @property 
    def mayor(self) -> typing.Union[Player, str]:
        return self.__world.get_player(self.__mayor, False) or self.__mayor

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
        a = await self.__world.client.activity_table.get_record(conditions=[db.CreationCondition("object_type", "town"), db.CreationCondition("object_name", self.name)])
        
        return Activity.from_record(a)
    
    @property 
    def areas(self):
        return self.__areas
    
    @property 
    def locations(self) -> MultiPolygon:
        return MultiPolygon([a.polygon for a in self.__areas])
    
    @property 
    def continents(self) -> list[str]:
        cs = []

        for polygon in self.locations.geoms:
            if polygon.contains(Point(self.spawn.x, self.spawn.z)):

                for continent_name, continent_polygon in continents.items():
                    
                    if continent_polygon.intersects(polygon):
                        cs.append(continent_name.replace("_", " ").title())
        return cs
    
    @property 
    def geography_description(self) -> str:
        continents = self.continents
        return f"{self.name_formatted} is a town in {'/'.join(continents) if len(continents) else 'no continent'}."

    @property 
    async def visited_players(self) -> list[Activity]:
        rs = await self.__world.client.visited_towns_table.get_records(
            [db.CreationCondition("town", self.name)], 
            ["player", "duration", "last"], group=["player"], order=db.CreationOrder("duration", db.types.OrderDescending)
        )
        return [Activity(r.attribute("duration"), r.attribute("last"), player=self.__world.get_player(r.attribute("player"), False) or r.attribute("player")) for r in rs]

    @property 
    async def exists_in_db(self):
        return await self.__world.client.towns_table.record_exists([db.CreationCondition("name", self.name)])
    
    @property 
    def borders(self) -> list[client_pre.object.Town]:
        borders = []

        for town in self.__world.towns:
            if town != self and town.name not in setup.DEFAULT_TOWNS and True not in [l in town.name for l in setup.DEFAULT_TOWNS_SUBSTRING]:
                if self.locations.intersects(town.locations):
                    borders.append(town)
        
        return borders
    
    async def set_flag(self, flag_name : str, flag_value):
        cond = [db.CreationCondition("object_type", "town"), db.CreationCondition("object_name", self.name)]
        val = ["town", self.name, flag_name, flag_value]

        if setup.flags["town"][flag_name].get("unique"):
            await self.__world.client.flags_table.delete_records([db.CreationCondition("object_type", "town"), db.CreationCondition("name", flag_name), db.CreationCondition("value", flag_value)])

        a = await self.__world.client.flags_table.add_record_if_not_exists(val, cond)
        if not a:
            await self.__world.client.flags_table.update_record(cond, *val)
    
    @property
    async def flags(self) -> dict:
        rs = await self.__world.client.flags_table.get_records([db.CreationCondition("object_type", "town"), db.CreationCondition("object_name", self.name)], ["name", "value"])
        d = {}
        for r in rs:
            if r.attribute("value"):
                d[r.attribute("name")] = r.attribute("value")
        return d
    
    @property 
    async def top_rankings(self) -> dict[str, list[int, int]]:
        rankings = {}
        for command in setup.top_commands["town"]:
            value = (await self.__world.client.towns_table.get_record(conditions=[db.CreationCondition("name", self.name)], attributes=[command["attribute"]])).attribute(command["attribute"])
            if value:
                ranking = await self.__world.client.towns_table.count_rows(conditions=[db.CreationCondition(command["attribute"], value, ">")])
                if command.get("reverse_notable"): ranking = len(self.__world.towns)-ranking-1
                notable = True if ranking <= len(self.__world.towns)/5 else False
                rankings[command.get("name") or command.get("attribute")] = [value, ranking+1, notable]
        
        return dict(sorted(rankings.items(), key=lambda x: x[1][1]))

    @property 
    def detached_area(self) -> int:
        t = 0 
        for area in self.__areas:
            if area.is_outpost:
                t += area.polygon.area
        return t / 256
        

    @property 
    def notable_statistics(self) -> list[str]:
        stats = []
        detached_area_perc = (self.detached_area / self.area) * 100
        if detached_area_perc > 0:
            stats.append(f"Detached territories make up **{detached_area_perc:,.2f}%** of {discord.utils.escape_markdown(self.name_formatted)}'s claims")
        return stats

    @property 
    async def total_visited_players(self) -> int:
        return await self.__world.client.visited_towns_table.count_rows([db.CreationCondition("town", self.name)])
    
    @property 
    async def previous_names(self) -> list[str]:
        rs = await self.__world.client.town_history_table.get_records([db.CreationCondition("town", self.name), db.CreationCondition("current_name", self.name, "!=")], ["current_name"], group=["current_name"], order=db.CreationOrder("date", db.types.OrderDescending))
        return [r.attribute("current_name") for r in rs]
    
    @property 
    async def total_mentions(self) -> tuple[int, datetime.datetime]: 
        r = await self.__world.client.chat_mentions_table.get_record([db.CreationCondition("object_type", "town"), db.CreationCondition("object_name", self.name)], ["amount", "last"])

        if r:
            return r.attribute("amount"), r.attribute("last")
        return 0, None
    @property
    async def mention_count(self): return (await self.total_mentions)[0]

    @property 
    def outposts(self):
        return [a for a in self.areas if a.is_outpost]

    def to_record(self) -> list:

        area = self.search_boost = self.area

        return [
            self.name, 
            str(self.nation), 
            str(self.religion), 
            str(self.culture), 
            str(self.mayor), 
            self.resident_count, 
            self.founded_date, 
            self.resident_tax.for_record(), 
            self.bank, 
            int(self.public), 
            int(self.peaceful), 
            area,
            0,
            len(self.outposts),
            0,
            db.CreationField.external_query(
                    self.__world.client.activity_table, 
                    "duration", 
                    [db.CreationCondition("object_type", "town"), db.CreationCondition("object_name", self.name)]
            ),
            self.last_updated
        ]
    
    def to_record_update(self) -> list:
        r = self.to_record()
        r[-3] = db.CreationField.external_query(
                    self.__world.client.visited_towns_table, 
                    "visited_players", 
                    [db.CreationCondition("town", self.name)],
                    query_attribute="COUNT(*)"
        )
        r[-5] = db.CreationField.external_query(
            self.__world.client.chat_mentions_table, "mentions", [db.CreationCondition("object_type", "town"), db.CreationCondition("object_name", self.name)], query_attribute="amount"
        )
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
            self.resident_tax.for_record(),
            self.bank,
            self.public,
            self.peaceful,
            self.area,
            db.CreationField.external_query(
                    self.__world.client.activity_table, 
                    "duration", 
                    [db.CreationCondition("object_type", "town"), db.CreationCondition("object_name", self.name)]
            ),
            db.CreationField.external_query(self.__world.client.visited_towns_table, "visited_players", [db.CreationCondition("town", self.name)], query_attribute="COUNT(*)"),
            self.name,
            db.CreationField.external_query(
                self.__world.client.chat_mentions_table, "mentions", [db.CreationCondition("object_type", "town"), db.CreationCondition("object_name", self.name)], query_attribute="amount"
            )
        ]
    
    def to_record_day_history(self) -> list:
        r = self.to_record_history()
        return [
            r[0],
            datetime.datetime.now(),
            r[6],
            r[7],
            r[8],
            r[11],
            r[12],
            r[13]
        ]
    
    def to_record_activity(self) -> list:
        return ["town", self.name, 0, datetime.datetime.now()]

    def to_record_activity_update(self, players : list[Player]) -> list:
        r = self.to_record_activity()
        r[-2] = db.CreationField.add("duration", self.__world.client.refresh_period*len(players))
        if len(players) == 0:
            r.pop()
        return r
    
    async def parse_desc(self, desc : str):
        if not desc:
            return
        
        if "Siege" not in desc:
            r = re.match(setup.template, desc.replace("\n", "").replace(" ", ""))
            if not r:
                await self.__world.client.bot.get_channel(setup.alert_channel).send(f"Could not extract from desc.\n\n```{desc}```")
                raise
            groups = r.groups()
            self.flag_url = groups[0]
            self.nation = Nation(self.__world, groups[2]) if groups[2].strip() != "" else None
            self.religion = Religion(self.__world, groups[3].replace("TownReligion-", "")) if "Selectyour" not in groups[3] else None
            self.culture = Culture(self.__world, groups[4].replace("Culture-", "")) if groups[4] != "Culture-" else None
            self.__mayor = groups[5]
            self.resident_count  = int(groups[7])

            try:
                self.founded_date = datetime.datetime.strptime(groups[8], "%b%d%Y").date()
            except ValueError:
                self.founded_date = datetime.date.today()

            self.resident_tax = Tax(float(groups[9].replace("%", "").replace("Dollars", "").replace("$", "").strip()), "%" if "%" in groups[9] else "$")
            
            self.bank = float(groups[10].replace(",", "").strip())
            self.public = True if "true" in groups[11] else False
            #self.peaceful = True if "true" in groups[12] else False

        self.__desc = desc
    
    def clear_areas(self):
        self.__areas = []
        self.outpost_spawns = []

    async def set_marker(self, data : dict):
        await self.parse_desc(data["desc"])
        self.spawn = Point(data["x"], data["y"], data["z"])
        self.icon = data["icon"]
        self.last_updated = datetime.datetime.now()
    
    async def set_outposts(self, outposts : list[Point]):
        self.outpost_spawns = outposts

    async def add_area(self, name : str, data : dict):
    
        self.name = data["label"]
        
        self.border_color = data.get("color") or "#000000"
        self.fill_color = data.get("fillcolor") or "#000000"

        locs = []
        
        for x, z in zip(data["x"], data["z"]):
            locs.append((x, z))
        
        a = Area(self, locs, name)
        if a not in self.__areas:
            self.__areas.append(a)
        else:
            self.__areas[self.__areas.index(a)].set_verticies(locs)
        
        
        self.last_updated = datetime.datetime.now()
    
    def __eq__(self, other):
        return self.name == (other.name if hasattr(other, "name") else other)

    def __str__(self):
        return str(self.name_formatted)

class Player():
    def __init__(self, world : client_pre.object.World):
        self.__world = world 

        self.__skin_identifier : str = None

        self.name : str = None
        self.location = None
        self.armor : int = None
        self.health : int = None
        self.online = False
        self.donator : bool = None

        self.search_boost = 0

        self._town_cache = None

    async def activity_in(self, town : Town) -> Activity:
        return Activity.from_record(
            await self.__world.client.visited_towns_table.get_record([db.CreationCondition("player", self.name), db.CreationCondition("town", town.name)], ["duration", "last"])
        )
    
    @property 
    def is_bedrock(self):
        return True if "." in self.name else False
    
    async def __fetch_skin_identifier(self):
        if self.is_bedrock:
            user = await self.__world.client.session.get(f"https://api.geysermc.org/v2/xbox/xuid/{self.name.replace('.', '').replace('_', '%20')}")
            user_json : dict = await user.json()
            if user_json.get("xuid"):
                texture = await self.__world.client.session.get(f"https://api.geysermc.org/v2/skin/{user_json['xuid']}")
                self.__skin_identifier = (await texture.json())['texture_id']
        else:
            self.__skin_identifier = self.name 
        
        return self.__skin_identifier
    
    @property 
    async def skin_identifier(self):
        if not self.__skin_identifier:
            await self.__fetch_skin_identifier()
        return self.__skin_identifier


    @property 
    async def face_url(self):
        return f"https://mc-heads.net/avatar/{await self.skin_identifier}/48" 
    
    @property 
    async def body_url(self):
        return f"https://mc-heads.net/body/{await self.skin_identifier}/180" 
    
    
    @property
    async def discord(self) -> discord.User:
        flags = await self.flags
        
        if "discord" in flags:
            return self.__world.client.bot.get_user(int(flags["discord"]))

        for guild in self.__world.client.bot.guilds:
            for member in guild.members:
                if str(self.name).lower().replace("_", " ") in member.display_name.lower().replace("_", " "):
                    return member 
        
    @property 
    async def top_rankings(self) -> dict[str, list[int, int]]:
        rankings = {}
        for command in setup.top_commands["player"]:
            value = (await self.__world.client.players_table.get_record(conditions=[db.CreationCondition("name", self.name)], attributes=[command["attribute"]])).attribute(command["attribute"])
            if value:
                ranking = await self.__world.client.players_table.count_rows(conditions=[db.CreationCondition(command["attribute"], value, ">")])
                if command.get("reverse_notable"): ranking = len(self.__world.players)-ranking-1
                notable = True if ranking <= len(self.__world.players)/10 else False
                rankings[command.get("name") or command.get("attribute")] = [value, ranking+1, notable]
        
        return dict(sorted(rankings.items(), key=lambda x: x[1][1]))

    @property 
    def spawn(self) -> Point: return self.location

    @property 
    def name_formatted(self):
        """Helper"""
        return self.name

    @property 
    def town(self) -> Town:
        nearby_town = None

        for town in self.__world.towns:
            if town.is_point_in_town(self.location):
                nearby_town = town

        self._town_cache = nearby_town
        return nearby_town

    @property 
    async def activity(self) -> Activity:
        a = await self.__world.client.activity_table.get_record([db.CreationCondition("object_type", "player"), db.CreationCondition("object_name", self.name)], ["duration", "last"])
        return Activity.from_record(a)
    
    @property 
    async def visited_towns(self) -> list[Activity]:
        rs = await self.__world.client.visited_towns_table.get_records(
            [db.CreationCondition("player", self.name)], 
            ["town", "duration", "last"], group=["town"], order=db.CreationOrder("duration", db.types.OrderDescending)
        )
        return [Activity(r.attribute("duration"), r.attribute("last"), self.__world.get_town(r.attribute("town"), False) or r.attribute("town")) for r in rs]
        
    
    @property 
    async def total_visited_towns(self) -> list[Town]:
        return await self.__world.client.visited_towns_table.count_rows([db.CreationCondition("player", self.name)])
    
    @property 
    async def total_mentions(self) -> tuple[int, datetime.datetime]: 
        r = await self.__world.client.chat_mentions_table.get_record([db.CreationCondition("object_type", "player"), db.CreationCondition("object_name", self.name)], ["amount", "last"])

        if r:
            return r.attribute("amount"), r.attribute("last")
        return 0, None
    
    @property 
    async def total_messages(self) -> tuple[int, datetime.datetime]: 
        r = await self.__world.client.chat_message_counts_table.get_record([db.CreationCondition("player", self.name)], ["amount", "last"])
        if r: return r.attribute("amount"), r.attribute("last")
        return 0, None

    @property
    async def message_count(self): return (await self.total_messages)[0]
    @property
    async def mention_count(self): return (await self.total_mentions)[0]
    
    @property 
    async def likely_residency(self) -> Town:

        for town in self.__world.towns:
            if town._mayor_raw == self.name:
                return town 
        
        r = await self.__world.client.visited_towns_table.get_record(
            [db.CreationCondition("player", self.name), db.CreationCondition("towns.name", None, "is not")], 
            ["visited_towns.town AS town", "towns.resident_count AS residents"], 
            group=["visited_towns.town"], 
            order=db.CreationOrder("visited_towns.duration", db.types.OrderDescending),
            join=db.CreationTableJoin(self.__world.client.towns_table, "visited_towns.town", "towns.name", "left") # Remove towns which don't exist anymore
        )

        if r and r.attribute("residents") != 1: # If town has one resident and player is not mayor they cannot be a resident
            return self.__world.get_town(r.attribute("town"), False)
    
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
        
    async def set_flag(self, flag_name : str, flag_value):
        cond = [db.CreationCondition("object_type", "player"), db.CreationCondition("object_name", self.name)]
        val = ["player", self.name, flag_name, flag_value]

        if setup.flags["player"][flag_name].get("unique"):
            await self.__world.client.flags_table.delete_records([db.CreationCondition("object_type", "player"), db.CreationCondition("name", flag_name), db.CreationCondition("value", flag_value)])
       
        a = await self.__world.client.flags_table.add_record_if_not_exists(val, cond)
        if not a:
            await self.__world.client.flags_table.update_record(cond, *val)
    
    @property
    async def flags(self) -> dict:
        rs = await self.__world.client.flags_table.get_records([db.CreationCondition("object_type", "player"), db.CreationCondition("object_name", self.name)], ["name", "value"])
        d = {}
        for r in rs:
            if r.attribute("value"):
                d[r.attribute("name")] = r.attribute("value")
        return d

    def update(self, data : dict):

        self.name : str = data["account"]
        self.location = Point((data["x"], data["y"], data["z"]))
        self.armor : int = data["armor"]
        self.health : int = data["health"]
        self.online = True

        self.donator = True if data.get("name") != data.get("account") and "color:#ffffff" not in data.get("name") and "color:#ff5555" not in data.get("name") else False

    
    def to_record(self) -> list:
        town = self.town
        return [
            self.name, 
            ",".join([str(self.location.x), str(self.location.y), str(self.location.z)]), 
            town.name if town else None, 
            self.armor, 
            self.health, 
            0,
            int(self.donator),
            0, 
            0,
            self.__world.client.refresh_period, 
            datetime.datetime.now()
        ]

    def to_record_update(self) -> list:
        r = self.to_record()
        r[-6] = db.CreationField.external_query(
                    self.__world.client.visited_towns_table, 
                    "visited_towns", 
                    [db.CreationCondition("player", self.name)],
                    query_attribute="COUNT(*)"
        )
        r[-2] = db.CreationField.external_query(
                    self.__world.client.activity_table, 
                    "duration", 
                    [db.CreationCondition("object_type", "player"), db.CreationCondition("object_name", self.name)]
        )
        r[-4] = db.CreationField.external_query(
                    self.__world.client.chat_message_counts_table, "messages", [db.CreationCondition("player", self.name)], query_attribute="amount"
        )
        r[-3] = db.CreationField.external_query(
                    self.__world.client.chat_mentions_table, "mentions", [db.CreationCondition("object_type", "player"), db.CreationCondition("object_name", self.name)], query_attribute="amount"
        )
        return r
    
    async def to_record_history(self) -> list:
        likely = await self.likely_residency
        return [
            self.name, 
            datetime.date.today(), 
            db.CreationField.external_query(self.__world.client.players_table, "duration", db.CreationCondition("name", self.name)), 
            db.CreationField.external_query(self.__world.client.visited_towns_table, "visited_towns", [db.CreationCondition("player", self.name)], query_attribute="COUNT(*)"),
            likely.name if likely else None,
            likely.nation.name if likely and likely.nation else None,
            db.CreationField.external_query(
                    self.__world.client.chat_message_counts_table, "messages", [db.CreationCondition("player", self.name)], query_attribute="amount"
            ),
            db.CreationField.external_query(
                    self.__world.client.chat_mentions_table, "mentions", [db.CreationCondition("object_type", "player"), db.CreationCondition("object_name", self.name)], query_attribute="amount"
            )
        ]
    
    async def to_record_day_history(self) -> list:
        r = await self.to_record_history()
        return [r[0], datetime.datetime.now(), r[2], r[3]]
    
    def to_record_activity(self) -> list:
        return ["player", self.name, 0, datetime.datetime.now()]

    def to_record_activity_update(self) -> list:
        r = self.to_record_activity()
        r[-2] = db.CreationField.add("duration", self.__world.client.refresh_period)
        return r

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

        self.towns_with_players : typing.Dict[str, typing.List[Player]] = {}
        self.last_refreshed : datetime.datetime = None
        

    def get_object(self, array : list, name : str, search=False, multiple=False, max=25):
        multi = []

        i=0
        for o in sorted(array, key = lambda x: (x.name.lower()==name.lower(),x.search_boost), reverse=True):
            if (not search and o.name == name) or (search and name.replace(" ", "_").lower() in str(o).replace(" ", "_").lower() ):
                if not multiple: return o 
                i += 1
                multi.append(o)
                if i >= max:break
        if multiple:
            return multi

    def get_town(self, town_name : str, search=False, multiple=False, max=25) -> Town:
        if not search and not multiple:
            return self.__towns.get(town_name)
        
        multi = []

        i=0
        for town in sorted(self.__towns, key = lambda x: (x.lower()==town_name.lower(),self.__towns[x].search_boost), reverse=True):
            if town_name.replace(" ", "_").lower() in str(town).replace(" ", "_").lower():
                if not multiple: return self.__towns[town]
                i+=1
                multi.append(self.__towns[town])
                if i >= max: break
        
        if multiple:
            return multi 

    def get_player(self, player_name : str, search=True, multiple=False, max=25) -> Player:
        if not search and not multiple:
            return self.__players.get(player_name)
        
        multi = []
        i=0
        for player in sorted(self.__players, key = lambda x: (x.lower()==player_name.lower(),self.__players[x].search_boost), reverse=True):
            if player_name.replace(" ", "_").lower() in str(player).replace(" ", "_").lower():
                if not multiple: return self.__players[player]
                i += 1
                multi.append(self.__players[player])
                if i >= max: break

        if multiple:
            return multi

    def get_nation(self, nation_name : str, search=False, multiple=False, max=25) -> Nation:
        return self.get_object(self.nations, nation_name, search, multiple, max)
    
    def get_culture(self, culture_name : str, search=False, multiple=False, max=25) -> Culture:
        return self.get_object(self.cultures, culture_name, search, multiple, max)
    
    def get_religion(self, religion_name : str, search=False, multiple=False, max=25) -> Religion:
        return self.get_object(self.religions, religion_name, search, multiple, max)
    
    def search(self, get_func : callable, query : str, max : int = 25) -> list:
        return get_func(query, True, True, max)
    
    def search_player(self, player_name : str, max : int = 25) -> list[Player]: return self.search(self.get_player, player_name, max)
    def search_town(self, town_name : str, max : int = 25) -> list[Town]: return self.search(self.get_town, town_name, max)
    def search_nation(self, nation_name : str, max : int = 25) -> list[Nation]: return self.search(self.get_nation, nation_name, max)
    def search_culture(self, nation_name : str, max : int = 25) -> list[Nation]: return self.search(self.get_culture, nation_name, max)
    def search_religion(self, nation_name : str, max : int = 25) -> list[Nation]: return self.search(self.get_religion, nation_name, max)

    @property
    def database_size(self):
        return round(os.path.getsize('towny.db')/1000/1000, 2)

    async def to_record_history(self) -> list:
        return [datetime.date.today(), len(self.towns), self.total_residents, len(self.nations), self.total_value, self.total_area, len(self.players), (await self.total_activity).total, await self.total_messages, self.database_size]

    async def to_record_day_history(self) -> list:
        r = await self.to_record_history()
        r[0] = datetime.datetime.now() 
        r.pop()
        r.append(self.player_count)
        return r

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

    @property 
    def offline_players(self) -> list[Player]:
        ps = []
        for p in self.players:
            if not p.online:
                ps.append(p)
        return ps
    
    def __total(self, arr : list, attr : str):
        t = 0
        for o in arr:
            t += getattr(o, attr) or 0
        return t

    @property 
    def total_residents(self) -> int: return self.__total(self.towns, "resident_count")
    @property 
    def total_area(self) -> int: return self.__total(self.towns, "area")
    @property 
    def total_value(self) -> float: return self.__total(self.towns, "bank")

    @property 
    async def total_activity(self) -> Activity:
        return Activity(await self.client.activity_table.total_column("duration", [db.CreationCondition("object_type", "player")]))

    @property 
    async def total_tracked(self) -> Activity:
        return Activity((await self.client.global_table.get_record([db.CreationCondition("name", "total_tracked")], ["value"])).attribute("value"))
    @property 
    async def total_tracked_chat(self) -> Activity:
        return Activity((await self.client.global_table.get_record([db.CreationCondition("name", "total_tracked_chat")], ["value"])).attribute("value"))
    
    @property 
    async def total_messages(self) -> int: 
        return await self.client.chat_message_counts_table.total_column("amount")
    
    @property 
    async def linked_discords(self) -> list[tuple[Player, discord.Member]]:
        discords = []
        members = {}
        for guild in self.client.bot.guilds:
            for member in guild.members:
                members[member.display_name] = member 
        for player in self.players:
            for member_name, member in members.items():
                if str(player.name).lower().replace("_", " ") in member_name.lower().replace("_", " "):
                    discords.append((player, member))
        return discords

    def _remove_player(self, player_name : str):
        del self.__players[player_name]
    def _remove_town(self, town_name : str):
        del self.__towns[town_name]
    def _remove_nation(self, nation_name : str):
        rm = []
        for nation in self._objects["nations"]:
            if nation.name == nation_name:
                rm.append(nation)
        for r in rm:
            self._objects["nations"].remove(r)
        

    async def refresh(self, map : StreamReader, map_data : StreamReader):

        objects_map = ijson.kvitems_async(map, "", use_float=True)
        
        player_list = None
        async for o in objects_map:
            if o[0] == "currentcount":
                self.player_count = o[1] or 0
            elif o[0] == "hasStorm":
                self.is_stormy = o[1] or False
            elif o[0] == "players":
                player_list = o[1]
            else:
                continue
        
        objects_map_data = ijson.kvitems_async(map_data, "sets.towny.markerset", use_float=True)
        areas = {}
        markers = {}
        async for o in objects_map_data:
            if o[0] == "areas":
                areas = o[1]
            elif o[0] == "markers":
                markers = o[1]
            else:
                continue

        await self.__update_town_list(areas, markers)
        await self.__update_global()
        if player_list: # Has to be done after towns are found
            self.towns_with_players = await self.__update_player_list(player_list)
        
        await self.__update_objects()
        await self.__update_town_tracking()
        await self.__update_nations()
        
        self.last_refreshed = datetime.datetime.now()

    async def __update_objects(self):
        new_records = []
        add_object_history = []

        objects_table_records = [r.attribute("type")+r.attribute("name") for r in await self.client.objects_table.get_records(attributes=["type", "name"])]
        object_history_table_records = [r.attribute("object")+str(r.attribute("date")) for r in await self.client.object_history_table.get_records(attributes=["object", "date"], conditions=[db.CreationCondition("type", "nation", "!=")])]

        for object_type, objects in self._objects.items():
            for object in objects:
                if object_type == "nations" and not object.capital:
                    continue 

                if object.object_type+object.name not in objects_table_records:
                    new_records.append(object.to_record())
                else:
                    await self.client.objects_table.update_record([db.CreationCondition("type", object.object_type), db.CreationCondition("name", object.name)], *object.to_record())

                if object_type in ["cultures", "religions"]: # Culture/religion history
                    try:
                        if object.name+str(datetime.date.today()) not in object_history_table_records:
                            add_object_history.append(object.to_record_history())
                        else:
                            await self.client.object_history_table.update_record([db.CreationCondition("object", object.name), db.CreationCondition("date", datetime.date.today())], *object.to_record_history())
                    except Exception as e:
                        # Nation needs to be removed! Should be removed on next pass from Client.cull_db()
                        await self.client.bot.get_channel(setup.alert_channel).send(f"{object.name} Object Tracking Update Error! `{e}`"[:2000])
        
        if len(new_records) > 0:
            await self.client.objects_table.add_record(new_records)

        if len(add_object_history) > 0:
            await self.client.object_history_table.add_record(add_object_history)

    async def __update_nations(self):
        add_nation_history = []
        new_records_activity= []
        add_nation_day_history = []

        for nation in self.nations:
            
            # Add town activity
            cond3 = [db.CreationCondition("object_name", nation.name), db.CreationCondition("object_type", "nation")]
            exists = await self.client.activity_table.record_exists(cond3)
            if not exists:
                new_records_activity.append(nation.to_record_activity())
            else:
                await self.client.activity_table.update_record(cond3, *nation.to_record_activity_update(self.towns_with_players))

            cond2 = [db.CreationCondition("nation", nation.name), db.CreationCondition("date", datetime.date.today())]
            exists = await self.client.nation_history_table.record_exists(cond2)
            try:
                if not exists:
                    add_nation_history.append(nation.to_record_history())
                else:
                    await self.client.nation_history_table.update_record(cond2, *nation.to_record_history())
                
                cond3 = [db.CreationCondition("nation", nation.name), db.CreationCondition("time", datetime.datetime.now()-setup.today_tracking_period, ">")]
                exists = await self.client.nation_day_history_table.record_exists(cond3)
                if not exists or datetime.datetime.now().minute in setup.production_today_tracking_minutes:
                    cond3[1] = db.CreationCondition("time", datetime.datetime.now()-datetime.timedelta(minutes=5), ">")
                    exists2 = await self.client.nation_day_history_table.record_exists(cond3)
                    if not exists2:
                        add_nation_day_history.append(nation.to_record_day_history())
            except Exception as e:
                # Nation needs to be removed! Should be removed on next pass from Client.cull_db()
                await self.client.bot.get_channel(setup.alert_channel).send(f"{nation.name} Nation Tracking Update Error! `{e}`"[:2000])
            
            

        if len(new_records_activity) > 0:
            await self.client.activity_table.add_record(new_records_activity)
        if len(add_nation_history) > 0:
            await self.client.nation_history_table.add_record(add_nation_history)
        if len(add_nation_day_history) > 0:
            await self.client.nation_day_history_table.add_record(add_nation_day_history)

    async def __update_global(self):

        if not await self.client.global_table.record_exists(db.CreationCondition("name", "total_tracked")):
            await self.client.global_table.add_record(["total_tracked", 0])
        await self.client.global_table.update_record(db.CreationCondition("name", "total_tracked"), db.CreationField.add("value", self.client.refresh_period))
        if not await self.client.global_table.record_exists(db.CreationCondition("name", "total_tracked_chat")):
            await self.client.global_table.add_record(["total_tracked_chat", 0])
        await self.client.global_table.update_record(db.CreationCondition("name", "total_tracked_chat"), db.CreationField.add("value", self.client.refresh_period))

        cond = [db.CreationCondition("date", datetime.date.today())]
        exists = await self.client.global_history_table.record_exists(cond)
        if not exists:
            await self.client.global_history_table.add_record(await self.to_record_history())
        else:
            await self.client.global_history_table.update_record(cond, *await self.to_record_history())
        
        exists = await self.client.global_day_history_table.record_exists([db.CreationCondition("time", datetime.datetime.now()-setup.today_tracking_period, ">")])
        if not exists or datetime.datetime.now().minute in setup.production_today_tracking_minutes:
            exists2 = await self.client.global_day_history_table.record_exists([db.CreationCondition("time", datetime.datetime.now()-datetime.timedelta(minutes=5), ">")])
            if not exists2:
                await self.client.global_day_history_table.add_record(await self.to_record_day_history())

    async def __update_town_list(self, areas : dict[str, dict], markers : dict[str, dict]):

        outposts = {}

        for marker_id, marker_data in markers.items():
            if "_Outpost_" in marker_id:
                town_name = marker_id.split("_Outpost_")[0]
                if town_name not in outposts:
                    outposts[town_name] = []
                outposts[town_name].append(Point(marker_data["x"], marker_data["y"], marker_data["z"]))
        
        for town in self.__towns.values():
            town.clear_areas()
        
        for area_name, area in areas.items():
            if area.get("set") != "siegewar.markerset":
                
                try:
                    
                    if area["label"] in setup.DONT_TRACK_TOWNS:
                        continue 

                    if True in [su in area["label"] for su in setup.DEFAULT_TOWNS_SUBSTRING]:
                        continue

                    if area["label"] not in self.__towns:
                        
                        t = Town(self)
                        await t.add_area(area_name, area)
                        
                        if markers.get(f"{t.name}__home"):
                            self.__towns[area["label"]] = t
                    else:
                        t = self.get_town(area["label"], False)
                        await t.add_area(area_name, area)
                    
                    if markers.get(f"{t.name}__home"):
                        await t.set_marker(markers[f"{t.name}__home"])
                    if t.name in outposts:
                        await t.set_outposts(outposts[t.name])
                    #await asyncio.sleep(0.001) # Allow "parallel" processing
                    
                except Exception as e:
                    # Error with town add. Town may need to be removed!
                    await self.client.bot.get_channel(setup.alert_channel).send(f"{area.get('label')} Town Update Error! `{e}`"[:2000])
    
    async def __update_town_tracking(self):
        new_records = []
        add_town_history = []
        add_town_day_history = []
        new_records_activity = []
        for town in self.towns:
            try:
                # Add town activity
                cond3 = [db.CreationCondition("object_name", town.name), db.CreationCondition("object_type", "town")]
                exists = await self.client.activity_table.record_exists(cond3)
                if not exists:
                    new_records_activity.append(town.to_record_activity())
                else:
                    await self.client.activity_table.update_record(cond3, *town.to_record_activity_update(self.towns_with_players.get(town.name) or []))

                
                cond = db.CreationCondition(self.client.towns_table.primary_key, town.name)
                exists = await self.client.towns_table.record_exists(cond)
                if not exists:
                    new_records.append(town.to_record())
                else:
                    await self.client.towns_table.update_record([cond], *town.to_record_update())
            
                # Add town history
                cond2 = [db.CreationCondition("town", town.name), db.CreationCondition("date", datetime.date.today())]
                exists = await self.client.town_history_table.record_exists(cond2)
                if not exists:
                    add_town_history.append(town.to_record_history())
                else:
                    await self.client.town_history_table.update_record(cond2, *town.to_record_history())
                
                cond3 = [db.CreationCondition("town", town.name), db.CreationCondition("time", datetime.datetime.now()-setup.today_tracking_period, ">")]
                exists = await self.client.town_day_history_table.record_exists(cond3)
                if not exists or datetime.datetime.now().minute in setup.production_today_tracking_minutes:
                    cond3[1] = db.CreationCondition("time", datetime.datetime.now()-datetime.timedelta(minutes=5), ">")
                    exists2 = await self.client.town_day_history_table.record_exists(cond3)
                    if not exists2:
                        add_town_day_history.append(town.to_record_day_history())
                
            except Exception as e:
                # Error with town add. Town may need to be removed!
                await self.client.bot.get_channel(setup.alert_channel).send(f"{town.name} Town Tracking Update Error! `{e}` {discord.utils.escape_markdown(traceback.format_exc())}"[:2000])

        if len(new_records_activity) > 0:
            await self.client.activity_table.add_record(new_records_activity)
        if len(new_records) > 0:
            await self.client.towns_table.add_record(new_records)
        if len(add_town_history) > 0:
                await self.client.town_history_table.add_record(add_town_history)
        if len(add_town_day_history) > 0:
            await self.client.town_day_history_table.add_record(add_town_day_history)

    async def initialise_player_list(self):
        players = await self.client.players_table.get_records()

        for player in players:
            p = Player(self)

            p.name = str(player.attribute("name"))
            p.location = Point(float(c) for c in player.attribute("location").split(","))
            p.armor = player.attribute("armor")
            p.health = player.attribute("health")
            p.donator = bool(player.attribute("donator")) if player.attribute("donator") else None

            self.__players[p.name] = p

    async def __update_player_list(self, players : list[dict]):
        add_players = []
        add_visited_towns = []
        add_player_history = []
        add_player_day_history =[]
        new_records_activity = []
        online_players : list[str] = []

        towns_with_players : dict[str, list[Player]] = {}

        for player_data in players:
            await asyncio.sleep(0.001) # Allow "parallel" processing

            online_players.append(player_data["account"])

            p = self.get_player(player_data["account"], False)

            if not p:
                
                p = Player(self)
                self.__players[player_data["account"]] = p
            p.update(player_data)

            # Add activity
            cond3 = [db.CreationCondition("object_name", p.name), db.CreationCondition("object_type", "player")]
            exists = await self.client.activity_table.record_exists(cond3)
            if not exists:
                new_records_activity.append(p.to_record_activity())
            else:
                await self.client.activity_table.update_record(cond3, *p.to_record_activity_update())


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
                add_player_history.append(await p.to_record_history())
            else:
                await self.client.player_history_table.update_record(cond2, *(await p.to_record_history()))
            
            cond3 = [db.CreationCondition("player", p.name), db.CreationCondition("time", datetime.datetime.now()-setup.today_tracking_period, ">")]
            exists = await self.client.player_day_history_table.record_exists(cond3)
            if not exists:
                add_player_day_history.append(await p.to_record_day_history())
            
            town = p._town_cache
            if town:
                if town.name not in towns_with_players:
                    towns_with_players[town.name] = []
                towns_with_players[town.name].append(p)

                conds = [db.CreationCondition(self.client.visited_towns_table.attribute("player"), p.name), db.CreationCondition(self.client.visited_towns_table.attribute("town"), town.name)]
                exists = await self.client.visited_towns_table.record_exists(conds)

                if not exists:
                    add_visited_towns.append([p.name, town.name, self.client.refresh_period, datetime.datetime.now()])
                else:
                    await self.client.visited_towns_table.update_record(conds, *[p.name, town.name, db.CreationField.add("duration", self.client.refresh_period), datetime.datetime.now()])
        
        if len(new_records_activity) > 0:
            await self.client.activity_table.add_record(new_records_activity)
        if len(add_players) > 0:
            await self.client.players_table.add_record(add_players)
        if len(add_visited_towns) > 0:
            await self.client.visited_towns_table.add_record(add_visited_towns)
        if len(add_player_history) > 0:
            await self.client.player_history_table.add_record(add_player_history)
        if len(add_player_day_history) > 0:
            await self.client.player_day_history_table.add_record(add_player_day_history)
        
        for player in self.players:
            if player.online and player.name not in online_players:
                player.online = False
        
        return towns_with_players

continents : dict[str, Polygon] = {
    "europe":Polygon(
        [
            [10620, -9600],
            [12900, -14300],
            [15550, -17400],
            [0, -17400],
            [-4450, -14000],
            [-5585, -13570],
            [-5276, -8000],
            [-1300, -7360],
            [-274, -7435],
            [1123, -7835],
            [2285, -7801],
            [3648, -7153],
            [4614, -7200],
            [6805, -8872],
            [8050, -9000],
            [10220, -8550],
            [10000, -9100],
            [10620, -9600]
        ]
    ),
    "asia":Polygon(
        [
            [10620, -9600],
            [12900, -14300],
            [15550, -17400],
            [18300, -16700],
            [37000, -16200],
            [36884, -12600],
            [29700, -6800],
            [29083, 605],
            [28427, 1966],
            [26555, 2037],
            [24828, 2553],
            [11650, -3170],
            [9000, -2386],
            [6417, -6888],
            [6805, -8872],
            [8050, -9000],
            [10220, -8550],
            [10000, -9100],
            [10620, -9600]
        ]
    ),
    "africa":Polygon(
        [
            [9000, -2386],
            [6417, -6888],
            [4614, -7200],
            [3648, -7153],
            [2285, -7801],
            [1123, -7835],
            [-274, -7435],
            [-1300, -7360],
            [-5800, -3400],
            [3900, 7829],
            [10600, 6500],
            [12000, -3000],
            [9000, -2386]
        ]
    ),
    "north_america":Polygon(
        [
            [-653, -17470],
            [-4450, -14050],
            [-11741, -7333],
            [-11805, -2400],
            [-14813, -2770],
            [-18250, -264],
            [-35170, -10600],
            [-34000, -16200],
            [-15000, -17800],
            [-653, -17470]
        ]
    ),
    "south_america":Polygon(
        [
            [-11805, -2400],
            [-14813, -2770],
            [-18250, -264],
            [-19100, -250],
            [-17000, 12500],
            [-10500, 11500],
            [-5000, 500],
            [-11805, -2400]
        ]
    ),
    "oceania":Polygon(
        [
            [29083, 605],
            [28427, 1966],
            [26555, 2037],
            [24828, 2553],
            [21630, 4440],
            [22230, 9600],
            [36888, 10864],
            [36888, -500],
            [29083, 605],
        ]
    )
}
    