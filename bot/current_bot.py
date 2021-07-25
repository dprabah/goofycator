import os

from discord import Forbidden, Embed
from discord.utils import get
from tinydb import Query
from discord.ext import tasks, commands
from db.db import create_and_return_db
from tverifier import tverify
from tverifier.tverify import get_screen_name_by_id, delete_message_by_id
import uuid
from random import randint


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


@bot.command(pass_context=True, name="verify", help="verifies your twitter account")
async def verify_twitter_account(ctx, twitter_handle: str):
    twitter_handle = "@" + twitter_handle.lower()
    try:
        if is_verified_user(ctx.message.author):
            await ctx.send("Hello! you are already a verified user!")
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
