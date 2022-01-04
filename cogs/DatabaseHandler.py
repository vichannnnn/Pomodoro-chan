import sqlite3
from discord.ext import commands

conn = sqlite3.connect('bot.db', timeout=5.0)
c = conn.cursor()
conn.row_factory = sqlite3.Row

# ---- Voice Rooms

c.execute(
    '''CREATE TABLE IF NOT EXISTS voiceList (
    serverID INT, 
    channelID INT, 
    UNIQUE(serverID, channelID)
    ) ''')

c.execute(
    '''CREATE TABLE IF NOT EXISTS textList (
    serverID INT, 
    textID INT, 
    voiceID INT, 
    UNIQUE(serverID, textID)
    ) ''')

c.execute(
    '''CREATE TABLE IF NOT EXISTS joinChannel (
    serverID INT PRIMARY KEY, 
    channelID INT
    ) ''')

c.execute(
    '''CREATE TABLE IF NOT EXISTS channelCategory (
    serverID INT PRIMARY KEY, 
    categoryID INT
    ) ''')

# ---- Pomodoro

c.execute('CREATE TABLE IF NOT EXISTS pomodoro '
          '('
          'serverID INT, '
          'channelID INT, '
          'userID INT, '
          'cycle INT,'
          'startTime INT, '
          'nextBreak INT, '
          'nextCycle INT, '
          'UNIQUE(serverID, userID)) '
          '')

# ---- Profile

c.execute('CREATE TABLE IF NOT EXISTS profile '
          '('
          'userID INT PRIMARY KEY, '
          'pomodoroCycle INT,'
          'miniCycle INT,'
          'focusTime INT'
          ')')

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

c.execute(
    '''CREATE TABLE IF NOT EXISTS userProfile (
    userID INT PRIMARY KEY, 
    roomName TEXT, 
    podLimit INT, 
    currentVoice INT,
    currentText INT
    ) ''')

c.execute(
    '''CREATE TABLE IF NOT EXISTS userWhitelist (
    userID INT, 
    whitelistedUser INT, 
    UNIQUE(userID, whitelistedUser)
    ) ''')

# ----



class DatabaseHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

def setup(bot):
    bot.add_cog(DatabaseHandler(bot))