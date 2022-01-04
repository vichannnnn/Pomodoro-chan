import discord
from discord.ext import commands
from discord.ext.commands import has_permissions
import cogs.colourEmbed as functions
import traceback
import sqlite3
from cogs.subjChannel import newTopic
from cogs.Study import focusRoleObject
from Database import Database
from cogs.Pomodoro import dmyConverter
import sys

sConn = sqlite3.connect('saved.db', timeout=5.0)
sC = sConn.cursor()

sC.execute(
    'CREATE TABLE IF NOT EXISTS subjectChannels ('
    'server_id INT, '
    'channel_id INT, '
    'UNIQUE('
    'server_id, channel_id)'
    ')''')


class AdminCommands(commands.Cog, name="🛠️ Admin Commands"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(brief="Checks the current voice channels settings. Administrator Only.",
                      description="voicesettings**\n\nChecks the current voice channels settings. Administrator Only.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @has_permissions(administrator=True)
    async def voicesettings(self, ctx):

        joinList = [i[0] for i in
                    Database.get(''' SELECT channelID FROM joinChannel WHERE serverID = ? ''', ctx.guild.id)]
        categoryList = [i[0] for i in
                        Database.get(''' SELECT categoryID FROM channelCategory WHERE serverID = ? ''',
                                         ctx.guild.id)]

        description = "Study Rooms will spawn under Voice Category while joining 'Join Here' Channel will trigger creation of Study Rooms.\n\n"

        for i in categoryList:
            category = self.bot.get_channel(i)
            description += f"**Voice Category**: {category.name}\n\n"

        for i in joinList:
            channel = self.bot.get_channel(i)
            description += f"**'Join Here' Channel**: {channel.name}\n\n"

        embed = discord.Embed(title="Voice Channel/Category List", description=description)
        await ctx.send(embed=embed)

    @commands.command(brief="Automatically sets up the Study Rooms System in the server.",
                      description="voicesystemcreate**\n\nAutomatically sets up the Study Rooms System in the server. Administrator Only.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @has_permissions(administrator=True)
    async def voicesystemcreate(self, ctx):

        try:  # Creates the 'Join Here' Channel
            joinHereChannel = await ctx.guild.create_voice_channel(name=f"➕ Create Study Rooms")
            Database.execute(''' INSERT INTO joinChannel VALUES (?, ?) ''', ctx.guild.id, joinHereChannel.id)

            # Creates the Category where the Study Rooms will spawn under
            categoryObject = await ctx.guild.create_category_channel(name='🔊 Study Rooms')
            Database.execute(''' INSERT INTO channelCategory VALUES (?, ?) ''', ctx.guild.id, categoryObject.id)
            await functions.successEmbedTemplate(ctx,
                                                 f"Successfully set-up the Study Rooms System! Please move the categories and voice channel to a position you would like!",
                                                 ctx.message.author)

        except sqlite3.IntegrityError:
            try:
                await joinHereChannel.delete()
            except:
                pass

            await functions.errorEmbedTemplate(ctx,
                                               f"There is already a voice system enabled in your server. Please make sure to run `voicesystemdelete` before running this command again!",
                                               ctx.message.author)

    @commands.command(brief="Automatically deletes the existing Study Rooms System in the server.",
                      description="voicesystemdelete**\n\nAutomatically deletes the existing Study Rooms System in the server. Administrator Only.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @has_permissions(administrator=True)
    async def voicesystemdelete(self, ctx):

        joinHereChannel = [r[0] for r in
                           Database.get('SELECT channelID from joinChannel WHERE serverID = ? ', ctx.guild.id)]
        categoryChannel = [r[0] for r in
                           Database.get('SELECT categoryID from channelCategory WHERE serverID = ? ', ctx.guild.id)]

        if not joinHereChannel and not categoryChannel:
            return await functions.errorEmbedTemplate(ctx,
                                                      f"Study Rooms System has not been set up in this server yet!",
                                                      ctx.author)

        channelObject = self.bot.get_channel(joinHereChannel[0])
        categoryObject = self.bot.get_channel(categoryChannel[0])

        try:
            await channelObject.delete()
        except:
            pass

        try:
            await categoryObject.delete()
        except:
            pass

        channelList = [i[0] for i in Database.get('SELECT channelID FROM voiceList WHERE serverID = ? ', ctx.guild.id)]

        for channel in channelList:
            try:
                channelObject = self.bot.get_channel(channel)
                await channelObject.delete()
            except:
                pass

        Database.execute(''' DELETE FROM channelCategory WHERE serverID = ? ''', ctx.guild.id)
        Database.execute(''' DELETE FROM joinChannel WHERE serverID = ? ''', ctx.guild.id)
        Database.execute(''' DELETE FROM voiceList WHERE serverID = ? ''', ctx.guild.id)
        await functions.successEmbedTemplate(ctx, f"Successfully deleted the Study Rooms System in this server.",
                                             ctx.author)

    @commands.command(brief="Sets up the Focus Role. Administrator Only.",
                      description=f"focusrolesetup**\n\nSets up the Focus Role. Administrator Only.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @has_permissions(administrator=True)
    async def focusrolesetup(self, ctx):

        focusRoleCheck = await focusRoleObject(ctx)

        if not focusRoleCheck:
            focusRole = await ctx.guild.create_role(name="Focus Mode")

            try:
                Database.execute('INSERT INTO focusSettings VALUES (?, ?)', ctx.guild.id, focusRole.id)
                await functions.successEmbedTemplate(ctx, f"Successfully set-up the Focus System in this server.",
                                                     ctx.message.author)

            except sqlite3.IntegrityError:
                Database.execute('UPDATE focusSettings SET roleID = ? WHERE serverID = ?', focusRole.id, ctx.guild.id)
                return await functions.successEmbedTemplate(ctx,
                                                            f"Something went wrong with the previous Focus Role.\n\n"
                                                            f"A new Focus Role has been set-up for this server.",
                                                            ctx.message.author)

        else:
            return await functions.errorEmbedTemplate(ctx, f"Focus Role has already been set-up in this server.",
                                                      ctx.message.author)

    @commands.command(brief="Shows the list of blacklisted focus channels. Administrator Only.",
                      description=f"focuschannellist**\n\nShows the list of blacklisted focus channels. Administrator Only.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @has_permissions(administrator=True)
    async def focuschannellist(self, ctx):
        channelList = [i[0] for i in
                       Database.get('SELECT channelID FROM focusChannels WHERE serverID = ? ', ctx.guild.id)]

        if not channelList:
            return await functions.errorEmbedTemplate(ctx, f"There are no focus channels in this server!", ctx.author)

        description = ""
        for chnl in channelList:
            description += f"{self.bot.get_channel(chnl).mention}\n"

        embed = discord.Embed(title=f"{ctx.guild.name}'s Blacklisted Focus Channels List", description=description)
        await ctx.send(embed=embed)

    @commands.command(brief="Toggles a channel's focus mode settings. Administrator Only.",
                      description=f"focuschannel [@Channel]**\n\n"
                                  f"Toggles a channel's focus mode settings. Administrator Only.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @has_permissions(administrator=True)
    async def focuschannel(self, ctx, channel: discord.TextChannel):

        roleCheck = [i[0] for i in Database.get('SELECT roleID FROM focusSettings WHERE serverID = ? ', ctx.guild.id)]

        if not roleCheck:
            await functions.errorEmbedTemplate(ctx, f"Focus Role has not been set up on this server yet!",
                                               ctx.message.author)

        if roleCheck:
            focusRoleObject = ctx.guild.get_role(roleCheck[0])

            if not focusRoleObject:
                return await functions.errorEmbedTemplate(ctx,
                                                          f"There was an error with the Focus Role, please run the `focusrolesetup` command again!",
                                                          ctx.message.author)

            channelList = [i[0] for i in
                           Database.get('SELECT channelID FROM focusChannels WHERE serverID = ? ', ctx.guild.id)]

            if channel.id not in channelList:
                Database.execute('INSERT INTO focusChannels VALUES (?, ?)', ctx.guild.id, channel.id)
                await channel.set_permissions(focusRoleObject, read_messages=False)

                await functions.successEmbedTemplate(ctx,
                                                     f"Successfully added {channel.mention} as a focus blacklist channel.\n\n"
                                                     f"Users who are in focused mode will not be able to access this channel.",
                                                     ctx.message.author)

            else:
                Database.execute('DELETE FROM focusChannels WHERE channelID = ?', channel.id)
                await channel.set_permissions(focusRoleObject, read_messages=True)
                await functions.successEmbedTemplate(ctx,
                                                     f"Successfully removed {channel.mention} as a focus blacklist channel.\n\n"
                                                     f"Users who are in focused mode will be able to access this channel now.",
                                                     ctx.message.author)

    @commands.command(
        brief="Toggles whether Valued Contributors are able to save messages in Subject Channels.",
        description=f"subjectchannel [#Channel]**\n\n"
                    f"Toggles whether Valued Contributors are able to save messages in Subject Channels. Administrator Only.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @has_permissions(administrator=True)
    async def subjectchannel(self, ctx, channel: discord.TextChannel):
        channelList = [chnl[0] for chnl in
                       sC.execute('SELECT channel_id FROM subjectChannels WHERE server_id = ? ', (ctx.guild.id,))]

        if channel.id not in channelList:
            sC.execute('INSERT INTO subjectChannels VALUES (?, ?)', (ctx.guild.id, channel.id))
            sConn.commit()
            msg = await ctx.send(
                "<a:loading:826529505656176651> Setting up google spreadsheet for the topic... <a:loading:826529505656176651>")
            newTopic(channel.name)
            await msg.delete()

            await functions.successEmbedTemplate(ctx,
                                                 f"Successfully added {channel.mention} as a Subject Channel. **Valued Contributors** will now be able to save messages in this channel",
                                                 ctx.message.author)
        else:
            sC.execute('DELETE FROM subjectChannels WHERE channel_id = ?', (channel.id,))
            sConn.commit()
            await functions.successEmbedTemplate(ctx,
                                                 f"Successfully removed {channel.mention} as a Subject Channel. **Valued Contributors** will no longer be able to save messages in thsi channel",
                                                 ctx.message.author)

    @commands.command(brief="Changes the colour of the embed. Administrator Only.",
                      description=f"embedsettings [colour code e.g. 0xffff0]**\n\nChanges the colour of the embed. Administrator Only.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @has_permissions(administrator=True)
    async def embedsettings(self, ctx, colour: str):

        try:
            colourCode = int(colour, 16)
            if not 16777216 >= colourCode >= 0:
                return await functions.errorEmbedTemplate(ctx, f"The colour code input is invalid, please try again.",
                                                          ctx.author)
            await functions.colourChange(ctx, colour)

        except ValueError:
            traceback.print_exc()
            return await functions.errorEmbedTemplate(ctx, f"The colour code input is invalid, please try again.",
                                                      ctx.author)

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        # if ctx.author.id == 624251187277070357:
        #     return await ctx.reinvoke()
        if isinstance(error, commands.CommandOnCooldown):
            embed = discord.Embed(description=f"This command is on cooldown. "
                                              f"Please try again after {dmyConverter(round(error.retry_after, 1))}")
        elif isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(description="You are missing the required permissions to run this command!")
        elif isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(description=f"Missing a required argument: `{error.param}`")
            ctx.command.reset_cooldown(ctx)
        elif isinstance(error, commands.MissingAnyRole):
            embed = discord.Embed(
                description=f"{ctx.author.mention}, You do not have the required role to run this command.")
        elif isinstance(error, commands.NotOwner):
            embed = discord.Embed(description=f"This command can only be run by the Bot Owner!")
        else:
            embed = discord.Embed(description=f"{ctx.author.mention}, "
                                              f"Oh no! Something went wrong while running the command!")
        traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)
        await ctx.send(embed=embed, delete_after=10)


def setup(bot):
    bot.add_cog(AdminCommands(bot))
