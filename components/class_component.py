from dataclasses import dataclass, field
import hikari
import lightbulb
from Database import Database
from typing import List
import yaml

with open("authentication.yaml", "r", encoding="utf8") as stream:
    yaml_data = yaml.safe_load(stream)

plugin = lightbulb.Plugin("Classes")


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

    async def room_closure(self, event: hikari.VoiceStateUpdateEvent):
        voice_delete = await event.app.rest.delete_channel(self.voice_id)
        text_delete = await event.app.rest.delete_channel(self.text_id)
        self.delete_room()
        print(voice_delete)
        print(text_delete)


@dataclass
class Profile:
    user_id: int
    room_name: str = None
    pod_limit: int = None
    current_voice: int = None
    current_text: int = None
    pomodoro_cycle: int = None
    mini_cycle: int = None
    focus_time: int = None
    pomodoro_duration: int = None
    pomodoro_break: int = None
    user_whitelist: List = field(default_factory=list)

    def create_room(self, guild: int, voice: int, text: int):
        Database.execute('UPDATE userProfile SET currentVoice = ?, currentText = ? WHERE userID = ? ', voice, text,
                         self.user_id)
        Database.execute('REPLACE INTO studyRoomList VALUES (?, ?, ?, ?) ', self.user_id, guild, text, voice)

    def delete_room(self):
        Database.execute('DELETE FROM studyRoomList WHERE ownerID = ? ', self.user_id)
        Database.execute('UPDATE userProfile SET currentVoice = ?, currentText = ? WHERE userID = ? ', 0, 0,
                         self.user_id)

    def get_user_whitelist(self):
        data = [i[0] for i in Database.get('SELECT whitelistedUser FROM userWhitelist WHERE userID = ? ', self.user_id)]
        if data:
            self.user_whitelist = data

    def get_user_data(self):
        data = [i for i in Database.get('SELECT * FROM userProfile WHERE userID = ? ', self.user_id)]

        if data:
            self.user_id, self.room_name, self.pod_limit, self.current_voice, self.current_text, \
            self.pomodoro_cycle, self.mini_cycle, self.focus_time, self.pomodoro_duration, self.pomodoro_break = data[0]

    def update_pomodoro_duration(self, minutes: int):
        Database.execute('UPDATE userProfile SET pomodoroDuration = ? WHERE userID = ? ', minutes, self.user_id)
        self.pomodoro_duration = minutes

    def update_pomodoro_break(self, minutes: int):
        Database.execute('UPDATE userProfile SET pomodoroBreak = ? WHERE userID = ? ', minutes, self.user_id)
        self.pomodoro_break = minutes

    def time_transaction(self, focus_duration: int):
        self.get_user_data()
        self.focus_time += focus_duration
        Database.execute('UPDATE userProfile SET focusTime = ? WHERE userID = ? ', self.focus_time, self.user_id)

    async def room_closure(self, event: hikari.VoiceStateUpdateEvent):
        voice_delete = await event.app.rest.delete_channel(self.current_voice)
        text_delete = await event.app.rest.delete_channel(self.current_text)
        study_room_object = StudyRoom(self.current_voice)
        study_room_object.delete_room()
        print(voice_delete)
        print(text_delete)

    async def create_study_room(self, event: hikari.VoiceStateUpdateEvent, server_room_object: ServerRoom):
        text_overwrite = [hikari.PermissionOverwrite(type=hikari.PermissionOverwriteType.ROLE,
                                                     id=event.guild_id,
                                                     deny=hikari.Permissions.VIEW_CHANNEL
                                                     ),
                          hikari.PermissionOverwrite(type=hikari.PermissionOverwriteType.ROLE,
                                                     id=yaml_data['Muted'],
                                                     deny=hikari.Permissions.SEND_MESSAGES
                                                     )]
        self.user_whitelist.append(event.state.member.id)
        guild_object = await event.app.rest.fetch_guild(event.guild_id)
        guild_members = guild_object.get_members()
        text_overwrite += [hikari.PermissionOverwrite(type=hikari.PermissionOverwriteType.MEMBER,
                                                      id=member,
                                                      allow=hikari.Permissions.VIEW_CHANNEL) for member in
                           self.user_whitelist]
        voice_overwrite = [hikari.PermissionOverwrite(type=hikari.PermissionOverwriteType.ROLE,
                                                      id=yaml_data['Muted'],
                                                      deny=hikari.Permissions.SPEAK
                                                      )]
        voice_overwrite += [hikari.PermissionOverwrite(type=hikari.PermissionOverwriteType.MEMBER,
                                                       id=member,
                                                       allow=hikari.Permissions.CONNECT | hikari.Permissions.MOVE_MEMBERS)
                            for member in
                            self.user_whitelist if member in guild_members]

        voice_channel = await event.app.rest.create_guild_voice_channel(guild=event.guild_id,
                                                                        name=f"{self.room_name}",
                                                                        category=server_room_object.category,
                                                                        user_limit=self.pod_limit,
                                                                        permission_overwrites=voice_overwrite)
        text_channel = await event.app.rest.create_guild_text_channel(guild=event.guild_id,
                                                                      name=f"{self.room_name}",
                                                                      category=server_room_object.category,
                                                                      permission_overwrites=text_overwrite)

        ''' Disallow Muted users from bypassing the mute & voice restriction in the server even if they're whitelisted.
            The role ID is hardcoded and in authentication.yaml '''

        self.create_room(event.state.guild_id, voice_channel.id, text_channel.id)

        try:
            await event.state.member.edit(voice_channel=voice_channel)
        except hikari.BadRequestError:
            print(
                f"{event.state.member.username} ({event.state.member.id}) is a bad actor and has left the voice channel"
                f" too fast, hence the room was destroyed.")
            await self.room_closure(event)
            await event.app.rest.delete_channel(voice_channel)
            await event.app.rest.delete_channel(text_channel)
            self.delete_room()


@dataclass
class Tomato:
    user_id: int
    server_id: int
    cycle: int = None
    start_time: int = None
    next_break: int = None
    next_cycle: int = None

    def pomodoro_check(self):
        count = [i[0] for i in
                 Database.get('SELECT COUNT(*) FROM pomodoro WHERE userID = ? AND serverID = ? ', self.user_id,
                              self.server_id)][0]
        return count

    def get_user_data(self):
        data = [i for i in Database.get('SELECT cycle, startTime, nextBreak, nextCycle '
                                        'FROM pomodoro WHERE userID = ? AND serverID = ? ', self.user_id,
                                        self.server_id)]

        if not data:
            return

        self.cycle, self.start_time, self.next_break, self.next_cycle = data[0]

    def cycle_update(self, cycle):
        Database.execute('UPDATE pomodoro SET cycle = ? WHERE userID = ? ', cycle, self.user_id)

    def next_cycle_update(self, cycle):
        Database.execute('UPDATE pomodoro SET nextCycle = ? WHERE userID = ? ', cycle, self.user_id)

    def next_break_update(self, cycle):
        Database.execute('UPDATE pomodoro SET nextBreak = ? WHERE userID = ? ', cycle, self.user_id)

    def mini_cycle_transaction(self, amount):
        cycle = [i[0] for i in Database.get('SELECT miniCycle FROM userProfile WHERE userID = ? ', self.user_id)][0]
        cycle += amount
        Database.execute('UPDATE userProfile SET miniCycle = ? WHERE userID = ? ', cycle, self.user_id)

    def cycle_transaction(self, amount):
        cycle = [i[0] for i in Database.get('SELECT pomodoroCycle FROM userProfile WHERE userID = ? ', self.user_id)][0]
        cycle += amount
        Database.execute('UPDATE userProfile SET pomodoroCycle = ? WHERE userID = ? ', cycle, self.user_id)

    def pomodoro_delete(self):
        Database.execute('DELETE FROM pomodoro WHERE userID = ? AND serverID = ?', self.user_id, self.server_id)


def load(bot):
    bot.add_plugin(plugin)


def unload(bot):
    bot.remove_plugin(plugin)
