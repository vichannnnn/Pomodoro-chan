import discord
import math
from discord.ext import commands
from discord.ext.commands import has_permissions
import sqlite3
from datetime import datetime
import pytz
import traceback
import os
import platform
import yaml

now = int(datetime.now(pytz.timezone("Singapore")).timestamp())

conn = sqlite3.connect('prefix.db', timeout=5.0)
c = conn.cursor()
conn.row_factory = sqlite3.Row

help_extensions = ['help']

c.execute('''CREATE TABLE IF NOT EXISTS prefix (
        `guildID` INT PRIMARY KEY,
        `prefix` TEXT)''')

with open("authentication.yml", "r", encoding="utf8") as stream:
    yaml_data = yaml.safe_load(stream)

async def determine_prefix(bot, message):
    try:
        currentPrefix = prefixDictionary[message.guild.id]
        return commands.when_mentioned_or(currentPrefix)(bot, message)
    except KeyError:
        c.execute(''' REPLACE INTO prefix VALUES (?, ?)''', (message.guild.id, defaultPrefix))
        conn.commit()
        prefixDictionary.update({message.guild.id: defaultPrefix})
        print(f"Error Detected: Created a prefix database for {message.guild.id}: {message.guild}")
        return commands.when_mentioned_or(defaultPrefix)(bot, message)
    except AttributeError:
        print("DM Error has occurred on user-end.")


class PersistentViewBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=determine_prefix, help_command=None,
            intents=discord.Intents(guilds=True, messages=True,
                                    members=True, guild_reactions=True,
                                    guild_messages=True, dm_messages=True, bans=True, voice_states=True
                                    ), slash_commands=True
        )

    async def on_ready(self):
        print(f"Logged in as {self.user} (ID: {self.user.id})")
        print(f"{str(bot.user)} has connected to Discord!")
        print(f"Current Discord Version: {discord.__version__}")
        print(f"Current Python Version: {platform.python_version()}")
        print(f"Current Sqlite3 Version: {sqlite3.sqlite_version}")
        print(f"Number of servers currently connected to {str(bot.user)}:")
        print(len([s for s in bot.guilds]))
        print("Number of players currently connected to Bot:")
        print(sum(guild.member_count for guild in bot.guilds))

        guild_id_database = [row[0] for row in c.execute('SELECT guildID FROM prefix')]

        async for guild in bot.fetch_guilds():
            if guild.id not in guild_id_database:
                c.execute(''' REPLACE INTO prefix VALUES (?, ?)''', (guild.id, defaultPrefix))
                conn.commit()
                prefixDictionary.update({guild.id: defaultPrefix})
                print(f"Bot started up: Created a prefix database for {guild.id}: {guild}")


bot = PersistentViewBot()

bot.load_extension("jishaku")
defaultPrefix = '.'
print(bot.slash_commands)

for cog in os.listdir("cogs"):

    try:
        if cog == '__pycache__':
            continue

        else:
            newCog = cog.replace(".py", "")
            bot.load_extension(f"cogs.{newCog}")
            print(f'{cog} successfully loaded!')

    except Exception as e:
        exc = f'{type(e).__name__}: {e}'
        print(f'Failed to load extension {cog}\n{exc}')
        traceback.print_exc()


@bot.command(help="Loads an extension. Bot Owner only!")
@commands.is_owner()
async def load(ctx, extension_name: str):
    try:

        bot.load_extension(extension_name)

    except (AttributeError, ImportError) as e:

        await ctx.send(f"```py\n{type(e).__name__}: {str(e)}\n```")
        return

    await ctx.send(f"{extension_name} loaded.")


@bot.command(help="Unloads an extension. Bot Owner only!")
@commands.is_owner()
async def unload(ctx, extension_name: str):
    bot.unload_extension(extension_name)
    await ctx.send(f"{extension_name} unloaded.")


@bot.command()
@has_permissions(manage_messages=True)
async def setprefix(ctx, new):
    guild = ctx.message.guild.id
    name = bot.get_guild(guild)

    for key, value in c.execute('SELECT guildID, prefix FROM prefix'):

        if key == guild:
            c.execute(''' UPDATE prefix SET prefix = ? WHERE guildID = ? ''', (new, guild))
            conn.commit()
            prefixDictionary.update({ctx.guild.id: f"{new}"})

            embed = discord.Embed(description=f"{name}'s Prefix has now changed to `{new}`.")
            await ctx.send(embed=embed)


@bot.command()
async def myprefix(ctx):
    c.execute(f'SELECT prefix FROM prefix WHERE guildID = {ctx.message.guild.id}')
    currentPrefix = c.fetchall()[0][0]

    name = bot.get_guild(ctx.message.guild.id)
    embed = discord.Embed(description=f"{name}'s Prefix currently is `{currentPrefix}`.")
    await ctx.send(embed=embed)




prefixDictionary = {}

for prefix in c.execute(f'SELECT guildID, prefix FROM prefix'):
    prefixDictionary.update({prefix[0]: f"{prefix[1]}"})


@bot.event
async def on_guild_join(guild):
    guildID_database = [row[0] for row in c.execute('SELECT guildID FROM prefix')]

    if guild.id not in guildID_database:
        c.execute(''' REPLACE INTO prefix VALUES (?, ?)''', (guild.id, defaultPrefix))
        conn.commit()
        prefixDictionary.update({guild.id: f"{defaultPrefix}"})
        print(f"Bot joined a new server: Created a prefix database for {guild.id}: {guild}")


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):

        seconds = error.retry_after
        minutes = seconds / 60
        hours = seconds / 3600

        if ctx.message.author.id == 624251187277070357:
            await ctx.reinvoke()
            return

        if seconds / 60 < 1:
            embed = discord.Embed(
                description=f'You\'re using this command too often! Try again in {str(int(seconds))} seconds!')
            await ctx.send(embed=embed)
            return

        elif minutes / 60 < 1:
            embed = discord.Embed(
                description=f'You\'re using this command too often! Try again in {math.floor(minutes)} minutes and {(int(seconds) - math.floor(minutes) * 60)} seconds!')
            await ctx.send(embed=embed)
            return

        else:
            embed = discord.Embed(
                description=f'You\'re using this command too often! Try again in {math.floor(hours)} hours, {(int(minutes) - math.floor(hours) * 60)} minutes, {(int(seconds) - math.floor(minutes) * 60)} seconds!')
            await ctx.send(embed=embed)
            return

    if isinstance(error, commands.CheckFailure):
        embed = discord.Embed(description='You do not have the permission to do this.')
        await ctx.send(embed=embed)
        return

    if isinstance(error, commands.MissingRequiredArgument):
        embed = discord.Embed(description='Missing arguments on your command. Please check and retry again.')
        await ctx.send(embed=embed)
        return

    if isinstance(error, commands.CommandNotFound):
        print("'Command Not Found' Error has been triggered from user-end.")
        return

    if isinstance(error, commands.MissingPermissions):
        print("'Missing Permissions' Error has been triggered from user-end.")
        return

    raise error


@bot.command()
async def ping(ctx):
    embed = discord.Embed(description=f"Pong! Time taken: **{round(bot.latency, 3) * 1000} ms**!")
    await ctx.send(embed=embed)


bot.remove_command('help')

if __name__ == "__main__":
    for extension in help_extensions:
        try:
            bot.load_extension(extension)
        except Exception as e:
            exc = f'{type(e).__name__}: {e}'
            print(f'Failed to load extension {extension}\n{exc}')

bot.run(yaml_data["Token"], reconnect=True)
