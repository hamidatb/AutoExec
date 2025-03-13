import discord
import os
import json

from dotenv import load_dotenv
from autoexec_langchain.get_mm_json import get_meeting_mins_json
from autoexec_langchain.main_agent import run_agent

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
    CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID"))

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
        # Fetch the channel and send a message
        channel = client.get_channel(CHANNEL_ID)
        if channel:
            await channel.send("✅ AutoExec Bot is now online and connected!")

    @client.event
    async def on_message(message):
        """ Handles incoming messages (both DMs and server messages). """
        if message.author == client.user:
            return

        try:
            # Fetch the correct server channel
            server_channel = await client.fetch_channel(CHANNEL_ID)
        except Exception as e:
            print(f"❌ Error fetching server channel: {e}")
            return

        # Check if message is a DM
        is_dm = isinstance(message.channel, discord.DMChannel)

        # Handle Meeting Minutes Request ($AEmm)
        if message.content.startswith('$AEmm'):
            formatted_response = get_meeting_min_reponse()

            if is_dm:
                # Send response to DM sender
                await message.channel.send("✅ Your request has been sent to the server!")
                # Forward response to the server
                #await server_channel.send(f'📌 **Meeting Minutes Requested by {message.author}:**')

                await server_channel.send(f'{formatted_response}')
            else:
                # Send response directly in server chat
                await message.channel.send(f'{formatted_response}')
        
        # Handle Agent Request ($AE)
        elif message.content.startswith('$AE'):
            result = run_agent(message.content)
            response = result.get("output", "⚠️ Error processing request.")

            if is_dm:
                await message.channel.send("✅ Your request has been processed and sent to the server!")
                await server_channel.send(f'🔍 **Agent Response for {message.author}:**\n{response}')
            else:
                await message.channel.send(response)

    return client
