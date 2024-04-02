# RulerHelper

A discord bot for RulerCraft which tracks the server and shows many stats, allowing you to interact with the server from your discord

## Feature overview

- Get commands: get basic information for different objects on the server
- Compare commands: compare different nations, towns and players with each other. Supports up to 5 of each
- History commands: get historical information for players and towns
- Top commands: rank players, nations and towns by multiple different figures
- Distribution commands: rank towns within another nation by different attributes
- Notifications: get notified when someone enters your territory

## Commands

Too many to list here [try the bot](https://rctools.coolo2.repl.co/bot) to see

# Installing and running

## Requirements

- Modules in requirements.txt
- Python 3.8+

## Set-up

1. Create a file named `.env` with the following:
```
token="discord bot token"
base_url="Base URL for the map, probably https://map.rulercraft.com"
```
2. Open setup.py:
  - Change the IDs in the "Adjust these on first run" section.
  - Set refresh_commands to True in the "Adjust these when bot is updated" section
3. Ensure the bot profile has "server members intent" enabled on [discord developers](https://discord.com/developers)

## Running

- Run the `main.py` file to start the bot.
- After first run, make sure to set refresh_commands to False in `setup.py`