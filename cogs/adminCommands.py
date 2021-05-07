import discord
from discord.ext import commands
from discord.ext.commands import has_permissions
import cogs.colourEmbed as functions
import traceback
import sqlite3

conn = sqlite3.connect('focus.db', timeout=5.0)
c = conn.cursor()
conn.row_factory = sqlite3.Row

c.execute('CREATE TABLE IF NOT EXISTS focusSettings (server_id INT PRIMARY KEY, role_id INT) ')
c.execute('CREATE TABLE IF NOT EXISTS focusChannels (server_id INT, channel_id INT, UNIQUE(server_id, channel_id)) ')

async def focusRoleObject(ctx):
    roleCheck = [role[0] for role in
                 c.execute('SELECT role_id FROM focusSettings WHERE server_id = ? ', (ctx.guild.id,))]

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
                c.execute('INSERT INTO focusSettings VALUES (?, ?)', (ctx.guild.id, focusRole.id))
                conn.commit()
                await functions.successEmbedTemplate(ctx, f"Successfully set-up the Focus System in this server.",
                                                     ctx.message.author)

            except:
                c.execute('UPDATE focusSettings SET role_id = ? WHERE server_id = ?', (focusRole.id, ctx.guild.id))
                conn.commit()
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
                       c.execute('SELECT channel_id FROM focusChannels WHERE server_id = ? ', (ctx.guild.id,))]

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
                     c.execute('SELECT role_id FROM focusSettings WHERE server_id = ? ', (ctx.guild.id,))]

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
                           c.execute('SELECT channel_id FROM focusChannels WHERE server_id = ? ', (ctx.guild.id,))]

            if channel.id not in channelList:
                c.execute('INSERT INTO focusChannels VALUES (?, ?)', (ctx.guild.id, channel.id))
                conn.commit()
                await channel.set_permissions(focusRoleObject, read_messages=False)

                await functions.successEmbedTemplate(ctx,
                                                     f"Successfully added {channel.mention} as a focus blacklist channel.\n\nUsers who are in focused mode will not be able to access this channel.",
                                                     ctx.message.author)

            else:
                c.execute('DELETE FROM focusChannels WHERE channel_id = ?', (channel.id,))
                conn.commit()
                await channel.set_permissions(focusRoleObject, read_messages=True)

                await functions.successEmbedTemplate(ctx,
                                                     f"Successfully removed {channel.mention} as a focus blacklist channel.\n\nUsers who are in focused mode will be able to access this channel now.",
                                                     ctx.message.author)


def setup(bot):
    bot.add_cog(adminCommands(bot))
