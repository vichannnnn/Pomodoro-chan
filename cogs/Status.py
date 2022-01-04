import discord
from discord.ext import commands


class Status(commands.Cog, name='Status'):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(brief="Sets the playing status.",
                      description="statusset [playing/watching] [Status]**\n\nSets the playing status. Bot Owner Only.")
    @commands.is_owner()
    async def statusset(self, ctx, type, *, status_name):

        if type == 'playing':
            await self.bot.change_presence(activity=discord.Game(name=status_name))
            await ctx.send("Status successfully set!")

        elif type == 'watching':
            await self.bot.change_presence(
                activity=discord.Activity(type=discord.ActivityType.watching, name=status_name))
            await ctx.send("Status successfully set!")

        else:
            await ctx.send('Type of status has to be either `watching` or `playing`!')

def setup(bot):
    bot.add_cog(Status(bot))
