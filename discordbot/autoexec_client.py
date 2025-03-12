import discord
import os
import json

from dotenv import load_dotenv
from autoexec_langchain.get_mm_json import get_meeting_mins_json

def get_autoexec_client() -> discord.Client:
    # Get the environment variables
    load_dotenv()

    # intents are 
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

        if message.content.startswith('$AEmm'):
            meeting_mins_dict = get_meeting_mins_json()

            # format all of the key updates
            formatted_key_updates = ""
            for update in meeting_mins_dict["key_updates"]:
                formatted_key_updates.join(f" - {update}")

            # format each persons action items
            formatted_action_items = ""
            for person in meeting_mins_dict["action_items"].keys():
                person_tasks = ""
                for task in person:
                    person_tasks.join(f" - {task}\n")
                formatted_action_items.join(person_tasks)

            message_to_send =    f"""
                Header: {meeting_mins_dict["header"]}
                Meeting Link: {meeting_mins_dict["meeting_link"]}

                Key Updates:
                {formatted_key_updates}

                Action Items:
                {formatted_action_items}
            """

            await message.channel.send(f'Hello Im listening!\n{message_to_send}\n')


    return client
