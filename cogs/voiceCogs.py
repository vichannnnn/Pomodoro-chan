import re
import traceback
import discord
import yaml
from discord.ext import commands
import cogs.colourEmbed as functions
from cogs.DisplayHandler import Confirm
from Database import Database
import math

with open("authentication.yml", "r", encoding="utf8") as stream:
    yaml_data = yaml.safe_load(stream)

def profileCreate(user):
    try:
        Database.execute('''INSERT INTO userProfile VALUES (?, ?, ?, ?, ?)''', user.id, f"{user.name}'s Room", 0, 0, 0)
    except:
        traceback.print_exc()

class User:
    def __init__(self, user):
        self.User = user
        self.Info = [i for i in Database.get('SELECT * FROM userProfile WHERE userID = ? ', self.User)][0] if \
            [i for i in Database.get('SELECT * FROM userProfile WHERE userID = ? ', self.User)] else None
        self.RoomName = self.Info[1] if self.Info else None
        self.PodLimit = self.Info[2] if self.Info else None
        self.VoiceChannel = self.Info[3] if self.Info else None
        self.TextChannel = self.Info[4] if self.Info else None

    def Whitelist(self):
        whitelistedUsers = [i[0] for i in Database.get('SELECT whitelistedUser FROM userWhitelist WHERE userID = ? ', self.User)] if \
            [i[0] for i in Database.get('SELECT COUNT(*) FROM userWhitelist WHERE userID = ? ', self.User)][0] else []
        return whitelistedUsers

class Room:
    def __init__(self):
        self.Owner = None
        self.TextChannel = None
        self.VoiceChannel = None

    def get_text_channel(self, voiceChannel):
        self.VoiceChannel = voiceChannel
        text = [i[0] for i in Database.get('SELECT currentText FROM userProfile WHERE currentVoice = ? ', self.VoiceChannel)]

        if text:
            self.TextChannel = text[0]
        return False

    def get_room_owner(self, voiceChannel):
        self.VoiceChannel = voiceChannel
        user = [i[0] for i in
                Database.get('SELECT userID FROM userProfile WHERE currentVoice = ? ', self.VoiceChannel)]

        if user:
            self.Owner = user[0]
        return False

class Server:
    def __init__(self, guild):
        self.Guild = guild
        self.VoiceChannels = [i[0] for i in Database.get('SELECT voiceID FROM textList WHERE serverID = ? ', self.Guild)]
        self.TextChannels = [i[0] for i in Database.get('SELECT textID FROM textList WHERE serverID = ? ', self.Guild)]
        self.JoinChannel = [i[0] for i in
                            Database.get('SELECT channelID FROM joinChannel WHERE serverID = ?', self.Guild)][0] if \
            [i[0] for i in Database.get('SELECT channelID FROM joinChannel WHERE serverID = ?', self.Guild)] else None
        self.Category = [i[0] for i in
                            Database.get('SELECT categoryID FROM channelCategory WHERE serverID = ?', self.Guild)][0] if \
            [i[0] for i in Database.get('SELECT categoryID FROM channelCategory WHERE serverID = ?', self.Guild)] else None

class Pages(discord.ui.View):
    def __init__(self, ctx, data):
        super().__init__()
        self.timeout = 60
        self.value = 1
        self.ctx = ctx
        self.data = data
        self.pages = math.ceil(len(self.data) / 10)

    async def interaction_check(self, interaction):
        self.message = interaction.message
        return interaction.user.id == self.ctx.author.id

    @discord.ui.button(label="Previous Page", emoji="⏪")
    async def left(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.value -= 1
        if self.value <= 0 or self.value > self.pages:
            embed = discord.Embed(description=f"You have reached the end of the pages.")
            if self.ctx.guild.icon:
                embed.set_thumbnail(url=self.ctx.guild.icon.url)
            else:
                pass
            embed.set_footer(text=f"Press '⏩' to go back.", icon_url=self.ctx.author.display_avatar.url)

            if self.value < 0:
                self.value += 1
            await self.message.edit(embed=embed)

        else:
            everyPage = [item for item in self.data[10 * (self.value - 1):self.value * 10]]
            description = "**Whitelisted Users**\n"

            for user in everyPage:
                member = self.ctx.guild.get_member(user)
                if member:
                    description += f"{member.mention}\n"

            UserObject = User(self.ctx.author.id)
            embed = discord.Embed(title=f"{self.ctx.author}'s Study Room", description=description)
            embed.add_field(name="Room Name", value=UserObject.RoomName)
            embed.add_field(name="Room Limit", value=f"{UserObject.PodLimit} Users")
            embed.set_thumbnail(url=self.ctx.author.display_avatar.url)
            if self.ctx.guild.icon:
                embed.set_thumbnail(url=self.ctx.guild.icon.url)
            else:
                pass
            embed.set_footer(text=f"Page {self.value} of {self.pages}", icon_url=self.ctx.author.display_avatar.url)
            await self.message.edit(embed=embed, view=self)

    @discord.ui.button(label="Next Page", emoji="⏩")
    async def right(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.value += 1

        if self.value > self.pages:
            embed = discord.Embed(description=f"You have reached the end of the pages.")
            if self.ctx.guild.icon:
                embed.set_thumbnail(url=self.ctx.guild.icon.url)
            else:
                pass
            embed.set_footer(text=f"Press '⏩' to go back.", icon_url=self.ctx.author.display_avatar.url)

            if self.value > self.pages + 1:
                self.value -= 1
            await self.message.edit(embed=embed)

        else:
            everyPage = [item for item in self.data[10 * (self.value - 1):self.value * 10]]
            description = "**Whitelisted Users**\n"

            for user in everyPage:
                member = self.ctx.guild.get_member(user)
                if member:
                    description += f"{member.mention}\n"

            UserObject = User(self.ctx.author.id)
            embed = discord.Embed(title=f"{self.ctx.author}'s Study Room", description=description)
            embed.add_field(name="Room Name", value=UserObject.RoomName)
            embed.add_field(name="Room Limit", value=f"{UserObject.PodLimit} Users")
            embed.set_thumbnail(url=self.ctx.author.display_avatar.url)
            if self.ctx.guild.icon:
                embed.set_thumbnail(url=self.ctx.guild.icon.url)
            else:
                pass
            embed.set_footer(text=f"Page {self.value} of {self.pages}", icon_url=self.ctx.author.display_avatar.url)
            await self.message.edit(embed=embed, view=self)

    @discord.ui.button(label="Exit", style=discord.ButtonStyle.red, emoji="❎")
    async def cancel(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.clear_items()
        self.add_item(item=discord.ui.Button(emoji="❎", label="Command Closed",
                                             style=discord.ButtonStyle.red, disabled=True))
        await self.message.edit(view=self)
        await interaction.response.send_message("Command closed successfully. Interface will close in 5 seconds.",
                                                ephemeral=True)
        self.stop()

    async def on_timeout(self) -> None:
        self.clear_items()
        self.add_item(item=discord.ui.Button(emoji="❎", label="Command Closed",
                                             style=discord.ButtonStyle.red, disabled=True))
        await self.message.edit(view=self)
        self.stop()


class VoiceCogs(commands.Cog, name='🏡 Study Rooms'):
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

    @commands.command(brief="Knocks on a user's study room. Has a cooldown of 30 minutes.",
                      description="knock [@User]**\n\nKnocks on a user's study room. Has a cooldown of 30 minutes.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def knock(self, ctx, user: discord.Member):

        if user == ctx.author:
            ctx.command.reset_cooldown(ctx)
            return await ctx.send(f"{ctx.author.mention}, Why are you trying to knock on your own door?")

        voice_state = ctx.author.voice

        if not voice_state:
            ctx.command.reset_cooldown(ctx)
            return await ctx.send('You need to be in a voice channel to use this command.')

        UserObject = User(user.id)
        whitelistedUsers = UserObject.Whitelist()

        if ctx.author.id in whitelistedUsers:
            ctx.command.reset_cooldown(ctx)
            return await ctx.send(f"You already have access to their room. There is no need to knock on their door.")

        if not UserObject.VoiceChannel or not UserObject.TextChannel:
            ctx.command.reset_cooldown(ctx)
            return await ctx.send(f"There is no door for you to knock on, sadly.")

        confirm = Confirm(ctx, 10, user)
        description = f"{user.mention}, Knock knock, who's there? {ctx.author.mention} would like to join your room, confirm entry?"
        confirm.message = await ctx.send(content=description, view=confirm)
        await confirm.wait()

        if confirm.value:
            voice_state = ctx.author.voice
            if not voice_state:
                ctx.command.reset_cooldown(ctx)
                return await ctx.send(f'{ctx.author.mention}, you need to be in a voice channel to be moved over.')
            voiceObject = self.bot.get_channel(UserObject.VoiceChannel)
            await ctx.author.move_to(voiceObject)
            await ctx.send(f"{ctx.author.mention}, you have entered their home, yay!")

        else:
            return await ctx.send(f"{ctx.author.mention}, how unfortunate. The owner of the room had shut their door on you. Sad.")


    @commands.command(brief="Checks your Study Room's Information.",
                      description="roominfo**\n\nChecks your Study Room's Information.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def roominfo(self, ctx):

        UserObject = User(ctx.author.id)
        whitelistedUsers = [i for i in UserObject.Whitelist() if ctx.guild.get_member(i)]

        if whitelistedUsers:
            description = "**Whitelisted Users**\n"
            i = 1
            everyPage = [item for item in whitelistedUsers[10 * (i - 1):i * 10]]

            for user in everyPage:
                member = ctx.guild.get_member(user)
                if member:
                    description += f"{member.mention}\n"

            embed = discord.Embed(title=f"{ctx.author}'s Study Room", description=description)
            embed.set_footer(text=f"Page {i} of {math.ceil(len(whitelistedUsers) / 10)}", icon_url=ctx.author.display_avatar.url)
            embed.add_field(name="Room Name", value=UserObject.RoomName)
            embed.add_field(name="Room Limit", value=f"{UserObject.PodLimit} Users")
            embed.set_thumbnail(url=ctx.author.display_avatar.url)
            view = Pages(ctx, whitelistedUsers)
            view.message = await ctx.send(embed=embed, view=view)
        else:
            embed = discord.Embed(title=f"{ctx.author}'s Study Room")
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
            return await functions.errorEmbedTemplate(ctx, f"{ctx.author.mention}, Why are you trying to whitelist yourself?", ctx.author)

        UserObject = User(ctx.author.id)
        whitelistedUsers = UserObject.Whitelist()

        if user.id in whitelistedUsers:
            Database.execute('DELETE FROM userWhitelist WHERE userID = ? AND whitelistedUser = ? ', ctx.author.id,
                             user.id)
            whitelistedUsers = UserObject.Whitelist()

            # --- Handles room edit if there is a room active ---
            if UserObject.VoiceChannel or UserObject.TextChannel:
                voiceOverwrites = {
                    ctx.author: discord.PermissionOverwrite(move_members=True),
                    user: discord.PermissionOverwrite(move_members=False),
                }

                textOverwrites = {
                    user: discord.PermissionOverwrite(view_channel=False),
                    ctx.author: discord.PermissionOverwrite(view_channel=True),
                    ctx.guild.default_role: discord.PermissionOverwrite(view_channel=False)
                }

                if ctx.guild.get_role(yaml_data['Moderators']):
                    voiceOverwrites[ctx.guild.get_role(yaml_data['Moderators'])] = discord.PermissionOverwrite(view_channel=True)
                    textOverwrites[ctx.channel.guild.get_role(yaml_data['Moderators'])] = discord.PermissionOverwrite(view_channel=True)

                if whitelistedUsers:
                    for u in whitelistedUsers:
                        member = ctx.guild.get_member(u)
                        if member:
                            voiceOverwrites[ctx.guild.get_member(u)] = discord.PermissionOverwrite(
                                move_members=True)
                            textOverwrites[ctx.guild.get_member(u)] = discord.PermissionOverwrite(
                                view_channel=True)

                try:
                    voiceObject = self.bot.get_channel(UserObject.VoiceChannel)
                    await voiceObject.edit(overwrites=voiceOverwrites)
                    textObject = self.bot.get_channel(UserObject.TextChannel)
                    await textObject.edit(overwrites=textOverwrites)
                except:
                    traceback.print_exc()
            # --- Handles room edit if there is a room active ---
            return await functions.successEmbedTemplate(ctx,
                                                        f"How sad, you've removed {user.mention} from your room's whitelist.",
                                                        ctx.author)

        else:
            Database.execute('INSERT INTO userWhitelist VALUES (?, ?) ', ctx.author.id, user.id)
            # --- Handles room edit if there is a room active ---
            if UserObject.VoiceChannel or UserObject.TextChannel:
                voiceOverwrites = {
                    user: discord.PermissionOverwrite(move_members=True),
                    ctx.author: discord.PermissionOverwrite(move_members=True),
                }
                textOverwrites = {
                    user: discord.PermissionOverwrite(view_channel=True),
                    ctx.author: discord.PermissionOverwrite(view_channel=True),
                    ctx.guild.default_role: discord.PermissionOverwrite(view_channel=False)
                }

                if ctx.guild.get_role(yaml_data['Moderators']):
                    voiceOverwrites[ctx.guild.get_role(yaml_data['Moderators'])] = discord.PermissionOverwrite(view_channel=True)
                    textOverwrites[ctx.channel.guild.get_role(yaml_data['Moderators'])] = discord.PermissionOverwrite(view_channel=True)

                if whitelistedUsers:
                    for u in whitelistedUsers:
                        member = ctx.guild.get_member(u)
                        if member:
                            voiceOverwrites[ctx.guild.get_member(u)] = discord.PermissionOverwrite(
                                move_members=True)
                            textOverwrites[ctx.guild.get_member(u)] = discord.PermissionOverwrite(
                                view_channel=True)

                try:
                    voiceObject = self.bot.get_channel(UserObject.VoiceChannel)
                    await voiceObject.edit(overwrites=voiceOverwrites)
                    textObject = self.bot.get_channel(UserObject.TextChannel)
                    await textObject.edit(overwrites=textOverwrites)
                except:
                    traceback.print_exc()
            # --- Handles room edit if there is a room active ---
            await functions.successEmbedTemplate(ctx,
                                                 f"You've whitelisted {user.mention}. "
                                                 f"They are now able to join your Study Room freely, yay!",
                                                 ctx.author)

    @commands.command(brief="Customize the user limit of your study room.",
                      description="setlimit [User Limit]**\n\n"
                                  "Customize the user limit of your study room. "
                                  "Type 0 for unlimited. Has a cooldown of 30 minutes.")
    @commands.cooldown(1, 1800, commands.BucketType.user)
    async def setlimit(self, ctx, limit: int):

        if limit < 0 or limit > 99:
            self.bot.get_command(ctx.command.name).reset_cooldown(ctx)
            return await functions.errorEmbedTemplate(ctx, f"Room's capacity can only be between 0 to 99.", ctx.author)

        Database.execute('UPDATE userProfile SET podLimit = ? WHERE userID = ? ', limit, ctx.author.id)
        UserObject = User(ctx.author.id)

        if UserObject.VoiceChannel:
            voiceObject = self.bot.get_channel(UserObject.VoiceChannel)
            await voiceObject.edit(user_limit=limit)
        return await functions.successEmbedTemplate(ctx, f"You've set your Study Room's capacity to **{limit}** users.",
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
            return await functions.errorEmbedTemplate(ctx, f"Only alphanumeric and `'` symbol are allowed.", ctx.author)

        Database.execute('UPDATE userProfile SET roomName = ? WHERE userID = ?', name, ctx.author.id)
        UserObject = User(ctx.author.id)

        if UserObject.VoiceChannel and UserObject.TextChannel:
            voiceObject = self.bot.get_channel(UserObject.VoiceChannel)
            textObject = self.bot.get_channel(UserObject.TextChannel)
            if voiceObject and textObject:
                await voiceObject.edit(name=name)
                await textObject.edit(name=name)
                return await functions.successEmbedTemplate(ctx,
                                                            f"You've set your room name to **{name}**. "
                                                            f"Your room's name has also been updated.",
                                                            ctx.author)
        return await functions.successEmbedTemplate(ctx,
                                                    f"You've set your room name to **{name}**. "
                                                    f"The changes will be reflected once you open a new room.",
                                                    ctx.author)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):

        ServerObject = Server(member.guild.id)
        joinHereChannel = self.bot.get_channel(ServerObject.JoinChannel)
        category = self.bot.get_channel(ServerObject.Category)

        # If trying to create new channel and joining from any other room, kick the user out.
        if after.channel and before.channel:
            if after.channel == joinHereChannel:
                await member.move_to(None)

        if after.channel:
            if after.channel == joinHereChannel:  # Creates a new study room if they joined here.
                # Check if they have an existing room
                UserObject = User(member.id)
                whitelistedUsers = UserObject.Whitelist()

                if UserObject.VoiceChannel:
                    voiceObject = self.bot.get_channel(UserObject.VoiceChannel)
                    return await member.move_to(voiceObject)

                # Adds the permission for a new voice room and text room.
                voiceOverwrites = {
                    member: discord.PermissionOverwrite(move_members=True),
                }
                textOverwrites = {
                    member: discord.PermissionOverwrite(view_channel=True),
                    after.channel.guild.default_role: discord.PermissionOverwrite(view_channel=False),
                }

                if after.channel.guild.get_role(yaml_data['Moderators']):
                    voiceOverwrites[
                        after.channel.guild.get_role(yaml_data['Moderators'])] = discord.PermissionOverwrite(
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

                newVoiceChannel = await after.channel.guild.create_voice_channel(name=UserObject.RoomName,
                                                                                 user_limit=UserObject.PodLimit, category=category,
                                                                                 overwrites=voiceOverwrites)
                newTextChannel = await after.channel.guild.create_text_channel(name=UserObject.RoomName,
                                                                               category=category,
                                                                               overwrites=textOverwrites)

                try:
                    await member.move_to(newVoiceChannel)
                    Database.execute('UPDATE userProfile SET currentVoice = ?, currentText = ? WHERE userID = ? ',
                                     newVoiceChannel.id, newTextChannel.id, member.id)
                    Database.execute(''' INSERT INTO textList VALUES (?, ?, ?) ''',
                                     after.channel.guild.id, newTextChannel.id, newVoiceChannel.id)

                except:
                    traceback.print_exc()
                    await newVoiceChannel.delete()
                    await newTextChannel.delete()
                    return

            else:
                # If joining a study room.
                if after.channel and after.channel.id in ServerObject.VoiceChannels:
                    RoomObject = Room()
                    RoomObject.get_room_owner(after.channel.id)
                    RoomObject.get_text_channel(after.channel.id)
                    UserObject = User(RoomObject.Owner)

                    # Set the permission to disable normal users, enable room owner and enable the new joiner to access the text channel.
                    textOverwrites = {
                        after.channel.guild.get_member(RoomObject.Owner): discord.PermissionOverwrite(
                            view_channel=True),
                        member: discord.PermissionOverwrite(view_channel=True),
                        after.channel.guild.default_role: discord.PermissionOverwrite(view_channel=False)
                    }

                    # Set the permission for moderator, if it exists, to view the channel.
                    if after.channel.guild.get_role(yaml_data['Moderators']):
                        textOverwrites[
                            after.channel.guild.get_role(yaml_data['Moderators'])] = discord.PermissionOverwrite(
                            view_channel=True)

                    # Sets the permission for all other members currently in the room to be able to view the text channel.
                    for member in after.channel.members:
                        textOverwrites[member] = discord.PermissionOverwrite(view_channel=True)

                    # Sets the permission for all whitelisted users to be able to see the text channel anytime.
                    whitelistedUsers = UserObject.Whitelist()
                    if whitelistedUsers:
                        for user in whitelistedUsers:
                            if after.channel.guild.get_member(user):
                                textOverwrites[after.channel.guild.get_member(user)] = discord.PermissionOverwrite(
                                    view_channel=True)

                    textObject = self.bot.get_channel(RoomObject.TextChannel)
                    await textObject.edit(overwrites=textOverwrites)


        # If leaving a study room.
        if before.channel:
            if before.channel.id in ServerObject.VoiceChannels:
                lenMembers = len(before.channel.members)
                RoomObject = Room()
                RoomObject.get_text_channel(before.channel.id)
                RoomObject.get_room_owner(before.channel.id)
                # If nobody is occupying the room, deletes the channel
                if lenMembers == 0:
                    await before.channel.delete()

                    textObject = self.bot.get_channel(RoomObject.TextChannel)
                    await textObject.delete()

                    Database.execute(''' DELETE FROM textList WHERE voiceID = ? ''', before.channel.id)
                    Database.execute('UPDATE userProfile SET currentVoice = ?, currentText = ? WHERE currentVoice = ? ',
                                     0, 0, before.channel.id)

                # If there are still members in the channel.
                else:
                    UserObject = User(RoomObject.Owner)
                    whitelistedUsers = UserObject.Whitelist()

                    # Set the permission to disable normal users, enable room owner and enable the new joiner to access the text channel.
                    textOverwrites = {
                        before.channel.guild.get_member(RoomObject.Owner): discord.PermissionOverwrite(view_channel=True),
                        member: discord.PermissionOverwrite(view_channel=False),
                        before.channel.guild.default_role: discord.PermissionOverwrite(view_channel=False),
                    }

                    # Set the permission to enable room owner and new joiner to access the voice channel.
                    voiceOverwrites = {
                        before.channel.guild.get_member(RoomObject.Owner): discord.PermissionOverwrite(move_members=True)
                    }

                    # Set the permission for moderators to access both text and voice channels.
                    if before.channel.guild.get_role(yaml_data['Moderators']):
                        voiceOverwrites[before.channel.guild.get_role(yaml_data['Moderators'])] = discord.PermissionOverwrite(move_members=True)
                        textOverwrites[before.channel.guild.get_role(yaml_data['Moderators'])] = discord.PermissionOverwrite(view_channel=True)

                    # Set the permission for all existing room members to access the text channel.
                    for member in before.channel.members:
                        textOverwrites[member] = discord.PermissionOverwrite(view_channel=True)

                    # Set the permission for all whitelisted users to access the text and voice channel.
                    if whitelistedUsers:
                        for user in whitelistedUsers:
                            if before.channel.guild.get_member(user):
                                textOverwrites[
                                    before.channel.guild.get_member(user)] = discord.PermissionOverwrite(
                                    view_channel=True)
                                voiceOverwrites[
                                    before.channel.guild.get_member(user)] = discord.PermissionOverwrite(
                                    move_members=True)

                    textObject = self.bot.get_channel(RoomObject.TextChannel)
                    await textObject.edit(overwrites=textOverwrites)



def setup(bot):
    bot.add_cog(VoiceCogs(bot))
