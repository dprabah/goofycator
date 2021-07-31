import os

from discord.ext import commands
from db.connection import create_session
from pathlib import Path


class Goofycator(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=">", case_insensitive=True)
        self.db_session = create_session()
        self.run(os.getenv("discord_token", "Discord_token is not available"))

    async def init(self):
        dirname = Path(__file__).parent.parent
        filename = os.path.join(dirname, 'cogs/')
        extensions = os.listdir(filename)
        # logger.info('Started loading cogs ...')
        print('Started loading cogs ...')
        for file in extensions:
            if file.startswith('__'):
                print("extension: {} : passed".format(file))
                pass
            elif file.endswith("_cog.py"):
                cog = file.split('.')[0]
                self.load_extension(f'cogs.{cog}')
                print("extension: {} : loaded".format(file))
            else:
                print("extension: {} : ignored".format(file))
        print('Successfully loaded all cogs!')

    async def on_ready(self):
        print("We have logged in as {0.user}".format(self))
        await self.init()

    async def on_message(self, message):
        if message.author == self.user:
            return

        await self.process_commands(message)
