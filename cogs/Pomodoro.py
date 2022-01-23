import datetime
import discord
import yaml
from discord.ext import commands, tasks
import cogs.colourEmbed as functions
from Database import Database
from cogs.Study import miniCycleTransaction, cycleTransaction, dmyConverter

with open("authentication.yml", "r", encoding="utf8") as stream:
    yaml_data = yaml.safe_load(stream)

def cycleUpdate(user, cycle):
    Database.execute('UPDATE profile SET cycle = ? WHERE userID = ? ', cycle, user)

def nextCycleUpdate(user, cycle):
    Database.execute('UPDATE profile SET nextCycle = ? WHERE userID = ? ', cycle, user)

def nextBreakUpdate(user, cycle):
    Database.execute('UPDATE profile SET nextBreak = ? WHERE userID = ? ', cycle, user)

class Tomato:
    def __init__(self, user):
        self.Info = [r for r in Database.get('SELECT * FROM pomodoro WHERE userID = ? ', user.id)][0] \
            if [r for r in Database.get('SELECT * FROM pomodoro WHERE userID = ? ', user.id)] else None
        self.Cycle = self.Info[3] if self.Info else None
        self.StartTime = self.Info[4] if self.Info else None
        self.NextBreak = self.Info[5] if self.Info else None
        self.NextCycle = self.Info[6] if self.Info else None


class Confirm(discord.ui.View):
    def __init__(self, ctx):
        super().__init__()
        self.timeout = 30
        self.value = None
        self.ctx = ctx

    async def interaction_check(self, interaction):
        return interaction.user.id == self.ctx.author.id

    async def on_timeout(self) -> None:
        self.clear_items()
        self.add_item(item=discord.ui.Button(emoji="❎", label="Timed out",
                                             style=discord.ButtonStyle.red, disabled=True))
        await self.message.edit(view=self)

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.green, emoji="✅")
    async def confirm(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.message = interaction.message
        self.clear_items()
        self.add_item(item=discord.ui.Button(emoji="✅", label="Confirmed",
                                             style=discord.ButtonStyle.red, disabled=True))

        TomatoObject = Tomato(interaction.user)
        now = datetime.datetime.now().timestamp()
        focusDuration = now - TomatoObject.StartTime
        timeStatement = dmyConverter(focusDuration)
        Database.execute('DELETE FROM pomodoro WHERE userID = ? ', interaction.user.id)
        await interaction.response.send_message(f"Pomodoro Cycle ended prematurely. You've lasted **{timeStatement}** in this cycle.",
                                                ephemeral=True)
        await self.message.edit(view=self)
        self.value = True
        self.stop()

    @discord.ui.button(label="No", style=discord.ButtonStyle.red, emoji="❎")
    async def cancel(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.message = interaction.message
        await interaction.response.send_message("Command Cancelled.", ephemeral=True)
        self.clear_items()
        self.add_item(item=discord.ui.Button(emoji="❎", label="Cancelled",
                                             style=discord.ButtonStyle.red, disabled=True))
        await self.message.edit(view=self)
        self.value = False
        self.stop()


class Pomodoro(commands.Cog, name="🍅 Pomodoro"):
    def __init__(self, bot):
        self.bot = bot
        self.pomodoroHandler.start()

    @tasks.loop(seconds=5.0)
    async def pomodoroHandler(self):
        now = datetime.datetime.now().timestamp()
        pomodoroList = [i for i in Database.get('SELECT * FROM pomodoro')]

        for server, channel, user, cycle, startTime, nextBreak, nextCycle in pomodoroList:
            try:
                channelObject = self.bot.get_channel(channel)
                guildObject = self.bot.get_guild(server)
                memberObject = guildObject.get_member(user)

                if cycle == 4 and now > nextBreak:
                    Database.execute('DELETE FROM pomodoro WHERE userID = ? AND serverID = ?', user, server)
                    cycleTransaction(user, 1)
                    miniCycleTransaction(user, 1)

                    await channelObject.send(f"{memberObject.mention}")
                    description = f"🍅 {memberObject.mention}, good job! 🍅\n\n" \
                                  f"You've completed a full Pomodoro Cycle! This will be recorded in your profile statistics!"
                    description += f"\n\nPlease use the `pomodoro` command again to start a new cycle whenever you're ready!"
                    embed = discord.Embed(description=description, colour=functions.embedColour(server))
                    embed.set_footer(text=f"Current Pomodoro Cycle: 4 of 4")
                    await channelObject.send(embed=embed)
                    continue

                if cycle == 3 and now > nextCycle:
                    nextCycleUpdate(user, now + 1800)
                    miniCycleTransaction(user, 1)
                    await channelObject.send(f"{memberObject.mention}")
                    embed = discord.Embed(
                        description=f"🍅 {memberObject.mention}, Your final Pomodoro Cycle begins NOW. 🍅\n\n"
                                    f"I will be pinging you at the end of the 25-minutes work cycle!", colour=functions.embedColour(server))
                    embed.set_footer(text=f"Current Pomodoro Cycle: {cycle + 1} of 4")
                    await channelObject.send(embed=embed)
                    continue

                if now > nextBreak:
                    nextBreakUpdate(user, now + 1800)
                    miniCycleTransaction(user, 1)
                    await channelObject.send(f"{memberObject.mention}")
                    await channelObject.send(
                        f"🍅 {memberObject.mention}, it's time for a 5-minutes break! 🍅\n\n"
                        f"I will ping you again once the next Pomodoro Cycle is starting!")

                if now > nextCycle:
                    cycleUpdate(user, cycle + 1)
                    nextCycleUpdate(user, now + 1800)
                    await channelObject.send(
                        f"{memberObject.mention}")
                    embed = discord.Embed(
                        description=f"🍅 {memberObject.mention}, Your next Pomodoro Cycle begins NOW. 🍅\n\n"
                                    f"I will be pinging you at the end of the 25-minutes work cycle for a 5-minutes break.")
                    embed.set_footer(text=f"Current Pomodoro Cycle: {cycle + 1} of 4")
                    await channelObject.send(embed=embed)

            except AttributeError:
                Database.execute('DELETE FROM pomodoro WHERE userID = ? AND serverID = ?', user, server)

    @pomodoroHandler.before_loop
    async def before_status(self):
        print("Waiting to handle Pomodoro Cycles...")
        await self.bot.wait_until_ready()

    @commands.command(brief="Starts a Pomodoro Cycle or ends a current cycle.",
                      description=f"pomodoro**\n\n"
                                  f"Starts a Pomodoro Cycle or ends a current cycle.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def pomodoro(self, ctx):

        if ctx.channel.id != yaml_data['BotCommands']:
            return await functions.errorEmbedTemplate(ctx,
                                                      f"You are not allowed to use this command in this channel. "
                                                      f"Pomodoro can only be used in #bot-commands to prevent unnecessary spam!",
                                                      ctx.author)

        now = datetime.datetime.now().timestamp()
        PomodoroObject = Tomato(ctx.author)

        if PomodoroObject.Info:
            embed = discord.Embed(title="Ending Pomodoro Cycle..",
                                  description="You're in the midst of a Pomodoro cycle, do you want to end it? Please react below to confirm.")
            embed.set_footer(text="Ending it prematurely will not be counted in your stats!")
            confirm = Confirm(ctx)
            confirm.message = await ctx.send(embed=embed, view=confirm)
            await confirm.wait()
            return

        # If user not already in Pomodoro Cycle
        Database.execute('INSERT INTO pomodoro VALUES (?, ?, ?, ?, ?, ?, ?)',
                         ctx.guild.id, ctx.channel.id, ctx.author.id, 1, now, now + 1500, now + 1800)
        await ctx.send(f"{ctx.author.mention}")
        embed = discord.Embed(
            description=f"🍅 {ctx.author.mention}, Your Pomodoro begins NOW. 🍅\n\n"
                        f"I will be pinging you at the end of the 25-minutes work cycle for a 5-minutes break.")
        embed.set_footer(text="Current Pomodoro Cycle: 1 of 4")
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Pomodoro(bot))
