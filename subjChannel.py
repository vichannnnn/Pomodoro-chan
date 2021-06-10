import discord
from discord.ext import commands
from discord.ext.commands import has_permissions
from discord.gateway import EventListener
import cogs.colourEmbed as functions
import traceback
import sqlite3

conn = sqlite3.connect("saved.db", timeout = 5.0)
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS savedQuestions (server_id INT, channel_id INT, channel_name TEXT, id INT, chapters TEXT, image TEXT, question TEXT, answer TEXT, UNIQUE(channel_id, id))')
conn.row_factory = sqlite3.Row


class subjCogs(commands.Cog, name = "🔖 Subject Channels"):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(description = f"save**\n\nSave questions in subject channels (requires permissions).\n\nUsage:\n`p!save \"<question>\" <discussion/answer link> <img if any>`")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @has_permissions(manage_messages = True)
    async def save(self, ctx, qn, ans, img = None):
        channelList = [chnl[0] for chnl in c.execute('SELECT channel_id FROM subjectChannels WHERE server_id = ? ', (ctx.guild.id,))]
        # get channel id
        chnl_id = ctx.message.channel.id
        name = ctx.message.channel.name
        # check if channel is approved
        if chnl_id not in channelList:
            await functions.errorEmbedTemplate(ctx,
                                                f"Unable to save message in <#{chnl_id}>, please ask **Administrators** for help",
                                                ctx.message.author)
            
        else:
            ## create table if not exist
            #c.execute("CREATE TABLE IF NOT EXISTS Chnl" + str(chnl_id) + " (`server_id` INT, `id` INT PRIMARY KEY, `image` TEXT, `question` TEXT,`answer` TEXT)")
            id = 1
            while True:
                try:
                    # if img is provided                                                # server_id channel_id channelname id chapters image question answer
                    if img:
                        c.execute("INSERT INTO savedQuestions VALUES (?, ?, ?, ?, ?, ?, ?, ?) ", (ctx.guild.id, chnl_id, name, id, "not tagged", img, qn, ans))
                    else:
                        c.execute("INSERT INTO savedQuestions VALUES (?, ?, ?, ?, ?, ?, ?, ?) ", (ctx.guild.id, chnl_id, name, id, "not tagged", "no image", qn, ans))
                    conn.commit()
                    break
                except sqlite3.IntegrityError:
                    id += 1
                    continue
            await functions.successEmbedTemplate(ctx,
                                                 f"Successfully saved question and answer in <#{chnl_id}>", 
                                                 ctx.message.author)
        
    @commands.command(description = f"tag**\n\nTag questions with their topics (requires permissions).\n\nUsage:\n`p!tag <qn id>\n\"<topic1,topic2,...>\"`")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @has_permissions(manage_messages = True)
    async def tag(self, ctx, id, topics):
        # get channel id
        chnl_id = ctx.message.channel.id
        try:
            c.execute("UPDATE savedQuestions SET chapters = ? WHERE server_id = ? AND channel_id = ? AND id = ? ", (topics, ctx.guild.id, chnl_id, id))
            conn.commit()
            await functions.successEmbedTemplate(ctx,
                                                 f"Successfully set `{topics}` as tags to <#{chnl_id}> question:`{id}`.",
                                                 ctx.message.author)
        except sqlite3.IntegrityError:
            await functions.errorEmbedTemplate(ctx,
                                                f"Unable to set tag for question in <#{chnl_id}>, check again and ping <@624251187277070357>/<@345945337770410006> for help if problem persists.",
                                                ctx.message.author)

    @commands.command(description = f"qdel**\n\nDeletes the question associated with an id.\n\nUsage: `p!qdel <id>`")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @has_permissions(manage_messages = True)
    async def qdel(self, ctx, id):
        #get channel id
        chnl_id = ctx.message.channel.id
        c.execute("DELETE FROM savedQuestions WHERE id = ? AND channel_id = ?", (id, chnl_id))
        conn.commit()
        await functions.successEmbedTemplate(ctx,
                                            f"Successfully deleted question and answer in <#{chnl_id}> with `id = {id}`", 
                                            ctx.message.author)


    @commands.command(description = f"question**\n\nReceive a random question in the subject channel `p!question` is used in.\n\nUsage:\n`p!question <id if any>`")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def question(self, ctx, id = None):
        # get channel id
        chnl_id = ctx.message.channel.id
        # if no id provided
        if not id:
            c.execute("SELECT id, chapters, image, question, answer FROM savedQuestions WHERE channel_id = ? ORDER BY RANDOM() LIMIT 1", (chnl_id,))
        else:
            c.execute("SELECT id, chapters, image, question, answer FROM savedQuestions WHERE id = ? AND channel_id = ?", (id, chnl_id))
        try: 
            num, tag, img, qn, ans = c.fetchall()[0]
            description = f"__**Question from <#{chnl_id}>**__\n\n{qn}\n\nDiscussion and Answer: ||{ans}||\n\nChapters: `{tag}`"
            # 0xdecaf0 R: 222 G: 202 B:240
            embed = discord.Embed(description=description, color = discord.Colour.from_rgb(222,202,240))
            if img != "no image":
                embed.set_image(url = img)
            # vio lemme keep this pls 😭
            if ctx.message.author.id == 345945337770410006:
                embed.set_footer(text=f"🥶Requested by {ctx.message.author}\nid: {num}", icon_url=ctx.message.author.avatar_url)
            else:
                embed.set_footer(text=f"Requested by {ctx.message.author}\nid: {num}", icon_url=ctx.message.author.avatar_url)
            await ctx.send(embed=embed)
        except IndexError:
            await functions.errorEmbedTemplate(ctx,
                                                f"Failed to retrieve <#{chnl_id}> with `id = {id}`, question might have been deleted.",
                                                ctx.message.author)

    
    @commands.command(description = f"bank**\n\nRequest for spreadsheet link of all the saved questions from SGExams.\n\nUsage:\n`p!bank`")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def bank(self, ctx):
        spreadsheet = "placeholder_link"
        await functions.successEmbedTemplate(ctx,
                                             f"All questions can be found in this link:\n{spreadsheet}\nRequest for navigation help if needed.",
                                             ctx.message.author)

def setup(bot):
    bot.add_cog(subjCogs(bot))