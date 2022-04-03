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

    def upload_confession(self, confessor_id: int, confession_id: int, msg_id: int):
        Database.execute('INSERT INTO confessions VALUES (?, ?, ?, ?)', self.guild_id, confessor_id, confession_id, msg_id)

    def get_confessor(self, confession_id: int):
        confessor_id = [i[0] for i in
                        Database.get('SELECT userID FROM confessions WHERE serverID = ? AND confessionID = ?',
                                     self.guild_id, confession_id)]

        if confessor_id:
            confessor_id = confessor_id[0]
        else:
            confessor_id = None
        return confessor_id

    def get_parent_id(self, confession_id: int):
        message_id = [i[0] for i in
                      Database.get('SELECT messageID INT FROM confessions WHERE serverID = ? AND confessionID = ?',
                                   self.guild_id, confession_id)]
        if message_id:
            message_id = message_id[0]
        else:
            message_id = None
        return message_id

@plugin.command()
@lightbulb.add_cooldown(1800, 1, lightbulb.UserBucket)
@lightbulb.option("confession", "Content of your confession.", str, required=True)
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
                             description=confession + "\n",
                             colour=random.choice(
                                 [0xFFE4E1, 0x00FF7F, 0xD8BFD8, 0xDC143C, 0xFF4500, 0xDEB887, 0xADFF2F, 0x800000,
                                  0x4682B4, 0x006400, 0x808080, 0xA0522D, 0xF08080, 0xFFB6C1, 0x00CED1]
                             ))
        confession_footer = "_________________________________________________________________________________________\n" \
                            "Use /confess to submit confessions anonymously! (nobody can see that you're typing)\n" \
                            "Do note that administrators can see who the sender is."

        # temp text while I finalise this feature
        if confession_id % 5 == 1:
            confession_footer += "\n\nThis feature is still in early development stage, do let me know if there are issues."

        embed.set_footer(text=confession_footer)

        await ctx.respond("Your confession has been submitted",
                          flags=hikari.MessageFlag.EPHEMERAL)
        msg_id = await channel_object.send(embed=embed)
        confession_server_object.upload_confession(confessor.user_id, confession_id, int(msg_id))


@plugin.command()
@lightbulb.add_cooldown(180, 1, lightbulb.UserBucket)
@lightbulb.option("reply_content", "Content of your reply.", str, required=True)
@lightbulb.option("confession_num", "ID of confession to reply to.", int, required=True)
@lightbulb.command("reply", "Replies anonymously to a confession. Has a cooldown of 3 minutes.")
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def reply(ctx: lightbulb.Context):
    parent = ctx.options.confession_num
    reply_content = ctx.options.reply_content
    replier = Profile(ctx.author.id)
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
        reply_id = confession_server_object.get_max_confession_id() + 1
        parent_id = confession_server_object.get_parent_id(parent)
        if not parent_id:
            await ctx.respond(f"Confession #{parent} does not exist, make sure you're replying to the correct confession",
                              flags=hikari.MessageFlag.EPHEMERAL)
        else:
            embed = hikari.Embed(title=f"Anonymous reply #{reply_id} to #{parent}",
                                 description=reply_content + "\n",
                                 colour=random.choice(
                                     [0xFFE4E1, 0x00FF7F, 0xD8BFD8, 0xDC143C, 0xFF4500, 0xDEB887, 0xADFF2F, 0x800000,
                                      0x4682B4, 0x006400, 0x808080, 0xA0522D, 0xF08080, 0xFFB6C1, 0x00CED1]
                                 ))
            reply_footer = "_________________________________________________________________________________________\n" \
                           "Use /reply to reply to confessions anonymously! (nobody can see that you're typing)\n" \
                                "Do note that administrators can see who the sender is."

            # temp text while I finalise this feature
            if reply_id % 5 == 1:
                reply_footer += "\n\nThis feature is still in early development stage, do let me know if there are issues."

            embed.set_footer(text=reply_footer)

            await ctx.respond("Your reply has been sent",
                              flags=hikari.MessageFlag.EPHEMERAL)
            msg_id = await channel_object.send(embed=embed, reply=parent_id)

            confession_server_object.upload_confession(replier.user_id, reply_id, int(msg_id))

def load(bot):
    bot.add_plugin(plugin)


def unload(bot):
    bot.remove_plugin(plugin)
