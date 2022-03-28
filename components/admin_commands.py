import hikari
import lightbulb
import random
from Database import Database
from components.study_component import focus_role_object, StudySettings, dmyConverter
from components.confession_component import ConfessionSettings
from components.class_component import ServerRoom
from components.display_handler import Confirm

plugin = lightbulb.Plugin("⚙️ Admin Commands")
plugin.add_checks(lightbulb.checks.has_guild_permissions(hikari.Permissions.ADMINISTRATOR))


async def embed_creator(ctx: lightbulb.Context, title: str, description: str):
    colour = random.randint(0x0, 0xFFFFFF)
    embed = hikari.Embed(title=title, description=description, colour=hikari.Colour(colour))
    embed.set_footer(text=f"Command used by {ctx.author}", icon=ctx.author.display_avatar_url)
    return await ctx.respond(embed=embed)


@plugin.listener(lightbulb.CommandErrorEvent)
async def on_error(event: lightbulb.CommandErrorEvent) -> None:
    if isinstance(event.exception, lightbulb.CommandInvocationError):
        await event.context.respond(
            f"Oh no! Something went wrong during invocation of command `{event.context.command.name}`.",
            delete_after=10)
        raise event.exception

    # Unwrap the exception to get the original cause
    exception = event.exception.__cause__ or event.exception

    if isinstance(exception, lightbulb.NotOwner):
        await event.context.respond(f"{event.context.author.mention}, You are not the owner of this bot.",
                                    delete_after=10, user_mentions=True)
    elif isinstance(exception, lightbulb.CommandIsOnCooldown):
        await event.context.respond(f"{event.context.author.mention}, "
                                    f"This command is on cooldown. Retry in {dmyConverter(exception.retry_after)}.",
                                    delete_after=10, user_mentions=True)
    elif isinstance(exception, lightbulb.MissingRequiredPermission):
        await event.context.respond(
            f"{event.context.author.mention}, You do not have the permission to run this command.", delete_after=10,
            user_mentions=True)
    else:
        raise exception


@plugin.command()
@lightbulb.command("voicesystemcreate",
                   "Automatically sets up the Study Rooms System in the server. Administrator Only.")
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def voicesystemcreate(ctx: lightbulb.Context):
    guild_object = ctx.get_guild()
    category_channel = await guild_object.create_category(name='🔊 Study Rooms')
    join_here_channel = await guild_object.create_voice_channel(name=f"➕ Create Study Rooms", category=category_channel)
    Database.execute(''' REPLACE INTO serverSettings VALUES (?, ?, ?) ''', ctx.guild_id, join_here_channel.id,
                     category_channel.id)
    await ctx.respond(f"Successfully set-up the Study Rooms System. "
                      f"Please move the categories and voice channel to a position you would like.",
                      flags=hikari.MessageFlag.EPHEMERAL)


@plugin.command()
@lightbulb.command("voicesystemdelete",
                   "Automatically deletes the existing Study Rooms System in the server. Administrator Only.")
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def voicesystemdelete(ctx: lightbulb.Context):
    settings_object = ServerRoom(ctx.guild_id)
    settings_object.get_all_room_data()
    settings_object.get_server_channels()

    if not settings_object.join_channel and not settings_object.category:
        return await ctx.respond(f"Study Rooms System has not been set up in this server yet.",
                                 flags=hikari.MessageFlag.EPHEMERAL)

    confirm = Confirm(ctx.options.user)
    proxy = await ctx.respond(
        f"{ctx.author.mention}, Are you sure you want to delete the Study Rooms System in this server?",
        components=confirm.build())
    message = await proxy.message()
    confirm.start(message)
    await confirm.wait()

    if confirm.value:
        guild_object = ctx.get_guild()
        channel_object = guild_object.get_channel(settings_object.join_channel)
        category_object = guild_object.get_channel(settings_object.category)

        await ctx.bot.rest.delete_channel(channel_object)
        await category_object.delete_channel(category_object)

        for owner, voice, text in settings_object.room_list:
            text_object = guild_object.get_channel(voice)
            voice_object = guild_object.get_channel(text)
            await ctx.bot.rest.delete_channel(text_object)
            await ctx.bot.rest.delete_channel(voice_object)

        settings_object.nuke()
        await ctx.respond(f"Successfully deleted the Study Rooms System in this server.",
                          flags=hikari.MessageFlag.EPHEMERAL)


@plugin.command()
@lightbulb.command("focusrolesetup", "Sets up the Focus Role. Administrator Only.")
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def focusrolesetup(ctx: lightbulb.Context):
    guild_object = ctx.get_guild()
    focus_role_check = await focus_role_object(ctx)

    if not focus_role_check:
        focus_role = await ctx.bot.rest.create_role(guild=guild_object, name="Focus Mode")
        Database.execute('REPLACE INTO focusSettings VALUES (?, ?)', ctx.guild_id, focus_role.id)
        await ctx.respond(f"Successfully set-up the Focus System in this server.", flags=hikari.MessageFlag.EPHEMERAL)

    else:
        return await ctx.respond(f"Focus Role has already been set-up in this server.",
                                 flags=hikari.MessageFlag.EPHEMERAL)


@plugin.command()
@lightbulb.command("focuschannellist", "Shows the list of blacklisted focus channels. Administrator Only.")
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def focus_channel_list_command(ctx: lightbulb.Context):
    guild_object = ctx.get_guild()
    study_server_object = StudySettings(guild_object)
    study_server_object.get_focus_channel_list()

    if not study_server_object.focus_channel_list:
        return await ctx.respond(f"There are no focus channels in this server.", flags=hikari.MessageFlag.EPHEMERAL)

    description = ""
    for chnl in study_server_object.focus_channel_list:
        description += f"{guild_object.get_channel(chnl).mention}\n"

    embed = hikari.Embed(title=f"{guild_object.name}'s Blacklisted Focus Channels List", description=description)
    await ctx.respond(embed=embed, flags=hikari.MessageFlag.EPHEMERAL)


@plugin.command()
@lightbulb.option("channel", "The channel to blacklist/whitelist.", type=hikari.TextableChannel,
                  channel_types=[hikari.ChannelType.GUILD_TEXT])
@lightbulb.command("focuschannel", "Toggles a channel's focus mode settings. Administrator Only.")
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def focus_channel_set_command(ctx: lightbulb.Context):
    guild_object = ctx.get_guild()
    focus_role = await focus_role_object(ctx)

    if not focus_role:
        return await ctx.respond(f"Focus Role has not been set up on this server yet.",
                                 flags=hikari.MessageFlag.EPHEMERAL)

    if focus_role:
        study_server_object = StudySettings(guild_object)
        study_server_object.get_focus_channel_list()
        channel_object = guild_object.get_channel(ctx.options.channel)

        if ctx.options.channel.id not in study_server_object.focus_channel_list:
            Database.execute('INSERT INTO focusChannels VALUES (?, ?)', ctx.guild_id, ctx.options.channel.id)

            ''' When a focus channel is added, a Focus Role user will not be able to view the channel. '''

            await ctx.bot.rest.edit_permission_overwrites(ctx.options.channel.id,
                                                          focus_role.id,
                                                          target_type=hikari.channels.PermissionOverwriteType.ROLE,
                                                          deny=(
                                                              hikari.Permissions.VIEW_CHANNEL
                                                          ))

            await ctx.respond(f"Successfully added {channel_object.mention} as a focus blacklist channel.\n\n"
                              f"Users who are in focused mode will not be able to access this channel.",
                              flags=hikari.MessageFlag.EPHEMERAL)

        else:
            Database.execute('DELETE FROM focusChannels WHERE channelID = ?', ctx.options.channel.id)

            await ctx.bot.rest.edit_permission_overwrites(ctx.options.channel.id,
                                                          focus_role.id,
                                                          target_type=hikari.channels.PermissionOverwriteType.ROLE,
                                                          allow=(
                                                              hikari.Permissions.VIEW_CHANNEL
                                                          ))

            await ctx.respond(f"Successfully removed {channel_object.mention} as a focus blacklist channel.\n\n"
                              f"Users who are in focused mode will be able to access this channel now.",
                              flags=hikari.MessageFlag.EPHEMERAL)


@plugin.command()
@lightbulb.option("channel", "The channel to blacklist/whitelist.", type=hikari.TextableChannel,
                  channel_types=[hikari.ChannelType.GUILD_TEXT])
@lightbulb.command("confessionchannel", "Toggles a channel's ability to accept confessions. Administrator Only.")
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def confession_channel_set_command(ctx: lightbulb.Context):
    guild_object = ctx.get_guild()
    confession_server_object = ConfessionSettings(guild_object)
    confession_server_object.get_confession_channel_list()
    channel_object = guild_object.get_channel(ctx.options.channel)

    if ctx.options.channel.id not in confession_server_object.confession_channel_list:
        Database.execute('INSERT INTO confessionChannels VALUES (?, ?)', ctx.guild_id, ctx.options.channel.id)

        ''' When a confession channel is added. '''

        await ctx.respond(f"Successfully added {channel_object.mention} as a confession channel.\n\n"
                          f"Users will now be able to do anonymous confessions in this channel.\n\n"
                          f"Administrators will be able to view the discord id of confessor to maximise anonymity\n"
                          f"and minimise trolls.\n\n"
                          ,
                          flags=hikari.MessageFlag.EPHEMERAL)

    else:
        Database.execute('DELETE FROM confessionChannels WHERE channelID = ?', ctx.options.channel.id)
        await ctx.respond(f"Successfully removed {channel_object.mention} as a confession channel.\n\n"
                          f"Users will no longer be able to do anonymous confessions in this channel.",
                          flags=hikari.MessageFlag.EPHEMERAL)


@plugin.command()
@lightbulb.option("confession_id", "The id of the confession you want to check.", type=int)
@lightbulb.command("getconfessor", "Retrieves discord id of the confessor. Administrator Only.")
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def get_confessor(ctx: lightbulb.Context):
    guild_object = ctx.get_guild()
    confession_id = ctx.options.confession_id

    confession_server_object = ConfessionSettings(guild_object)
    confession_server_object.get_confession_channel_list()
    channel_object = guild_object.get_channel(ctx.options.channel)

    if channel_object.id not in confession_server_object.confession_channel_list:
        await ctx.respond(f"{channel_object.mention} has not been configured to take confessions.\n"
                          f"Use this command in a confession channel.\n"
                          f"(displayed id will be visible to you only)"
                          ,
                          flags=hikari.MessageFlag.EPHEMERAL)

    else:

        confessor_id = Database.get('SELECT userID FROM confessions WHERE serverID = ? AND confessionID = ?',
                                    ctx.guild_id,
                                    confession_id)[0][0]

        await ctx.respond(f"Confession #{confession_id} made by user <@{confessor_id}> `id: {confessor_id}`",
                          flags=hikari.MessageFlag.EPHEMERAL)


def load(bot):
    bot.add_plugin(plugin)


def unload(bot):
    bot.remove_plugin(plugin)
