import discord
from discord.ext import commands, tasks

class Status(commands.Cog, name='Status'):

    def __init__(self, bot):
        self.bot = bot
        self.change_status.start()

    @tasks.loop(seconds=3600)
    async def change_status(self):

        try:
            await self.bot.change_presence(
                activity=discord.Activity(type=discord.ActivityType.watching, name='vichannnnn.github.io | p!help'))
        except:
            pass

    @change_status.before_loop
    async def before_status(self):
        print('Waiting to update status...')
        await self.bot.wait_until_ready()


def setup(bot):
    bot.add_cog(Status(bot))
