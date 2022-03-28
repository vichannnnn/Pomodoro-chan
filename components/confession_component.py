import random

import yaml
import lightbulb
import re
import hikari
from Database import Database
from dataclasses import dataclass, field
from components.pomodoro_component import Profile
from typing import List
from components.display_handler import Confirm, Pages
import math

with open("authentication.yaml", "r", encoding="utf8") as stream:
    yaml_data = yaml.safe_load(stream)

plugin = lightbulb.Plugin("🤫 Confession")


class ConfessionSettings:
    def __init__(self, guild: hikari.Guild):
        self.confession_channel_list = []
        self.guild_object = guild
        self.guild_id = guild.id

    def get_confession_channel_list(self):
        data = [i[0] for i in
                Database.get('SELECT channelID FROM confessionChannels WHERE serverID = ? ', self.guild_id)]
        if data:
            self.confession_channel_list = data
            return True
        return False

    def get_max_confession_id(self):
        max_id = Database.get('SELECT MAX(confessionID) FROM confessions WHERE serverID = ? ', self.guild_id)[0][0]
        return max_id if max_id else 0

    def upload_confession(self, confessor_id: int, confession_id: int):
        Database.execute('INSERT INTO confessions VALUES (?, ?, ?)', self.guild_id, confessor_id, confession_id)

    def get_confessor(self, confession_id: int):
        confessor_id = [i[0] for i in
                        Database.get('SELECT userID FROM confessions WHERE serverID = ? AND confessionID = ?',
                                     self.guild_id, confession_id)]

        if confessor_id:
            confessor_id = confessor_id[0]
        else:
            confessor_id = None
        return confessor_id


@plugin.command()
@lightbulb.add_cooldown(1800, 1, lightbulb.UserBucket)
@lightbulb.option("confession", "Content of your confession.", str)
@lightbulb.command("confess", "Creates an anonymous* confession. Has a cooldown of 30 minutes.")
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def confess(ctx: lightbulb.Context):
    confession = ctx.options.confession
    confessor = Profile(ctx.author.id)
    guild_object = ctx.get_guild()
    confession_server_object = ConfessionSettings(guild_object)
    confession_server_object.get_confession_channel_list()
    channel_object = ctx.get_channel()

    if channel_object.id not in confession_server_object.confession_channel_list:

        ''' When command is used in not whitelisted channel for confession'''

        await ctx.respond(f"You are not allowed to perform this action in {channel_object.mention}.",
                          flags=hikari.MessageFlag.EPHEMERAL)
        await ctx.bot.get_slash_command(ctx.command.name).cooldown_manager.reset_cooldown(ctx)

    else:
        confession_id = confession_server_object.get_max_confession_id() + 1
        embed = hikari.Embed(title=f"Anonymous confession #{confession_id}",
                             description=confession,
                             colour=random.choice(
                                 [0xFFE4E1, 0x00FF7F, 0xD8BFD8, 0xDC143C, 0xFF4500, 0xDEB887, 0xADFF2F, 0x800000,
                                  0x4682B4, 0x006400, 0x808080, 0xA0522D, 0xF08080, 0xC71585, 0xFFB6C1, 0x00CED1]
                             ))
        confession_footer = "Use /confess to submit confessions anonymously! (nobody can see that you're typing)\n" \
                            "Do note that administrators can see who the sender is."

        # temp text while I finalise this feature
        if confession_id % 5 == 1:
            confession_footer += "\n\nThis feature is still in early development stage, do let me know if there are issues."

        embed.set_footer(text=confession_footer)
        confession_server_object.upload_confession(confessor.user_id, confession_id)
        await ctx.respond("Your confession has been submitted",
                          flags=hikari.MessageFlag.EPHEMERAL)
        await channel_object.send(embed=embed)


def load(bot):
    bot.add_plugin(plugin)


def unload(bot):
    bot.remove_plugin(plugin)
