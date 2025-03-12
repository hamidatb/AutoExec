from discordbot.autoexec_client import get_autoexec_client
from autoexec_langchain.get_mm_json import get_meeting_mins_json

import discord
import os
from dotenv import load_dotenv

# get the auth token to run the client
# if this bot token isnt working, load_dotenv may be using an old ver
# run unset DISCORD_BOT_TOKEN in terminal in that case
botToken = os.getenv("DISCORD_BOT_TOKEN")
if botToken is None:
    raise ValueError("DISCORD_BOT_TOKEN not found! Make sure .env is set up correctly.")


client = get_autoexec_client()
client.run(botToken)