import os
import io
from dotenv import load_dotenv

import asyncio

import discord
from discord.ext import commands

import messages
from bad_people import BadPeople

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix='$', intents=intents)

start_msg = None
curr_game = BadPeople(None)
players = {}


def check_channel(ctx):
    return ctx.channel.name == 'bad_people'


@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')


@bot.command()
@commands.check(check_channel)
@commands.has_role('dex_admin')
async def game(ctx):
    global start_msg

    if start_msg:
        await ctx.send('There is already a game in progress.')

    else:
        embed = discord.Embed(
            title='Bad People',
            description="The Party Game You Probably Shouldn't Play.",
            colour=discord.Color.red(),
        )

        embed.add_field(name='Rules', value=messages.RULES, inline=False)
        embed.add_field(name='Commands', value=messages.COMMANDS, inline=False)
        embed.add_field(name='Join', value=messages.JOIN, inline=False)
        embed.add_field(name='Start', value=messages.START, inline=False)

        img = discord.File('images/bad_people.jpg', filename='bad_people.jpg')
        embed.set_image(url='attachment://bad_people.jpg')

        msg = await ctx.send(file=img, embed=embed)
        start_msg = msg.id
        await msg.add_reaction('\U0001F595')


@bot.command()
@commands.check(check_channel)
@commands.has_role('dex_admin')
async def start(ctx):
    global start_msg
    global curr_game
    global players

    if not start_msg:
        await ctx.send('You cannot start a game without calling `$game` first.')

    elif curr_game.game_state() != 0:
        await ctx.send('There is already a game in progress.')

    else:
        msg = await ctx.channel.fetch_message(start_msg)
        users = set()
        async for user in msg.reactions[0].users():  # first reaction will be '\U0001F595'
            if user != bot.user:
                guild = ctx.guild
                member = guild.get_member(user.id)
                users.add(member.mention)
                players[member.mention] = member

        if users:
            curr_game = BadPeople(list(users))
            await ctx.send(f'The game has begun with {len(list(users))} players.')
            await ctx.invoke(bot.get_command('new_dictator'))

        else:
            await ctx.send(f'No one joined the game. Shutting the game down.')
            await ctx.invoke(bot.get_command('stop'))


@bot.command()
@commands.check(check_channel)
@commands.has_role('dex_admin')
async def new_dictator(ctx):
    global curr_game

    await ctx.invoke(bot.get_command('remove_dictator'))

    if curr_game.game_state() != 0:
        dictator = players[curr_game.get_dictator()]
        role = discord.utils.get(ctx.guild.roles, name='Dictator')
        await dictator.add_roles(role)
        await ctx.send(f'{dictator.mention} is the current the dictator.')


@bot.command()
@commands.check(check_channel)
@commands.has_role('dex_admin')
async def remove_dictator(ctx):

    role = discord.utils.get(ctx.guild.roles, name='Dictator')
    for member in role.members:
        await member.remove_roles(role)


@bot.command()
@commands.check(check_channel)
@commands.has_role('dex_admin')
async def stop(ctx):
    global start_msg
    global curr_game
    global players

    dictator = curr_game.get_dictator()
    if dictator:
        await ctx.invoke(bot.get_command('remove_dictator'))

    start_msg = None
    curr_game = BadPeople(None)
    players = {}

    await ctx.send('The game has been ended.')


@bot.command()
@commands.check(check_channel)
@commands.has_role('Dictator')
async def draw(ctx):
    global curr_game

    drawn_card = curr_game.draw_card()
    buff = io.BytesIO()
    drawn_card.save(buff, format='PNG')
    buff.seek(0)
    card = discord.File(buff, filename='card.png')
    await ctx.send(file=card)


@draw.error
async def draw_error(ctx, error):
    if isinstance(error, commands.CommandInvokeError):
        await ctx.send(error.original)


@bot.command()
@commands.check(check_channel)
@commands.has_role('Dictator')
async def nominate(ctx, member: discord.Member):
    global curr_game

    curr_game.nominate(member.mention)
    await ctx.send(f'Nominated {member.mention}.')


@nominate.error
async def nominate_error(ctx, error):
    if isinstance(error, commands.BadArgument):
        await ctx.send('I could not find that member.')

    elif isinstance(error, commands.CommandInvokeError):
        await ctx.send(error)


@bot.command()
@commands.check(check_channel)
@commands.has_role('Dictator')
async def vote(ctx):
    global curr_game
    global players

    embed = discord.Embed(
        title='Player Votes',
        colour=discord.Color.red(),
    )

    nominees = curr_game.get_nominees()

    embed.add_field(name=players[nominees[0]].name, value=f'React with \U0001F92C to vote for {nominees[0]}.', inline=False)
    embed.add_field(name=players[nominees[1]].name, value=f'React with \U0001F608 to vote for {nominees[1]}.', inline=False)

    msg = await ctx.send(embed=embed)
    msg_id = msg.id
    await msg.add_reaction('\U0001F92C')
    await msg.add_reaction('\U0001F608')
    await asyncio.sleep(15)

    msg = await ctx.channel.fetch_message(msg_id)

    votes_1 = 0
    votes_2 = 0
    async for user in msg.reactions[0].users():  # first reaction will be '\U0001F92C'
        if user != bot.user:
            votes_1 += 1

    async for user in msg.reactions[1].users():  # second reaction will be '\U0001F608'
        if user != bot.user:
            votes_2 += 1

    if votes_1 > votes_2:
        await ctx.send(f'Seems like {nominees[0]} takes this one.')
        game_winner = curr_game.winner(0)
    elif votes_1 < votes_2:
        await ctx.send(f'Truly, {nominees[1]} would do such a thing.')
        game_winner = curr_game.winner(1)
    else:
        await ctx.send(f"It's a tie. I guess {nominees[0]} and {nominees[1]} are both terrible people.")
        game_winner = curr_game.winner(-1)

    if game_winner:
        await ctx.send(f'Winner winner chicken dinner. Congrats to {game_winner} for being terrible.')
        await ctx.invoke(bot.get_command('score'))
        await ctx.invoke(bot.get_command('stop'))

    await ctx.invoke(bot.get_command('new_dictator'))


# TODO vote skip

@bot.command()
async def score(ctx):
    global curr_game
    global players

    embed = discord.Embed(
        title='Current Scores',
        colour=discord.Color.red(),
    )

    scores = curr_game.score()
    for player in scores.keys():
        embed.add_field(name=f'{players[player].name}', value=f'{scores[player]}', inline=False)

    await ctx.send(embed=embed)


bot.run(TOKEN)
