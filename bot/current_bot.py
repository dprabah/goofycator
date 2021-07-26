import os
import ffmpeg
from discord import Forbidden, Embed, FFmpegPCMAudio
import discord
from discord.utils import get
from tinydb import Query
from discord.ext import tasks, commands
from db.db import create_and_return_db
from tverifier import tverify
from tverifier.tverify import get_screen_name_by_id, delete_message_by_id
import uuid
from random import randint
from youtube_dl import YoutubeDL
import moviepy.editor as moviepy
from datetime import datetime
from tqdm import tqdm
import requests
import re
import sys


twitter_verified = "tvfd"
twitter_bot_handle = os.getenv("twitter_bot_name")
bot = commands.Bot(command_prefix=">")


def init_bot():
    global bot
    batch_update.start()
    bot.run(os.getenv("discord_token", "Discord_token is not available"))


@bot.event
async def on_ready():
    print("We have logged in as {0.user}".format(bot))


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    await bot.process_commands(message)





@bot.command(name="insta")
async def insta_download(ctx , *args):

    url = args[0]
    x = re.match(r'^(https:)[/][/]www.([^/]+[.])*instagram.com', url)
    try:
            request_image = requests.get(url)
            src = request_image.content.decode('utf-8')
            check_type = re.search(r'<meta name="medium" content=[\'"]?([^\'" >]+)', src)
            check_type_f = check_type.group()
            final = re.sub('<meta name="medium" content="', '', check_type_f)
            
            print("Downloading the video...")
            extract_video_link = re.search(r'meta property="og:video" content=[\'"]?([^\'" >]+)', src)
            video_link = extract_video_link.group()
            final = re.sub('meta property="og:video" content="', '', video_link)
            response = requests.get(final).content
            file_size_request = requests.get(final, stream=True)
            file_size = int(file_size_request.headers['Content-Length'])
            block_size = 1024 
            filename = datetime.strftime(datetime.now(), '%Y-%m-%d-%H-%M-%S')
            t=tqdm(total=file_size, unit='B', unit_scale=True, desc=filename, ascii=True)
            with open(filename + '.mp4', 'wb') as f:
                for data in file_size_request.iter_content(block_size):
                    t.update(len(data))
                    f.write(data)
                t.close()
    except Exception as e:
        print(e)



@bot.command(name="convert")
async def convert(ctx):
    """
    Convert user video into mp4
    """

    user_video = ctx.message.attachments[0].url


    if user_video[-3:] == "mp4":
        embed = Embed(
            color=0x00FF00,
            description=":warning: MP4 videos cannot be converted as they can be played in Discord.",
        )
        embed.set_footer(
            icon_url=ctx.author.avatar_url,
            text="Requested by {} ".format(ctx.author.name),
        )
        await ctx.send(embed=embed)
        return

    print(user_video)
    embed = Embed(color=0x00FF00, description="Begining to convert")
    embed.set_footer(
        icon_url=ctx.author.avatar_url,
        text="Requested by {} ".format(ctx.author.name),
    )
    await ctx.send(embed=embed)
    clip = moviepy.VideoFileClip(user_video)
    if clip.rotation == 90:
        clip = clip.resize(clip.size[::-1])
        clip.rotation = 0
    clip.write_videofile("test.mp4")
    await ctx.reply(file=discord.File(r"D:\python_proj\goofycator\test.mp4"))
    clip.close()


@bot.command(name="play")
async def connect(ctx, *args):
    channel = ctx.message.author.voice.channel
    voice = get(bot.voice_clients, guild=ctx.guild)
    if voice and voice.is_connected():
        await ctx.send(*args)
        await voice.move_to(channel)
    else:
        await ctx.send(*args)
        voice = await channel.connect()


@bot.command(
    pass_context=True, name="whois", help="find the twitter id of the discord user"
)
async def find_twitter_handle(ctx, user_handle: str):
    try:
        user_id = get_user_clean_code(user_handle)
        db = create_and_return_db("core_db", "accounts")
        guild_id = str(ctx.message.guild.id)
        bot_id = str(bot.user.id)
        handle = get_twitter_handel_of_id(db, user_id, guild_id)
        if len(handle) > 0:
            await ctx.reply(
                "{} is {} in Twitter.".format(user_handle, handle[0]["handle"]),
                mention_author=False,
            )
        elif user_id == bot_id:
            await ctx.send("That is me :man_raising_hand: ")
        else:
            await ctx.reply(
                "I don't know who {} is :man_shrugging: , ask them to verify by hitting `>verify`".format(
                    user_handle
                ),
                mention_author=False,
            )

    except Exception as e:
        print(e)


@bot.command(pass_context=True, name="verify", help="verifies your twitter account")
async def verify_twitter_account(ctx, twitter_handle: str):
    twitter_handle = "@" + twitter_handle.lower()
    try:
        if is_verified_user(ctx.message.author):
            await ctx.reply("Hello! you are already a verified user!")
            return
        db = create_and_return_db("core_db", "accounts")
        guild_name = str(ctx.message.guild.id)
        is_verified_flagset_no_role(db, twitter_handle, guild_name)
        if tverify.verify_twitter_handle(twitter_handle):
            if verify_handle_already_added(db, twitter_handle, guild_name):
                db.insert(
                    {
                        "handle": twitter_handle,
                        "verified": False,
                        "unique_id": random_with_n_digits(6),
                        "user_id": str(ctx.message.author.id),
                        "guild_id": str(guild_name),
                    }
                )
            unique_id = get_unique_id_of_user(db, twitter_handle, guild_name)

            embed = Embed(
                title="Verification",
                color=0x00FF00,
                description="Follow me in Twitter:  " + str(twitter_bot_handle),
            )
            embed.add_field(
                name="DM me the Verification ID: ",
                value="{}\n*and wait untill I add you the private role 👀*".format(
                    str(unique_id)
                ),
            )
            embed.set_footer(
                icon_url=ctx.author.avatar_url,
                text="Requested by {} ".format(ctx.author.name),
            )
            await ctx.send("You")
            await ctx.send(embed=embed)
        else:
            await ctx.send("I couldn't fetch your handle, Pls try again!!")

    except Exception as e:
        print(e)


def get_twitter_handel_of_id(db, user_id, guild_id):
    q = Query()
    return db.search(
        (q.verified == True) & (q.guild_id == guild_id) & (q.user_id == user_id)
    )


def verify_handle_already_added(db, handle, guild_id):
    q = Query()
    return (
        not len(
            db.search(
                (q.handle == handle) & (q.guild_id == guild_id) & (q.verified == False)
            )
        )
        > 0
    )


def get_user_clean_code(user_id):
    return str(user_id.replace("<@!", "").replace(">", ""))


def get_unique_id_of_user(db, handle, guild_id):
    q = Query()
    result = db.search((q.handle == handle) & (q.guild_id == guild_id))
    if len(result) > 0:
        return result[0]["unique_id"]
    else:
        raise AssertionError("more than one handle exception")


def is_verified_user(author):
    if twitter_verified in [y.name for y in author.roles]:
        return True


def is_verified_flagset_no_role(db, handle, guild_id):
    q = Query()
    db.update({"verified": False}, (q.handle == handle) & (q.guild_id == guild_id))


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.errors.CheckFailure):
        await ctx.send(error)


@tasks.loop(minutes=5.0)
async def batch_update():
    db = create_and_return_db("core_db", "accounts")
    direct_messages = tverify.get_twitter_dms()
    for direct_message in direct_messages:
        handle = get_screen_name_by_id(direct_message.message_create["sender_id"])
        unique_id = str(direct_message.message_create["message_data"]["text"]).strip()
        print("twitter dm: " + handle)
        print("twitter unique_id: " + unique_id)
        result = get_user_row(db, handle, unique_id)
        if len(result) == 1:
            await add_role_and_cleanup(db, handle, result[0], direct_message.id)
        elif len(result) > 1:
            raise AssertionError(
                "More user entries are available. Deleting all entries. Try Again!!"
            )


async def add_role_and_cleanup(db, handle, result, direct_message_id):
    guild = await bot.fetch_guild(int(result["guild_id"]))
    member = await guild.fetch_member(int(result["user_id"]))
    try:
        await member.add_roles(get(guild.roles, name=twitter_verified))
    except Forbidden:
        print("Missing permission")
        return
    delete_message_by_id(direct_message_id)
    update_processed_row(db, handle, result["unique_id"], str(result["guild_id"]))


def get_user_row(db, handle, unique_id):
    q = Query()
    return db.search(
        (q.handle == handle) & (q.unique_id == unique_id) & (q.verified == False)
    )


def update_processed_row(db, handle, unique_id, guild_id):
    q = Query()
    db.update(
        {"verified": True},
        (q.handle == handle) & (q.unique_id == unique_id) & (q.guild_id == guild_id),
    )


def random_with_n_digits(n):
    range_start = 10 ** (n - 1)
    range_end = (10 ** n) - 1
    return randint(range_start, range_end)
