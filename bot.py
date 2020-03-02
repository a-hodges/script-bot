"""Script Bot

Note:
Any parameter value that has spaces in it needs to be wrapped in quotes "
Parameters marked with a * may omit the quotes

Certain commands are only usable by administrators
"""

import asyncio
import re

import discord
from discord.ext import commands
import redis

bot = commands.Bot(
    command_prefix="!",
    description=__doc__,
    loop=asyncio.new_event_loop())

tasks = {}


def context_key(ctx):
    return (ctx.guild.id, ctx.channel.id)


# ----#-   Events


@bot.event
async def on_ready():
    """
    Sets up the bot
    """
    print("Logged in as")
    print(bot.user.name)
    print(bot.user.id)
    print("------")
    game = "Type `{}help` for command list".format(bot.command_prefix)
    await bot.change_presence(activity=discord.Game(name=game))


@bot.event
async def on_command_error(ctx, error: Exception):
    unknown = False
    message = None
    tasks.pop(context_key(ctx), None)
    if (isinstance(error, commands.CommandInvokeError)):
        error = error.original

    # server command used in DMs
    if (isinstance(error, AttributeError) and ctx.guild is None and str(error) == "`'NoneType' object has no attribute 'id'`"):
        message = "`This command can only be used in a server`"

    # command invocation errors
    elif isinstance(error, commands.CommandNotFound):
        pass
    elif isinstance(error, commands.CheckFailure):
        message = "`Error: You do not meet the requirements to use this command`"
    elif isinstance(error, commands.BadArgument):
        message = "`{}\nSee the help text for valid parameters`".format(error)
    elif isinstance(error, commands.MissingRequiredArgument):
        message = "`Missing parameter: {}\nSee the help text for valid parameters`".format(error.param)
    elif isinstance(error, commands.TooManyArguments):
        message = "`Too many parameters\nSee the help text for valid parameters`"
    elif isinstance(error, ValueError):
        if error.args:
            message = "`Invalid parameter: {}`".format(error.args[0])
        else:
            message = "`Invalid parameter`"

    # no response to bot, close the script
    elif isinstance(error, asyncio.TimeoutError):
        message = 'Timed out\n\n``` ```'

    # misc errors
    else:
        message = "`Error: {}`".format(error)
        unknown = True

    if message is not None:
        await ctx.send(message)

    if unknown:
        raise error


# ----#-   Context


@bot.before_invoke
async def before_any_command(ctx):
    '''
    Set up database connection
    '''
    ctx.conn = redis.Redis(connection_pool=ctx.bot.pool)


@bot.after_invoke
async def after_any_command(ctx):
    '''
    Tear down database connection
    '''
    ctx.conn.close()
    ctx.conn = None


# ----#-   Commands


@bot.command()
async def ping(ctx):
    await ctx.send('`Ping time (ms): {0}`'.format(round(ctx.bot.latency * 1000)))


pattern = re.compile(r"(?:(\d+|r|R)\|)?(.+)")
default_delay = '1'


async def run_script(ctx, lines, tts=False):
    def check(m):
        return m.channel == ctx.channel and m.author == ctx.author

    l = len(lines)
    i = 0
    async with ctx.typing():
        while i < l:
            match = pattern.match(lines[i])
            if match is not None:
                delay, text = match.groups()
                if delay is None:
                    delay = default_delay

                if delay.lower() == 'r':
                    await ctx.bot.wait_for('message', check=check, timeout=5*60)
                    await asyncio.sleep(int(default_delay))
                else:
                    await asyncio.sleep(int(delay))

                await ctx.send(text, tts=tts)
            i += 1
        await asyncio.sleep(3)

    tasks.pop(context_key(ctx), None)
    
    await ctx.send('``` ```')


@bot.group(invoke_without_command=True)
async def script(ctx, script: str, tts=False):
    lines = ctx.conn.hget('scripts', script)

    if lines is None:
        await ctx.send('`No script named: {}`'.format(script))
        return

    lines = lines.decode(encoding='utf-8')
    lines = lines.replace('\r\n', '\n')
    lines = lines.split('\n')

    key = context_key(ctx)
    if key not in tasks:
        tasks[key] = bot.loop.create_task(run_script(ctx, lines, bool(tts)))
    else:
        await ctx.send('`Already running a script`')


@bot.command()
async def cancel(ctx):
    task = tasks.pop(context_key(ctx), None)
    if task is not None:
        task.cancel()
        await ctx.send('`Cancelled`')
    else:
        await ctx.send('`Nothing to cancel`')


@script.command('list')
async def list(ctx):
    keys = ctx.conn.hkeys('scripts')
    keys = sorted(keys)
    keys = [key.decode('utf-8').replace('_', ' ').title()
            for key in keys]
    await ctx.send(', '.join(keys))


# ----#-   Run

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-t', dest='token', required=True, help='Discord bot token')
    parser.add_argument('-p', dest='prefix', default=bot.command_prefix, help='Override command prefix')
    parser.add_argument('-d', dest='database', help='Redis connection string')

    args = parser.parse_args()
    bot.command_prefix = args.prefix

    match = re.match(r"redis://h:(\w+)@(.+?):(\d+)", args.database)
    password, hostname, port = match.groups()
    pool = redis.ConnectionPool(host=hostname, port=int(port), password=password)
    bot.pool = pool

    bot.run(args.token)
