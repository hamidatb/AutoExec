from discordbot.autoexec_client import get_autoexec_client

import os
from dotenv import load_dotenv

def run_bot():
    """
    This function runs the AutoExec bot
    """
    # get the auth token to run the client
    load_dotenv()

    # if this bot token isnt working, load_dotenv may be using an old ver
    # run unset DISCORD_BOT_TOKEN in terminal in that case
    botToken = os.getenv("DISCORD_BOT_TOKEN")
    if botToken is None:
        raise ValueError("DISCORD_BOT_TOKEN not found! Make sure .env is set up correctly.")

    client = get_autoexec_client()
    client.run(botToken)

def main():
    run_bot()

if __name__ == "__main__":
    main()