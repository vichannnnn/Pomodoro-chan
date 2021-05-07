import discord
from discord.ext import commands
import sqlite3

conn = sqlite3.connect('colour.db', timeout=5.0)
c = conn.cursor()
conn.row_factory = sqlite3.Row

c.execute('''CREATE TABLE IF NOT EXISTS server (`server_id` INT PRIMARY KEY, `embed` TEXT) ''')


async def requestEmbedTemplate(ctx, description, author):
    embed = discord.Embed(description=f"{description}", colour=embedColour(ctx.guild.id))
    embed.set_footer(text=f"Requested by {author}", icon_url=author.avatar_url)
    return await ctx.send(embed=embed)

async def errorEmbedTemplate(ctx, description, author):
    embed = discord.Embed(description=f"❎ {description}", colour=embedColour(ctx.guild.id))
    embed.set_footer(text=f"Requested by {author}", icon_url=author.avatar_url)
    return await ctx.send(embed=embed)

async def successEmbedTemplate(ctx, description, author):
    embed = discord.Embed(description=f"☑️ {description}", colour=embedColour(ctx.guild.id))
    embed.set_footer(text=f"Requested by {author}", icon_url=author.avatar_url)
    return await ctx.send(embed=embed)

async def colourChange(ctx, colour):
    c.execute(f''' UPDATE server SET embed = ? WHERE server_id = ? ''', (colour, ctx.guild.id))
    conn.commit()
    return await requestEmbedTemplate(ctx, f"☑️ Embed colour successfully set to `{colour}` for `{ctx.message.guild}`.", ctx.message.author)

def embedColour(guild):
    for row in c.execute(f'SELECT embed FROM server WHERE server_id = {guild}'):
        colourEmbed = row[0]
        colourEmbedInt = int(colourEmbed, 16)
        return colourEmbedInt


def createGuildProfile(ID):
    c.execute(''' INSERT OR REPLACE INTO server VALUES (?, ?) ''', (ID, "0xdecaf0"))
    conn.commit()
    print(f"Added for {ID} into guild database.")


class ColourEmbed(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_guild_join(self, guild):

        guild_database = [row for row in c.execute('SELECT server_id FROM server')]

        if guild.id not in guild_database:
            createGuildProfile(guild.id)


    @commands.Cog.listener()
    async def on_ready(self):

        guild_database = [row[0] for row in c.execute('SELECT server_id FROM server')]

        for guild in self.bot.guilds:

            if guild.id not in guild_database:
                createGuildProfile(guild.id)




def setup(bot):
    bot.add_cog(ColourEmbed(bot))
