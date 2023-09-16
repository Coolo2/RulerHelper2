
import client 
import os
import setup as s
import discord 

import dotenv 

dotenv.load_dotenv()

from discord import app_commands
from discord.ext import tasks, commands


intents = discord.Intents()
intents.members = True

bot = commands.Bot(".", intents=intents)

c = client.Client()

bot.client = c 
client.bot = bot

@bot.event 
async def on_ready():
    print(bot.user.name, "online")

    await c.init_db()
    await c.world.initialise_player_list()
    _refresh.start()

    

@tasks.loop(seconds=c.refresh_period)
async def _refresh():
    
    print("Refreshing")
    await c.fetch_world()
    await c.cull_db()

    await c.database.commit()
    print("Refreshed")

    await bot.change_presence(activity=discord.CustomActivity(name=f"{c.world.player_count} online"))

extensions = [file.replace(".py", "") for file in os.listdir('./cmds') if file.endswith(".py")]

async def setup_hook():
    for extension in extensions:
        await bot.load_extension(f"cmds.{extension}")
    
    if s.PRODUCTION_MODE:
        await bot.load_extension("cogs.errors")

    if s.refresh_commands:
        await bot.tree.sync()

bot.setup_hook = setup_hook


bot.run(os.getenv("token"))

