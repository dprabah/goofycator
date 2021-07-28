import os

from discord import Forbidden, Embed
from discord.utils import get
from discord.ext import tasks, commands

from db.connection import create_session
from db.entities.Users import Users
from tverifier import tverify
from tverifier.tverify import get_screen_name_by_id, delete_message_by_id, get_own_screen_id
from random import randint
from sqlalchemy import update, select

twitter_verified = "TJ"
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
            twitter_dm_url = "https://twitter.com/messages/compose?recipient_id={}".format(get_own_screen_id())
            embed = Embed(
                title="Verification",
                color=0x00FF00,
                description="Click here: [DM Link]({})".format(twitter_dm_url)
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


@bot.command(
    pass_context=True, name="whois", help="find the twitter id of the discord user"
)
async def find_twitter_handle(ctx, discord_user_handle: str):
    try:
        discord_user_id = get_user_clean_code(discord_user_handle)
        users_guild_id = str(ctx.message.guild.id)
        print("whois: {} -> {}, users_guild_id: {}".format(discord_user_handle, discord_user_id, users_guild_id))
        if users_guild_id == bot.user.id:
            await ctx.send("That is me :man_raising_hand: ")

        twitter_handle = get_twitter_handle(session, discord_user_id, users_guild_id)
        if twitter_handle is None:
            await ctx.send(
                "I don't know who {} is :man_shrugging: , ask him to run `>verify `".format(
                    discord_user_handle
                )
            )
            return

        twitter_url = "https://twitter.com/{}".format(twitter_handle.replace("@", ""))
        await ctx.send(
            "{} is {} in Twitter {}".format(discord_user_handle, twitter_handle, twitter_url)
        )

    except Exception as e:
        print(e)


def get_user_clean_code(args):
    return ''.join([n for n in args if n.isdigit()]).strip()


def get_twitter_handle(db_session, discord_user_id, users_guild_id):
    print("get_twitter_handle: {}, {}".format(discord_user_id, users_guild_id))
    select_stmt = select(Users.twitter_handle) \
        .where(Users.discord_user_id == discord_user_id) \
        .where(Users.users_guild_id == users_guild_id) \
        .where(Users.is_verified_user == True)
    result = db_session.execute(select_stmt).fetchall()

    if len(result) == 1:
        return str(result[0].twitter_handle)
    elif len(result) > 1:
        for r in result:
            print(r)
        raise AssertionError("more than one handle exception")
    else:
        return None


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
    except Forbidden as e:
        print(e)
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
