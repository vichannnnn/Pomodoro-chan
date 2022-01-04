import discord
from discord.ext import commands
from discord.ext.commands import has_permissions
import cogs.colourEmbed as functions
import sqlite3
import gspread

conn = sqlite3.connect("saved.db", timeout=5.0)
c = conn.cursor()
c.execute(
    'CREATE TABLE IF NOT EXISTS savedQuestions (server_id INT, channel_id INT, channel_name TEXT, id INT, chapters TEXT, image TEXT, question TEXT, answer TEXT, UNIQUE(channel_id, id))')
conn.row_factory = sqlite3.Row

SCOPES = ['https://www.googleapis.com/auth/drive']
headers = [['Topic'], ['ID'], ['Chapter'], ['Image'], ['Question'], ['Answer']]
gc = gspread.service_account(filename="token.json", scopes=SCOPES)
spreadsheet = gc.open_by_key("1BiJnc8-R7Dy7HWWTGWbZeG7HYD6DNDEAiHij0Gf61Co")
sht1 = spreadsheet.sheet1

def newTopic(name):
    ns = spreadsheet.add_worksheet(title=name, rows="100", cols="20")
    ns.update('A1:F1', headers, major_dimension="columns")
    ns.format('A1:F1', {"textFormat": {"bold": True}})

def nextAvailableRow(worksheet):
    str_list = list(worksheet.col_values(1))

    try:
        i = str_list.index('')

    except ValueError:
        str_list = list(filter(None, worksheet.col_values(1)))
        return str(len(str_list) + 1)
    return i + 1


def addQuestion(topic, id, chapter, image, question, answer):
    worksheet = spreadsheet.worksheet(topic)
    n = nextAvailableRow(worksheet)
    worksheet.update(f'A{n}:F{n}', [[topic], [id], [chapter], [image], [question], [answer]], major_dimension="columns")
    worksheet.sort((2, 'asc'), range='B2:F1000')


def deleteQuestion(topic, id):
    worksheet = spreadsheet.worksheet(topic)
    values_list = worksheet.find(str(id), in_column=2)
    worksheet.delete_rows(values_list.row)
    worksheet.sort((2, 'asc'), range='B2:F1000')


class subjCogs(commands.Cog, name="🔖 Subject Channels"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(brief="Save questions in subject channels. Requires Manage Message.",
        description=f"save**\n\nSave questions in subject channels. Requires Manage Message.\n\n"
                    f"Usage:\n`p!save <chapter>\"<question>\" <discussion/answer link> <img if any>`")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @has_permissions(manage_messages=True)
    async def save(self, ctx, chapter, qn, ans, img=None):
        channelList = [chnl[0] for chnl in
                       c.execute('SELECT channel_id FROM subjectChannels WHERE server_id = ? ', (ctx.guild.id,))]
        # get channel id
        chnl_id = ctx.message.channel.id
        name = ctx.message.channel.name
        # check if channel is approved
        if chnl_id not in channelList:
            await functions.errorEmbedTemplate(ctx,
                                               f"Unable to save message in <#{chnl_id}>, please ask **Administrators** for help.",
                                               ctx.message.author)
        elif img and (".png" not in img and ".jpg" not in img):
            await functions.errorEmbedTemplate(ctx,
                                               f"That seems wrong, your image is not in `.png` or `.jpg` format, please check again.",
                                               ctx.message.author)
        else:
            ## create table if not exist
            # c.execute("CREATE TABLE IF NOT EXISTS Chnl" + str(chnl_id) + " (`server_id` INT, `id` INT PRIMARY KEY, `image` TEXT, `question` TEXT,`answer` TEXT)")
            id = 1
            while True:
                try:
                    # if img is provided                                                # server_id channel_id channelname id chapters image question answer
                    if img:
                        c.execute("INSERT INTO savedQuestions VALUES (?, ?, ?, ?, ?, ?, ?, ?) ",
                                  (ctx.guild.id, chnl_id, name, id, chapter, img, qn, ans))
                    else:
                        c.execute("INSERT INTO savedQuestions VALUES (?, ?, ?, ?, ?, ?, ?, ?) ",
                                  (ctx.guild.id, chnl_id, name, id, chapter, "no image", qn, ans))
                    conn.commit()

                    msg = await ctx.send(
                        "<a:loading:826529505656176651> Adding question into spreadsheet... <a:loading:826529505656176651>")
                    addQuestion(name, id, chapter, img, qn, ans)
                    await msg.delete()
                    break
                except sqlite3.IntegrityError:
                    id += 1
                    continue
            await functions.successEmbedTemplate(ctx,
                                                 f"Successfully saved question and answer in <#{chnl_id}>. Question has `id: {id}`.",
                                                 ctx.message.author)

    # @commands.command(description = f"tag**\n\nTag questions with their topics (requires permissions).\n\nUsage:\n`p!tag <qn id>\n\"<topic1,topic2,...>\"`")
    # @commands.cooldown(1, 5, commands.BucketType.user)
    # @has_permissions(manage_messages = True)
    # async def tag(self, ctx, id, topics):
    #     # get channel id
    #     chnl_id = ctx.message.channel.id
    #     c.execute("SELECT question FROM savedQuestions WHERE server_id = ? AND channel_id = ? AND id = ? ", (ctx.guild.id, chnl_id, id))
    #     if not c.fetchall():
    #         await functions.errorEmbedTemplate(ctx,
    #                                             f"<#{chnl_id}> question `id: {id}` does not exist in the database, check again and ping <@624251187277070357>/<@345945337770410006> for help if problem persists.",
    #                                             ctx.message.author)
    #     else:
    #         try:
    #             c.execute("UPDATE savedQuestions SET chapters = ? WHERE server_id = ? AND channel_id = ? AND id = ? ", (topics.lower(), ctx.guild.id, chnl_id, id))
    #             conn.commit()
    #             await functions.successEmbedTemplate(ctx,
    #                                                 f"Successfully set `{topics.lower()}` as tags to <#{chnl_id}> question:`{id}`.\nAdd quotation marks `\"<tags>\"` to tag more than one chapters.",
    #                                                 ctx.message.author)
    #         except sqlite3.IntegrityError:
    #             await functions.errorEmbedTemplate(ctx,
    #                                                 f"Unable to set tag for <#{chnl_id}> question `id: {id}`, check again and ping <@624251187277070357>/<@345945337770410006> for help if problem persists.",
    #                                                 ctx.message.author)

    @commands.command(description=f"qdel**\n\nDeletes the question associated with an id.\n\nUsage: `p!qdel <id>`")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @has_permissions(manage_messages=True)
    async def qdel(self, ctx, id):
        channelList = [chnl[0] for chnl in
                       c.execute('SELECT channel_id FROM subjectChannels WHERE server_id = ? ', (ctx.guild.id,))]
        # get channel id
        chnl_id = ctx.message.channel.id

        # check if command is being used in a subject channel
        if chnl_id not in channelList:
            await functions.errorEmbedTemplate(ctx,
                                               f"Please use this command in the respective subject channel you want to delete the question in.",
                                               ctx.message.author)
        else:
            c.execute("SELECT question FROM savedQuestions WHERE server_id = ? AND channel_id = ? AND id = ? ",
                      (ctx.guild.id, chnl_id, id))
            if not c.fetchall():
                await functions.errorEmbedTemplate(ctx,
                                                   f"<#{chnl_id}> question `id: {id}` does not exist in the database, please check again.",
                                                   ctx.message.author)
            else:
                try:
                    c.execute("DELETE FROM savedQuestions WHERE id = ? AND channel_id = ?", (id, chnl_id))
                    conn.commit()
                    msg = await ctx.send(
                        "<a:loading:826529505656176651> Deleting question from spreadsheet... <a:loading:826529505656176651>")
                    deleteQuestion(ctx.channel.name, id)
                    await msg.delete()
                    await functions.successEmbedTemplate(ctx,
                                                         f"Successfully deleted question and answer in <#{chnl_id}> with `id: {id}`",
                                                         ctx.message.author)
                except sqlite3.IntegrityError:
                    await functions.errorEmbedTemplate(ctx,
                                                       f"Unable to delete question with in <#{chnl_id} with `id = {id}`, try again and request for help if needed",
                                                       ctx.message.author)

    @commands.command(
        description=f"question**\n\nReceive a random question in the subject channel `p!question` is used in.\n\nUsage:\n`p!question <id if any>`")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def question(self, ctx, id=None):
        channelList = [chnl[0] for chnl in
                       c.execute('SELECT channel_id FROM subjectChannels WHERE server_id = ? ', (ctx.guild.id,))]

        # get channel id
        chnl_id = ctx.message.channel.id

        # check if channel is approved
        if chnl_id not in channelList:
            await functions.errorEmbedTemplate(ctx,
                                               f"You are not allowed to use this command in <#{chnl_id}>.",
                                               ctx.message.author)
        # channel approved
        else:
            # if no id provided
            if not id:
                c.execute(
                    "SELECT id, chapters, image, question, answer FROM savedQuestions WHERE channel_id = ? ORDER BY RANDOM() LIMIT 1",
                    (chnl_id,))
            else:
                c.execute(
                    "SELECT id, chapters, image, question, answer FROM savedQuestions WHERE id = ? AND channel_id = ?",
                    (id, chnl_id))
            try:
                num, tag, img, qn, ans = c.fetchall()[0]
                description = f"__**Question from <#{chnl_id}>**__\n\n{qn}\n\nDiscussion and Answer: ||{ans}||\n\nChapters: `{tag}`"
                # 0xdecaf0 R: 222 G: 202 B:240
                embed = discord.Embed(description=description, color=discord.Colour.from_rgb(222, 202, 240))
                if img != "no image":
                    embed.set_image(url=img)
                # vio lemme keep this pls 😭
                if ctx.message.author.id == 345945337770410006:
                    embed.set_footer(text=f"Requested by {ctx.message.author}🥶\nid: {num}",
                                     icon_url=ctx.message.author.display_avatar.url)
                else:
                    embed.set_footer(text=f"Requested by {ctx.message.author}\nid: {num}",
                                     icon_url=ctx.message.author.display_avatar.url)
                try:
                    await ctx.send(embed=embed)
                except discord.errors.HTTPException:
                    await functions.errorEmbedTemplate(ctx,
                                                       f"Something went wrong when embedding the saved image for question `id: {num}`. Ping <@624251187277070357>/<@345945337770410006> for help if problem persists.",
                                                       ctx.message.author)
            except IndexError:
                await functions.errorEmbedTemplate(ctx,
                                                   f"Failed to retrieve question from <#{chnl_id}> with `id = {id}`, question might have been deleted.",
                                                   ctx.message.author)

    @commands.command(
        description=f"bank**\n\nRequest for spreadsheet link of all the saved questions from SGExams.\n\nUsage:\n`p!bank`")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def bank(self, ctx):
        spreadsheet = "https://docs.google.com/spreadsheets/d/1BiJnc8-R7Dy7HWWTGWbZeG7HYD6DNDEAiHij0Gf61Co"
        await functions.successEmbedTemplate(ctx,
                                             f"All questions can be found over [here]({spreadsheet})!\nRequest for navigation help if needed.",
                                             ctx.message.author)


def setup(bot):
    bot.add_cog(subjCogs(bot))
