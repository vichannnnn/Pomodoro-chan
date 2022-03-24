import lightbulb
import miru
import hikari
from lightbulb.ext import tasks

plugin = lightbulb.Plugin("Help Commands")


@tasks.task(s=3600, pass_app=True)
async def status_loop(self):
    guilds = self.rest.fetch_my_guilds()
    await self.update_presence(
        activity=hikari.Activity(
            name=f"in {await guilds.count()} servers | /help",
            type=hikari.ActivityType.WATCHING,
        )
    )


@plugin.listener(hikari.StartedEvent)
async def on_ready(event: hikari.StartedEvent) -> None:
    status_loop.start()


class HelpDropdown(miru.Select):
    def __init__(self, bot, header, selections, icon_url):
        self.bot = bot
        self.icon_url = icon_url
        options = []
        for row in selections:
            options.append(miru.SelectOption(label=row))
        super().__init__(placeholder=header, min_values=1, max_values=1, options=options)

    async def callback(self, ctx: lightbulb.Context) -> None:
        labels = [i.label for i in self.options]
        idx = labels.index(self.values[0])
        name = str(self.options[idx].label)
        self.view.value = name

        embed = hikari.Embed(title=f"{name} Help")
        embed.set_thumbnail(self.icon_url)
        embed.set_footer(
            text=f"Select dropdown menu below category help! ::",
            icon=self.bot.application.icon_url)

        commands = list(set([commands.name for commands in self.bot.get_plugin(name).all_commands]))

        for comm in commands:
            comm_object = self.bot.get_slash_command(comm)
            embed.add_field(name=f"/{comm_object.name}",
                            value=comm_object.description, inline=True)

        await ctx.respond(embed=embed, flags=hikari.MessageFlag.EPHEMERAL)


class View(miru.View):
    def __init__(self, item, bot):
        self.item = item
        self.bot = bot
        super().__init__(timeout=300)
        self.add_item(self.item)

    async def on_timeout(self) -> None:
        embed = hikari.Embed(description="Help command has timed out. Please restart the command.")
        await self.message.edit(embed=embed, components=[])

    async def view_check(self, ctx: miru.Context) -> bool:
        return ctx.interaction.user == ctx.user


@plugin.command
@lightbulb.add_cooldown(5, 1, lightbulb.UserBucket)
@lightbulb.command("help", "Help command to navigate the bot.")
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def help(ctx: lightbulb.Context):

    perms = hikari.Permissions.NONE

    for role in ctx.member.get_roles():
        perms |= role.permissions

    if hikari.Permissions.ADMINISTRATOR in perms or await ctx.get_guild().fetch_owner() == ctx.user:
        admin = True
    else:
        admin = False

    cogs = [ctx.bot.get_plugin(cog) for cog in ctx.bot.plugins if
            ctx.bot.get_plugin(cog).name != "Help Commands" and ctx.bot.get_plugin(cog).all_commands] if admin else \
        [ctx.bot.get_plugin(cog) for cog in ctx.bot.plugins if
            ctx.bot.get_plugin(cog).name not in ["Help Commands", "⚙️ Admin Commands"] and ctx.bot.get_plugin(cog).all_commands]

    embed = hikari.Embed(
        description="Pomodoro is only supported with slash commands now.")
    embed.set_author(name=f"{str(ctx.bot.get_me().username).partition('#')[0]}'s Commands and Help",
                     icon=ctx.bot.application.icon_url)
    embed.set_thumbnail(ctx.bot.application.icon_url)
    embed.set_footer(
        text=f"Select dropdown menu below for more category help! :: ",
        icon=ctx.bot.application.icon_url)

    for cog in cogs:
        commands_list = ''
        lst = list(set([commands.name for commands in cog.all_commands]))
        for command in lst:
            commands = ctx.bot.get_slash_command(command)
            commands_list += f'`{commands.name}` '
        embed.add_field(name=cog.name, value=commands_list, inline=False)

    lst = [cog.name for cog in cogs]
    view = View(HelpDropdown(ctx.bot, "Choose a category", lst, ctx.bot.application.icon_url), ctx.bot)
    proxy = await ctx.respond(embed=embed, components=view.build())
    message = await proxy.message()
    view.start(message)
    await view.wait()


def load(bot):
    bot.add_plugin(plugin)


def unload(bot):
    bot.remove_plugin(plugin)
