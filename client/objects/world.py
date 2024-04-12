from __future__ import annotations
import typing
if typing.TYPE_CHECKING:
    import client as client_pre

from shapely.geometry import Point
import discord
import os

class World():
    def __init__(self, client : client_pre.Client):

        self.client = client

        self.__towns : dict[str, client_pre.objects.Town] = {}
        self.__players : dict[str, client_pre.objects.Player] = {}
        self._objects : dict[str, list[client_pre.objects.Object]] = {
            "nations":[],
            "cultures":[],
            "religions":[]
        }

        self.player_count : int = None 
        self.is_stormy : bool = None

        self.towns_with_players : typing.Dict[str, typing.List[client_pre.objects.Player]] = {}

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

    def get_town(self, town_name : str, search=False, multiple=False, max=25) -> client_pre.objects.Town:
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

    def get_player(self, player_name : str, search=True, multiple=False, max=25) -> client_pre.objects.Player:
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

    def get_nation(self, nation_name : str, search=False, multiple=False, max=25) -> client_pre.objects.Nation:
        return self.get_object(self.nations, nation_name, search, multiple, max)
    
    def get_culture(self, culture_name : str, search=False, multiple=False, max=25) -> client_pre.objects.Culture:
        return self.get_object(self.cultures, culture_name, search, multiple, max)
    
    def get_religion(self, religion_name : str, search=False, multiple=False, max=25) -> client_pre.objects.Religion:
        return self.get_object(self.religions, religion_name, search, multiple, max)
    
    def search(self, get_func : callable, query : str, max : int = 25) -> list:
        return get_func(query, True, True, max)
    
    def search_player(self, player_name : str, max : int = 25) -> list[client_pre.objects.Player]: return self.search(self.get_player, player_name, max)
    def search_town(self, town_name : str, max : int = 25) -> list[client_pre.objects.Town]: return self.search(self.get_town, town_name, max)
    def search_nation(self, nation_name : str, max : int = 25) -> list[client_pre.objects.Nation]: return self.search(self.get_nation, nation_name, max)
    def search_culture(self, nation_name : str, max : int = 25) -> list[client_pre.objects.Nation]: return self.search(self.get_culture, nation_name, max)
    def search_religion(self, nation_name : str, max : int = 25) -> list[client_pre.objects.Nation]: return self.search(self.get_religion, nation_name, max)

    @property
    def database_size(self):
        return round(os.path.getsize('towny.db')/1000/1000, 2)

    @property 
    def towns(self) -> list[client_pre.objects.Town]:
        return list(self.__towns.values())
    @property 
    def players(self) -> list[client_pre.objects.Player]:
        return list(self.__players.values() )
    @property 
    def nations(self) -> list[client_pre.objects.Nation]:
        return self._objects["nations"]
    @property 
    def cultures(self) -> list[client_pre.objects.Culture]:
        return self._objects["cultures"]
    @property 
    def religions(self) -> list[client_pre.objects.Religion]:
        return self._objects["religions"]
    
    @property 
    def online_players(self) -> list[client_pre.objects.Player]:
        ps = []
        for p in self.players:
            if p.online:
                ps.append(p)
        return ps

    @property 
    def offline_players(self) -> list[client_pre.objects.Player]:
        ps = []
        for p in self.players:
            if not p.online:
                ps.append(p)
        return ps

    @property 
    def total_residents(self) -> int: return self.client.funcs._total(self.towns, "resident_count")
    @property 
    def total_area(self) -> int: return self.client.funcs._total(self.towns, "area")
    @property 
    def total_value(self) -> float: return self.client.funcs._total(self.towns, "bank")
    @property 
    def total_mayor_value(self) -> float: return self.client.funcs._total(self.players, "bank")

    @property 
    async def total_activity(self) -> client_pre.objects.Activity:
        r = await (await self.client.execute("SELECT SUM(duration) FROM activity WHERE object_type='player'")).fetchone()

        return self.client.objects.Activity(r[0])

    @property 
    async def total_tracked(self) -> client_pre.objects.Activity:
        try:
            r = await (await self.client.execute("SELECT value FROM global WHERE name='total_tracked'")).fetchone()

            if r:
                return self.client.objects.Activity(r[0])
        except:
            return self.client.objects.Activity()
    @property 
    async def total_tracked_chat(self) -> client_pre.objects.Activity:
        r = await (await self.client.execute("SELECT value FROM global WHERE name='total_tracked_chat'")).fetchone()

        if r:
            return self.client.objects.Activity(r[0])
    
    @property 
    async def total_messages(self) -> int: 
        return (await (await self.client.execute("SELECT SUM(amount) FROM chat_message_counts")).fetchone())[0]
    
    @property 
    async def linked_discords(self) -> list[tuple[client_pre.objects.Player, discord.Member]]:
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
    
    def set_town(self, name : str, value : client_pre.objects.Town):
        self.__towns[name] = value

    def set_player(self, name : str, value : client_pre.objects.Player):
        self.__players[name] = value  
    

    async def initialise_player_list(self):
        player_records = await (await self.client.execute("SELECT name, location, armor, health, nickname FROM players ORDER BY last DESC")).fetchall()

        for (name, location, armor, health, nickname) in player_records:
            p = self.client.objects.Player(self)

            p.name = str(name)
            p.location = Point(float(c) for c in location.split(","))
            p.armor = armor
            p.health = health
            p.nickname = nickname

            self.__players[p.name] = p

    