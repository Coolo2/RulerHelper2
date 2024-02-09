
import client 
import os
import setup as s
import discord 
import traceback
import dotenv 
import datetime 
import math

from funcs import graphs

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

    _refresh.start()
    _chat_refresh.start()

    for guild in bot.guilds:
        print(guild.name, guild.owner)

@tasks.loop(seconds=10)
async def _chat_refresh():
    try:
        await c.fetch_chat_messages()
    except Exception as e:
        print(e)

@tasks.loop(seconds=c.refresh_period)
async def _refresh():
    c.refresh_no += 1
    c.messages_sent = 0

    t = datetime.datetime.now()
    print("Refreshing", c.refresh_period)
    w = False
    try:
        w = await c.fetch_world()

        if w != False:
            await c.cull_db()
            await c.database.commit()

            try:
                await c.notifications.refresh(graphs)
            except Exception as e:
                await bot.get_channel(s.alert_channel).send(f"Notifications refresh error: \n```{e}``` {discord.utils.escape_markdown(traceback.format_exc())}"[:2000])
            
            await c.backup_db_if_not()
            
    except Exception as e:
        print(e)
        await bot.get_channel(s.alert_channel).send(f"Refresh error: \n```{e}``` {discord.utils.escape_markdown(traceback.format_exc())}"[:2000])

    c.last_refreshed = datetime.datetime.now()
    refresh_time = c.last_refreshed-t
    c.refresh_period = math.ceil((refresh_time.total_seconds()+1) / 10) * 10
    _refresh.change_interval(seconds=c.refresh_period)
    print("Refreshed", refresh_time)
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

    if s.refresh_commands:
        await bot.tree.sync()
        await bot.tree.sync(guild=s.mod_guild)
    
    await c.init_db(client.funcs.update_db(c))
    #await c.test()
    
    await c.world.initialise_player_list()

bot.setup_hook = setup_hook

bot.run(os.getenv("token"))
