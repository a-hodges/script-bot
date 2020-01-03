"""Hotel Management Bot

Note:
Any parameter value that has spaces in it needs to be wrapped in quotes "
Parameters marked with a * may omit the quotes

Certain commands are only usable by administrators
"""

import asyncio
from collections import OrderedDict
from contextlib import closing

import discord
from discord.ext import commands

bot = commands.Bot(
    command_prefix=";",
    description=__doc__,
    loop=asyncio.new_event_loop())


@bot.event
async def on_ready():
    """
    Sets up the bot
    """
    print("Logged in as")
    print(bot.user.name)
    print(bot.user.id)
    print("------")
    game = "Type `;help` for command list"
    await bot.change_presence(activity=discord.Game(name=game))


@bot.event
async def on_command_error(ctx, error: Exception):
    unknown = False
    if (isinstance(error, commands.CommandInvokeError)):
        error = error.original

    if (isinstance(error, AttributeError) and ctx.guild is None
            and str(error) == "'NoneType' object has no attribute 'id'"):
        message = "This command can only be used in a server"

    elif isinstance(error, commands.CheckFailure):
        message = "Error: You do not meet the requirements to use this command"
    elif isinstance(error, commands.CommandNotFound):
        if error.args:
            message = error.args[0]
        else:
            message = "Error: command not found"
    elif isinstance(error, commands.BadArgument):
        message = "{}\nSee the help text for valid parameters".format(error)
    elif isinstance(error, commands.MissingRequiredArgument):
        message = "Missing parameter: {}\nSee the help text for valid parameters".format(error.param)
    elif isinstance(error, commands.TooManyArguments):
        message = "Too many parameters\nSee the help text for valid parameters"
    elif isinstance(error, ValueError):
        if error.args:
            message = "Invalid parameter: {}".format(error.args[0])
        else:
            message = "Invalid parameter"
    elif isinstance(error, Exception):
        message = "Error: {}".format(error)
    else:
        message = "Error: {}".format(error)
        unknown = True

    embed = discord.Embed(description=message, color=discord.Color.red())
    await ctx.send(embed=embed)

    if unknown:
        raise error


# ----#-   Commands


@bot.command()
async def ping(ctx):
    await ctx.send('Ping time (ms): {0}'.format(round(bot.latency * 1000)))


# ----#-


def main(token: str):
    bot.run(token)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-t', dest='token', required=True, help='Disocrd bot token')
    args = parser.parse_args()
    main(args.token)
