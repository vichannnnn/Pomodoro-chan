from discord.ext import commands
from discord.ext.commands import has_permissions
import cogs.colourEmbed
import traceback
import sqlite3
import discord
import itertools

conn = sqlite3.connect('profile.db', timeout=5.0)
c = conn.cursor()
conn.row_factory = sqlite3.Row

c.execute('CREATE TABLE IF NOT EXISTS profile '
          '('
          'user_id INT PRIMARY KEY, '
          'pomodoroCycle INT,'
          'miniCycle INT,'
          'focusTime INT'
          ')')

def profileCreate(id):
    try:
        c.execute('''INSERT INTO profile VALUES (?, ?, ?, ?)''', (id, 0, 0, 0))
        conn.commit()
    except:
        traceback.print_exc()


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
        timeStatement += f"{round(days)} days, "
    if hours != 0:
        timeStatement += f"{round(hours)} hours, "
    if minutes != 0:
        timeStatement += f"{round(minutes)} minutes, "
    if remainingSeconds != 0:
        timeStatement += f"{round(remainingSeconds)} seconds"
    if timeStatement[-2:] == ", ":
        timeStatement = timeStatement[:-2]

    return timeStatement


class profileCogs(commands.Cog, name="📑 Pomodoro & Focus Profile"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(description="lb**\n\nShows the leaderboard for the longest focus mode and pomodoro completion users!")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def lb(self, ctx):

        leaderboardUsers = [[r[0], r[1], r[2], r[3]] for r in c.execute('SELECT * FROM profile')]

        guildMemberList = [member.id for member in ctx.guild.members]
        guildLeaderboardUsers = [[item[0], item[1], item[2], item[3]] for item in leaderboardUsers if item[0] in guildMemberList]

        def sortSecond(val):
            return val[1]

        guildLeaderboardUsers.sort(key=sortSecond, reverse=True)
        topFive = [item for item in guildLeaderboardUsers[0:5] if item[0] in guildMemberList and item[1]]
        embed = discord.Embed(title=f"{ctx.guild}", description="Below are the top five Pomodoro users.")
        embed.set_author(name="Study Leaderboard")
        embed.set_thumbnail(url=ctx.guild.icon_url)

        i = 0
        medals = ['🥇', '🥈', '🥉']

        for item in topFive:

            if i > 2:

                member = ctx.guild.get_member(item[0])

                desc = f"Pomodoro Completed: `{item[1]} full cycle(s)`\n"
                desc += f"Pomodoro Completed: `{item[2]} mini cycle(s)`\n"
                if not item[3]:
                    desc += f"Focus Duration: `None`"
                else:
                    desc += f"Focus Duration: `{dmyConverter(item[3])}`"
                embed.add_field(name=f"**{i + 1}.** {member.name}", value=desc, inline=False)
                i += 1
                continue

            member = ctx.guild.get_member(item[0])

            desc = f"Pomodoro Completed: `{item[1]} full cycle(s)`\n"
            desc += f"Pomodoro Completed: `{item[2]} mini cycle(s)`\n"
            if not item[3]:
                desc += f"Focus Duration: `None`"
            else:
                desc += f"Focus Duration: `{dmyConverter(item[3])}`"
            embed.add_field(name=f"{medals[i]} {member.name}", value=desc, inline=False)
            i += 1

        await ctx.send(embed=embed)

    @commands.command(description="p [user mention (optional)]**\n\nShows a user's (or your own) profile.", aliases=['p'])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def profile(self, ctx, user: discord.Member = None):

        if user == None:
            actualUser = ctx.author

        else:
            actualUser = user

        pCycle, miniCycle, focusTime = [[r[0], r[1], r[2]] for r in
                             c.execute('SELECT pomodoroCycle, miniCycle, focusTime FROM profile WHERE user_id = ? ', (actualUser.id, ))][0]

        embed = discord.Embed()
        embed.set_author(name=f"{actualUser.name}'s Profile", icon_url=actualUser.avatar_url)
        embed.set_thumbnail(url=actualUser.avatar_url)
        embed.add_field(name="Full Pomodoro Cycle Completed", value=pCycle, inline=False)
        embed.add_field(name="Mini Pomodoro Cycle Completed", value=miniCycle, inline=False)

        if not focusTime:
            embed.add_field(name="Time spent in Focus Mode", value="None", inline=False)
        else:
            embed.add_field(name="Time spent in Focus Mode", value=dmyConverter(focusTime), inline=False)
        await ctx.send(embed=embed)


    @commands.Cog.listener()
    async def on_ready(self):

        userDatabase = [user[0] for user in c.execute('SELECT user_id FROM profile')]

        memberList = [[member.id for member in guild.members if not member.bot] for guild in self.bot.guilds]
        memberList2 = list(itertools.chain.from_iterable(memberList))
        filteredMemberList = list(set(memberList2))

        for member in filteredMemberList:
            if member not in userDatabase:
                profileCreate(member)


    @commands.Cog.listener()
    async def on_guild_join(self, guild):

        userDatabase = [user[0] for user in c.execute('SELECT user_id FROM profile')]

        for member in guild.members:
            if not member.bot:
                if member.id not in userDatabase:
                    profileCreate(member.id)


    @commands.Cog.listener()
    async def on_member_join(self, member):

        userDatabase = [user[0] for user in c.execute('SELECT user_id FROM profile')]

        if not member.bot:
            if member.id not in userDatabase:
                profileCreate(member.id)





def setup(bot):
    bot.add_cog(profileCogs(bot))
