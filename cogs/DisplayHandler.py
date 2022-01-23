import discord
from discord.ext import commands
import math

class Confirm(discord.ui.View):
    def __init__(self, ctx, timeout, user):
        super().__init__()
        self.timeout = timeout
        self.value = None
        self.ctx = ctx
        self.user = user
        self.cancelled = None

    async def interaction_check(self, interaction):
        return interaction.user.id == self.user.id

    async def on_timeout(self) -> None:
        self.clear_items()
        self.cancelled = True
        self.add_item(item=discord.ui.Button(emoji="❎", label="Confirmation Timed Out",
                                             style=discord.ButtonStyle.red, disabled=True))
        await self.message.edit(view=self)

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.green, emoji="✅")
    async def confirm(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.message = interaction.message
        self.clear_items()
        self.add_item(item=discord.ui.Button(emoji="✅", label="Confirmed",
                                             style=discord.ButtonStyle.red, disabled=True))
        await self.message.edit(view=self)
        self.value = True
        self.stop()

    @discord.ui.button(label="No", style=discord.ButtonStyle.red, emoji="❎")
    async def cancel(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.message = interaction.message
        self.clear_items()
        self.add_item(item=discord.ui.Button(emoji="❎", label="Cancelled",
                                             style=discord.ButtonStyle.red, disabled=True))
        await self.message.edit(view=self)
        self.value = False
        self.stop()


class Choice(discord.ui.Select):
    def __init__(self, ctx, placeholder, choices):
        self.ctx = ctx
        options = []
        for label, desc in choices:
            options.append(discord.SelectOption(label=label,
                                                description=desc))
        super().__init__(placeholder=placeholder, min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        labels = [l.label for l in self.options]
        idx = labels.index(self.values[0])
        name = str(self.options[idx].label)
        self.view.value = name
        self.view.stop()

class View(discord.ui.View):
    def __init__(self, ctx, item):
        super().__init__()
        self.timeout = 300
        self.value = None
        self.ctx = ctx
        self.item = item
        self.add_item(self.item)


class Interface(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

def setup(bot):
    bot.add_cog(Interface(bot))
