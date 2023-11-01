
import client 
import os
import setup as s
import discord 
import traceback
import dotenv 
import datetime 

dotenv.load_dotenv()

import funcs
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

@tasks.loop(seconds=c.refresh_period)
async def _refresh():
    t = datetime.datetime.now()
    print("Refreshing")
    w = False
    try:
        w = await c.fetch_world()

        if w != False:
        
            await c.cull_db()
            await c.database.commit()

            try:
                await c.notifications.refresh()
            except Exception as e:
                await bot.get_channel(s.alert_channel).send(f"Notifications refresh error: \n```{e}``` {discord.utils.escape_markdown(traceback.format_exc())}"[:2000])
            
            await c.backup_db_if_not()
    except Exception as e:
        print(e)
        await bot.get_channel(s.alert_channel).send(f"Refresh error: \n```{e}``` {discord.utils.escape_markdown(traceback.format_exc())}"[:2000])

    print("Refreshed", datetime.datetime.now()-t)
    #await funcs.activity_to_json(c)
    await bot.change_presence(activity=discord.CustomActivity(name=f"{c.world.player_count} online | v{s.version} | /changelog"))

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
    
    await c.init_db()
    # Add column if needed. WIll get errors, just rerun
    #await c.database.connection.execute("ALTER TABLE players ADD donator integer;")
    await c.world.initialise_player_list()
    #await c.fetch_world()
    
    _refresh.start()

bot.setup_hook = setup_hook


bot.run(os.getenv("token"))

