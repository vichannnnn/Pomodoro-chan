import discord
from discord.ext import commands
import cogs.colourEmbed as functions
import sqlite3
import datetime
import itertools
import math
from Database import Database
import traceback
import asyncio


async def focusRoleObject(ctx):
    roleCheck = [i[0] for i in
                 Database.get('SELECT roleID FROM focusSettings WHERE serverID = ? ', ctx.guild.id)]

    if roleCheck:
        focusRole = ctx.guild.get_role(roleCheck[0])

        if not focusRole:
            return False
    else:
        return False
    return focusRole


async def focusRoleCreate(ctx):
    focusRole = await ctx.guild.create_role(name="Focus Mode")

    for channel in ctx.guild.channels:
        await channel.set_permissions(focusRole, read_messages=False)
    return focusRole


def miniCycleTransaction(user, amount):
    cycle = [i[0] for i in Database.get('SELECT miniCycle FROM profile WHERE userID = ? ', user)][0]
    cycle += amount
    Database.execute('UPDATE profile SET miniCycle = ? WHERE userID = ? ', cycle, user)


def cycleTransaction(user, amount):
    cycle = [i[0] for i in Database.get('SELECT pomodoroCycle FROM profile WHERE userID = ? ', user)][0]
    cycle += amount
    Database.execute('UPDATE profile SET pomodoroCycle = ? WHERE userID = ? ', cycle, user)


def profileCreate(id):
    try:
        Database.execute('''INSERT INTO profile VALUES (?, ?, ?, ?)''', id, 0, 0, 0)
    except:
        traceback.print_exc()


def timeTransaction(user, focusDuration):
    focusTime = [i[0] for i in Database.get('SELECT focusTime FROM profile WHERE userID = ? ', user.id)][0]
    focusTime += focusDuration
    Database.execute('UPDATE profile SET focusTime = ? WHERE userID = ? ', focusTime, user.id)


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


def sortSecond(val):
    return val[1]


class Pages(discord.ui.View):
    def __init__(self, ctx, data):
        super().__init__()
        self.timeout = 60
        self.value = 1
        self.ctx = ctx
        self.data = data
        self.pages = math.ceil(len(self.data) / 4)

    async def interaction_check(self, interaction):
        self.message = interaction.message
        return interaction.user.id == self.ctx.author.id

    @discord.ui.button(label="Previous Page", emoji="⏪")
    async def left(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.value -= 1
        if self.value <= 0 or self.value > self.pages:
            embed = discord.Embed(description=f"You have reached the end of the pages.")
            if self.ctx.guild.icon.url:
                embed.set_thumbnail(url=self.ctx.guild.icon.url)
            else:
                pass
            embed.set_footer(text=f"Press '⏩' to go back.", icon_url=self.ctx.author.display_avatar.url)

            if self.value < 0:
                self.value += 1
            await self.message.edit(embed=embed)

        else:
            everyPage = [item for item in self.data[5 * (self.value - 1):self.value * 5]]
            embed = discord.Embed(title=f"{self.ctx.guild}", description="Below are the top five Pomodoro users.",
                                  colour=functions.embedColour(self.ctx.guild.id))
            embed.set_author(name=f"{self.ctx.guild} Leaderboard")
            embed.set_thumbnail(url=self.ctx.guild.icon.url)

            if self.value == 1:
                n = 0
                medals = ['🥇', '🥈', '🥉']

                for id, cycle, mini, time in everyPage:
                    member = self.ctx.guild.get_member(id)
                    if n > 2:
                        desc = f"Pomodoro Completed: `{cycle:,} full cycle(s)`\n"
                        desc += f"Pomodoro Completed: `{mini:,} mini cycle(s)`\n"
                        if not time:
                            desc += f"Focus Duration: `None`"
                        else:
                            desc += f"Focus Duration: `{dmyConverter(time)}`"
                        embed.add_field(name=f"**{n + 1}.** {member.name}", value=desc, inline=False)
                        n += 1
                        continue

                    desc = f"Pomodoro Completed: `{cycle:,} full cycle(s)`\n"
                    desc += f"Pomodoro Completed: `{mini:,} mini cycle(s)`\n"
                    if not time:
                        desc += f"Focus Duration: `None`"
                    else:
                        desc += f"Focus Duration: `{dmyConverter(time)}`"
                    embed.add_field(name=f"{medals[n]} {member.name}", value=desc, inline=False)
                    n += 1

            else:
                n = (self.value - 1) * 5
                for id, cycle, mini, time in everyPage:
                    n += 1
                    member = self.ctx.guild.get_member(id)
                    desc = f"Pomodoro Completed: `{cycle:,} full cycle(s)`\n"
                    desc += f"Pomodoro Completed: `{mini:,} mini cycle(s)`\n"
                    if not time:
                        desc += f"Focus Duration: `None`"
                    else:
                        desc += f"Focus Duration: `{dmyConverter(time)}`"
                    embed.add_field(name=f"**{n}.** {member.name}", value=desc, inline=False)

            embed.set_footer(text=f"Page {self.value} of {self.pages}", icon_url=self.ctx.author.display_avatar.url)
            await self.message.edit(embed=embed, view=self)

    @discord.ui.button(label="Next Page", emoji="⏩")
    async def right(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.value += 1

        if self.value > self.pages:
            embed = discord.Embed(description=f"You have reached the end of the pages.")
            if self.ctx.guild.icon.url:
                embed.set_thumbnail(url=self.ctx.guild.icon.url)
            else:
                pass
            embed.set_footer(text=f"Press '⏩' to go back.", icon_url=self.ctx.author.display_avatar.url)

            if self.value > self.pages + 1:
                self.value -= 1
            await self.message.edit(embed=embed)

        else:
            everyPage = [item for item in self.data[5 * (self.value - 1):self.value * 5]]
            embed = discord.Embed(title=f"{self.ctx.guild}", description="Below are the top five Pomodoro users.",
                                  colour=functions.embedColour(self.ctx.guild.id))
            embed.set_author(name=f"{self.ctx.guild} Leaderboard")
            embed.set_thumbnail(url=self.ctx.guild.icon.url)

            if self.value == 1:
                n = 0
                medals = ['🥇', '🥈', '🥉']

                for id, cycle, mini, time in everyPage:
                    member = self.ctx.guild.get_member(id)
                    if n > 2:
                        desc = f"Pomodoro Completed: `{cycle:,} full cycle(s)`\n"
                        desc += f"Pomodoro Completed: `{mini:,} mini cycle(s)`\n"
                        if not time:
                            desc += f"Focus Duration: `None`"
                        else:
                            desc += f"Focus Duration: `{dmyConverter(time)}`"
                        embed.add_field(name=f"**{n + 1}.** {member.name}", value=desc, inline=False)
                        n += 1
                        continue

                    desc = f"Pomodoro Completed: `{cycle:,} full cycle(s)`\n"
                    desc += f"Pomodoro Completed: `{mini:,} mini cycle(s)`\n"
                    if not time:
                        desc += f"Focus Duration: `None`"
                    else:
                        desc += f"Focus Duration: `{dmyConverter(time)}`"
                    embed.add_field(name=f"{medals[n]} {member.name}", value=desc, inline=False)
                    n += 1

            else:
                n = (self.value - 1) * 5
                for id, cycle, mini, time in everyPage:
                    n += 1
                    member = self.ctx.guild.get_member(id)
                    desc = f"Pomodoro Completed: `{cycle:,} full cycle(s)`\n"
                    desc += f"Pomodoro Completed: `{mini:,} mini cycle(s)`\n"
                    if not time:
                        desc += f"Focus Duration: `None`"
                    else:
                        desc += f"Focus Duration: `{dmyConverter(time)}`"
                    embed.add_field(name=f"**{n}.** {member.name}", value=desc, inline=False)
            embed.set_footer(text=f"Page {self.value} of {self.pages}", icon_url=self.ctx.author.display_avatar.url)
            await self.message.edit(embed=embed, view=self)

    @discord.ui.button(label="Exit", style=discord.ButtonStyle.red, emoji="❎")
    async def cancel(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.clear_items()
        self.add_item(item=discord.ui.Button(emoji="❎", label="Leaderboard Closed",
                                             style=discord.ButtonStyle.red, disabled=True))
        embed = discord.Embed(description="Leaderboard closed. Please restart the command.")
        await self.message.edit(embed=embed, view=self)
        await interaction.response.send_message("Leaderboard closed successfully. Interface will close in 5 seconds.",
                                                ephemeral=True)
        self.stop()

    async def on_timeout(self) -> None:
        self.clear_items()
        embed = discord.Embed(description="Leaderboard command has timed out. Please restart the command.")
        await self.message.edit(embed=embed, view=self)
        self.add_item(item=discord.ui.Button(emoji="❎", label="Leaderboard Closed",
                                             style=discord.ButtonStyle.red, disabled=True))
        self.stop()


class StudySettings:
    def __init__(self, guild):
        self.Info = [r for r in Database.get('SELECT * FROM focusSettings WHERE serverID = ? ', guild.id)][0] \
            if [r for r in Database.get('SELECT * FROM focusSettings WHERE serverID = ? ', guild.id)] else None
        self.FocusRole = self.Info[1] if self.Info else None
        self.FocusRoleObject = guild.get_role(self.FocusRole) if self.Info else None
        self.FocusChannels = [i[0] for i in Database.get('SELECT channelID FROM '
                                                         'focusChannels WHERE serverID = ? ',
                                                         guild.id)] if self.Info else None


class FocusMembers:
    def __init__(self, guild, member):
        self.Info = \
            [r for r in
             Database.get('SELECT * FROM focusUsers WHERE serverID = ? AND userID = ? ', guild.id, member.id)][0] \
                if [r for r in Database.get('SELECT * FROM focusUsers WHERE serverID = ? AND userID = ? ', guild.id,
                                            member.id)] else None
        self.Server = self.Info[0] if self.Info else None
        self.MemberID = self.Info[1] if self.Info else None
        self.StartTime = self.Info[2] if self.Info else None


class User:
    def __init__(self, user):
        self.Info = [r for r in Database.get('SELECT * FROM profile WHERE userID = ? ', user.id)][0] \
            if [r for r in Database.get('SELECT * FROM profile WHERE userID = ? ', user.id)] else None
        self.PomodoroCycle = self.Info[1] if self.Info else None
        self.MiniCycle = self.Info[2] if self.Info else None
        self.FocusTime = self.Info[3] if self.Info else None


class Study(commands.Cog, name="📚 Study"):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        MemberObject = FocusMembers(member.guild, member)
        if MemberObject.Info:
            Database.execute('DELETE FROM focusUsers WHERE serverID = ? AND userID = ? ', member.guild.id, member.id)

    @commands.command(brief="Shows the leaderboard for the longest Focus Mode and Pomodoro completion users.",
                      description="lb**\n\nShows the leaderboard for the longest Focus Mode and Pomodoro completion users.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def lb(self, ctx):

        leaderboardUsers = [i for i in Database.get('SELECT * FROM profile')]
        guildMemberList = [member.id for member in ctx.guild.members]
        guildLeaderboardUsers = [i for i in leaderboardUsers if i[0] in guildMemberList and i[1]]
        guildLeaderboardUsers.sort(key=sortSecond, reverse=True)

        pages = math.ceil(len(guildLeaderboardUsers) / 5)
        i = 1
        everyPage = [item for item in guildLeaderboardUsers[5 * (i - 1):i * 5]]
        embed = discord.Embed(title=f"{ctx.guild}",
                              description="Below are the top five Pomodoro users.",
                              colour=functions.embedColour(ctx.guild.id))
        embed.set_footer(text=f"Page {i} of {pages}", icon_url=ctx.author.display_avatar.url)
        embed.set_author(name=f"{ctx.guild} Leaderboard")

        if ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)

        n = 0
        medals = ['🥇', '🥈', '🥉']

        for id, cycle, mini, time in everyPage:
            if n > 2:
                member = ctx.guild.get_member(id)
                desc = f"Pomodoro Completed: `{cycle:,} full cycle(s)`\n"
                desc += f"Pomodoro Completed: `{mini:,} mini cycle(s)`\n"
                if not time:
                    desc += f"Focus Duration: `None`"
                else:
                    desc += f"Focus Duration: `{dmyConverter(time)}`"
                embed.add_field(name=f"**{n + 1}.** {member.name}", value=desc, inline=False)
                n += 1
                continue

            member = ctx.guild.get_member(id)

            desc = f"Pomodoro Completed: `{cycle:,} full cycle(s)`\n"
            desc += f"Pomodoro Completed: `{mini:,} mini cycle(s)`\n"
            if not time:
                desc += f"Focus Duration: `None`"
            else:
                desc += f"Focus Duration: `{dmyConverter(time)}`"
            embed.add_field(name=f"{medals[n]} {member.name}", value=desc, inline=False)
            n += 1
        view = Pages(ctx, guildLeaderboardUsers)
        view.message = await ctx.send(embed=embed, view=view)
        await view.wait()
        await asyncio.sleep(3)
        await view.message.delete()

    @commands.command(brief="Shows a user's (or your own) Pomodoro Profile.",
                      description="p [@User (Optional)]**\n\nShows a user's (or your own) Pomodoro Profile.",
                      aliases=['p'])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def profile(self, ctx, user: discord.Member = None):

        if user is None:
            target = ctx.author

        else:
            target = user

        UserObject = User(target)
        embed = discord.Embed(colour=functions.embedColour(ctx.guild.id))
        embed.set_author(name=f"{target.name}'s Profile", icon_url=target.display_avatar.url)
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(name="Full Pomodoro Cycle Completed", value=UserObject.PomodoroCycle, inline=False)
        embed.add_field(name="Mini Pomodoro Cycle Completed", value=UserObject.MiniCycle, inline=False)

        if not UserObject.FocusTime:
            embed.add_field(name="Time spent in Focus Mode", value="None", inline=False)
        else:
            embed.add_field(name="Time spent in Focus Mode", value=dmyConverter(UserObject.FocusTime), inline=False)
        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_ready(self):
        userDatabase = [i[0] for i in Database.get('SELECT userID FROM profile')]
        memberList = [[member.id for member in guild.members if not member.bot] for guild in self.bot.guilds]
        memberList2 = list(itertools.chain.from_iterable(memberList))
        filteredMemberList = list(set(memberList2))

        for member in filteredMemberList:
            if member not in userDatabase:
                profileCreate(member)

    @commands.Cog.listener()
    async def on_guild_join(self, guild):

        userDatabase = [i[0] for i in Database.get('SELECT userID FROM profile')]

        for member in guild.members:
            if not member.bot:
                if member.id not in userDatabase:
                    profileCreate(member.id)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        userDatabase = [user[0] for user in Database.get('SELECT userID FROM profile')]

        if not member.bot:
            if member.id not in userDatabase:
                profileCreate(member.id)

    @commands.command(brief="Toggles your focus mode on/off. "
                            f"You will lose access to all non-study channels while in Focus Mode.",
                      description=f"focusmode**\n\n"
                                  f"Toggles your focus mode on/off. "
                                  f"You will lose access to all non-study channels while in Focus Mode.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def focusmode(self, ctx):

        FocusObject = StudySettings(ctx.guild)
        now = datetime.datetime.now().timestamp()

        if not FocusObject.Info:
            return await functions.errorEmbedTemplate(ctx,
                                                      f"Focus Role has not been set up yet in this server, "
                                                      f"please contact the Server Administrator for assistance!",
                                                      ctx.message.author)

        if FocusObject.FocusRoleObject not in ctx.author.roles:
            try:
                Database.execute('INSERT INTO focusUsers VALUES (?, ?, ?)', ctx.guild.id, ctx.author.id, now)
            except sqlite3.IntegrityError:
                Database.execute('DELETE FROM focusUsers WHERE serverID = ? AND userID = ? ', ctx.guild.id,
                                 ctx.author.id)
                Database.execute('INSERT INTO focusUsers VALUES (?, ?, ?)', ctx.guild.id, ctx.author.id, now)

            embed = discord.Embed(description=f"{ctx.author.mention}, you're now in focus mode."
                                              f"\n\nYou will only have access to the focus-enabled channels from now on. "
                                              f"Use `focusmode` command again to get out of focus mode.",
                                  colour=functions.embedColour(ctx.guild.id))
            await ctx.send(embed=embed, delete_after=10)
            await ctx.author.add_roles(FocusObject.FocusRoleObject)

        else:
            MemberObject = FocusMembers(ctx.guild, ctx.author)
            startTime = MemberObject.StartTime
            focusDuration = now - startTime
            timeStatement = dmyConverter(focusDuration)

            timeTransaction(ctx.author, focusDuration)
            Database.execute('DELETE FROM focusUsers WHERE serverID = ? AND userID = ? ', ctx.guild.id, ctx.author.id)
            await ctx.author.remove_roles(FocusObject.FocusRoleObject)

            return await functions.successEmbedTemplate(ctx, f"{ctx.author.mention}, "
                                                             f"you're now out of focus mode.\n\n"
                                                             f"You were in focus mode for **{timeStatement}**, great job!"
                                                             f"\n\nYou will now be able to access all channels normally. "
                                                             f"Use `focusmode` command again to enter focus mode.",
                                                        ctx.message.author)


def setup(bot):
    bot.add_cog(Study(bot))
