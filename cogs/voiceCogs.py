import discord
from discord.ext import commands, tasks
from discord.ext.commands import has_permissions
import random
import sqlite3
import cogs.colourEmbed as functions
import traceback
import re


conn = sqlite3.connect('bot.db', timeout=5.0)
c = conn.cursor()
conn.row_factory = sqlite3.Row

c.execute('''CREATE TABLE IF NOT EXISTS voiceList (`server_id` INT, `channelID` INT, UNIQUE(server_id, channelID)) ''')
c.execute('''CREATE TABLE IF NOT EXISTS textList (`server_id` INT, `textID` INT, voiceID INT, UNIQUE(server_id, textID)) ''')
c.execute('''CREATE TABLE IF NOT EXISTS joinChannel (`server_id` INT PRIMARY KEY, `channelID` INT) ''')
c.execute('''CREATE TABLE IF NOT EXISTS channelCategory (`server_id` INT PRIMARY KEY, `categoryID` INT) ''')
c.execute('''CREATE TABLE IF NOT EXISTS userProfile (`user_id` INT PRIMARY KEY, roomName TEXT, podLimit INT, currentVoice INT, currentText INT) ''')
c.execute('''CREATE TABLE IF NOT EXISTS userWhitelist (`user_id` INT, `whitelistedUser` INT, UNIQUE(user_id, whitelistedUser)) ''')

def profileCreate(id):
    try:
        c.execute('''INSERT INTO userProfile VALUES (?, ?, ?, ?, ?)''', (id.id, f"{id.name}'s Room", 0, 0, 0))
        conn.commit()
    except:
        traceback.print_exc()

class voiceCogs(commands.Cog, name='🎙️ Study Rooms'):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        userDatabase = [user[0] for user in c.execute('SELECT user_id FROM userProfile')]
        for guild in self.bot.guilds:
            for member in guild.members:
                if not member.bot:
                    if member.id not in userDatabase:
                        profileCreate(member)

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        userDatabase = [user[0] for user in c.execute('SELECT user_id FROM userProfile')]
        for member in guild.members:
            if not member.bot:
                if member.id not in userDatabase:
                    profileCreate(member)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        userDatabase = [user[0] for user in c.execute('SELECT user_id FROM userProfile')]
        if not member.bot:
            if member.id not in userDatabase:
                profileCreate(member)

    @commands.command(description="roominfo**\n\nChecks your Study Room settings.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def roominfo(self, ctx):

        roomName, podLimit = [[r[0], r[1]] for r in
                              c.execute('SELECT roomName, podLimit FROM userProfile WHERE user_id = ? ', (ctx.author.id,))][
            0]
        whitelistedUsers = [u[0] for u in
                            c.execute('SELECT whitelistedUser FROM userWhitelist WHERE user_id = ? ', (ctx.author.id,))]

        if whitelistedUsers:
            description = "**Whitelisted Users**\n"
            for user in whitelistedUsers:
                member = ctx.guild.get_member(user)
                description += f"{member.mention}\n"
            description += "\n"
            embed = discord.Embed(title=f"{ctx.author}'s Study Room", description=description)

        else:
            embed = discord.Embed(title=f"{ctx.author}'s Study Room")

        embed.add_field(name="Room Name", value=roomName)
        embed.add_field(name="Room Limit", value=f"{podLimit} Users")
        embed.set_thumbnail(url=ctx.author.avatar_url)
        await ctx.send(embed=embed)

    @commands.command(description="roomreset**\n\nA debug command to clear your study room's cache if something went wrong.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def roomreset(self, ctx):

        textChannel = [r[0] for r in c.execute('SELECT textID FROM textList WHERE user_id = ?', (ctx.author.id,))][
            0]
        textObject = self.bot.get_channel(textChannel)

        voiceChannel = [r[0] for r in c.execute('SELECT voiceID FROM voiceList WHERE user_id = ?', (ctx.author.id,))][
            0]
        voiceObject = self.bot.get_channel(voiceChannel)

        if not voiceObject and not textObject:
            c.execute('UPDATE userProfile SET currentVoice = ?, currentText = ? WHERE user_id = ? ',
                      (0, 0, ctx.author.id))
            conn.commit()
            return await functions.successEmbedTemplate(ctx, "Successfully reset your room!", ctx.author)

        await functions.errorEmbedTemplate(ctx, f"The command can't be used because Study Room is functioning normally.", ctx.author)

    @commands.command(description="whitelist [@user]**\n\nWhitelist a Discord user that can bypass your Study Room Limit. Use again to remove the whitelist.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def whitelist(self, ctx, user: discord.Member):

        if user == ctx.author:
            return await functions.errorEmbedTemplate(ctx, f"You cannot whitelist yourself!", ctx.author)


        try:
            c.execute('INSERT INTO userWhitelist VALUES (?, ?) ', (ctx.author.id, user.id))
            conn.commit()

            c.execute('SELECT currentVoice, currentText FROM userProfile WHERE user_id = ?', (ctx.author.id,))
            currentVoice, currentText = c.fetchall()[0]

            if currentVoice and currentText:
                whitelistedUsers = [u[0] for u in
                                    c.execute('SELECT whitelistedUser FROM userWhitelist WHERE user_id = ? ',
                                              (ctx.author.id,))]

                voiceOverwrites = {
                    user: discord.PermissionOverwrite(move_members=True),
                    ctx.author: discord.PermissionOverwrite(move_members=True),
                    ctx.guild.get_role(role_id=566986562525724692): discord.PermissionOverwrite(move_members=True)
                }
                textOverwrites = {
                    user: discord.PermissionOverwrite(view_channel=True),
                    ctx.author: discord.PermissionOverwrite(view_channel=True),
                    ctx.guild.get_role(role_id=566986562525724692): discord.PermissionOverwrite(view_channel=True),
                    ctx.guild.default_role: discord.PermissionOverwrite(view_channel=False)
                }

                if whitelistedUsers:
                    for u in whitelistedUsers:
                        voiceOverwrites[ctx.guild.get_member(u)] = discord.PermissionOverwrite(
                            move_members=True)
                        textOverwrites[ctx.guild.get_member(u)] = discord.PermissionOverwrite(
                            view_channel=True)

                voiceObject = self.bot.get_channel(currentVoice)
                await voiceObject.edit(overwrites=voiceOverwrites)
                textObject = self.bot.get_channel(currentText)
                await textObject.edit(overwrites=textOverwrites)
            await functions.successEmbedTemplate(ctx, f"Successfully whitelisted {user.mention}. They are now able to join your Study Room freely regardless of room user limit.", ctx.author)

        except sqlite3.IntegrityError:
            c.execute('DELETE FROM userWhitelist WHERE user_id = ? AND whitelistedUser = ? ', (ctx.author.id, user.id))
            conn.commit()
            c.execute('SELECT currentVoice, currentText FROM userProfile WHERE user_id = ?', (ctx.author.id,))
            currentVoice, currentText = c.fetchall()[0]

            if currentVoice and currentText:
                whitelistedUsers = [u[0] for u in
                                    c.execute('SELECT whitelistedUser FROM userWhitelist WHERE user_id = ? ',
                                              (ctx.author.id,))]

                voiceOverwrites = {
                    ctx.author: discord.PermissionOverwrite(move_members=True),
                    user: discord.PermissionOverwrite(move_members=False),
                    ctx.guild.get_role(role_id=566986562525724692): discord.PermissionOverwrite(move_members=True),
                }

                if whitelistedUsers:
                    for u in whitelistedUsers:
                        voiceOverwrites[ctx.guild.get_member(u)] = discord.PermissionOverwrite(
                            move_members=True)

                voiceObject = self.bot.get_channel(currentVoice)
                await voiceObject.edit(overwrites=voiceOverwrites)
            await functions.successEmbedTemplate(ctx, f"Successfully removed {user.mention} from whitelist. They are now unable to bypass your Study Room user limit.", ctx.author)


    @commands.command(description="setlimit [user limit]**\n\nCustomize the user limit of your study room. Type 0 for unlimited.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def setlimit(self, ctx, limit: int):

        if limit < 0 or limit > 99:
            return await functions.errorEmbedTemplate(ctx, f"User Limit can only be between 0 to 99!", ctx.author)

        c.execute('UPDATE userProfile SET podLimit = ? WHERE user_id = ? ', (limit, ctx.author.id))
        conn.commit()
        c.execute('SELECT currentVoice FROM userProfile WHERE user_id = ?', (ctx.author.id, ))
        result = c.fetchall()

        if result[0][0]:
            voiceObject = self.bot.get_channel(result[0][0])
            await voiceObject.edit(user_limit=limit)

        return await functions.successEmbedTemplate(ctx, f"Successfully set your Study Room user limit to **{limit}**.",
                                                    ctx.author)

    @commands.command(description="setroomname [name]**\n\nCustomize the name of your study room.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def setroomname(self, ctx, *, name):

        if len(name) > 30:
            return await functions.errorEmbedTemplate(ctx, f"Please reduce the length of your room name to less than 30 characters.", ctx.author)

        if not re.match("^[a-zA-Z0-9' ]*$", name):
            return await functions.errorEmbedTemplate(ctx, f"Only alphanumeric letters and `'` are allowed!", ctx.author)

        c.execute('UPDATE userProfile SET roomName = ? WHERE user_id = ?', (name, ctx.author.id))
        conn.commit()

        c.execute('SELECT currentVoice, currentText FROM userProfile WHERE user_id = ?', (ctx.author.id,))
        currentVoice, currentText = c.fetchall()[0]

        if currentVoice and currentText:
            voiceObject = self.bot.get_channel(currentVoice)
            await voiceObject.edit(name=name)
            textObject = self.bot.get_channel(currentText)
            await textObject.edit(name=name)

        await functions.successEmbedTemplate(ctx, f"Successfully set your room name to **{name}**.", ctx.author)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):

        joinList = [channel[0] for channel in
                    c.execute(''' SELECT channelID FROM joinChannel WHERE server_id = ? ''', (member.guild.id,))]
        userChannelList = [channel[0] for channel in
                           c.execute(''' SELECT channelID FROM voiceList WHERE server_id = ? ''', (member.guild.id,))]
        categoryList = [channel[0] for channel in
                        c.execute(''' SELECT categoryID FROM channelCategory WHERE server_id = ? ''',
                                  (member.guild.id,))]

        if after.channel and after.channel.id in userChannelList:
            c.execute('SELECT user_id FROM userProfile WHERE currentVoice = ? ', (after.channel.id,))
            result = c.fetchall()[0][0]

            whitelistedUsers = [u[0] for u in
                                c.execute('SELECT whitelistedUser FROM userWhitelist WHERE user_id = ? ',
                                          (result,))]

            textOverwrites = {
                after.channel.guild.get_member(result): discord.PermissionOverwrite(view_channel=True),
                member: discord.PermissionOverwrite(view_channel=True),
                after.channel.guild.get_role(role_id=566986562525724692): discord.PermissionOverwrite(
                    view_channel=True),
                after.channel.guild.default_role: discord.PermissionOverwrite(view_channel=False)
            }

            if whitelistedUsers:
                for user in whitelistedUsers:
                    textOverwrites[after.channel.guild.get_member(user)] = discord.PermissionOverwrite(
                        view_channel=True)

            textID = [r[0] for r in c.execute('SELECT textID FROM textList WHERE voiceID = ? ', (after.channel.id, ))][0]
            textObject = self.bot.get_channel(textID)
            await textObject.edit(overwrites=textOverwrites)

        joinHereChannel = self.bot.get_channel(joinList[0])
        category = self.bot.get_channel(categoryList[0])

        if before.channel and before.channel.id in userChannelList: # Tracks leaver
            c.execute('SELECT user_id FROM userProfile WHERE currentVoice = ? ', (before.channel.id,))
            result = c.fetchall()[0][0]

            if result:
                whitelistedUsers = [u[0] for u in
                                    c.execute('SELECT whitelistedUser FROM userWhitelist WHERE user_id = ? ',
                                              (result,))]

                if result == member.id or result in whitelistedUsers:
                    pass

                else:
                    textOverwrites = {
                        before.channel.guild.get_member(result): discord.PermissionOverwrite(view_channel=True),
                        member: discord.PermissionOverwrite(view_channel=False),
                        before.channel.guild.default_role: discord.PermissionOverwrite(view_channel=False),
                        before.channel.guild.get_role(role_id=566986562525724692): discord.PermissionOverwrite(
                            view_channel=True)
                    }

                    if whitelistedUsers:
                        for user in whitelistedUsers:
                            textOverwrites[before.channel.guild.get_member(user)] = discord.PermissionOverwrite(
                                view_channel=True)

                    textID = [r[0] for r in c.execute('SELECT textID FROM textList WHERE voiceID = ? ', (before.channel.id,))][0]
                    textObject = self.bot.get_channel(textID)
                    await textObject.edit(overwrites=textOverwrites)

            lenMembers = len(before.channel.members)
            if lenMembers == 0: # If nobody is occupying the room, deletes the channel
                await before.channel.delete()
                c.execute(''' DELETE FROM voiceList WHERE channelID = ? ''', (before.channel.id,))
                conn.commit()
                textChannel = [r[0] for r in c.execute('SELECT textID FROM textList WHERE voiceID = ?', (before.channel.id, ))][0]
                textObject = self.bot.get_channel(textChannel)
                await textObject.delete()
                c.execute(''' DELETE FROM textList WHERE voiceID = ? ''', (before.channel.id,))
                conn.commit()
                c.execute('UPDATE userProfile SET currentVoice = ?, currentText = ? WHERE currentVoice = ? ',
                          (0, 0, before.channel.id))
                conn.commit()

        #-------------------------------------------------------------------------------------------------

        if after.channel == joinHereChannel: # Creates a new study room
            # Check if they have an existing room
            c.execute('SELECT currentVoice FROM userProfile WHERE user_id = ?', (member.id,))
            result = c.fetchall()

            if result[0][0]:
                voiceObject = self.bot.get_channel(result[0][0])
                return await member.move_to(voiceObject)

            roomName, podLimit = [[r[0], r[1]] for r in c.execute('SELECT roomName, podLimit FROM userProfile WHERE user_id = ? ', (member.id, ))][0]
            whitelistedUsers = [u[0] for u in c.execute('SELECT whitelistedUser FROM userWhitelist WHERE user_id = ? ', (member.id, ))]

            voiceOverwrites = {
                member: discord.PermissionOverwrite(move_members=True),
                after.channel.guild.get_role(role_id=566986562525724692): discord.PermissionOverwrite(move_members=True)
            }
            textOverwrites = {
                member: discord.PermissionOverwrite(view_channel=True),
                after.channel.guild.default_role: discord.PermissionOverwrite(view_channel=False),
                after.channel.guild.get_role(role_id=566986562525724692): discord.PermissionOverwrite(
                    view_channel=True),
            }

            if whitelistedUsers:
                for user in whitelistedUsers:
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

                c.execute('UPDATE userProfile SET currentVoice = ?, currentText = ? WHERE user_id = ? ',
                          (newVoiceChannel.id, newTextChannel.id, member.id))
                conn.commit()
                c.execute(''' INSERT INTO voiceList VALUES (?, ?) ''',
                          (after.channel.guild.id, newVoiceChannel.id))
                conn.commit()
                c.execute(''' INSERT INTO textList VALUES (?, ?, ?) ''',
                          (after.channel.guild.id, newTextChannel.id, newVoiceChannel.id))
                conn.commit()

            except:
                traceback.print_exc()
                await newVoiceChannel.delete()
                await newTextChannel.delete()
                return







def setup(bot):
    bot.add_cog(voiceCogs(bot))
