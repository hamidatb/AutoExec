import discord
import os
import json

from dotenv import load_dotenv
from autoexec_langchain.get_mm_json import get_meeting_mins_json

def get_meeting_min_reponse() -> str:
    """ 
    Gets the formatted string response when a user asks for the meeting minutes.

    Args:
        None
    Returns:
        response_str (str): The meeting minute response
    """
    meeting_mins_dict = get_meeting_mins_json()

    # format all of the key updates
    formatted_key_updates = "**Key Updates**:\n"
    for update in meeting_mins_dict["key_updates"]:
        formatted_key_updates += f"- {update}\n"

    # format each persons action items
    formatted_action_items = "**Action Items**:\n"
    for person, tasks in meeting_mins_dict["action_items"].items():
        formatted_action_items += f"**{person}**\n"  # Add person's name in bold
        for task in tasks:
            formatted_action_items += f"- {task}\n"  # Append each task with a bullet point
        #formatted_action_items += "\n"  # Add a blank line between different people

    message_to_send =    f"""
    \n{meeting_mins_dict["header"]}
    \n{meeting_mins_dict["meeting_link"]}
    \n{formatted_key_updates.rstrip()}
    \n\n{formatted_action_items}
    """

    return message_to_send


def get_autoexec_client() -> discord.Client:
    """
    Creates the AutoExec client returns it.
    Does not run the client, rather sets up its parameters.
    """
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
        
        # handle the user asking for the most recent meeting minutes
        if message.content.startswith('$AEmm'):
            formatted_response = get_meeting_min_reponse()
            await message.channel.send(f'{formatted_response}')
        
        # TODO: Handle asking for the action item status of everyone and saying what still has to be completed
                

    return client
