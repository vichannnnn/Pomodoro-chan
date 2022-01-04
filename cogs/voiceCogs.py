import discord
from discord.ext import commands
import sqlite3
import cogs.colourEmbed as functions
import traceback
import re
from Database import Database
import yaml

with open("authentication.yml", "r", encoding="utf8") as stream:
    yaml_data = yaml.safe_load(stream)


def profileCreate(user):
    try:
        Database.execute('''INSERT INTO userProfile VALUES (?, ?, ?, ?, ?)''', user.id, f"{user.name}'s Room", 0, 0, 0)
    except:
        traceback.print_exc()


class VoiceCogs(commands.Cog, name='🎙️ Study Rooms'):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        userDatabase = [i[0] for i in Database.get('SELECT userID FROM userProfile')]
        for guild in self.bot.guilds:
            for member in guild.members:
                if not member.bot:
                    if member.id not in userDatabase:
                        profileCreate(member)

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        userDatabase = [i[0] for i in Database.get('SELECT userID FROM userProfile')]
        for member in guild.members:
            if not member.bot:
                if member.id not in userDatabase:
                    profileCreate(member)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        userDatabase = [i[0] for i in Database.get('SELECT userID FROM userProfile')]
        if not member.bot:
            if member.id not in userDatabase:
                profileCreate(member)

    @commands.command(brief="Checks your Study Room's Information.",
                      description="roominfo**\n\nChecks your Study Room's Information.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def roominfo(self, ctx):

        roomName, podLimit = [i for i in
                              Database.get('SELECT roomName, podLimit FROM userProfile WHERE userID = ? ',
                                           ctx.author.id)][0]
        whitelistedUsers = [i[0] for i in
                            Database.get('SELECT whitelistedUser FROM userWhitelist WHERE userID = ? ', ctx.author.id)]

        if whitelistedUsers:
            description = "**Whitelisted Users**\n"
            for user in whitelistedUsers:
                member = ctx.guild.get_member(user)

                if member:
                    description += f"{member.mention}\n"

            description += "\n"
            embed = discord.Embed(title=f"{ctx.author}'s Study Room", description=description)

        else:
            embed = discord.Embed(title=f"{ctx.author}'s Study Room")

        embed.add_field(name="Room Name", value=roomName)
        embed.add_field(name="Room Limit", value=f"{podLimit} Users")
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.command(brief="A debug command to clear your study room's cache if something went wrong.",
                      description="roomreset**\n\nA debug command to clear your study room's cache if something went wrong.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def roomreset(self, ctx):

        voiceChannel, textChannel = [i for i in
                                     Database.get('SELECT currentVoice, currentText FROM userProfile WHERE userID = ? ',
                                                  ctx.author.id)][0]

        textObject = self.bot.get_channel(textChannel)
        voiceObject = self.bot.get_channel(voiceChannel)

        if not voiceObject and not textObject:
            Database.execute('UPDATE userProfile SET currentVoice = ?, currentText = ? WHERE userID = ? ',
                             0, 0, ctx.author.id)
            return await functions.successEmbedTemplate(ctx, "Successfully reset your room.", ctx.author)

        await functions.errorEmbedTemplate(ctx,
                                           f"The command can't be used because Study Room is functioning normally.",
                                           ctx.author)

    @commands.command(
        brief="Whitelist a Discord user that can bypass your Study Room Limit.",
        description="whitelist [@User]**\n\n"
                    "Whitelist a Discord user that can bypass your Study Room Limit. Use again to remove the whitelist.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def whitelist(self, ctx, user: discord.Member):

        if user == ctx.author:
            return await functions.errorEmbedTemplate(ctx, f"You cannot whitelist yourself!", ctx.author)

        try:
            Database.execute('INSERT INTO userWhitelist VALUES (?, ?) ', ctx.author.id, user.id)
            currentVoice, currentText = [i for i in Database.get('SELECT currentVoice, currentText '
                                                                 'FROM userProfile WHERE userID = ?', ctx.author.id)][0]

            if currentVoice and currentText:
                whitelistedUsers = [i[0] for i in
                                    Database.get('SELECT whitelistedUser FROM userWhitelist WHERE userID = ? ',
                                                 ctx.author.id)]

                voiceOverwrites = {
                    user: discord.PermissionOverwrite(move_members=True),
                    ctx.author: discord.PermissionOverwrite(move_members=True),
                    ctx.guild.get_role(yaml_data['Moderators']): discord.PermissionOverwrite(move_members=True)
                }
                textOverwrites = {
                    user: discord.PermissionOverwrite(view_channel=True),
                    ctx.author: discord.PermissionOverwrite(view_channel=True),
                    ctx.guild.get_role(yaml_data['Moderators']): discord.PermissionOverwrite(view_channel=True),
                    ctx.guild.default_role: discord.PermissionOverwrite(view_channel=False)
                }

                if whitelistedUsers:
                    for u in whitelistedUsers:
                        member = ctx.guild.get_member(u)
                        if member:
                            voiceOverwrites[ctx.guild.get_member(u)] = discord.PermissionOverwrite(
                                move_members=True)
                            textOverwrites[ctx.guild.get_member(u)] = discord.PermissionOverwrite(
                                view_channel=True)

                voiceObject = self.bot.get_channel(currentVoice)
                await voiceObject.edit(overwrites=voiceOverwrites)
                textObject = self.bot.get_channel(currentText)
                await textObject.edit(overwrites=textOverwrites)
            await functions.successEmbedTemplate(ctx,
                                                 f"Successfully whitelisted {user.mention}. "
                                                 f"They are now able to join your Study Room freely regardless of room user limit.",
                                                 ctx.author)

        except sqlite3.IntegrityError:
            Database.execute('DELETE FROM userWhitelist WHERE userID = ? AND whitelistedUser = ? ', ctx.author.id,
                             user.id)
            currentVoice, currentText = [i for i in Database.get('SELECT currentVoice, currentText '
                                                                 'FROM userProfile WHERE userID = ?', ctx.author.id)][0]

            if currentVoice and currentText:
                whitelistedUsers = [i[0] for i in
                                    Database.get('SELECT whitelistedUser FROM userWhitelist WHERE userID = ? ',
                                                 ctx.author.id)]

                voiceOverwrites = {
                    ctx.author: discord.PermissionOverwrite(move_members=True),
                    user: discord.PermissionOverwrite(move_members=False),
                    ctx.guild.get_role(yaml_data['Moderators']): discord.PermissionOverwrite(move_members=True),
                }

                if whitelistedUsers:
                    for u in whitelistedUsers:
                        member = ctx.guild.get_member(u)
                        if member:
                            voiceOverwrites[ctx.guild.get_member(u)] = discord.PermissionOverwrite(
                                move_members=True)

                voiceObject = self.bot.get_channel(currentVoice)
                await voiceObject.edit(overwrites=voiceOverwrites)
            await functions.successEmbedTemplate(ctx,
                                                 f"Successfully removed {user.mention} from whitelist. "
                                                 f"They are now unable to bypass your Study Room user limit.",
                                                 ctx.author)

    @commands.command(brief="Customize the user limit of your study room.",
                      description="setlimit [User Limit]**\n\n"
                                  "Customize the user limit of your study room. "
                                  "Type 0 for unlimited. Has a cooldown of 30 minutes.")
    @commands.cooldown(1, 1800, commands.BucketType.user)
    async def setlimit(self, ctx, limit: int):

        if limit < 0 or limit > 99:
            self.bot.get_command(ctx.command.name).reset_cooldown(ctx)
            return await functions.errorEmbedTemplate(ctx, f"User Limit can only be between 0 to 99.", ctx.author)

        Database.execute('UPDATE userProfile SET podLimit = ? WHERE userID = ? ', limit, ctx.author.id)
        voice = \
            [i[0] for i in Database.execute('SELECT currentVoice FROM userProfile WHERE userID = ?', ctx.author.id)][0]

        if voice:
            voiceObject = self.bot.get_channel(voice)
            await voiceObject.edit(user_limit=limit)
        return await functions.successEmbedTemplate(ctx, f"Successfully set your Study Room user limit to **{limit}**.",
                                                    ctx.author)

    @commands.command(brief="Customize the name of your study room.",
                      description="setroomname [Name]**\n\nCustomize the name of your study room. Has a cooldown of 30 minutes.")
    @commands.cooldown(1, 1800, commands.BucketType.user)
    async def setroomname(self, ctx, *, name):

        if len(name) > 30:
            self.bot.get_command(ctx.command.name).reset_cooldown(ctx)
            return await functions.errorEmbedTemplate(ctx,
                                                      f"Please reduce the length of your room name to less than 30 characters.",
                                                      ctx.author)

        if not re.match("^[a-zA-Z0-9' ]*$", name):
            self.bot.get_command(ctx.command.name).reset_cooldown(ctx)
            return await functions.errorEmbedTemplate(ctx, f"Only alphanumeric and `'` symbol are allowed!", ctx.author)

        Database.execute('UPDATE userProfile SET roomName = ? WHERE userID = ?', name, ctx.author.id)
        currentVoice, currentText = [i for i in Database.get('SELECT currentVoice, currentText '
                                                             'FROM userProfile WHERE userID = ?', ctx.author.id)][0]

        if currentVoice and currentText:
            voiceObject = self.bot.get_channel(currentVoice)
            textObject = self.bot.get_channel(currentText)
            if voiceObject and textObject:
                await voiceObject.edit(name=name)
                await textObject.edit(name=name)
                return await functions.successEmbedTemplate(ctx,
                                                            f"Successfully set your room name to **{name}**. "
                                                            f"Your existing room has also been updated.",
                                                            ctx.author)
        return await functions.successEmbedTemplate(ctx,
                                                    f"Successfully set your room name to **{name}**. "
                                                    f"Changes will be reflected once you open a new room.",
                                                    ctx.author)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):

        joinList = [i[0] for i in
                    Database.get(''' SELECT channelID FROM joinChannel WHERE serverID = ? ''', member.guild.id)][0]
        userChannelList = [i[0] for i in
                           Database.get(''' SELECT channelID FROM voiceList WHERE serverID = ? ''', member.guild.id)]
        categoryList = [i[0] for i in
                        Database.get(''' SELECT categoryID FROM channelCategory WHERE serverID = ? ''',
                                     member.guild.id)][0]

        joinHereChannel = self.bot.get_channel(joinList)
        category = self.bot.get_channel(categoryList)

        if after.channel == joinHereChannel and before.channel:

            # If trying to create new channel and joining from an existing study room, kick the user out.
            if before.channel.id in userChannelList:
                lenMembers = len(before.channel.members)
                if lenMembers == 0:  # If nobody is occupying the room, deletes the channel
                    await before.channel.delete()
                    Database.execute(''' DELETE FROM voiceList WHERE channelID = ? ''', before.channel.id)
                    textChannel = \
                        [r[0] for r in
                         Database.get('SELECT textID FROM textList WHERE voiceID = ?', before.channel.id)][0]
                    textObject = self.bot.get_channel(textChannel)
                    await textObject.delete()
                    Database.execute(''' DELETE FROM textList WHERE voiceID = ? ''', before.channel.id)
                    Database.execute('UPDATE userProfile SET currentVoice = ?, currentText = ? WHERE currentVoice = ? ',
                                     0, 0, before.channel.id)
                    Database.execute('UPDATE userProfile SET currentVoice = ?, currentText = ? WHERE userID = ? ',
                                     0, 0, member.id)
                return await member.move_to(None)

        if after.channel and after.channel.id in userChannelList:
            # If joining a room and a room is a study room,
            userID = \
                [i[0] for i in
                 Database.get('SELECT userID FROM userProfile WHERE currentVoice = ? ', after.channel.id)][0]
            whitelistedUsers = [i[0] for i in
                                Database.get('SELECT whitelistedUser FROM userWhitelist WHERE userID = ? ', userID)]

            textOverwrites = {
                after.channel.guild.get_member(userID): discord.PermissionOverwrite(view_channel=True),
                member: discord.PermissionOverwrite(view_channel=True),
                after.channel.guild.default_role: discord.PermissionOverwrite(view_channel=False)
            }

            if after.channel.guild.get_role(yaml_data['Moderators']):
                textOverwrites[
                    after.channel.guild.get_role(yaml_data['Moderators'])] = discord.PermissionOverwrite(
                    view_channel=True)

            for member in after.channel.members:
                textOverwrites[member] = discord.PermissionOverwrite(view_channel=True)

            if whitelistedUsers:
                for user in whitelistedUsers:
                    if after.channel.guild.get_member(user):
                        textOverwrites[after.channel.guild.get_member(user)] = discord.PermissionOverwrite(
                            view_channel=True)

            textID = [i[0] for i in Database.get('SELECT textID FROM textList WHERE voiceID = ? ', after.channel.id)][0]
            textObject = self.bot.get_channel(textID)
            await textObject.edit(overwrites=textOverwrites)

        if before.channel and before.channel.id in userChannelList:  # Tracks leaver
            # If leaving a channel and the channel is a study room,
            lenMembers = len(before.channel.members)
            if lenMembers == 0:  # If nobody is occupying the room, deletes the channel
                await before.channel.delete()
                Database.execute(''' DELETE FROM voiceList WHERE channelID = ? ''', before.channel.id)
                textChannel = \
                    [r[0] for r in Database.get('SELECT textID FROM textList WHERE voiceID = ?', before.channel.id)][0]
                textObject = self.bot.get_channel(textChannel)
                await textObject.delete()
                Database.execute(''' DELETE FROM textList WHERE voiceID = ? ''', before.channel.id)
                Database.execute('UPDATE userProfile SET currentVoice = ?, currentText = ? WHERE currentVoice = ? ',
                                 0, 0, before.channel.id)
                Database.execute('UPDATE userProfile SET currentVoice = ?, currentText = ? WHERE userID = ? ',
                                 0, 0, member.id)

            user = [i[0] for i in Database.get('SELECT userID FROM userProfile WHERE currentVoice = ? ', before.channel.id)]

            if user:
                whitelistedUsers = [i[0] for i in
                                    Database.get('SELECT whitelistedUser FROM userWhitelist WHERE userID = ? ', user)]

                if user == member.id or user in whitelistedUsers:
                    return
                else:
                    textOverwrites = {
                        before.channel.guild.get_member(user): discord.PermissionOverwrite(view_channel=True),
                        member: discord.PermissionOverwrite(view_channel=False),
                        before.channel.guild.default_role: discord.PermissionOverwrite(view_channel=False),
                    }

                    voiceOverwrites = {
                        member: discord.PermissionOverwrite(move_members=True),
                    }

                    if before.channel.guild.get_role(yaml_data['Moderators']):
                        voiceOverwrites[
                            before.channel.guild.get_role(yaml_data['Moderators'])] = discord.PermissionOverwrite(
                            view_channel=True)
                        textOverwrites[
                            before.channel.guild.get_role(yaml_data['Moderators'])] = discord.PermissionOverwrite(
                            view_channel=True)

                    for member in before.channel.members:
                        textOverwrites[member] = discord.PermissionOverwrite(view_channel=True)

                    if whitelistedUsers:
                        for user in whitelistedUsers:
                            if before.channel.guild.get_member(user):
                                textOverwrites[before.channel.guild.get_member(user)] = discord.PermissionOverwrite(
                                    view_channel=True)
                                voiceOverwrites[before.channel.guild.get_member(user)] = discord.PermissionOverwrite(
                                    move_members=True)

                    textID = \
                        [i[0] for i in
                         Database.get('SELECT textID FROM textList WHERE voiceID = ? ', before.channel.id)][0]
                    textObject = self.bot.get_channel(textID)
                    await textObject.edit(overwrites=textOverwrites)

        # -------------------------------------------------------------------------------------------------

        if after.channel == joinHereChannel:  # Creates a new study room
            # Check if they have an existing room
            currentVoice = [i[0] for i in
                            Database.get('SELECT currentVoice FROM userProfile WHERE userID = ?', member.id)][0]

            if currentVoice:
                voiceObject = self.bot.get_channel(currentVoice)
                return await member.move_to(voiceObject)

            roomName, podLimit = \
                [i for i in Database.get('SELECT roomName, podLimit FROM userProfile WHERE userID = ? ', member.id)][0]
            whitelistedUsers = [i[0] for i in Database.get('SELECT whitelistedUser FROM userWhitelist WHERE userID = ? ', member.id)]

            voiceOverwrites = {
                member: discord.PermissionOverwrite(move_members=True),
            }
            textOverwrites = {
                member: discord.PermissionOverwrite(view_channel=True),
                after.channel.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            }

            if after.channel.guild.get_role(yaml_data['Moderators']):
                voiceOverwrites[after.channel.guild.get_role(yaml_data['Moderators'])] = discord.PermissionOverwrite(
                    view_channel=True)
                textOverwrites[after.channel.guild.get_role(yaml_data['Moderators'])] = discord.PermissionOverwrite(
                    view_channel=True)

            if whitelistedUsers:
                for user in whitelistedUsers:
                    if after.channel.guild.get_member(user):
                        voiceOverwrites[after.channel.guild.get_member(user)] = discord.PermissionOverwrite(
                            move_members=True)
                        textOverwrites[after.channel.guild.get_member(user)] = discord.PermissionOverwrite(
                            view_channel=True)

            newVoiceChannel = await after.channel.guild.create_voice_channel(name=roomName,
                                                                             user_limit=podLimit, category=category,
                                                                             overwrites=voiceOverwrites)
            newTextChannel = await after.channel.guild.create_text_channel(name=roomName,
                                                                           category=category, overwrites=textOverwrites)

            try:
                await member.move_to(newVoiceChannel)

                Database.execute('UPDATE userProfile SET currentVoice = ?, currentText = ? WHERE userID = ? ',
                                 newVoiceChannel.id, newTextChannel.id, member.id)
                Database.execute(''' INSERT INTO voiceList VALUES (?, ?) ''',
                                 after.channel.guild.id, newVoiceChannel.id)
                Database.execute(''' INSERT INTO textList VALUES (?, ?, ?) ''',
                                 after.channel.guild.id, newTextChannel.id, newVoiceChannel.id)

            except:
                traceback.print_exc()
                await newVoiceChannel.delete()
                await newTextChannel.delete()
                return


def setup(bot):
    bot.add_cog(VoiceCogs(bot))
