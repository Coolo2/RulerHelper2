
from __future__ import annotations
import typing
if typing.TYPE_CHECKING:
    import client as client_pre

import datetime
from shapely.geometry import MultiPolygon

import setup 

import discord

class Object():
    def __init__(self, world : client_pre.objects.World, name : str, object_type : str):
        self.name = name 
        self.world = world
        self.object_type = object_type
        self.last_seen = datetime.datetime.now() 
        self.search_boost = 0
        self._towns_cache = None

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

    @property 
    async def total_mentions(self) -> tuple[int, datetime.datetime]: 
        r = await (await self.world.client.execute("SELECT amount, last FROM chat_mentions WHERE object_type=? AND object_name=?", (self.object_type, self.name))).fetchone()

        if r:
            return r
        return 0, None
    
    @property
    async def mention_count(self): return (await self.total_mentions)[0]

    @property 
    def total_residents(self) -> int: 
        return self.world.client.funcs._total(self.towns, "resident_count")
        
    @property 
    def total_outposts(self) -> int:
        t= 0
        for town in self.towns:
            t += len(town.outposts)
        return t
    @property 
    def total_area(self) -> int: return self.world.client.funcs._total(self.towns, "area")
    @property 
    def total_value(self) -> float: return self.world.client.funcs._total(self.towns, "bank")
    @property 
    def total_detached_area(self) -> int: return self.world.client.funcs._total(self.towns, "detached_area")
    @property
    def vertex_count(self) -> int:
        return self.world.client.funcs._total(self.towns, "vertex_count")
    
    @property 
    def outpost_spawns(self) -> list[tuple[float]]:
        t = []
        for town in self.towns:
            t += town.outpost_spawns 
        return t

    async def set_flag(self, flag_name : str, flag_value):
        await self.world.client.funcs.set_flag(self.world.client, self.object_type, self.name, flag_name, flag_value)
    
    @property
    async def flags(self) -> dict:
        rs = await (await self.world.client.execute("SELECT name, value FROM flags WHERE object_type=? AND object_name=?", (self.object_type, self.name))).fetchall()
        d = {}
        for r in rs:
            if r[1]:
                d[r[0]] = r[1]
        return d
    
    @property 
    def areas(self):
        l = []
        for town in self.towns:
            l += town.areas
        return l

    def reset_town_cache(self):
        self._towns_cache = None

    def __str__(self):
        return self.name
    
    def __eq__(self, other):
        return self.name == (other.name if hasattr(other, "name") else other)

class Nation(Object):
    def __init__(self, world, name : str):
        super().__init__(world, name, "nation")
    
    @property 
    def towns(self) -> list[client_pre.objects.Town]:
        if not self._towns_cache:
            self._towns_cache = [t for t in self.world.towns if t.nation == self]
        return self._towns_cache

    @property 
    def capital(self) -> client_pre.objects.Town:
        for town in self.towns:
            if town.icon == "ruler":
                return town 
    
    @property 
    def leader(self) -> client_pre.objects.Player:
        return self.capital.mayor

    @property 
    def borders(self) -> tuple[list[client_pre.objects.Nation]|list[client_pre.objects.Town]]:
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
    async def first_seen_in_history(self) -> datetime.date:
        r = await (await self.world.client.execute("SELECT date FROM nation_history WHERE nation=? ORDER BY date ASC LIMIT 1", (self.name,))).fetchone()
        return r[0]

    @property 
    async def visited_players(self) -> list[client_pre.objects.Activity]:
        rs = await (await self.world.client.execute("SELECT player, duration, last FROM visited_nations WHERE nation=? GROUP BY player ORDER BY duration DESC", (self.name,))).fetchall()

        return [self.world.client.objects.Activity(r[1], r[2], player=self.world.get_player(r[0], False) or r[0]) for r in rs]

    @property 
    async def total_visited_players(self) -> int:
        r = await (await self.world.client.execute("SELECT COUNT(*) FROM visited_nations WHERE nation=?", (self.name,))).fetchone()
        return r[0]

    @property 
    async def top_rankings(self) -> dict[str, list[int, int]]:
        rankings = {}
        for command in setup.top_commands["nation"]:
            if command.get("notable") == False: continue

            r1 = await (await self.world.client.execute(f"""SELECT {command['attribute']} FROM objects WHERE type='nation' AND name=?""", (self.name,))).fetchone()
            if r1 and r1 != (None,):
                r2 = await (await self.world.client.execute(f"""SELECT COUNT(*) FROM objects WHERE type='nation' AND {command['attribute']}>?""", (r1[0],))).fetchone()
                ranking = r2[0]
                if command.get("reverse_notable"): ranking = len(self.world.nations)-ranking-1
                notable = True if ranking <= len(self.world.nations)/2 else False
                rankings[command.get("name") or command.get("attribute")] = [r1[0], ranking+1, notable]
        
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
            stats.append(f"The total mayor bank balance for {discord.utils.escape_markdown(self.name_formatted)} is **${self.world.client.funcs._total(self.towns, 'mayor_bank'):,.2f}**")
            stats.append(f"Detached territories make up **{detached_area_perc:,.2f}%** of {discord.utils.escape_markdown(self.name_formatted)}'s claims")
            stats.append(f"The average town balance in {discord.utils.escape_markdown(self.name_formatted)} is **${self.average_town_balance:,.2f}**")
        return stats
    
    @property 
    def upkeep(self) -> int:
        return 100 + (self.total_residents//5)*50
    
    @property
    def average_town_balance(self) -> float:
        return self.total_value/self.total_towns
    
    @property 
    def population_density(self):
        return int(self.total_area/self.total_residents)

    @property 
    async def activity(self) -> client_pre.objects.Activity:
        r = await (await self.world.client.execute("SELECT duration, last FROM activity WHERE object_type='nation' AND object_name=?", (self.name,))).fetchone()

        return self.world.client.objects.Activity.from_record(r)

    @property 
    async def previous_names(self) -> list[str]:
        rs = await (await self.world.client.execute("SELECT current_name FROM nation_history WHERE nation=? AND current_name != ? GROUP BY current_name ORDER BY date DESC", (self.name, self.name))).fetchall()
        return [r[0] for r in rs]
    
    def __str__(self):
        return self.name_formatted

class Culture(Object):
    def __init__(self, world, name : str):
        super().__init__(world, name, "culture")
    
    @property 
    def towns(self) -> list[client_pre.objects.Town]:
        if not self._towns_cache:
            self._towns_cache = [t for t in self.world.towns if t.culture == self]
        return self._towns_cache
    
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
    def towns(self) -> list[client_pre.objects.Town]:
        if not self._towns_cache:
            self._towns_cache = [t for t in self.world.towns if t.religion == self]
        return self._towns_cache
    
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
    
    