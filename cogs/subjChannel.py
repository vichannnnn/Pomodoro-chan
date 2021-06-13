import discord
from discord.ext import commands
from discord.ext.commands import has_permissions
from discord.gateway import EventListener
import cogs.colourEmbed as functions
import traceback
import sqlite3

conn = sqlite3.connect("saved.db", timeout = 5.0)
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS savedQuestions (server_id INT, channel_id INT, channel_name TEXT, id INT, image TEXT, question TEXT, answer TEXT)')
conn.row_factory = sqlite3.Row


class subjCogs(commands.Cog, name = "🔖 Subject Channels"):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(description = f"save**\n\nSave questions in subject channels (requires permissions).\n\nUsage:\n`p!save \"<question>\" <discussion/answer link> <img if any>`\n\n`question` should be quoted")
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
                    # if img is provided                                                # server_id channel_id channelname id image question answer
                    if img:
                        c.execute("INSERT INTO savedQuestions VALUES (?, ?, ?, ?, ?, ?, ?) ", (ctx.guild.id, chnl_id, name, id, img, qn, ans))
                    else:
                        c.execute("INSERT INTO savedQuestions VALUES (?, ?, ?, ?, ?, ?, ?) ", (ctx.guild.id, chnl_id, name, id, "no image", qn, ans))
                    conn.commit()
                    break
                except sqlite3.IntegrityError:
                    id += 1
                    continue
            await functions.successEmbedTemplate(ctx,
                                                 f"Successfully saved question and answer in <#{chnl_id}>", 
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

    @commands.command(description = f"question**\n\nReceive a random question in the subject channel `p!question` is used in.\n\n Usage:\n`p!question <id if any>`")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def question(self, ctx, id = None):
        # get channel id
        chnl_id = ctx.message.channel.id
        # if no id provided
        if not id:
            c.execute("SELECT id, image, question, answer FROM savedQuestions WHERE channel_id = ? ORDER BY RANDOM() LIMIT 1", (chnl_id,))
        else:
            c.execute("SELECT id, image, question, answer FROM savedQuestions WHERE id = ? AND channel_id = ?", (id, chnl_id))
        try: 
            num, img, qn, ans = c.fetchall()[0]
            description = f"__**Question from <#{chnl_id}>**__\n\n{qn}\n\nDiscussion and Answer: ||{ans}||"
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


def setup(bot):
    bot.add_cog(subjCogs(bot))