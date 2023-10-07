
import aiohttp
from client import object
import json

import datetime
import setup as s

import db
from db import wrapper

from discord.ext import commands

from client import errors

class Client():
    def __init__(self):
        
        self.session : aiohttp.ClientSession= None
        self.database = db.Database("towny.db", auto_commit=False)
        self.bot : commands.Bot = None
        self.url = s.map_url

        self.towns_table : wrapper.Table = []
        self.players_table : wrapper.Table = []
        self.visited_towns_table : wrapper.Table = []

        self.refresh_period = s.refresh_period
        self.world = object.World(self) 

    async def init_db(self):
        await self.database.connect()

        self.global_table = await self.database.create_or_get_table(
            db.CreationTable(
                "global",
                [
                    db.CreationAttribute("name", db.types.String),
                    db.CreationAttribute("value", db.types.Any)
                ]
            )
        )

        self.towns_table = await self.database.create_or_get_table(
            db.CreationTable(
                "towns",
                [
                    db.CreationAttribute("name", db.types.String, primary_key=True),
                    db.CreationAttribute("flag_url", db.types.String),
                    db.CreationAttribute("nation", db.types.String),
                    db.CreationAttribute("religion", db.types.String),
                    db.CreationAttribute("culture", db.types.String),
                    db.CreationAttribute("mayor", db.types.String),
                    db.CreationAttribute("resident_count", db.types.Int),
                    db.CreationAttribute("founded_date", db.types.Date),
                    db.CreationAttribute("resident_tax", db.types.Float),
                    db.CreationAttribute("bank", db.types.Float),
                    db.CreationAttribute("public", db.types.Int),
                    db.CreationAttribute("peaceful", db.types.Int),
                    db.CreationAttribute("area", db.types.Int),
                    db.CreationAttribute("last_seen", db.types.Datetime),
                    db.CreationAttribute("duration", db.types.Int),
                    db.CreationAttribute("last", db.types.Datetime)
                ]
            )
        )

        self.players_table = await self.database.create_or_get_table(
            db.CreationTable(
                "players",
                [
                    db.CreationAttribute("name", db.types.String, primary_key=True),
                    db.CreationAttribute("location", db.types.String),
                    db.CreationAttribute("town", db.types.String),
                    db.CreationAttribute("armor", db.types.Int),
                    db.CreationAttribute("health", db.types.Int),
                    db.CreationAttribute("duration", db.types.Int),
                    db.CreationAttribute("last", db.types.Datetime)
                ]
            )
        )

        self.objects_table = await self.database.create_or_get_table(
            db.CreationTable(
                "objects",
                [
                    db.CreationAttribute("type", db.types.String),
                    db.CreationAttribute("name", db.types.String),
                    db.CreationAttribute("towns", db.types.Int),
                    db.CreationAttribute("town_balance", db.types.Float),
                    db.CreationAttribute("residents", db.types.Int),
                    db.CreationAttribute("area", db.types.Int),
                    db.CreationAttribute("last", db.types.Datetime)
                ]
            )
        )

        self.visited_towns_table = await self.database.create_or_get_table(
            db.CreationTable(
                "visited_towns",
                [
                    db.CreationAttribute("player", db.types.String),
                    db.CreationAttribute("town", db.types.String),
                    db.CreationAttribute("duration", db.types.Int),
                    db.CreationAttribute("last", db.types.Datetime)
                ]
            )
        )

        self.town_history_table = await self.database.create_or_get_table(
            db.CreationTable(
                "town_history",
                [
                    db.CreationAttribute("town", db.types.String),
                    db.CreationAttribute("date", db.types.Date),
                    db.CreationAttribute("nation", db.types.String),
                    db.CreationAttribute("religion", db.types.String),
                    db.CreationAttribute("culture", db.types.String),
                    db.CreationAttribute("mayor", db.types.String),
                    db.CreationAttribute("resident_count", db.types.Int),
                    db.CreationAttribute("resident_tax", db.types.Float),
                    db.CreationAttribute("bank", db.types.Float),
                    db.CreationAttribute("public", db.types.Int),
                    db.CreationAttribute("peaceful", db.types.Int),
                    db.CreationAttribute("area", db.types.Int),
                    db.CreationAttribute("duration", db.types.Int)
                ]
            )
        )

        self.player_history_table = await self.database.create_or_get_table(
            db.CreationTable(
                "player_history",
                [
                    db.CreationAttribute("player", db.types.String),
                    db.CreationAttribute("date", db.types.Date),
                    db.CreationAttribute("duration", db.types.Int)
                ]
            )
        )

        self.nation_history_table = await self.database.create_or_get_table(
            db.CreationTable(
                "nation_history",
                [
                    db.CreationAttribute("nation", db.types.String),
                    db.CreationAttribute("date", db.types.Date),
                    db.CreationAttribute("towns", db.types.Int),
                    db.CreationAttribute("town_balance", db.types.Float),
                    db.CreationAttribute("residents", db.types.Int),
                    db.CreationAttribute("capital", db.types.String),
                    db.CreationAttribute("leader", db.types.String),
                    db.CreationAttribute("area", db.types.Int)
                ]
            )
        )

        self.global_history_table = await self.database.create_or_get_table(
            db.CreationTable(
                "global_history",
                [
                    db.CreationAttribute("date", db.types.Date),
                    db.CreationAttribute("towns", db.types.Int),
                    db.CreationAttribute("residents", db.types.Int),
                    db.CreationAttribute("nations", db.types.Int),
                    db.CreationAttribute("town_value", db.types.Float),
                    db.CreationAttribute("area", db.types.Int),
                    db.CreationAttribute("known_players", db.types.Int)
                ]
            )
        )

        self.object_history_table = await self.database.create_or_get_table(
            db.CreationTable(
                "object_history",
                [
                    db.CreationAttribute("date", db.types.Date),
                    db.CreationAttribute("type", db.types.String),
                    db.CreationAttribute("object", db.types.String),
                    db.CreationAttribute("towns", db.types.Int),
                    db.CreationAttribute("town_balance", db.types.Float),
                    db.CreationAttribute("residents", db.types.Int),
                    db.CreationAttribute("area", db.types.Int)
                ]
            )
        )

        self.flags_table = await self.database.create_or_get_table(
            db.CreationTable(
                "flags",
                [
                    db.CreationAttribute("object_type", db.types.String),
                    db.CreationAttribute("object_name", db.types.String),
                    db.CreationAttribute("name", db.types.String),
                    db.CreationAttribute("value", db.types.Any)
                ]
            )
        )

    async def create_session(self):
        if not self.session:
            self.session = aiohttp.ClientSession()


    async def fetch_world(self):
        

        await self.create_session()

        r = await self.session.get(f"{self.url}/up/world/RulerEarth/0")
        

        await self.world.refresh(r.content)
    
    async def cull_db(self):

        await self.town_history_table.delete_records([db.CreationCondition("date", datetime.date.today()-s.cull_history_from, "<")])
        await self.player_history_table.delete_records([db.CreationCondition("date", datetime.date.today()-s.cull_history_from, "<")])
        await self.global_history_table.delete_records([db.CreationCondition("date", datetime.date.today()-s.cull_history_from, "<")])
        await self.nation_history_table.delete_records([db.CreationCondition("date", datetime.date.today()-s.cull_history_from, "<")])
        await self.visited_towns_table.delete_records([db.CreationCondition("last", datetime.date.today()-s.cull_history_from, "<")])

        await self.players_table.delete_records([db.CreationCondition("last", datetime.datetime.now()-s.cull_players_from, "<")])
        await self.towns_table.delete_records([db.CreationCondition("last_seen", datetime.datetime.now()-s.cull_objects_after, "<")])
        await self.objects_table.delete_records([db.CreationCondition("last", datetime.datetime.now()-s.cull_objects_after, "<")])

        await self.flags_table.delete_records([db.CreationCondition("object_type", "nation"), db.CreationField.external_query(self.objects_table, "object_name", db.CreationCondition("type", "nation"), operator="NOT IN")])

        for player in self.world.players.copy():
            if not await player.exists_in_db:
                self.world._remove_player(player.name)
        for town in self.world.towns.copy():
            if not await town.exists_in_db:
                self.world._remove_town(town.name)
        for nation in self.world.nations.copy():
            if not await nation.exists_in_db:
                self.world._remove_nation(nation.name)
        