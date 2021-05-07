import discord
from discord.ext import commands, tasks
import random
from discord.ext.commands import has_permissions


class Status(commands.Cog, name='Status'):  # You create a class instance and everything goes in it

    def __init__(self, bot): # This runs when you first load this extension script
        self.bot = bot
        self.change_status.start()

    @tasks.loop(seconds=3600) # You can run a tasks loop function that repeats itself every x seconds
    async def change_status(self): # All function takes self as the first argument and ctx as the second argument in a Class Cog!

        """ In this case, we are going to make it so that the bot's status is randomly changed every 10 minutes """

        try:
            name = [f'p!help or @{self.bot.user} help for help commands!']
            # I set a bunch of statuses in the list above for it to be randomized below.
            await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=random.choice(name)))


        except: # Sometimes it might cause an error that doesn't really matter (apparently a library bug so I'm just going to suppress it)
            pass

    @change_status.before_loop
    async def before_status(self):
        print('Waiting to update status...')
        await self.bot.wait_until_ready()


def setup(bot):
    bot.add_cog(Status(bot))
