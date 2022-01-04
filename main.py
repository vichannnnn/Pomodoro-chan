import discord
from discord.ext import commands
from discord.ext.commands import has_permissions
import sqlite3
from datetime import datetime
import pytz
from os import listdir
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

def dmyConverter(seconds):
    secondsInDays = 60 * 60 * 24
    secondsInHours = 60 * 60
    secondsInMinutes = 60

    days = seconds // secondsInDays
    hours = (seconds - (days * secondsInDays)) // secondsInHours
    minutes = ((seconds - (days * secondsInDays)) - (hours * secondsInHours)) // secondsInMinutes
    remainingSeconds = seconds - (days * secondsInDays) - (hours * secondsInHours) - (
            minutes * secondsInMinutes)

    timeStatement = ""

    if days != 0:
        timeStatement += f"{round(days)} days,"
    if hours != 0:
        timeStatement += f" {round(hours)} hours,"
    if minutes != 0:
        timeStatement += f" {round(minutes)} minutes,"
    if remainingSeconds != 0:
        timeStatement += f" {round(remainingSeconds)} seconds"
    if timeStatement[-1] == ",":
        timeStatement = timeStatement[:-1]

    return timeStatement

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

owners = [344350545697439747, 624251187277070357]

class PersistentViewBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=determine_prefix, help_command=None,
            intents=discord.Intents(guilds=True, messages=True,
                                    members=True, guild_reactions=True,
                                    guild_messages=True, dm_messages=True, bans=True, voice_states=True
                                    ), slash_commands=True, owner_ids=set(owners)
        )
        for ext in [f'cogs.{file[:-3]}' for file in listdir('./cogs') if file.endswith('.py') and file[:3] != 'help']:
            self.load_extension(ext)

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

        @self.command()
        @commands.is_owner()
        async def load(ctx, extension_name: str):
            try:
                bot.load_extension(extension_name)

            except (AttributeError, ImportError) as e:
                await ctx.send(f"```py\n{type(e).__name__}: {str(e)}\n```")
                return
            await ctx.send(f"{extension_name} loaded.")

        @self.command()
        @commands.is_owner()
        async def unload(ctx, extension_name: str):
            bot.unload_extension(extension_name)
            await ctx.send(f"{extension_name} unloaded.")

        @self.command()
        @commands.is_owner()
        async def reload(ctx, cog: str):
            self.unload_extension(f'cogs.{cog}')
            self.load_extension(f'cogs.{cog}')
            await ctx.send(f'{cog} has been reloaded.')

        @self.command()
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

        @self.command()
        async def myprefix(ctx):
            c.execute(f'SELECT prefix FROM prefix WHERE guildID = {ctx.message.guild.id}')
            currentPrefix = c.fetchall()[0][0]

            name = bot.get_guild(ctx.message.guild.id)
            embed = discord.Embed(description=f"{name}'s Prefix currently is `{currentPrefix}`.")
            await ctx.send(embed=embed)

        @commands.Cog.listener()
        async def on_guild_join(guild):
            guildID_database = [row[0] for row in c.execute('SELECT guildID FROM prefix')]

            if guild.id not in guildID_database:
                c.execute(''' REPLACE INTO prefix VALUES (?, ?)''', (guild.id, defaultPrefix))
                conn.commit()
                prefixDictionary.update({guild.id: f"{defaultPrefix}"})
                print(f"Bot joined a new server: Created a prefix database for {guild.id}: {guild}")

        @bot.command()
        async def ping(ctx):
            embed = discord.Embed(description=f"Pong! Time taken: **{round(bot.latency, 3) * 1000} ms**!")
            await ctx.send(embed=embed)

        @commands.Cog.listener()
        async def on_command_error(ctx: commands.Context, error: commands.CommandError):
            if isinstance(error, commands.CommandOnCooldown):
                message = f"This command is on cooldown. Please try again after {dmyConverter(round(error.retry_after, 1))}"
            elif isinstance(error, commands.MissingPermissions):
                message = "You are missing the required permissions to run this command!"
            elif isinstance(error, commands.MissingRequiredArgument):
                message = f"Missing a required argument: {error.param}"
                ctx.command.reset_cooldown(ctx)
            elif isinstance(error, commands.ConversionError):
                message = str(error)
            else:
                message = "Oh no! Something went wrong while running the command!"
                print(error)
            await ctx.send(message, delete_after=5)
            await ctx.message.delete(delay=5)


bot = PersistentViewBot()
bot.load_extension("jishaku")
defaultPrefix = '.'

prefixDictionary = {}

for prefix in c.execute(f'SELECT guildID, prefix FROM prefix'):
    prefixDictionary.update({prefix[0]: f"{prefix[1]}"})

bot.remove_command('help')
try:
    bot.load_extension('help')
except Exception as e:
    exc = f'{type(e).__name__}: {e}'
    print(f'Failed to load help extension')
bot.run(yaml_data["Token"], reconnect=True)
