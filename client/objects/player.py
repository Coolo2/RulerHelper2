
from __future__ import annotations
import typing
if typing.TYPE_CHECKING:
    import client as client_pre

import datetime
from shapely.geometry import Point
import re

import setup 

import discord

class Player():
    def __init__(self, world : client_pre.objects.World):
        self.__world = world 

        self.__skin_identifier : str = None

        self.name : str = None
        self.location = None
        self.armor : int = None
        self.health : int = None
        self.online = False
        self.nickname : str = None
        self.residence : client_pre.objects.Town = None
        self.bank : float = None

        self.search_boost = 0

        self._town_cache = None

    async def activity_in(self, town : client_pre.objects.Town) -> client_pre.objects.Activity:
        r = await (await self.__world.client.execute("SELECT duration, last FROM visited_towns WHERE player=? AND town=?", (self.name, town.name))).fetchone()

        return self.__world.client.objects.Activity.from_record(r)
    
    @property 
    def is_bedrock(self):
        return True if "." in self.name else False
    
    async def __fetch_skin_identifier(self):
        if self.is_bedrock:
            try:
                user = await self.__world.client.session.get(f"https://api.geysermc.org/v2/xbox/xuid/{self.name.replace('.', '').replace('_', '%20')}")
                user_json : dict = await user.json()
                if user_json.get("xuid"):
                    texture = await self.__world.client.session.get(f"https://api.geysermc.org/v2/skin/{user_json['xuid']}")
                    self.__skin_identifier = (await texture.json())['texture_id']
            except Exception as e:
                print(e)
        else:
            self.__skin_identifier = self.name 
        
        return self.__skin_identifier
    
    @property 
    async def skin_identifier(self):
        if not self.__skin_identifier:
            await self.__fetch_skin_identifier()
        return self.__skin_identifier

    @property 
    def is_mayor(self):
        return True if self.residence and self.residence.mayor == self else False

    @property 
    async def face_url(self):
        return f"https://mc-heads.net/avatar/{await self.skin_identifier}/{setup.face_size}" 
    
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

            r1 = await (await self.__world.client.execute(f"""SELECT {command['attribute']} FROM players WHERE name=?""", (self.name,))).fetchone()
            if r1 and r1 != (None,):
                r2 = await (await self.__world.client.execute(f"""SELECT COUNT(*) FROM players WHERE {command['attribute']}>?""", (r1[0],))).fetchone()
                ranking = r2[0]
                if command.get("reverse_notable"): ranking = len(self.__world.players)-ranking-1
                notable = True if ranking <= len(self.__world.players)/10 else False
                rankings[command.get("name") or command.get("attribute")] = [r1[0], ranking+1, notable]
        
        return dict(sorted(rankings.items(), key=lambda x: x[1][1]))

    @property 
    def spawn(self) -> Point: return self.location

    @property 
    def name_formatted(self):
        """Helper"""
        return self.name

    @property 
    def town(self) -> client_pre.objects.Town:
        nearby_town = None
        if self._town_cache:
            return self._town_cache

        for town in self.__world.towns:
            if town.is_point_in_town(self.location):
                nearby_town = town

        self._town_cache = nearby_town
        return nearby_town

    @property 
    async def activity(self) -> client_pre.objects.Activity:
        r = await (await self.__world.client.execute("SELECT duration, last FROM activity WHERE object_type='player' AND object_name=?", (self.name,))).fetchone()

        return self.__world.client.objects.Activity.from_record(r)
    
    @property 
    async def visited_towns(self) -> list[client_pre.objects.Activity]:
        rs = await (await self.__world.client.execute("SELECT town, duration, last FROM visited_towns WHERE player=? GROUP BY town ORDER BY duration DESC", (self.name,))).fetchall()

        return [self.__world.client.objects.Activity(r[1], r[2], town=self.__world.get_town(r[0], False) or r[0]) for r in rs]
    
    @property 
    async def visited_nations(self) -> list[client_pre.objects.Activity]:
        rs = await (await self.__world.client.execute("SELECT nation, duration, last FROM visited_nations WHERE player=? GROUP BY nation ORDER BY duration DESC", (self.name,))).fetchall()

        return [self.__world.client.objects.Activity(r[1], r[2], nation=self.__world.get_nation(r[0], False) or r[0]) for r in rs]
    
    @property 
    async def first_seen_in_history(self) -> datetime.date:
        r = await (await self.__world.client.execute("SELECT date FROM player_history WHERE player=? ORDER BY date ASC LIMIT 1", (self.name,))).fetchone()
        return r[0]
    
    @property 
    async def total_visited_towns(self) -> list[client_pre.objects.Town]:
        return (await (await self.__world.client.execute("SELECT COUNT(*) FROM visited_towns WHERE player=?", (self.name,))).fetchone())[0]
    @property 
    async def total_visited_nations(self) -> list[client_pre.objects.Town]:
        return (await (await self.__world.client.execute("SELECT COUNT(*) FROM visited_nations WHERE player=?", (self.name,))).fetchone())[0]
    
    @property 
    async def total_mentions(self) -> tuple[int, datetime.datetime]: 
        r = await (await self.__world.client.execute("SELECT amount, last FROM chat_mentions WHERE object_type='player' AND object_name=?", (self.name,))).fetchone()
        if r:
            return r
        return 0, None
    
    @property 
    async def total_messages(self) -> tuple[int, datetime.datetime]: 
        r = await (await self.__world.client.execute("SELECT amount, last FROM chat_message_counts WHERE player=?", (self.name,))).fetchone()
        if r: 
            return r
        return 0, None

    @property
    async def message_count(self): return (await self.total_messages)[0]
    @property
    async def mention_count(self): return (await self.total_mentions)[0]
    
    async def get_activity_today(self, activity : client_pre.objects.Activity = None):
        twodays_records = await (await self.__world.client.execute("SELECT duration FROM player_history WHERE player=? ORDER BY duration DESC LIMIT 2", (self.name,))).fetchall()

        a = activity
        if not activity:
            a = await self.activity
        if len(twodays_records) == 1:
            return a
        yesterday = twodays_records[1]
        return self.__world.client.objects.Activity(a.total - yesterday[0], last=a.last)
        
    async def set_flag(self, flag_name : str, flag_value):
        await self.__world.client.funcs.set_flag(self.__world.client, "player", self.name, flag_name, flag_value)

    @property
    async def flags(self) -> dict:
        rs = await (await self.__world.client.execute("SELECT name, value FROM flags WHERE object_type='player' AND object_name=?", (self.name,))).fetchall()
        d = {}
        for r in rs:
            if r[1]:
                d[r[0]] = r[1]
        return d

    def update(self, data : dict):
        
        self.name : str = data["account"]
        self.location = Point((data["x"], data["y"], data["z"]))
        self.armor : int = data["armor"]
        self.health : int = data["health"]
        self.online = True
        self.nickname = data["name"]

        self._town_cache = None
        

    @property 
    def donator(self):
        return True if self.nickname and (self.name != self.nickname and "color:#ffffff" not in self.nickname and "color:#ff5555" not in self.nickname) else False if self.nickname else None
    
    @property 
    def pvp(self):
        return True if self.nickname and "color:#ff5555" in self.nickname else False if self.nickname else None
    
    @property 
    def nickname_no_tags(self):
        return re.sub(r'(?!<)[^<]*(?=>)', '', self.nickname).replace("<", "").replace(">", "") if self.nickname else None

    def __eq__(self, other):
        return self.name == (other.name if hasattr(other, "name") else other)

    def __str__(self):
        return self.name