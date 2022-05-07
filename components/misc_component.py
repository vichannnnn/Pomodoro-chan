import yaml
import lightbulb
import hikari

with open("authentication.yaml", "r", encoding="utf8") as stream:
    yaml_data = yaml.safe_load(stream)

plugin = lightbulb.Plugin("⛭ Misc")

@plugin.command()
@lightbulb.command("joinroom", "Joins a voice channel.")
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def joinroom(ctx: lightbulb.Context):
    caller = ctx.author.id
    if str(caller) not in yaml_data['Owners']:
        return await ctx.respond("You are not allowed to use this command", flags=hikari.MessageFlag.EPHEMERAL)

    states = ctx.bot.cache.get_voice_states_view_for_guild(ctx.guild_id)
    voice_state = [state async for state in states.iterator().filter(lambda i: i.user_id == caller)]
    if not voice_state:
        return await ctx.respond("Connect to a voice channel first.", hikari.MessageFlag.EPHEMERAL)

    voice_channel_id = voice_state[0].channel_id

    await ctx.bot.update_voice_state(ctx.guild_id, voice_channel_id, self_mute=True, self_deaf=True)
    return await ctx.respond(f"Connected to <#{voice_channel_id}>", flag=hikari.MessageFlag.EPHEMERAL)

def load(bot):
    bot.add_plugin(plugin)

def unload(bot):
    bot.remove_plugin(plugin)
