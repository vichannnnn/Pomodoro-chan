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

plugin = lightbulb.Plugin("📚 Library")


@plugin.listener(hikari.VoiceStateUpdateEvent)
async def on_voice_state_update(event: hikari.VoiceStateUpdateEvent) -> None:

    if event.state:
        if event.state.member.is_bot:
            return

    if event.old_state:
        if event.old_state.member.is_bot:
            return

    server_room_object = ServerRoom(event.guild_id)
    server_room_object.get_server_channels()

    if not server_room_object.join_channel or not server_room_object.category:  # If the voice system wasn't set-up on the server.
        return

    user_profile = Profile(event.state.member.id)
    user_profile.get_user_data()
    user_profile.get_user_whitelist()

    if not event.old_state and event.state:  # Joined a room from nothing
        if event.state.channel_id == server_room_object.join_channel:  # Joined the 'Join Here' Channel
            if not user_profile.current_voice and not user_profile.current_text:

                ''' Check if user already has a study room, if they do not have any, create a study room for them 
                    with themselves and all other whitelisted members given access to bypass limit and partake in text channel chat.
                    Move the said creator into their respective voice room as well. '''

                voice_channel = await event.app.rest.create_guild_voice_channel(guild=event.guild_id,
                                                                                name=f"{user_profile.room_name}",
                                                                                category=server_room_object.category,
                                                                                user_limit=user_profile.pod_limit)
                text_channel = await event.app.rest.create_guild_text_channel(guild=event.guild_id,
                                                                              name=f"{user_profile.room_name}",
                                                                              category=server_room_object.category)

                ''' Disallow Muted users from bypassing the mute & voice restriction in the server even if they're whitelisted.
                    The role ID is hardcoded and in authentication.yaml '''
                await event.app.rest.edit_permission_overwrites(text_channel.id,
                                                                yaml_data['Muted'],
                                                                target_type=hikari.channels.PermissionOverwriteType.ROLE,
                                                                deny=hikari.Permissions.SEND_MESSAGES)
                await event.app.rest.edit_permission_overwrites(text_channel.id,
                                                                event.guild_id,
                                                                target_type=hikari.channels.PermissionOverwriteType.ROLE,
                                                                deny=hikari.Permissions.VIEW_CHANNEL)
                await event.app.rest.edit_permission_overwrites(voice_channel.id,
                                                                yaml_data['Muted'],
                                                                target_type=hikari.channels.PermissionOverwriteType.ROLE,
                                                                deny=hikari.Permissions.SPEAK)

                user_profile.user_whitelist.append(event.state.member.id)
                for member in user_profile.user_whitelist:
                    try:
                        await event.app.rest.edit_permission_overwrites(text_channel.id,
                                                                        member,
                                                                        target_type=hikari.channels.PermissionOverwriteType.MEMBER,
                                                                        allow=hikari.Permissions.VIEW_CHANNEL)
                        await event.app.rest.edit_permission_overwrites(voice_channel.id,
                                                                        member,
                                                                        target_type=hikari.channels.PermissionOverwriteType.MEMBER,
                                                                        allow=(
                                                                                hikari.Permissions.CONNECT | hikari.Permissions.MOVE_MEMBERS))

                    except hikari.errors.NotFoundError:
                        print(f"{member} left the guild and will not be included in the whitelist creation.")
                user_profile.create_room(event.state.guild_id, voice_channel.id, text_channel.id)

                try:
                    await event.state.member.edit(voice_channel=voice_channel)
                except hikari.BadRequestError:
                    print(
                        f"{event.state.member.username} ({event.state.member.id}) is a bad actor and has left the voice channel"
                        f" too fast, hence the room was destroyed.")
                    await event.app.rest.delete_channel(voice_channel)
                    await event.app.rest.delete_channel(text_channel)
                    user_profile.delete_room()
            return

        else:
            server_room_object.get_all_room_data()
            voice_list = [i[1] for i in server_room_object.room_list] if server_room_object.room_list else []

            ''' If user is joining a Study Room, give them access to the appropriate text channel if they aren't in the whitelist. '''

            if voice_list:
                if event.state.channel_id in voice_list:
                    idx = voice_list.index(event.state.channel_id)
                    owner, voice, text = server_room_object.room_list[idx]
                    owner_profile = Profile(owner)
                    owner_profile.get_user_whitelist()
                    if event.state.user_id not in owner_profile.user_whitelist:
                        await event.app.rest.edit_permission_overwrites(text,
                                                                        event.state.user_id,
                                                                        target_type=hikari.channels.PermissionOverwriteType.MEMBER,
                                                                        allow=hikari.Permissions.VIEW_CHANNEL)
            return

    if event.state and event.old_state:  # Transferred room
        study_room_object = StudyRoom(event.old_state.channel_id)
        study_room_object.get_data()

        ''' Check if the room that user left from is a study room when they join a new room from this room, 
            if it is a study room, delete it if there is nobody left in the room. '''

        if study_room_object.owner_id:
            room_members = len(
                plugin.bot.cache.get_voice_states_view_for_channel(event.guild_id, event.old_state.channel_id))
            if not room_members:
                await event.app.rest.delete_channel(study_room_object.voice_id)
                await event.app.rest.delete_channel(study_room_object.text_id)
                study_room_object.delete_room()
                return

            ''' If user left a Study Room that they don't own or isn't whitelisted on, remove their access to the text channel. '''

            if study_room_object.owner_id != event.old_state.user_id:
                owner_profile = Profile(study_room_object.owner_id)
                owner_profile.get_user_whitelist()
                owner_profile.get_user_data()
                if event.old_state.user_id not in owner_profile.user_whitelist:
                    await event.app.rest.edit_permission_overwrites(owner_profile.current_text,
                                                                    event.old_state.user_id,
                                                                    target_type=hikari.channels.PermissionOverwriteType.MEMBER,
                                                                    deny=hikari.Permissions.VIEW_CHANNEL)

        ''' If they joined the 'Join Here' Channel from another room, expel them to prevent buggy interaction. '''

        if event.state.channel_id == server_room_object.join_channel:
            return await event.state.member.edit(voice_channel=None)

    if not event.state.channel_id:  # User left the room event
        study_room_object = StudyRoom(event.old_state.channel_id)
        study_room_object.get_data()

        ''' Check if the event room that they left from is a study room, if it is a study room, delete it if there is nobody left in the room. '''

        if study_room_object.owner_id:
            room_members = len(
                plugin.bot.cache.get_voice_states_view_for_channel(event.guild_id, event.old_state.channel_id))
            if not room_members:
                await event.app.rest.delete_channel(study_room_object.voice_id)
                await event.app.rest.delete_channel(study_room_object.text_id)
                study_room_object.delete_room()
                return

            ''' If user left a Study Room that they don't own or isn't whitelisted on, remove their access to the text channel. '''

            if study_room_object.owner_id != event.state.user_id:
                owner_profile = Profile(study_room_object.owner_id)
                owner_profile.get_user_whitelist()
                owner_profile.get_user_data()
                if event.state.user_id not in owner_profile.user_whitelist:
                    await event.app.rest.edit_permission_overwrites(owner_profile.current_text,
                                                                    event.state.user_id,
                                                                    target_type=hikari.channels.PermissionOverwriteType.MEMBER,
                                                                    deny=hikari.Permissions.VIEW_CHANNEL)


@dataclass
class StudyRoom:
    voice_id: int
    owner_id: int = None
    text_id: int = None
    server_id: int = None

    def get_data(self):
        data = [i for i in Database.get('SELECT * FROM studyRoomList WHERE voiceID = ? ', self.voice_id)]

        if data:
            self.owner_id, self.server_id, self.text_id, self.voice_id = data[0]

    def delete_room(self):
        Database.execute('UPDATE userProfile SET currentText = ?, currentVoice = ? WHERE userID = ? ', 0, 0,
                         self.owner_id)
        Database.execute('DELETE FROM studyRoomList WHERE voiceID = ? ', self.voice_id)


@dataclass
class ServerRoom:
    guild_id: int
    room_list: List = field(default_factory=list)
    join_channel: int = None
    category: int = None

    def get_all_room_data(self):
        self.room_list = [i for i in
                          Database.get('SELECT ownerID, voiceID, textID FROM studyRoomList WHERE serverID = ? ',
                                       self.guild_id)]

    def get_server_channels(self):
        join_check = [i for i in Database.get('SELECT channelID, categoryID FROM serverSettings WHERE serverID = ?',
                                              self.guild_id)]

        if join_check:
            self.join_channel, self.category = join_check[0]

    def nuke(self):
        Database.execute('DELETE FROM studyRoomList WHERE serverID = ?', self.guild_id)
        Database.execute('DELETE FROM serverSettings WHERE serverID = ?', self.guild_id)


@plugin.command()
@lightbulb.add_cooldown(30, 1, lightbulb.UserBucket)
@lightbulb.option("user", "The user of the room that you want to knock.", hikari.Member)
@lightbulb.command("knock", "Knocks on a user's study room. Has a cooldown of 30 minutes.")
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def knock(ctx: lightbulb.Context):
    if ctx.options.member == ctx.author:
        await ctx.bot.get_slash_command(ctx.command.name).cooldown_manager.reset_cooldown(ctx)
        return await ctx.respond(f"{ctx.author.mention}, Why are you trying to knock on your own door?",
                                 flags=hikari.MessageFlag.EPHEMERAL)

    guild_object = ctx.get_guild()
    voice_state = guild_object.get_voice_state(user=ctx.member)

    if not voice_state:
        await ctx.bot.get_slash_command(ctx.command.name).cooldown_manager.reset_cooldown(ctx)
        return await ctx.respond('You need to be in a voice channel to use this command.',
                                 flags=hikari.MessageFlag.EPHEMERAL)

    target_profile = Profile(ctx.options.user.id)
    target_profile.get_user_data()
    target_profile.get_user_whitelist()

    if ctx.author.id in target_profile.user_whitelist:
        await ctx.bot.get_slash_command(ctx.command.name).cooldown_manager.reset_cooldown(ctx)
        return await ctx.respond(f"You already have access to their room. There is no need to knock on their door.",
                                 flags=hikari.MessageFlag.EPHEMERAL)

    if not target_profile.current_voice or not target_profile.current_text:
        await ctx.bot.get_slash_command(ctx.command.name).cooldown_manager.reset_cooldown(ctx)
        return await ctx.respond(f"There is no door for you to knock on, sadly.", flags=hikari.MessageFlag.EPHEMERAL)

    target_member_object = guild_object.get_member(ctx.options.user.id)
    confirm = Confirm(ctx.options.user.id)
    proxy = await ctx.respond(
        f"{target_member_object.mention}, Knock knock, who's there? {ctx.author.mention} would like to join your room, confirm entry?",
        components=confirm.build(), user_mentions=True)
    message = await proxy.message()
    confirm.start(message)
    await confirm.wait()

    if confirm.value:
        guild_object = ctx.get_guild()
        voice_state = guild_object.get_voice_state(user=ctx.member)
        if not voice_state:
            await ctx.bot.get_slash_command(ctx.command.name).cooldown_manager.reset_cooldown(ctx)
            return await ctx.respond(f'{ctx.author.mention}, you need to be in a voice channel to be moved over.',
                                     flags=hikari.MessageFlag.EPHEMERAL)
        voice_object = guild_object.get_channel(target_profile.current_voice)
        await ctx.bot.rest.edit_member(voice_channel=voice_object, user=ctx.member, guild=guild_object)
        await ctx.bot.rest.edit_permission_overwrites(target_profile.current_text,
                                                      ctx.author.id,
                                                      target_type=hikari.channels.PermissionOverwriteType.MEMBER,
                                                      allow=hikari.Permissions.VIEW_CHANNEL)
        await ctx.respond(f"{ctx.author.mention}, you have entered their home, yay!")

    else:
        return await ctx.respond(
            f"{ctx.author.mention}, how unfortunate. The owner of the room had shut their door on you. Sad.",
            flags=hikari.MessageFlag.EPHEMERAL)


@plugin.command()
@lightbulb.add_cooldown(5, 1, lightbulb.UserBucket)
@lightbulb.command("roominfo", "Checks your Study Room's Information.")
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def roominfo(ctx: lightbulb.Context):
    user_profile = Profile(ctx.author.id)
    user_profile.get_user_whitelist()
    user_profile.get_user_data()

    guild_object = ctx.get_guild()
    if user_profile.user_whitelist:
        description = "**Whitelisted Users**\n"
        i = 1
        every_page = [item for item in user_profile.user_whitelist[10 * (i - 1):i * 10]]

        for user in every_page:
            member = guild_object.get_member(user)
            if member:
                description += f"{member.mention}\n"

        embed = hikari.Embed(title=f"{ctx.author}'s Study Room", description=description)
        embed.set_footer(text=f"Page {i} of {math.ceil(len(user_profile.user_whitelist) / 10)}",
                         icon=ctx.author.display_avatar_url)
        embed.add_field(name="Room Name", value=user_profile.room_name)
        embed.add_field(name="Room Limit", value=f"{user_profile.pod_limit if user_profile.pod_limit else 'Unlimited'} "
                                                 f"User{'s' if user_profile.pod_limit > 1 else ''}")

        embed.set_thumbnail(ctx.author.display_avatar_url)
        view = Pages(10, user_profile.user_whitelist, user_profile)
        proxy = await ctx.respond(embed=embed, components=view.build())
        message = await proxy.message()
        view.start(message)

    else:
        embed = hikari.Embed(title=f"{ctx.author}'s Study Room")
        embed.add_field(name="Room Name", value=user_profile.room_name)
        embed.add_field(name="Room Limit", value=f"{user_profile.pod_limit if user_profile.pod_limit else 'Unlimited'} "
                                                 f"User{'s' if user_profile.pod_limit > 1 else ''}")
        embed.set_thumbnail(ctx.author.display_avatar_url)
        await ctx.respond(embed=embed)


@plugin.command()
@lightbulb.add_cooldown(5, 1, lightbulb.UserBucket)
@lightbulb.option("member", "The user that you want to whitelist/blacklist.", hikari.Member)
@lightbulb.command("whitelist",
                   "Whitelist a Discord user that can bypass your Study Room Limit. Use again to remove the whitelist.")
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def whitelist(ctx: lightbulb.Context):
    if ctx.options.member.id == ctx.author.id:
        return await ctx.respond(f"{ctx.author.mention}, Why are you trying to whitelist yourself?",
                                 flags=hikari.MessageFlag.EPHEMERAL)

    user_profile = Profile(ctx.author.id)
    user_profile.get_user_whitelist()
    user_profile.get_user_data()

    if ctx.options.member.id in user_profile.user_whitelist:
        Database.execute('DELETE FROM userWhitelist WHERE userID = ? AND whitelistedUser = ? ', ctx.author.id,
                         ctx.options.member.id)

        # --- Handles room edit if there is a room active ---
        if user_profile.current_text and user_profile.current_voice:
            await ctx.bot.rest.edit_permission_overwrites(user_profile.current_text,
                                                          ctx.options.member.id,
                                                          target_type=hikari.channels.PermissionOverwriteType.MEMBER,
                                                          deny=hikari.Permissions.VIEW_CHANNEL)
            await ctx.bot.rest.edit_permission_overwrites(user_profile.current_voice,
                                                          ctx.options.member.id,
                                                          target_type=hikari.channels.PermissionOverwriteType.MEMBER,
                                                          deny=hikari.Permissions.MOVE_MEMBERS)
        # --- Handles room edit if there is a room active ---
        return await ctx.respond(f"How sad, you've removed "
                                 f"{ctx.get_guild().get_member(ctx.options.member.id).mention} from your room's whitelist.",
                                 flags=hikari.MessageFlag.EPHEMERAL)

    else:
        Database.execute('INSERT INTO userWhitelist VALUES (?, ?) ', ctx.author.id, ctx.options.member.id)
        # --- Handles room edit if there is a room active ---
        if user_profile.current_text and user_profile.current_voice:
            await ctx.bot.rest.edit_permission_overwrites(user_profile.current_text,
                                                          ctx.options.member.id,
                                                          target_type=hikari.channels.PermissionOverwriteType.MEMBER,
                                                          allow=hikari.Permissions.VIEW_CHANNEL)
            await ctx.bot.rest.edit_permission_overwrites(user_profile.current_voice,
                                                          ctx.options.member.id,
                                                          target_type=hikari.channels.PermissionOverwriteType.MEMBER,
                                                          allow=hikari.Permissions.MOVE_MEMBERS)

        await ctx.respond(f"You've whitelisted {ctx.get_guild().get_member(ctx.options.member.id).mention}. "
                          f"They are now able to join your Study Room freely, yay!", flags=hikari.MessageFlag.EPHEMERAL)


@plugin.command()
@lightbulb.add_cooldown(1800, 1, lightbulb.UserBucket)
@lightbulb.option("limit", "The user limit you are setting.", int)
@lightbulb.command("setlimit",
                   "Customize the user limit of your study room. Type 0 for unlimited. Has a cooldown of 30 minutes.")
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def setlimit(ctx: lightbulb.Context):
    limit = ctx.options.limit
    if limit < 0 or limit > 99:
        await ctx.bot.get_slash_command(ctx.command.name).cooldown_manager.reset_cooldown(ctx)
        return await ctx.respond(f"Room's capacity can only be between 0 to 99.")

    Database.execute('UPDATE userProfile SET podLimit = ? WHERE userID = ? ', limit, ctx.author.id)
    user_object = Profile(ctx.author.id)
    user_object.get_user_data()

    if user_object.current_voice and user_object.current_text:
        voice_object = ctx.get_guild().get_channel(user_object.current_voice)
        await voice_object.edit(user_limit=limit)
    return await ctx.respond(f"You've set your Study Room's capacity to **{limit}** users.",
                             flags=hikari.MessageFlag.EPHEMERAL)


@plugin.command()
@lightbulb.add_cooldown(1800, 1, lightbulb.UserBucket)
@lightbulb.option("name", "The room name you're changing to.", str)
@lightbulb.command("setroomname", "Customize the name of your study room. Has a cooldown of 30 minutes.")
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def setroomname(ctx: lightbulb.Context):
    name = ctx.options.name

    if len(name) > 30:
        await ctx.bot.get_slash_command(ctx.command.name).cooldown_manager.reset_cooldown(ctx)
        return await ctx.respond(f"Please reduce the length of your room name to less than 30 characters.",
                                 flags=hikari.MessageFlag.EPHEMERAL)

    if not re.match("^[a-zA-Z0-9' ]*$", name) and ctx.author.id not in yaml_data['Owners']:
        await ctx.bot.get_slash_command(ctx.command.name).cooldown_manager.reset_cooldown(ctx)
        return await ctx.respond(f"Only alphanumeric and `'` symbol are allowed.", flags=hikari.MessageFlag.EPHEMERAL)

    Database.execute('UPDATE userProfile SET roomName = ? WHERE userID = ?', name, ctx.author.id)
    user_object = Profile(ctx.author.id)
    user_object.get_user_data()

    if user_object.current_voice and user_object.current_text:
        guild_object = ctx.get_guild()
        voice_object = guild_object.get_channel(user_object.current_voice)
        text_object = guild_object.get_channel(user_object.current_text)

        if voice_object and text_object:
            await voice_object.edit(name=name)
            await text_object.edit(name=name)
            return await ctx.respond(
                f"You've set your room name to **{name}**. Your room's name has also been updated.",
                flags=hikari.MessageFlag.EPHEMERAL)
    return await ctx.respond(
        f"You've set your room name to **{name}**. The changes will be reflected once you open a new room.",
        flags=hikari.MessageFlag.EPHEMERAL)


def load(bot):
    bot.add_plugin(plugin)


def unload(bot):
    bot.remove_plugin(plugin)
