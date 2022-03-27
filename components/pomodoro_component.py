import datetime
import sqlite3
import traceback
from typing import List
import hikari
import lightbulb
import miru
import yaml
from Database import Database
from dataclasses import dataclass, field
from lightbulb.ext import tasks
from components.class_component import Profile, Tomato

with open("authentication.yaml", "r", encoding="utf8") as stream:
    yaml_data = yaml.safe_load(stream)

plugin = lightbulb.Plugin("🍅 Pomodoro")


def dmyConverter(seconds):
    """ Function to convert seconds directly into a statement with time left in days, hours, minutes and seconds. """

    seconds_in_days = 60 * 60 * 24
    seconds_in_hours = 60 * 60
    seconds_in_minutes = 60

    days = seconds // seconds_in_days
    hours = (seconds - (days * seconds_in_days)) // seconds_in_hours
    minutes = ((seconds - (days * seconds_in_days)) - (hours * seconds_in_hours)) // seconds_in_minutes
    seconds_left = seconds - (days * seconds_in_days) - (hours * seconds_in_hours) - (minutes * seconds_in_minutes)

    time_statement = ""

    if days != 0:
        time_statement += f"{round(days)} days, "
    if hours != 0:
        time_statement += f"{round(hours)} hours, "
    if minutes != 0:
        time_statement += f"{round(minutes)} minutes, "
    if seconds_left != 0:
        time_statement += f"{round(seconds_left)} seconds"
    if time_statement[-2:] == ", ":
        time_statement = time_statement[:-1]
    return time_statement


class View(miru.View):
    def __init__(self):
        self.value = None
        super().__init__(timeout=30)

    async def view_check(self, ctx: miru.Context) -> bool:
        return ctx.interaction.user == ctx.user

    async def on_timeout(self) -> None:
        await self.message.edit(content="Command timed out.", components=[])

    @miru.button(label="Confirm", style=hikari.ButtonStyle.SUCCESS, emoji="☑")
    async def confirm(self, button: miru.Button, ctx: miru.Context) -> None:
        button.label = "Confirmed"
        button.emoji = "☑"
        button.disabled = True

        for b in self.children:
            if b is not button:
                self.remove_item(b)

        tomato_object = Tomato(ctx.user.id, ctx.guild_id)
        tomato_object.get_user_data()
        now = datetime.datetime.now().timestamp()
        focus_duration = now - tomato_object.start_time
        time_statement = dmyConverter(focus_duration)
        Database.execute('DELETE FROM pomodoro WHERE userID = ? ', ctx.user.id)
        await ctx.respond(f"Pomodoro Cycle ended prematurely. You've lasted **{time_statement}** in this cycle.",
                          flags=hikari.MessageFlag.EPHEMERAL)
        await self.message.edit(components=self.build())
        self.value = True
        self.stop()

    @miru.button(label="Cancel", style=hikari.ButtonStyle.DANGER, emoji="❎")
    async def stop_button(self, button: miru.Button, ctx: miru.Context) -> None:
        await ctx.respond("Command cancelled.", flags=hikari.MessageFlag.EPHEMERAL)
        button.label = "Cancelled"
        button.emoji = "❎"
        button.disabled = True

        for b in self.children:
            if b is not button:
                self.remove_item(b)

        await self.message.edit(components=self.build())
        self.value = False
        self.stop()


@tasks.task(s=5.0, pass_app=True)
async def pomodoro_handler(self):
    now = datetime.datetime.now().timestamp()
    pomodoro_list = [i for i in Database.get('SELECT * FROM pomodoro')]

    ''' Handles Pomodoro check every 5 seconds and triggers cycle break, cycle continuation and cycle end events based on time. '''

    for server, channel, user, cycle, start_time, next_break, next_cycle in pomodoro_list:
        try:
            guild_object = await self.rest.fetch_guild(server)
            channel_object = guild_object.get_channel(channel)
            member_object = guild_object.get_member(user)
            tomato_object = Tomato(user, server)
            user_profile = Profile(user)
            tomato_object.get_user_data()
            user_profile.get_user_data()

            if cycle == 4 and now > next_break:  # Finished full 4 cycles
                tomato_object.pomodoro_delete()
                tomato_object.cycle_transaction(1)
                tomato_object.mini_cycle_transaction(1)

                description = f"🍅 {member_object.mention}, good job! 🍅\n" \
                              f"You've completed a full Pomodoro Cycle! This will be recorded in your profile statistics."
                description += f"\n\nPlease use the **pomodoro** command again to start a new cycle whenever you're ready."
                await channel_object.send(content=description, user_mentions=True)
                continue

            if now > next_cycle:  # Starting a new cycle
                tomato_object.cycle_update(tomato_object.cycle + 1)
                tomato_object.next_cycle_update(
                    now + (user_profile.pomodoro_duration + user_profile.pomodoro_break) * 60)
                tomato_object.mini_cycle_transaction(1)

                if cycle == 3:
                    description = f"🍅 {member_object.mention}, Your final Pomodoro Cycle begins NOW. 🍅\n" \
                                  f"I will be pinging you at the end of the **{user_profile.pomodoro_duration}-minutes work cycle.** " \
                                  f"({tomato_object.cycle + 1}/4)"
                else:
                    description = f"🍅 {member_object.mention}, Your next Pomodoro Cycle begins NOW. 🍅\n" \
                                  f"I will be pinging you at the end of the **{user_profile.pomodoro_duration}-minutes work cycle.** " \
                                  f"for a **{user_profile.pomodoro_break}-minutes break.** ({tomato_object.cycle + 1}/4)"
                await channel_object.send(content=description, user_mentions=True)

            if now > next_break:  # Starting a new break
                tomato_object.next_break_update(
                    now + (user_profile.pomodoro_duration + user_profile.pomodoro_break) * 60)
                tomato_object.mini_cycle_transaction(1)
                await channel_object.send(
                    content=f"🍅 {member_object.mention}, it's time for a **{user_profile.pomodoro_break}-minutes break.** 🍅\n"
                            f"I will ping you again once the next Pomodoro Cycle is starting.", user_mentions=True)

        except AttributeError:
            traceback.print_exc()
            tomato_object = Tomato(user, server)
            tomato_object.pomodoro_delete()


@plugin.listener(hikari.StartedEvent)
async def on_ready(event: hikari.StartedEvent) -> None:
    pomodoro_handler.start()


def profile_create(user: hikari.Member):
    try:
        Database.execute('INSERT INTO userProfile (userID, roomName) VALUES (?, ?) ', user.id,
                         f"{user.username}'s Room")
        print(f"Created profile for User {user} ({user.id})")
    except sqlite3.IntegrityError:
        print(f"User {user} ({user.id}) already has a user profile created.")


class User:
    def __init__(self, list: List[int]):
        self.list = list


lst = [i[0] for i in Database.get('SELECT userID FROM userProfile ')]
user_list = User(lst).list


@plugin.listener(hikari.StartedEvent)
async def on_ready(event: hikari.StartedEvent) -> None:
    guilds = event.app.rest.fetch_my_guilds()

    async for guild in guilds:
        members = await event.app.rest.fetch_members(guild)
        for member in members:
            if not member.is_bot:
                if member.id not in user_list:
                    profile_create(member)
                    user_list.append(member.id)


@plugin.listener(hikari.GuildJoinEvent)
async def on_guild_join(event: hikari.GuildJoinEvent) -> None:
    for member in event.guild.get_members():
        if not member.is_bot:
            if member.id not in user_list:
                profile_create(member)
                user_list.append(member.id)


@plugin.listener(hikari.MemberCreateEvent)
async def on_member_join(event: hikari.MemberCreateEvent) -> None:
    if event.member.id not in user_list:
        if not event.member.is_bot:
            profile_create(event.member)
            user_list.append(event.member.id)


# ---- Commands ----
@plugin.command()
@lightbulb.add_cooldown(5, 1, lightbulb.UserBucket)
@lightbulb.option("minutes", "The duration in minutes. (10-120)", int)
@lightbulb.command("setpomodoroduration", "Sets the duration of a Pomodoro cycle (in minutes). Default is 25 minutes.")
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def set_pomodoro_duration(ctx: lightbulb.Context):
    user_profile = Profile(ctx.author.id)
    user_profile.get_user_data()
    previous_duration = user_profile.pomodoro_duration
    user_profile.update_pomodoro_duration(ctx.options.minutes)
    await ctx.respond(f"Successfully updated your Pomodoro Cycle's duration. "
                      f"({previous_duration} minutes -> {user_profile.pomodoro_duration} minutes)")


@plugin.command()
@lightbulb.add_cooldown(5, 1, lightbulb.UserBucket)
@lightbulb.option("minutes", "The duration in minutes. (5-60)", int)
@lightbulb.command("setpomodorobreak",
                   "Sets the duration of a Pomodoro cycle's break (in minutes). Default is 60 minutes.")
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def set_pomodoro_break(ctx: lightbulb.Context):
    user_profile = Profile(ctx.author.id)
    user_profile.get_user_data()
    previous_duration = user_profile.pomodoro_break
    user_profile.update_pomodoro_break(ctx.options.minutes)
    await ctx.respond(f"Successfully updated your Pomodoro Cycle's break. "
                      f"({previous_duration} minutes -> {user_profile.pomodoro_break} minutes)")


@plugin.command()
@lightbulb.add_cooldown(5, 1, lightbulb.UserBucket)
@lightbulb.command("pomodoro", "Starts a new pomodoro, or cancels if you're halfway through it.")
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def pomodoro(ctx: lightbulb.Context):
    if ctx.channel_id != yaml_data['BotCommands']:
        return await ctx.respond(f"You are not allowed to use this command in this channel. "
                                 f"Pomodoro can only be used in #bot-commands to prevent unnecessary spam!",
                                 flags=hikari.MessageFlag.EPHEMERAL)

    now = datetime.datetime.now().timestamp()
    tomato_object = Tomato(ctx.author.id, ctx.guild_id)
    user_profile = Profile(ctx.author.id)
    tomato_object.get_user_data()
    user_profile.get_user_data()
    progress_check = tomato_object.pomodoro_check()

    # Allows user to have the option to cancel mid-cycle if they're in one
    if progress_check:
        embed = hikari.Embed(title="Ending Pomodoro Cycle..",
                             description="You're in the midst of a Pomodoro cycle, do you want to end it? Please react below to confirm.")
        embed.set_footer(text="Ending it prematurely will not be counted in your stats.")
        view = View()
        proxy = await ctx.respond(embed=embed, components=view.build())
        message = await proxy.message()
        view.start(message)
        await view.wait()
        return

    # If user not already in Pomodoro Cycle
    Database.execute('INSERT INTO pomodoro VALUES (?, ?, ?, ?, ?, ?, ?)',
                     ctx.guild_id, ctx.channel_id, ctx.author.id, 1, now,
                     now + user_profile.pomodoro_duration * 60,
                     now + (user_profile.pomodoro_duration + user_profile.pomodoro_break) * 60)
    description = f"🍅 {ctx.author.mention}, Your Pomodoro begins NOW. 🍅\n " \
                  f"I will be pinging you at the end of the **{user_profile.pomodoro_duration}-minutes work cycle.** " \
                  f"for a **{user_profile.pomodoro_break}-minutes break.** (1/4)"
    await ctx.respond(description, user_mentions=True)


def load(bot):
    bot.add_plugin(plugin)


def unload(bot):
    bot.remove_plugin(plugin)
