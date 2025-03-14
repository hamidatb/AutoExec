import discord
import asyncio

from ae_langchain.meeting_mins import get_meeting_mins_json
from ae_langchain.main_agent import run_agent
from config import Config

Config()

class MeetingMinutesFormatter:
    def __init__(self):
        self.meetingMinsDict = None

    def fetch_meeting_minutes(self):
        """Fetches the latest meeting minutes only when called."""
        self.meetingMinsDict = get_meeting_mins_json()

        if not self.meetingMinsDict:
            print("❌ ERROR: Failed to fetch meeting minutes. Ensure Google Drive API is working.")
            
            self.meetingMinsDict = {"header": "⚠️ No meeting minutes available.", "meeting_link": "", "key_updates": [], "action_items": {}}


    def format(self) -> str:
        """
        Formats the meeting minutes into a string
        """
        if self.meetingMinsDict is None:
            self.fetch_meeting_minutes()  # Fetch only when needed

        formatted_key_updates = "**Key Updates**:\n"
        for update in self.meetingMinsDict["key_updates"]:
            formatted_key_updates += f"- {update}\n"

        formatted_action_items = "**Action Items**:\n"
        for person, tasks in self.meetingMinsDict["action_items"].items():
            formatted_action_items += f"**{person}**\n"
            for task in tasks:
                formatted_action_items += f"- {task}\n"

        message_to_send = f"""
        \n{self.meetingMinsDict["header"]}
        \n{self.meetingMinsDict["meeting_link"]}
        \n{formatted_key_updates.rstrip()}
        \n\n{formatted_action_items}
        """
        return message_to_send


class DiscordBot(discord.Client):
    """ 
    Encapsulates Discord connection and event handling.
    """
    def __init__(self, channel_id: int, minutes_formatter: MeetingMinutesFormatter, **options):
        intents = discord.Intents.default()
        intents.message_content = True  # Needed to read messages
        intents.guilds = True  # Needed for server interactions
        intents.members = True  # Needed for user interactions
        intents.messages = True  # Needed to send/receive messages

        # initialize discord.Client with intents
        super().__init__(intents=intents, **options) 

        self.channel_id = channel_id
        self.minutes_formatter = minutes_formatter

    async def on_ready(self):
        """
        Triggered when the bot successfully logs in.
        """
        print(f'We have logged in as {self.user}')
        channel = self.get_channel(self.channel_id)
        if channel:
            await channel.send("✅ AutoExec Bot is now online and connected!")
    

    async def on_message(self, message: discord.Message):
        """
        Handles incoming messages
        """
        # AutoExec must ignore itself
        if message.author == self.user: 
            return

        try:
            # get the server channel it's on
            server_channel = await self.fetch_channel(self.channel_id)  
        except Exception as e:
            print(f"❌ Error fetching server channel: {e}")
            return

        # check if it's a dm
        is_dm = isinstance(message.channel, discord.DMChannel)

        if is_dm:
            result = run_agent(message.content)
            response = result.get("output", " Error processing request.")
            await message.channel.send("Your request has been processed and sent to the server!")
            await server_channel.send(f"{response}")

        elif message.content.startswith('$AEmm'):
            # get the meeting minutes 
            res = run_agent(message.content)
            result = res['output']
            print(res)
            print(result)

            

            if is_dm:
                await message.channel.send("Your request has been sent to the server!")
                await server_channel.send("Test response")
            else:
                await message.channel.send(result)

        elif message.content.startswith('$AE'):
            result = run_agent(message.content)
            response = result.get("output", "Error processing request.")
            if is_dm:
                await message.channel.send("Your request has been processed and sent to the server!")
                await server_channel.send(f'{response}')
            else:
                await message.channel.send(response)


def run_bot():
    """
    Runs the AutoExec bot.
    """
    botToken = Config.DISCORD_TOKEN  # Get bot token
    channelId = Config.CHANNEL_ID  # Get channel ID

    # Instantiate MeetingMinutesFormatter
    minutes_formatter = MeetingMinutesFormatter()

    # Create the bot instance
    bot = DiscordBot(channelId, minutes_formatter)

    # Start the bot using asyncio
    asyncio.run(bot.start(botToken))


if __name__ == "__main__":
    run_bot()