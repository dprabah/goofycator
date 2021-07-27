import os

from discord import Forbidden, Embed
from discord.utils import get
from discord.ext import tasks, commands

from db.connection import create_session
from db.entities.Users import Users
from tverifier import tverify
from tverifier.tverify import get_screen_name_by_id, delete_message_by_id, get_own_screen_name
from random import randint
from sqlalchemy import update, select

twitter_verified = "tvfd"
bot = commands.Bot(command_prefix=">")
session = create_session()


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

        guild_name = str(ctx.message.guild.id)
        is_verified_flagset_no_role(session, twitter_handle, guild_name)
        if tverify.verify_twitter_handle(twitter_handle):
            if verify_handle_already_added(session, twitter_handle, guild_name):
                user = Users(twitter_handle=twitter_handle, is_verified_user=False, unique_id=random_with_n_digits(6),
                             discord_user_id=str(ctx.message.author.id), users_guild_id=str(guild_name))
                session.add(user)
                session.commit()
            unique_id = get_unique_id_of_user(session, twitter_handle, guild_name)

            embed = Embed(
                title="Verification",
                color=0x00FF00,
                description="Follow me in Twitter:  " + str(get_own_screen_name()),
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
            await ctx.send(embed=embed)
        else:
            await ctx.send("I couldn't fetch your handle, Pls try again!!")

    except Exception as e:
        print(e)


def verify_handle_already_added(db_session, handle, guild_id):
    select_stmt = select(Users) \
        .where(Users.twitter_handle == handle) \
        .where(Users.users_guild_id == guild_id) \
        .where(Users.is_verified_user == False)
    result = db_session.execute(select_stmt).fetchall()
    return not len(result) > 0


def get_unique_id_of_user(db_session, handle, guild_id):
    select_stmt = select(Users.unique_id) \
        .where(Users.twitter_handle == handle) \
        .where(Users.users_guild_id == guild_id)
    result = db_session.execute(select_stmt).fetchall()

    if len(result) > 0:
        return result[0].unique_id
    else:
        raise AssertionError("more than one handle exception")


def is_verified_user(author):
    if twitter_verified in [y.name for y in author.roles]:
        return True


def is_verified_flagset_no_role(db_session, handle, guild_id):
    update_stmt = update(Users) \
        .where(Users.twitter_handle == handle) \
        .where(Users.users_guild_id == guild_id) \
        .values(is_verified_user=False)
    db_session.execute(update_stmt)
    db_session.commit()


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.errors.CheckFailure):
        await ctx.send(error)


@tasks.loop(minutes=5.0)
async def batch_update():
    direct_messages = tverify.get_twitter_dms()
    for direct_message in direct_messages:
        handle = get_screen_name_by_id(direct_message.message_create["sender_id"])
        unique_id = str(direct_message.message_create["message_data"]["text"]).strip()
        print("twitter dm: " + handle)
        print("twitter unique_id: " + unique_id)
        result = get_user_row(session, handle, unique_id)
        if len(result) == 1:
            await add_role_and_cleanup(session, handle, result[0], direct_message.id)
        elif len(result) > 1:
            raise AssertionError("More user entries are available. Deleting all entries. Try Again!!")


async def add_role_and_cleanup(db_session, handle, result, direct_message_id):
    guild = await bot.fetch_guild(int(result.users_guild_id))
    member = await guild.fetch_member(int(result.discord_user_id))
    try:
        await member.add_roles(get(guild.roles, name=twitter_verified))
    except Forbidden:
        print("Missing permission")
        return
    delete_message_by_id(direct_message_id)
    update_processed_row(db_session, handle, result.unique_id, str(result.users_guild_id))


def get_user_row(db_session, handle, unique_id):
    select_stmt = select(Users.unique_id, Users.users_guild_id, Users.discord_user_id) \
        .where(Users.twitter_handle == handle) \
        .where(Users.unique_id == unique_id) \
        .where(Users.is_verified_user == False)
    return db_session.execute(select_stmt).fetchall()


def update_processed_row(db_session, handle, unique_id, guild_id):
    update_stmt = update(Users) \
        .where(Users.twitter_handle == handle) \
        .where(Users.unique_id == unique_id) \
        .where(Users.users_guild_id == guild_id) \
        .values(is_verified_user=True)
    db_session.execute(update_stmt)
    db_session.commit()


def random_with_n_digits(n):
    range_start = 10 ** (n - 1)
    range_end = (10 ** n) - 1
    return randint(range_start, range_end)
