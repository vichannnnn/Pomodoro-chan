import sqlite3

conn = sqlite3.connect('bot.db', timeout=5.0)
c = conn.cursor()
conn.row_factory = sqlite3.Row

# ---- Voice Rooms

c.execute(
    '''CREATE TABLE IF NOT EXISTS userWhitelist (
    userID INT, 
    whitelistedUser INT, 
    UNIQUE(userID, whitelistedUser)
    ) ''')

c.execute(
    '''CREATE TABLE IF NOT EXISTS studyRoomList (
    ownerID INT, 
    serverID INT, 
    textID INT, 
    voiceID INT, 
    UNIQUE(ownerID, serverID)
    ) ''')

c.execute(
    '''CREATE TABLE IF NOT EXISTS serverSettings (
    serverID INT PRIMARY KEY, 
    channelID INT,
    categoryID INT
    ) ''')

# ---- Pomodoro

c.execute(
    'CREATE TABLE IF NOT EXISTS pomodoro '
    '('
    'serverID INT, '
    'channelID INT, '
    'userID INT, '
    'cycle INT,'
    'startTime INT, '
    'nextBreak INT, '
    'nextCycle INT, '
    'UNIQUE(serverID, userID)'
    ') ''')

# ---- Profile

c.execute(
    '''CREATE TABLE IF NOT EXISTS userProfile (
    userID INT PRIMARY KEY, 
    roomName TEXT, 
    podLimit INT DEFAULT 0, 
    currentVoice INT DEFAULT 0,
    currentText INT DEFAULT 0,
    pomodoroCycle INT DEFAULT 0,
    miniCycle INT DEFAULT 0,
    focusTime INT DEFAULT 0,
    pomodoroDuration INT DEFAULT 30,
    pomodoroBreak INT DEFAULT 5
    ) ''')

# ---- Study

c.execute(
    'CREATE TABLE IF NOT EXISTS focusSettings ('
    'serverID INT PRIMARY KEY, '
    'roleID INT) '
    '')

c.execute(
    'CREATE TABLE IF NOT EXISTS focusChannels ('
    'serverID INT, '
    'channelID INT, '
    'UNIQUE(serverID, channelID)) '
    '')

c.execute(
    'CREATE TABLE IF NOT EXISTS focusUsers ('
    'serverID INT, '
    'userID INT, '
    'startTime INT, '
    'UNIQUE(serverID, userID)'
    ')')

# ---- Confession
c.execute(
    'CREATE TABLE IF NOT EXISTS confessionChannels ('
    'serverID INT, '
    'channelID INT, '
    'UNIQUE(serverID, channelID))'
    '')

c.execute(
    'CREATE TABLE IF NOT EXISTS confessions ('
    'serverID INT, '
    'userID INT, '
    'confessionID INT)'
)

class Database:
    @staticmethod
    def connect():
        conn = sqlite3.connect('bot.db', timeout=5.0)
        c = conn.cursor()
        return c

    @staticmethod
    def execute(statement, *args):
        c = Database.connect()
        c.execute(statement, args)
        c.connection.commit()
        c.connection.close()

    @staticmethod
    def get(statement, *args):
        c = Database.connect()
        c.execute(statement, args)
        res = c.fetchall()
        c.connection.close()
        return res
