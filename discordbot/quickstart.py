# This example requires the 'message_content' intent.

import discord
import os
import dotenv

from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True

# create a new instance of the connection to discord (a client)
client = discord.Client(intents=intents)

# client.event decorator registers an event
@client.event
async def on_ready():
    """
    on_ready() is called when the bot finished logging in and setting things up.
    """
    print(f'We have logged in as {client.user}')

@client.event
async def on_message(message):
    """
    on_message() is called when the bot has recieved a message.
    """
    # Avoiding listening to messages from ourself
    if message.author == client.user:
        return

    if message.content.startswith('$hello'):
        await message.channel.send('Hello Im listening!')

# get the auth token to run the client
botToken = os.getenv("DISCORD_BOT_TOKEN")
if botToken is None:
    raise ValueError("DISCORD_BOT_TOKEN not found! Make sure .env is set up correctly.")

# login as autoExec to make it online
client.run(botToken)