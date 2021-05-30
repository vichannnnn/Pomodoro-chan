import discord
from discord.ext import commands
from discord.ext.commands import has_permissions
import cogs.colourEmbed as functions
import traceback
import sqlite3

fConn = sqlite3.connect('focus.db', timeout=5.0)
fC = fConn.cursor()

fC.execute('CREATE TABLE IF NOT EXISTS focusSettings (server_id INT PRIMARY KEY, role_id INT) ')
fC.execute('CREATE TABLE IF NOT EXISTS focusChannels (server_id INT, channel_id INT, UNIQUE(server_id, channel_id)) ')

conn = sqlite3.connect('bot.db', timeout=5.0)
c = conn.cursor()
conn.row_factory = sqlite3.Row

c.execute('''CREATE TABLE IF NOT EXISTS voiceList (`server_id` INT, `channelID` INT, UNIQUE(server_id, channelID)) ''')
c.execute('''CREATE TABLE IF NOT EXISTS textList (`server_id` INT, `textID` INT, voiceID INT, UNIQUE(server_id, textID)) ''')
c.execute('''CREATE TABLE IF NOT EXISTS joinChannel (`server_id` INT PRIMARY KEY, `channelID` INT) ''')
c.execute('''CREATE TABLE IF NOT EXISTS channelCategory (`server_id` INT PRIMARY KEY, `categoryID` INT) ''')

async def focusRoleObject(ctx):
    roleCheck = [role[0] for role in
                 fC.execute('SELECT role_id FROM focusSettings WHERE server_id = ? ', (ctx.guild.id,))]

    if roleCheck:
        focusRole = ctx.guild.get_role(role_id=roleCheck[0])

        if not focusRole:
            return False
    else:
        return False

    return focusRole


class adminCommands(commands.Cog, name="🛠️ Admin Commands"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(description="adminsetroomname [@User] [Name]**\n\nCustomize the name of a user's study room. Bot Owner Only.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.is_owner()
    async def adminsetroomname(self, ctx, member: discord.Member, *, name):

        if len(name) > 30:
            return await functions.errorEmbedTemplate(ctx,
                                                      f"Please reduce the length of your room name to less than 30 characters.",
                                                      ctx.author)

        c.execute('UPDATE userProfile SET roomName = ? WHERE user_id = ?', (name, member.id))
        conn.commit()

        c.execute('SELECT currentVoice, currentText FROM userProfile WHERE user_id = ?', (member.id,))
        currentVoice, currentText = c.fetchall()[0]

        if currentVoice and currentText:
            voiceObject = self.bot.get_channel(currentVoice)
            textObject = self.bot.get_channel(currentText)
            if voiceObject and textObject:
                await voiceObject.edit(name=name)
                await textObject.edit(name=name)
                return await functions.successEmbedTemplate(ctx,
                                                            f"Successfully set {member.mention}'s room name to **{name}**. Their existing room has also been updated.",
                                                            ctx.author)

        await functions.successEmbedTemplate(ctx,
                                             f"Successfully set {member.mention}'s room name to **{name}**. Changes will be reflected once they open a new room.",
                                             ctx.author)

    @commands.command(description="voicedetails**\n\nChecks the current voice channels settings. Administrator Only.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @has_permissions(administrator=True)
    async def voicedetails(self, ctx):

        joinList = [channel[0] for channel in
                    c.execute(''' SELECT channelID FROM joinChannel WHERE server_id = ? ''', (ctx.guild.id,))]
        categoryList = [channel[0] for channel in
                        c.execute(''' SELECT categoryID FROM channelCategory WHERE server_id = ? ''', (ctx.guild.id,))]

        description = "Study Rooms will spawn under Voice Category while joining 'Join Here' Channel will trigger creation of Study Rooms.\n\n"

        for i in categoryList:
            category = self.bot.get_channel(i)
            description += f"**Voice Category**: {category.name}\n\n"

        for i in joinList:
            channel = self.bot.get_channel(i)
            description += f"**'Join Here' Channel**: {channel.name}\n\n"

        embed = discord.Embed(title="Voice Channel/Category List", description=description)
        await ctx.send(embed=embed)

    @commands.command(
        description="voicesystemcreate**\n\nAutomatically sets up the Study Rooms System in the server. Administrator Only.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @has_permissions(administrator=True)
    async def voicesystemcreate(self, ctx):

        try:  # Creates the 'Join Here' Channel
            joinHereChannel = await ctx.guild.create_voice_channel(name=f"➕ Create Study Rooms")
            c.execute(''' INSERT INTO joinChannel VALUES (?, ?) ''', (ctx.guild.id, joinHereChannel.id))
            conn.commit()

            # Creates the Category where the Study Rooms will spawn under
            categoryObject = await ctx.guild.create_category_channel(name='🔊 Study Rooms')
            c.execute(''' INSERT INTO channelCategory VALUES (?, ?) ''', (ctx.guild.id, categoryObject.id))
            conn.commit()

            await functions.successEmbedTemplate(ctx,
                                                 f"Successfully set-up the Study Rooms System! Please move the categories and voice channel to a position you would like!",
                                                 ctx.message.author)

        except sqlite3.IntegrityError:
            await joinHereChannel.delete()
            await functions.errorEmbedTemplate(ctx,
                                               f"There is already a voice system enabled in your server! Please make sure to run `voicesystemdelete` before running this command again!",
                                               ctx.message.author)

    @commands.command(
        description="voicesystemdelete**\n\nAutomatically deletes the existing Study Rooms System in the server. Administrator Only.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @has_permissions(administrator=True)
    async def voicesystemdelete(self, ctx):

        joinHereChannel = [r[0] for r in
                           c.execute('SELECT channelID from joinChannel WHERE server_id = ? ', (ctx.guild.id,))]
        categoryChannel = [r[0] for r in
                           c.execute('SELECT categoryID from channelCategory WHERE server_id = ? ', (ctx.guild.id,))]

        # if not joinHereChannel and not categoryChannel:
        #     return await functions.errorEmbedTemplate(ctx, f"Study Rooms System has not been set up in this server yet!", ctx.author)

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

        channelList = [chnl[0] for chnl in
                       c.execute('SELECT channelID FROM voiceList WHERE server_id = ? ', (ctx.guild.id,))]

        for channel in channelList:
            try:
                channelObject = self.bot.get_channel(channel)
                await channelObject.delete()
            except:
                pass

        c.execute(''' DELETE FROM channelCategory WHERE server_id = ? ''', (ctx.guild.id,))
        conn.commit()
        c.execute(''' DELETE FROM joinChannel WHERE server_id = ? ''', (ctx.guild.id,))
        conn.commit()
        c.execute(''' DELETE FROM voiceList WHERE server_id = ? ''', (ctx.guild.id,))
        conn.commit()

        await functions.successEmbedTemplate(ctx, f"Successfully deleted the Study Rooms System in this server.",
                                             ctx.author)

    @commands.command(description=f"embedsettings [colour code e.g. 0xffff0]**\n\nChanges the colour of the embed.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @has_permissions(administrator=True)
    async def embedsettings(self, ctx, colour):

        try:
            await functions.colourChange(ctx, colour)

        except ValueError:
            traceback.print_exc()

    @commands.command(description=f"focusrolesetup**\n\nSets up the Focus Role. Requires Administrator Permission.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @has_permissions(administrator=True)
    async def focusrolesetup(self, ctx):

        focusRoleCheck = await focusRoleObject(ctx)

        if not focusRoleCheck:
            focusRole = await ctx.guild.create_role(name="Focus Mode")

            try:
                fC.execute('INSERT INTO focusSettings VALUES (?, ?)', (ctx.guild.id, focusRole.id))
                fConn.commit()
                await functions.successEmbedTemplate(ctx, f"Successfully set-up the Focus System in this server.",
                                                     ctx.message.author)

            except:
                fC.execute('UPDATE focusSettings SET role_id = ? WHERE server_id = ?', (focusRole.id, ctx.guild.id))
                fConn.commit()
                return await functions.successEmbedTemplate(ctx,
                                                            f"Something went wrong with the previous Focus Role.\n\nA new Focus Role has been set-up for this server.",
                                                            ctx.message.author)

        else:
            return await functions.errorEmbedTemplate(ctx, f"Focus Role has already been set-up in this server!",
                                                      ctx.message.author)

    @commands.command(
        description=f"fchannellist**\n\nShows the list of blacklisted focus channels. Requires Administrator Permission.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @has_permissions(administrator=True)
    async def fchannellist(self, ctx):
        channelList = [chnl[0] for chnl in
                       fC.execute('SELECT channel_id FROM focusChannels WHERE server_id = ? ', (ctx.guild.id,))]

        if not channelList:
            return await functions.errorEmbedTemplate(ctx, f"There are no focus channels in this server!", ctx.author)

        description = ""
        for chnl in channelList:
            description += f"{self.bot.get_channel(chnl).mention}\n"

        embed = discord.Embed(title=f"{ctx.guild.name}'s Blacklisted Focus Channels List", description=description)
        await ctx.send(embed=embed)


    @commands.command(
        description=f"focuschannel [channel mention]**\n\nToggles a channel's focus mode settings. Requires Administrator Permission.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @has_permissions(administrator=True)
    async def focuschannel(self, ctx, channel: discord.TextChannel):

        roleCheck = [role[0] for role in
                     fC.execute('SELECT role_id FROM focusSettings WHERE server_id = ? ', (ctx.guild.id,))]

        if not roleCheck:
            await functions.errorEmbedTemplate(ctx, f"Focus Role has not been set up on this server yet!",
                                               ctx.message.author)

        if roleCheck:
            focusRoleObject = ctx.guild.get_role(role_id=roleCheck[0])

            if not focusRoleObject:
                return await functions.errorEmbedTemplate(ctx,
                                                          f"There was an error with the Focus Role, please run the `focusrolesetup` command again!",
                                                          ctx.message.author)

            channelList = [chnl[0] for chnl in
                           fC.execute('SELECT channel_id FROM focusChannels WHERE server_id = ? ', (ctx.guild.id,))]

            if channel.id not in channelList:
                fC.execute('INSERT INTO focusChannels VALUES (?, ?)', (ctx.guild.id, channel.id))
                fConn.commit()
                await channel.set_permissions(focusRoleObject, read_messages=False)

                await functions.successEmbedTemplate(ctx,
                                                     f"Successfully added {channel.mention} as a focus blacklist channel.\n\nUsers who are in focused mode will not be able to access this channel.",
                                                     ctx.message.author)

            else:
                fC.execute('DELETE FROM focusChannels WHERE channel_id = ?', (channel.id,))
                fConn.commit()
                await channel.set_permissions(focusRoleObject, read_messages=True)

                await functions.successEmbedTemplate(ctx,
                                                     f"Successfully removed {channel.mention} as a focus blacklist channel.\n\nUsers who are in focused mode will be able to access this channel now.",
                                                     ctx.message.author)


def setup(bot):
    bot.add_cog(adminCommands(bot))
