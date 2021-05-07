from discord.ext import commands, tasks
import cogs.colourEmbed as functions
import sqlite3
import datetime
import discord
import asyncio
from cogs.focusCogs import dmyConverter


conn = sqlite3.connect('pomodoro.db', timeout=5.0)
c = conn.cursor()
conn.row_factory = sqlite3.Row

pConn = sqlite3.connect('profile.db', timeout=5.0)
pC = pConn.cursor()


c.execute('CREATE TABLE IF NOT EXISTS pomodoro '
          '('
          'server_id INT, '
          'channel_id INT, '
          'user_id INT, '
          'cycle INT,'
          'startTime INT, '
          'nextBreak INT, '
          'nextCycle INT, '
          'UNIQUE(server_id, user_id)) '
          '')


class pomodoroCogs(commands.Cog, name="🍅 Pomodoro"):
    def __init__(self, bot):
        self.bot = bot
        self.pomodoroHandler.start()

    @tasks.loop(seconds=1.0)
    async def pomodoroHandler(self):
        now = int(datetime.datetime.now().timestamp())

        pomodoroList = [[r[0], r[1], r[2], r[3], r[4], r[5], r[6]] for r in c.execute('SELECT * FROM pomodoro')]

        for server, channel, user, cycle, startTime, nextBreak, nextCycle in pomodoroList:

            try:
                channelObject = self.bot.get_channel(channel)
                guildObject = self.bot.get_guild(server)
                memberObject = guildObject.get_member(user)

                if cycle == 4 and now > nextBreak:
                    c.execute('DELETE FROM pomodoro WHERE user_id = ? AND server_id = ?', (user, server))
                    conn.commit()
                    await channelObject.send(f"{memberObject.mention}")

                    # Record Pomodoro Score
                    pC.execute('SELECT pomodoroCycle FROM profile WHERE user_id = ? ', (user,))
                    result = pC.fetchall()
                    cycle = result[0][0]
                    cycle += 1

                    pC.execute('UPDATE profile SET pomodoroCycle = ? WHERE user_id = ? ', (cycle, user))
                    pConn.commit()

                    pC.execute('SELECT miniCycle FROM profile WHERE user_id = ? ', (user,))
                    result = pC.fetchall()
                    cycle = result[0][0]
                    cycle += 1

                    pC.execute('UPDATE profile SET miniCycle = ? WHERE user_id = ? ', (cycle, user))
                    pConn.commit()

                    description = f"🍅 {memberObject.mention}, good job! 🍅\n\nYou've completed a full Pomodoro Cycle! This will be recorded in your profile statistics!"
                    description += f"\n\nPlease use the `pomodoro` command again to start a new cycle whenever you're ready!"
                    embed = discord.Embed(
                        description=description)
                    embed.set_footer(text=f"Current Pomodoro Cycle: 4 of 4")
                    await channelObject.send(embed=embed)
                    continue

                if cycle == 3 and now > nextCycle:
                    c.execute('UPDATE pomodoro SET cycle = ?, nextCycle = ? WHERE user_id = ? AND server_id = ?',
                              (cycle + 1, now + 1800, user, server))
                    conn.commit()
                    await channelObject.send(
                        f"{memberObject.mention}")
                    embed = discord.Embed(
                        description=f"🍅 {memberObject.mention}, Your final Pomodoro Cycle begins NOW. 🍅\n\nI will be pinging you at the end of the 25-minutes work cycle!")
                    embed.set_footer(text=f"Current Pomodoro Cycle: {cycle + 1} of 4")
                    await channelObject.send(embed=embed)
                    continue

                if now > nextBreak:
                    c.execute('UPDATE pomodoro SET nextBreak = ? WHERE user_id = ? AND server_id = ?',
                              (now + 1800, user, server))
                    conn.commit()

                    pC.execute('SELECT miniCycle FROM profile WHERE user_id = ? ', (user,))
                    result = pC.fetchall()
                    cycle = result[0][0]
                    cycle += 1

                    pC.execute('UPDATE profile SET miniCycle = ? WHERE user_id = ? ', (cycle, user))
                    pConn.commit()

                    await channelObject.send(
                        f"🍅 {memberObject.mention}, it's time for a 5-minutes break! 🍅\n\nI will ping you again once the next Pomodoro Cycle is starting!")

                if now > nextCycle:
                    c.execute('UPDATE pomodoro SET cycle = ?, nextCycle = ? WHERE user_id = ? AND server_id = ?',
                              (cycle + 1, now + 1800, user, server))
                    conn.commit()
                    await channelObject.send(
                        f"{memberObject.mention}")
                    embed = discord.Embed(
                        description=f"🍅 {memberObject.mention}, Your next Pomodoro Cycle begins NOW. 🍅\n\nI will be pinging you at the end of the 25-minutes work cycle for a 5-minutes break.")
                    embed.set_footer(text=f"Current Pomodoro Cycle: {cycle + 1} of 4")
                    await channelObject.send(embed=embed)

            except AttributeError:
                c.execute('DELETE FROM pomodoro WHERE user_id = ? AND server_id = ?', (user, server))
                conn.commit()



    @pomodoroHandler.before_loop
    async def before_status(self):
        print("Waiting to handle Pomodoro Cycles...")
        await self.bot.wait_until_ready()


    @commands.command(description=f"pomodoro**\n\nStarts a Pomodoro Cycle or ends a current cycle.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def pomodoro(self, ctx):

        if ctx.channel.id != 566986619979169833:
            return await functions.errorEmbedTemplate(ctx, f"You are not allowed to use this command in this channel. Pomodoro can only be used in #bot-commands to prevent unnecessary spam!", ctx.author)

        now = int(datetime.datetime.now().timestamp())
        pomodoroCheck = [user[0] for user in c.execute(
            'SELECT user_id FROM pomodoro WHERE user_id = ? AND server_id = ? ', (ctx.author.id, ctx.guild.id))]

        if pomodoroCheck:
            embed = discord.Embed(title="Ending Pomodoro Cycle..", description="You're in the midst of a Pomodoro cycle, do you want to end it? Please react below to confirm.")
            embed.set_footer(text="Ending it prematurely will not be counted in your stats!")
            msg = await ctx.send(embed=embed)
            await msg.add_reaction("☑")
            await msg.add_reaction("❌")

            def confirmationCheck(reaction, user):

                return str(reaction.emoji) in ['☑',
                                               '❌'] and user == ctx.message.author and reaction.message.id == msg.id

            try:
                reaction, user = await self.bot.wait_for('reaction_add', check=confirmationCheck, timeout=30)

                if str(reaction.emoji) == "❌":
                    return await functions.requestEmbedTemplate(ctx, "Command cancelled.", ctx.message.author)

                elif str(reaction.emoji) == "☑":
                    startTime = [t[0] for t in
                                 c.execute('SELECT startTime FROM pomodoro WHERE server_id = ? AND user_id = ? ',
                                           (ctx.guild.id, ctx.author.id))][0]
                    focusDuration = now - startTime
                    timeStatement = dmyConverter(focusDuration)
                    c.execute('DELETE FROM pomodoro WHERE server_id = ? AND user_id = ? ',
                              (ctx.guild.id, ctx.author.id))
                    conn.commit()
                    return await functions.successEmbedTemplate(ctx, f"Pomodoro Cycle ended prematurely. You've lasted **{timeStatement}** in this cycle.", ctx.message.author)

            except asyncio.TimeoutError:
                return await functions.requestEmbedTemplate(ctx, "HMPH! You took too long to respond. Try again when you're going to respond to me!",
                                                          ctx.message.author)

        # If user not already in Pomodoro Cycle
        c.execute('INSERT INTO pomodoro VALUES (?, ?, ?, ?, ?, ?, ?)', (ctx.guild.id, ctx.channel.id, ctx.author.id, 1, now, now + 1500, now + 1800))
        conn.commit()
        await ctx.send(f"{ctx.author.mention}")
        embed = discord.Embed(description=f"🍅 {ctx.author.mention}, Your Pomodoro begins NOW. 🍅\n\nI will be pinging you at the end of the 25-minutes work cycle for a 5-minutes break.")
        embed.set_footer(text="Current Pomodoro Cycle: 1 of 4")
        await ctx.send(embed=embed)







def setup(bot):
    bot.add_cog(pomodoroCogs(bot))
