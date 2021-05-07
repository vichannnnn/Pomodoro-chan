import discord
from discord.ext import commands
from discord.ext.commands import has_permissions
import cogs.colourEmbed as functions
import traceback
import sqlite3
import datetime

conn = sqlite3.connect('focus.db', timeout=5.0)
c = conn.cursor()
conn.row_factory = sqlite3.Row

c.execute('CREATE TABLE IF NOT EXISTS focusSettings (server_id INT PRIMARY KEY, role_id INT) ')
c.execute('CREATE TABLE IF NOT EXISTS focusChannels (server_id INT, channel_id INT, UNIQUE(server_id, channel_id)) ')
c.execute('CREATE TABLE IF NOT EXISTS focusUsers (server_id INT, user_id INT, startTime INT, UNIQUE(server_id, user_id))')

pConn = sqlite3.connect('profile.db', timeout=5.0)
pC = pConn.cursor()


async def focusRoleObject(ctx):
    roleCheck = [role[0] for role in
                 c.execute('SELECT role_id FROM focusSettings WHERE server_id = ? ', (ctx.guild.id,))]

    if roleCheck:
        focusRole = ctx.guild.get_role(role_id=roleCheck[0])

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


class focusCogs(commands.Cog, name="📚 Study"):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_remove(self, member):

        memberCheck = [member[0] for member in c.execute('SELECT user_id FROM focusUsers WHERE server_id = ? ', (member.guild.id, ))]

        if memberCheck:
            c.execute('DELETE FROM focusUsers WHERE server_id = ? AND user_id = ? ', (member.guild.id, member.id))
            conn.commit()


    @commands.command(description=f"focusmode**\n\nToggles your focus mode on/off. You will lose access to all non-study channels while in Focus Mode.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def focusmode(self, ctx):

        focusRoleCheck = await focusRoleObject(ctx)
        now = int(datetime.datetime.now().timestamp())

        if not focusRoleCheck:
            return await functions.errorEmbedTemplate(ctx, f"Focus Role has not been set up yet in this server, please contact the Server Administrator for assistance!",
                                                      ctx.message.author)

        if focusRoleCheck not in ctx.author.roles:
            await ctx.message.add_reaction('<a:peace:824495250822266931>')
            embed = discord.Embed(description=f"<a:peace:824495250822266931> {ctx.author.mention}, you're now in focus mode! <a:peace:824495250822266931>\n\nYou will only have access to the focus channels from now on. Use `focusmode` command again to get out of focus mode.", colour=functions.embedColour(ctx.guild.id))
            await ctx.send(embed=embed, delete_after=10)
            await ctx.author.add_roles(focusRoleCheck)

            c.execute('INSERT INTO focusUsers VALUES (?, ?, ?)', (ctx.guild.id, ctx.author.id, now))
            conn.commit()

        else:
            startTime = [t[0] for t in c.execute('SELECT startTime FROM focusUsers WHERE server_id = ? AND user_id = ? ', (ctx.guild.id, ctx.author.id))][0]
            focusDuration = now - startTime
            timeStatement = dmyConverter(focusDuration)
            await functions.successEmbedTemplate(ctx, f"{ctx.author.mention}, you're now out of focus mode!\n\nYou were in focus mode for **{timeStatement}**, great job!\n\nYou will be able to access all channels normally. Use `focusmode` command again to enter focus mode.", ctx.message.author)

            # Record Focus score
            pC.execute('SELECT focusTime FROM profile WHERE user_id = ? ', (ctx.author.id,))
            result = pC.fetchall()
            focusTime = result[0][0]
            focusTime += focusDuration

            pC.execute('UPDATE profile SET focusTime = ? WHERE user_id = ? ', (focusTime, ctx.author.id))
            pConn.commit()

            c.execute('DELETE FROM focusUsers WHERE server_id = ? AND user_id = ? ', (ctx.guild.id, ctx.author.id))
            conn.commit()
            await ctx.author.remove_roles(focusRoleCheck)




def setup(bot):
    bot.add_cog(focusCogs(bot))
