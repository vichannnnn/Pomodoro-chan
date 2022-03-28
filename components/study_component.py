import asyncio
import datetime
import math
import random
import hikari
import lightbulb
import miru
from Database import Database
from components.pomodoro_component import dmyConverter
from components.room_component import Profile

plugin = lightbulb.Plugin("📊 Focus & Statistics")


async def focus_role_object(ctx: lightbulb.Context):
    role_check = [i[0] for i in Database.get('SELECT roleID FROM focusSettings WHERE serverID = ? ', ctx.guild_id)]

    if role_check:
        focus_role = ctx.get_guild().get_role(role_check[0])
        if not focus_role:
            return False
    else:
        return False
    return focus_role


async def focus_role_create(ctx: lightbulb.Context):
    guild_object = ctx.get_guild()
    focus_role_object = await ctx.bot.rest.create_role(guild=guild_object, name="Focus Mode")

    for channel in guild_object.channels:
        await channel.set_permissions(focus_role_object, read_messages=False)
    return focus_role_object


def sortPomodoro(val):
    return val[5]


class Pages(miru.View):
    def __init__(self, n, data):
        super().__init__(timeout=60)
        self.value = 1
        self.data = data
        self.current_page = None
        self.n = n
        self.pages = math.ceil(len(self.data) / n)

    async def view_check(self, ctx: miru.Context) -> bool:
        return ctx.message.interaction.user == ctx.user

    @miru.button(label="Previous", style=hikari.ButtonStyle.PRIMARY, emoji="◀", disabled=True)
    async def previous_button(self, button: miru.Button, ctx: miru.Context) -> None:

        self.value -= 1
        self.current_page = [item for item in self.data[self.n * (self.value - 1):self.value * self.n]]

        colour = random.randint(0x0, 0xFFFFFF)
        guild_object = ctx.get_guild()
        embed = hikari.Embed(title=guild_object.name, description="Below are the top Pomodoro users.",
                             colour=hikari.Colour(colour))
        embed.set_author(name=f"{guild_object.name} Leaderboard")

        medals = ['🥇', '🥈', '🥉']
        rank = (self.value - 1) * self.n
        for id, name, limit, voice, text, cycle, mini_cycle, focus_time, pomodoro_duration, pomodoro_break in self.current_page:
            member = guild_object.get_member(id)
            desc = f"> Pomodoro Completed: `{cycle:,} full cycle{'s' if cycle > 1 else ''}`\n"
            desc += f"> Pomodoro Completed: `{mini_cycle:,} mini cycle{'s' if cycle > 1 else ''}`\n"
            if not focus_time:
                desc += f"> Focus Duration: `None`"
            else:
                desc += f"> Focus Duration: `{dmyConverter(focus_time)}`"
            embed.add_field(name=f"{medals[rank] if rank <= 2 and self.value == 1 else f'**{rank + 1}.**'} {member.username}", value=desc, inline=False)
            rank += 1

        embed.set_thumbnail(guild_object.icon_url)
        embed.set_footer(text=f"Page {self.value} of {self.pages}")

        if self.value <= 1:
            self.children[0].disabled = True
        else:
            self.children[0].disabled = False
        if self.value >= self.pages:
            self.children[1].disabled = True
        else:
            self.children[1].disabled = False
        await self.message.edit(embed=embed, components=self.build())

    @miru.button(label="Next", style=hikari.ButtonStyle.PRIMARY, emoji="▶")
    async def next_button(self, button: miru.Button, ctx: miru.Context) -> None:
        self.value += 1

        if self.value > self.pages:
            self.children[1].disabled = True
            return await self.message.edit(components=self.build())

        self.current_page = [item for item in self.data[self.n * (self.value - 1):self.value * self.n]]

        colour = random.randint(0x0, 0xFFFFFF)
        guild_object = ctx.get_guild()
        embed = hikari.Embed(title=guild_object.name, description="Below are the top Pomodoro users.",
                             colour=hikari.Colour(colour))
        embed.set_author(name=f"{guild_object.name} Leaderboard")

        medals = ['🥇', '🥈', '🥉']
        rank = (self.value - 1) * self.n
        for id, name, limit, voice, text, cycle, mini_cycle, focus_time, pomodoro_duration, pomodoro_break in self.current_page:
            member = guild_object.get_member(id)
            desc = f"> Pomodoro Completed: `{cycle:,} full cycle{'s' if cycle > 1 else ''}`\n"
            desc += f"> Pomodoro Completed: `{mini_cycle:,} mini cycle{'s' if cycle > 1 else ''}`\n"
            if not focus_time:
                desc += f"> Focus Duration: `None`"
            else:
                desc += f"> Focus Duration: `{dmyConverter(focus_time)}`"
            embed.add_field(name=f"{medals[rank] if rank <= 2 and self.value == 1 else f'**{rank + 1}.**'} {member.username}", value=desc, inline=False)
            rank += 1

        embed.set_thumbnail(guild_object.icon_url)
        embed.set_footer(text=f"Page {self.value} of {self.pages}")

        if self.value <= 1:
            self.children[0].disabled = True
        else:
            self.children[0].disabled = False
        if self.value >= self.pages:
            self.children[1].disabled = True
        else:
            self.children[1].disabled = False
        await self.message.edit(embed=embed, components=self.build())

    @miru.button(label="Exit", style=hikari.ButtonStyle.DANGER, emoji="❎")
    async def cancel(self, button: miru.Button, ctx: miru.Context):
        embed = hikari.Embed(description="Successfully closed the leaderboard.")
        await self.message.edit(embed=embed, components=[])
        await asyncio.sleep(5)
        await self.message.edit()

    async def on_timeout(self) -> None:
        embed = hikari.Embed(description="Leaderboard has timed out. Please restart the command.")
        await self.message.edit(embed=embed, components=[])


class StudySettings:
    def __init__(self, guild: hikari.Guild):
        self.focus_role = None
        self.focus_channel_list = []
        self.guild_object = guild
        self.guild_id = guild.id

    def get_focus_role(self):
        data = [i[0] for i in Database.get('SELECT roleID FROM focusSettings WHERE serverID = ? ', self.guild_id)]

        if data:
            focus_role = data[0]
            self.focus_role = self.guild_object.get_role(focus_role)
            return True
        return False

    def get_focus_channel_list(self):
        data = [i for i in Database.get('SELECT channelID FROM focusChannels WHERE serverID = ? ', self.guild_id)]

        if data:
            self.focus_channel_list = data[0]
            return True
        return False


class FocusMembers:
    def __init__(self, guild: int, member: int):
        self.guild_id = guild
        self.member_id = member
        self.start_time = None

    def get_data(self):
        data = [i for i in Database.get('SELECT * FROM focusUsers WHERE serverID = ? AND userID = ? ', self.guild_id,
                                        self.member_id)]

        if data:
            self.guild_id, self.member_id, self.start_time = data[0]
            return True
        return False

    def remove_focus_mode(self):
        Database.execute('DELETE FROM focusUsers WHERE serverID = ? AND userID = ? ', self.guild_id, self.member_id)


@plugin.listener(hikari.MemberDeleteEvent)
async def on_member_remove(event: hikari.MemberDeleteEvent) -> None:

    """ Removes their focus mode role and their whitelist to prevent any interaction bug from User not existing in Guild """

    member_object = FocusMembers(event.guild_id, event.old_member.id)
    check = member_object.get_data()

    if check:
        member_object.remove_focus_mode()

    Database.execute('DELETE FROM userWhitelist WHERE whitelistedUser = ? ', event.old_member.id)
    member_object = Profile(event.old_member.id)

    if member_object.current_text and member_object.current_voice:
        member_object.delete_room()


@plugin.command()
@lightbulb.add_cooldown(5, 1, lightbulb.UserBucket)
@lightbulb.option("user", "The user that you want to check profile of. Argument is optional.", hikari.Member,
                  default=None)
@lightbulb.command("profile", "Shows your Pomodoro Profile or another user's.")
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def profile(ctx: lightbulb.Context) -> None:

    if ctx.options.user is None:
        target = ctx.author
    else:
        target = ctx.options.user

    user_profile = Profile(target.id)
    user_profile.get_user_data()
    embed = hikari.Embed()
    embed.set_author(name=f"{target.username}'s Profile", icon=target.display_avatar_url)
    embed.set_thumbnail(target.display_avatar_url)
    embed.add_field(name="Full Pomodoro Cycle Completed",
                    value=user_profile.pomodoro_cycle if user_profile.pomodoro_cycle else "None", inline=False)
    embed.add_field(name="Mini Pomodoro Cycle Completed",
                    value=user_profile.mini_cycle if user_profile.mini_cycle else "None", inline=False)
    embed.add_field(name="Time spent in Focus Mode",
                    value=dmyConverter(user_profile.focus_time) if user_profile.focus_time else "None", inline=False)
    await ctx.respond(embed=embed)


@plugin.command()
@lightbulb.add_cooldown(5, 1, lightbulb.UserBucket)
@lightbulb.command("focusmode",
                   'Toggles your focus mode. You will lose access to all non-study channels while you are in Focus Mode.')
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def focus_mode(ctx: lightbulb.Context):
    focus_object = StudySettings(ctx.get_guild())
    check = focus_object.get_focus_role()
    now = datetime.datetime.now().timestamp()
    user_profile = Profile(ctx.author.id)

    if not check:
        return await ctx.respond(f"Focus Role has not been set up yet in this server, "
                                 f"please contact the Server Administrator for assistance.",
                                 flags=hikari.MessageFlag.EPHEMERAL)

    if focus_object.focus_role not in ctx.member.get_roles():
        Database.execute('INSERT INTO focusUsers VALUES (?, ?, ?)', ctx.guild_id, ctx.author.id, now)

        await ctx.respond(f"{ctx.author.mention}, you're now in focus mode."
                          f"\n\nYou will only have access to the focus-enabled channels from now on. "
                          f"Use `focusmode` command again to get out of focus mode.",
                          flags=hikari.MessageFlag.EPHEMERAL)
        await ctx.member.add_role(focus_object.focus_role)

    else:
        user_focus_object = FocusMembers(ctx.guild_id, ctx.author.id)
        user_focus_object.get_data()
        focus_duration = now - user_focus_object.start_time
        time_statement = dmyConverter(focus_duration)
        user_profile.time_transaction(focus_duration)
        Database.execute('DELETE FROM focusUsers WHERE serverID = ? AND userID = ? ', ctx.guild_id, ctx.author.id)
        await ctx.member.remove_role(focus_object.focus_role)
        return await ctx.respond(f"{ctx.author.mention}, "
                                 f"you're now out of focus mode.\n\n"
                                 f"You were in focus mode for **{time_statement}**, great job!"
                                 f"\n\nYou will now be able to access all channels normally. "
                                 f"Use `focusmode` command again to enter focus mode.",
                                 flags=hikari.MessageFlag.EPHEMERAL)


@plugin.command()
@lightbulb.add_cooldown(5, 1, lightbulb.UserBucket)
@lightbulb.command("leaderboard", 'Shows the leaderboard for the Pomodoro users')
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def leaderboard(ctx: lightbulb.Context):
    guild_object = ctx.get_guild()
    leaderboard_users = [i for i in Database.get('SELECT * FROM userProfile')]
    guild_member_list = [i for i in guild_object.get_members()]
    guild_leaderboard_users = [i for i in leaderboard_users if i[0] in guild_member_list]
    guild_leaderboard_users.sort(key=sortPomodoro, reverse=True)

    n = 5
    i = 1
    current_page = [item for item in guild_leaderboard_users[n * (i - 1):i * n]]
    colour = random.randint(0x0, 0xFFFFFF)
    pages = math.ceil(len(guild_leaderboard_users) / n)

    embed = hikari.Embed(title=guild_object.name, description="Below are the top Pomodoro users.", colour=hikari.Colour(colour))
    medals = ['🥇', '🥈', '🥉']

    rank = 0
    for id, name, limit, voice, text, cycle, mini_cycle, focus_time, pomodoro_duration, pomodoro_break in current_page:
        member = guild_object.get_member(id)
        desc = f"> Pomodoro Completed: `{cycle:,} full cycle{'s' if cycle > 1 else ''}`\n"
        desc += f"> Pomodoro Completed: `{mini_cycle:,} mini cycle{'s' if cycle > 1 else ''}`\n"
        if not focus_time:
            desc += f"> Focus Duration: `None`"
        else:
            desc += f"> Focus Duration: `{dmyConverter(focus_time)}`"
        embed.add_field(name=f"{medals[rank] if rank <= 2 else f'**{rank + 1}.**'} {member.username}", value=desc, inline=False)
        rank += 1

    embed.set_author(name=f"{guild_object.name} Leaderboard")
    embed.set_footer(text=f"Page 1 of {pages}")
    embed.set_thumbnail(guild_object.icon_url)
    view = Pages(n, guild_leaderboard_users)

    proxy = await ctx.respond(embed=embed, components=view.build())
    message = await proxy.message()
    view.start(message)


def load(bot):
    bot.add_plugin(plugin)


def unload(bot):
    bot.remove_plugin(plugin)
