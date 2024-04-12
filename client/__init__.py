
import aiohttp
from client import errors, image_generator, notifications, objects, funcs, refresh, database
from client.continents import continents

import datetime
from client.db_mgmt import cull, merge, migrate
from client.objects import properties
import setup as s

from discord.ext import commands
import aiosqlite

import shutil
import os


class Client():
    def __init__(self):

        self.refresh_no : int = 0
        self.current_refresh_started : datetime.datetime = None
        self.dynmap_update_timestamp = 0
        self.messages_sent = 0
        
        self.session : aiohttp.ClientSession= None
        self.database = database.RawDatabase(self, "towny.db")
        self.bot : commands.Bot = None
        self.url = "https://map.rulercraft.com"

        self.refresh_period : dict[str, int] = s.default_refresh_period
        self.last_refreshed : dict[str, datetime.datetime] = {k:None for k in s.default_refresh_period}
        self.world = objects.World(self) 
        self.notifications = notifications.Notifications(self)

        self.image_generator = image_generator.ImageGenerator(self)

        
    
    errors = errors
    objects = objects 
    continents = continents
    funcs = funcs

    merge_objects = merge.merge_objects

    def add_execute(self):
        self.execute = self.database.connection.execute
        
    @property 
    async def tracking_footer(self):
        return f"Tracked: game for {(await self.world.total_tracked).str_no_timestamp(False)}, chat for {(await self.world.total_tracked_chat).str_no_timestamp(False)}"
    
    @property 
    async def db_version(self) -> int:

        val = await (await self.execute("SELECT value FROM global WHERE name='db_version'")).fetchone()
        return val[0] if val else 0
    
    @property 
    async def tracking_started(self) -> datetime.date:
        r = await (await self.execute("SELECT date FROM town_history ORDER BY date ASC LIMIT 1")).fetchone()
        return r[0]

    async def create_session(self):
        if not self.session:
            self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10))

    async def fetch_world(self):

        await self.create_session()

        map_data = await self.session.get(f"{s.refresh_map_url}/tiles/_markers_/marker_RulerEarth.json")

        if map_data.status == 502:
            return False

        await refresh.main_refresh(self.world, map_data.content)


    async def fetch_short(self):
        
        await self.create_session()

        r = await self.session.get(f"{s.refresh_map_url}/up/world/RulerEarth/{self.dynmap_update_timestamp+1}")

        if r.status == 502:
            return False

        await refresh.refresh_short(self.world, r.content)
        
                            
    
    async def backup_db_if_not(self):
        epoch = datetime.date(2022, 1, 1)
        td = datetime.date.today()
        backup_name = f"backups/towny_{(td-epoch).days}_{td.year}_{td.month}_{td.day}_v{await self.db_version}.db"
        if not os.path.exists(backup_name):
            shutil.copyfile("towny.db", backup_name)
    
