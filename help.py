import discord
from discord.ext import commands
import sqlite3
from cogs.colourEmbed import embedColour

conn = sqlite3.connect('prefix.db', timeout=5.0)
c = conn.cursor()
conn.row_factory = sqlite3.Row

class Choice(discord.ui.Select):
    def __init__(self, ctx, placeholder, choices):
        self.ctx = ctx
        options = []
        for emoji, desc, label in choices:
            options.append(discord.SelectOption(label=label[1:],
                             description=desc,
                             emoji=emoji))
        super().__init__(placeholder=placeholder, min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        currentPrefix = [i[0] for i in c.execute(f'SELECT prefix FROM prefix WHERE guildID = ? ', (self.ctx.guild.id,))][0]
        labels = [l.label for l in self.options]
        idx = labels.index(self.values[0])
        self.choice = str(self.options[idx].emoji) + self.values[0]

        embed = discord.Embed(title=f'{self.choice} Help', colour=embedColour(self.ctx.guild.id))
        embed.set_footer(
            text=f"React for more category help! :: {self.ctx.message.guild}'s prefix currently is {currentPrefix}",
            icon_url=self.ctx.author.display_avatar.url)

        cog_commands = self.ctx.bot.get_cog(f"{self.choice}").get_commands()
        commands_list = ''

        for comm in cog_commands:
            commands_list += f'**{comm.name}** - {comm.description}\n'

            embed.add_field(name=comm, value=f"**{currentPrefix}{comm.description}", inline=True)
        await interaction.message.edit(embed=embed)



class DropdownView(discord.ui.View):
    def __init__(self, ctx, item):
        super().__init__(timeout=60.0)
        self.add_item(item)
        self.item = item
        self.ctx = ctx

    async def interaction_check(self, interaction):
        self.message = interaction.message
        return interaction.user.id == self.ctx.author.id

    async def on_timeout(self):
        embed = discord.Embed(description="Help command has timed out. Please restart the command.")
        await self.message.edit(embed=embed, view=None)



class Help(commands.Cog, name="Help"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(brief="Help command to navigate the bot.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def help(self, ctx):

        admin: bool = ctx.channel.permissions_for(ctx.author).administrator

        if admin:
            excludedCogs = ['Help', 'ColourEmbed', 'Example Cogs', 'Jishaku', 'Status']
        else:
            excludedCogs = ['Help', 'ColourEmbed', 'Example Cogs', 'Jishaku', 'Status', "🛠️ Admin Commands"]

        rCogs = [cog for cog in self.bot.cogs.keys() if cog not in excludedCogs]
        reactionsCogs = [cog for cog in rCogs if len(self.bot.get_cog(cog).get_commands()) != 0]
        reactions = [cog[0] for cog in reactionsCogs]
        currentPrefix = [i[0] for i in c.execute(f'SELECT prefix FROM prefix WHERE guildID = ? ', (ctx.guild.id, ))][0]

        embed = discord.Embed(description=f"Type `{currentPrefix}myprefix` for this server's prefix.\n"
                                          f"Type `{currentPrefix}setprefix` to change the prefix for this server.",
                              colour=embedColour(ctx.guild.id))
        embed.set_author(name=f"{str(self.bot.user).partition('#')[0]}'s Commands and Help", icon_url=self.bot.user.display_avatar.url)
        embed.set_footer(text=f"React for more category help! :: {ctx.message.guild}'s prefix currently is {currentPrefix}",
            icon_url=self.bot.user.display_avatar.url)

        for cog in reactionsCogs:
            cog_commands = self.bot.get_cog(cog).get_commands()
            commands_list = ''

            for comm in cog_commands:
                commands_list += f'`{comm}` '

            embed.add_field(name=cog, value=commands_list, inline=False)

        lst = [[reactions[n], "", r] for n, r in enumerate(reactionsCogs)]
        view = DropdownView(ctx, Choice(ctx, "Choose a category", lst))
        view.message = await ctx.send(embed=embed, view=view)
        await view.wait()


def setup(bot):
    bot.add_cog(Help(bot))