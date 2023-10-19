
import client 
import os
import setup as s
import discord 
import traceback
import dotenv 
import datetime 

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
    

    await c.init_db()
    await c.world.initialise_player_list()
    #await c.fetch_world()
    
    
    _refresh.start()

@tasks.loop(seconds=c.refresh_period)
async def _refresh():
    t = datetime.datetime.now()
    print("Refreshing")
    try:
        await c.fetch_world()
        
        await c.cull_db()
        await c.database.commit()
    except Exception as e:
        print(e)
        await bot.get_channel(s.alert_channel).send(f"Refresh error: \n```{e}``` {discord.utils.escape_markdown(traceback.format_exc())}"[:2000])
    
    try:
        await c.notifications.refresh()
    except Exception as e:
        await bot.get_channel(s.alert_channel).send(f"Notifications refresh error: \n```{e}``` {discord.utils.escape_markdown(traceback.format_exc())}"[:2000])

    print("Refreshed", datetime.datetime.now()-t)

    await bot.change_presence(activity=discord.CustomActivity(name=f"{c.world.player_count} online | v{s.version}"))

extensions = [file.replace(".py", "") for file in os.listdir('./cmds') if file.endswith(".py")]

async def setup_hook():
    if s.commands:
        for extension in extensions:
            await bot.load_extension(f"cmds.{extension}")
    
    if s.PRODUCTION_MODE:
        await bot.load_extension("cogs.errors")

    if s.refresh_commands:
        await bot.tree.sync()
        await bot.tree.sync(guild=s.mod_guild)

bot.setup_hook = setup_hook


bot.run(os.getenv("token"))

