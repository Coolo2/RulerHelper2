
import client 
import os
import setup as s
import discord 
import traceback
import dotenv 
import datetime 
import math
import aiohttp

dotenv.load_dotenv()

from discord.ext import tasks, commands

intents = discord.Intents().default()
intents.members = True

bot = commands.Bot(commands.when_mentioned, intents=intents)

c = client.Client()

bot.client = c 
c.bot = bot

@bot.event 
async def on_ready():
    print(bot.user.name, "online")
    for guild in bot.guilds:
        if s.debug_mode: print(guild.name, guild.owner)

@bot.event
async def on_connect():
    if s.debug_mode: print("Connected")
    if not _short_refresh.is_running():
        _short_refresh.start()

@bot.event
async def on_resumed():
    if s.debug_mode: print("Resumed")
    if not _short_refresh.is_running():
        _short_refresh.start()

@tasks.loop(seconds=c.refresh_period["players"])
async def _short_refresh():
    # Refresh chat and player locations
    if not _refresh.is_running():
        _refresh.start()
    d = datetime.datetime.now()
    if c.refresh_no > 0:
        try:
            sh = await c.fetch_short()

            if sh != False:
                try:
                    await c.notifications.refresh()
                except Exception as e:
                    await bot.get_channel(s.alert_channel).send(f"Notifications refresh error: \n```{e}``` {discord.utils.escape_markdown(traceback.format_exc())}"[:2000])
        except Exception as e:
            print(e)
            if type(e) not in (aiohttp.ClientOSError, TimeoutError):
                await bot.get_channel(s.alert_channel).send(f"Short refresh error: \n```{e}``` {discord.utils.escape_markdown(traceback.format_exc())}"[:2000])
            else:
                await bot.get_channel(s.alert_channel).send("Short Refresh TimeoutError")
    
    refresh_time = datetime.datetime.now()-d
    c.refresh_period["players"] = math.ceil((refresh_time.total_seconds()+1) / 10) * 10
    c.last_refreshed["players"] = datetime.datetime.now()
    _short_refresh.change_interval(seconds=c.refresh_period["players"])

@tasks.loop(seconds=c.refresh_period["map"])
async def _refresh():

    # Refresh towns/nations (map)
    
    c.refresh_no += 1
    c.messages_sent = 0
    refresh_time = None

    t = datetime.datetime.now()
    if s.debug_mode: print("Refreshing", c.refresh_period["map"])
    w = False
    try:
        w = await c.fetch_world()

        if w != False:
            dbcull = await client.cull.cull_db(c)
            await c.database.connection.commit()
            
            await c.backup_db_if_not()

            if dbcull != False:
                c.last_refreshed["map"] = datetime.datetime.now()
                refresh_time = c.last_refreshed["map"]-t
                c.refresh_period["map"] = math.ceil((refresh_time.total_seconds()+1) / 10) * 10
                _refresh.change_interval(seconds=c.refresh_period["map"])
            
    except Exception as e:
        print(e)
        if type(e) not in (aiohttp.ClientOSError, TimeoutError):
            await bot.get_channel(s.alert_channel).send(f"Refresh error: \n```{e}``` {discord.utils.escape_markdown(traceback.format_exc())}"[:2000])
        else:
            await bot.get_channel(s.alert_channel).send("Refresh TimeoutError")

    
    if s.debug_mode: print("Refreshed", refresh_time)
    await bot.change_presence(activity=discord.CustomActivity(name=f"{c.world.player_count} online | v{s.version} | /changelog"))

extensions = [file.replace(".py", "") for file in os.listdir('./cmds') if file.endswith(".py")]

async def setup_hook():
    if s.commands:
        for extension in extensions:
            if s.PRODUCTION_MODE and extension == "test":
                continue
            await bot.load_extension(f"cmds.{extension}")
        await bot.load_extension("cogs.events")
    
    await bot.load_extension("cogs.errors")

    if s.refresh_commands and s.commands:
        await bot.tree.sync()
        await bot.tree.sync(guild=s.mod_guild)
    
    await c.database.initialise(client.migrate.upgrade_db(c))
    #await c.test()
    
    await c.world.initialise_player_list()

bot.setup_hook = setup_hook

bot.run(os.getenv("token"))
