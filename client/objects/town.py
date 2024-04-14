
from __future__ import annotations
import typing
if typing.TYPE_CHECKING:
    import client as client_pre

import datetime
from shapely.geometry import MultiPolygon, Point
import re

import setup 

import discord

class Town():
    def __init__(self, world : client_pre.objects.World):
        self.__world = world
        self.__desc = None

        self.outpost_spawns : list[Point] = []
        self.__areas : list[client_pre.objects.Area] = []
        self._resident_names = None

        self.residents : list[client_pre.objects.Player] = None

        self.search_boost = 0

        self.spawn : Point = None
        self.name : str = None 
        self.icon : str = None

        self.flag_url : str = None 
        self.nation : client_pre.objects.Nation = None
        self.religion : client_pre.objects.Religion = None 
        self.culture : client_pre.objects.Culture = None 
        self.__mayor : str = None 
        self.resident_count : int = None 
        self.founded_date : datetime.date = None 
        self.resident_tax : client_pre.objects.Tax = None 
        self.bank : float = None 
        self.mayor_bank : float = None
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
    def mayor(self) -> typing.Union[client_pre.objects.Player, str]:
        return self.__world.get_player(self.__mayor, False) or self.__mayor

    @property 
    def area(self) -> int:
        return round((self.locations.area)/256)

    @property 
    async def activity(self) -> client_pre.objects.Activity:
        r = await (await self.__world.client.execute("SELECT duration, last FROM activity WHERE object_type='town' AND object_name=?", (self.name,))).fetchone()
        
        return self.__world.client.objects.Activity.from_record(r)
    
    @property 
    async def deletion_warning(self) -> typing.Union[int, None]:
        if self.resident_count != 1:
            return None
        r : tuple[datetime.datetime] = await (await self.__world.client.execute("SELECT last FROM activity WHERE object_type='player' AND object_name=?", (str(self.mayor),))).fetchone()
        time_since = (datetime.datetime.now()-r[0])
        if time_since > datetime.timedelta(days=setup.get_town_deletion_warning_threshold_days):
            return 45-time_since.days
    
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
            if polygon.contains(self.spawn_xz):

                for continent_name, continent_polygon in self.__world.client.continents.continents.items():
                    
                    if continent_polygon.intersects(polygon):
                        cs.append(continent_name)
        return cs
    
    @property 
    def spawn_xz(self):
        return Point(self.spawn.x, self.spawn.z)
    
    @property 
    def geography_description(self) -> str:
        continent_names = []

        for continent_name in self.continents:
            cont_centre = self.__world.client.continents.centres[continent_name]
            continent_names.append(self.__world.client.funcs.location_description(self.spawn_xz, cont_centre) + " " + continent_name)

        return f"{self.name_formatted} is a town in {'/'.join(cn.replace('_', ' ').title() for cn in continent_names) if len(continent_names) else 'no continent'}"

    @property 
    async def visited_players(self) -> list[client_pre.objects.Activity]:
        rs = await (await self.__world.client.execute("SELECT player, duration, last FROM visited_towns WHERE town=? AND last >= ? GROUP BY player ORDER BY duration DESC", (self.name, self.founded_date))).fetchall()

        return [self.__world.client.objects.Activity(r[1], r[2], player=self.__world.get_player(r[0], False) or r[0]) for r in rs]
    
    @property 
    def borders(self) -> list[client_pre.objects.Town]:
        borders = []

        for town in self.__world.towns:
            if town != self and town.name not in setup.DEFAULT_TOWNS and True not in [l in town.name for l in setup.DEFAULT_TOWNS_SUBSTRING]:
                if self.locations.intersects(town.locations):
                    borders.append(town)
        
        return borders
    
    async def set_flag(self, flag_name : str, flag_value):
        await self.__world.client.funcs.set_flag(self.__world.client, "town", self.name, flag_name, flag_value)
    
    @property
    async def flags(self) -> dict:
        rs = await (await self.__world.client.execute("SELECT name, value FROM flags WHERE object_type='town' AND object_name=?", (self.name,))).fetchall()
        d = {}
        for r in rs:
            if r[1]:
                d[r[0]] = r[1]
        return d
    
    @property 
    async def top_rankings(self) -> dict[str, list[int, int]]:
        rankings = {}
        for command in setup.top_commands["town"]:

            r1 = await (await self.__world.client.execute(f"""SELECT {command['attribute']} FROM towns WHERE name=?""", (self.name,))).fetchone()
            if r1 and r1 != (None,):
                r2 = await (await self.__world.client.execute(f"""SELECT COUNT(*) FROM towns WHERE {command['attribute']}>?""", (r1[0],))).fetchone()
                ranking = r2[0]
                if command.get("reverse_notable"): ranking = len(self.__world.towns)-ranking-1
                notable = True if ranking <= len(self.__world.nations)/5 else False
                rankings[command.get("name") or command.get("attribute")] = [r1[0], ranking+1, notable]
        
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
        r = await (await self.__world.client.execute("SELECT COUNT(*) FROM visited_towns WHERE town=?", (self.name,))).fetchone()
        return r[0]
    
    @property 
    async def previous_names(self) -> list[str]:
        rs = await (await self.__world.client.execute("SELECT current_name FROM town_history WHERE town=? AND current_name != ? GROUP BY current_name ORDER BY date DESC", (self.name, self.name))).fetchall()
        return [r[0] for r in rs]
    
    @property 
    async def total_mentions(self) -> tuple[int, datetime.datetime]: 
        r = await (await self.__world.client.execute("SELECT amount, last FROM chat_mentions WHERE object_type='town' AND object_name=?", (self.name,))).fetchone()

        if r:
            return r
        return 0, None
    @property
    async def mention_count(self): return (await self.total_mentions)[0]

    @property 
    def outposts(self):
        return [a for a in self.areas if a.is_outpost]
    
    @property 
    def population_density(self):
        return int(self.area/self.resident_count)
    
    @property
    async def bank_change_today(self) -> float:
        yesterday_record = await (await self.__world.client.execute("SELECT bank FROM town_history WHERE town=? AND date=?", (self.name, datetime.date.today()-datetime.timedelta(days=1)))).fetchone()

        yesterday_bank = 0.0
        if yesterday_record:
            yesterday_bank = yesterday_record[0]

        return self.bank-yesterday_bank
    
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
            self.nation = self.__world.client.objects.Nation(self.__world, groups[2]) if groups[2].strip() != "NoNation" else None
            self.religion = self.__world.client.objects.Religion(self.__world, groups[3].replace("TownReligion-", "")) if "Selectyour" not in groups[3] else None
            self.culture = self.__world.client.objects.Culture(self.__world, groups[4].replace("Culture-", "")) if groups[4] != "Culture-" else None
            self.__mayor = groups[6]
            self.resident_count  = int(groups[7])
            self._resident_names = groups[8].strip().split(",")

            try:
                self.founded_date = datetime.datetime.strptime(groups[9], "%b%d%Y").date()
            except ValueError:
                self.founded_date = datetime.date.today()

            self.resident_tax = self.__world.client.objects.Tax(float(groups[10].replace("%", "").replace("Dollars", "").replace("$", "").strip()), "%" if "%" in groups[10] else "$")
            
            self.bank = float(groups[11].replace(",", "").strip())
            self.mayor_bank = float(groups[12].replace(",", "").replace("$", "").strip())
            self.public = True if "true" in groups[13] else False

            self.residents = []
            for player_name in self._resident_names:
                p = self.__world.get_player(player_name, False)
                if p:
                    if p.name == self.__mayor:
                        p.bank = self.mayor_bank

                    p.residence = self
                    self.residents.append(p)

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
        
        a = self.__world.client.objects.Area(self, locs, name)
        if a not in self.__areas:
            self.__areas.append(a)
        else:
            self.__areas[self.__areas.index(a)].set_verticies(locs)
        
        
        self.last_updated = datetime.datetime.now()
    
    def __eq__(self, other):
        return self.name == (other.name if hasattr(other, "name") else other)

    def __str__(self):
        return str(self.name_formatted)