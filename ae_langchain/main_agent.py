"""
This is the file to run the agent from.
It will intialize the discord bot on startup, and any messages to the bot are routed through this agent.
"""
import os
import asyncio
from asyncio import create_task
from langchain.tools import tool
from langchain.agents import AgentExecutor, create_tool_calling_agent, tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI 

from googledrive.file_handler import create_meeting_mins_for_today
from googledrive.calendar import get_upcoming_meetings_list, get_formatted_meeting_schedule

from config import Config
import datetime

# Load environment variables
Config().validate()

# if the api key is outdated, run unset OPENAI_API_KEY in terminal
if not os.getenv("OPENAI_API_KEY"):
    raise EnvironmentError("API Key not found. Check your .env file!")

@tool 
def start_discord_bot():
    """
    Starts the Discord bot asynchronously, allowing the LangChain agent to remain active.

    Args:
        None
    Returns:
        str: Confirmation message that the bot was started.
    """
    from discordbot.discord_client import run_bot

    loop = asyncio.get_event_loop()
    if loop.is_running():
        loop.create_task(run_bot())  # Run bot as async task in existing event loop
    else:
        asyncio.run(run_bot())  # Run bot in a new event loop if none is running

    return "✅ Discord bot has been started and is now running!"

@tool
def send_meeting_mins_summary():
    """
    Must return the FULL formatted string from this as your response if the users question asked for the meeting minutes or said $AEmm. 

    Args:
        None
    Returns:
        str: Confirmation message that the bot was started.
    """
    from discordbot.discord_client import BOT_INSTANCE

    if BOT_INSTANCE is None:
        return "❌ ERROR: The bot instance is not running."

    # Run the message-sending function inside the bot event loop
    loop = asyncio.get_event_loop()
    if loop.is_running():
        #print("The loop is already running")
        loop.create_task(BOT_INSTANCE.send_meeting_minutes())  # Use existing bot instance
    else:
        asyncio.run(BOT_INSTANCE.send_meeting_minutes())  # Create new loop if needed

    return "✅ Meeting minutes have been sent via Discord."

@tool
def create_meeting_mins() -> str:
    """
    Creates the meeting minute document for today 
    and returns the link the minutes, which should be sent to Discord afterwards using send_output_to_discord()

    Args:
        None
    Returns:
        The meeting minute link (str)
    """
    meetingMinsLink = create_meeting_mins_for_today()
    if not meetingMinsLink:
        print("There was an error in creating the meeting minutes")
        return "There was an error in creating the meeting minutes"
    else:
        return meetingMinsLink

@tool
def send_output_to_discord(messageToSend:str) -> str:
    """
    Sends a message directly to the Discord chat on behalf of the bot.

    **MANDATORY USAGE**: 
    - If a user asks the AI a direct question that doesn't trigger another tool, this function MUST be used.
    - Always call this function when responding to general questions in Discord.
    - NEVER answer in plain text without using this function when interacting in Discord.

    Args:
        messageToSend (str): The response message to send.

    Returns:
        str: A confirmation that the message was sent.
    """
    from discordbot.discord_client import BOT_INSTANCE

    if BOT_INSTANCE is None:
        return "❌ ERROR: The bot instance is not running."

    # Run the message-sending function inside the bot event loop
    loop = asyncio.get_event_loop()
    if loop.is_running():
        # Call send_any_message with the message parameter
        loop.create_task(BOT_INSTANCE.send_any_message(str(messageToSend)))
    else:
        # Call send_any_message with the message parameter
        asyncio.run(BOT_INSTANCE.send_any_message(str(messageToSend)))

    return "✅ Message has been sent to Discord."

@tool
def send_meeting_schedule(amount_of_meetings_to_return: int):
    """
    Retrieves a formatted string representation of the upcoming few meetings, 
    and automatically sends it to Discord. 

    **This function REQUIRES an argument. It will raise an error if none is provided.**

    Args:
        amount_of_meetings_to_return (int): The number of meetings to return (REQUIRED).
        
    Returns:
        str: Confirmation that the schedule was sent.
    """
    # Ensure an argument is provided
    if amount_of_meetings_to_return is None:
        raise ValueError("❌ ERROR: 'amount_of_meetings_to_return' is REQUIRED but was not provided. Please try again")

    # error handling is done within each of these respective functions
    meetings = get_upcoming_meetings_list(amount_of_meetings_to_return)
    res = get_formatted_meeting_schedule(meetings)
    send_output_to_discord(res)

    return "The meeting schedule has been sent to Discord now"
    
@tool
def send_reminder_for_next_meeting():
    """
    Send a message in Discord reminding everyone about the upcoming meeting.
    """

    # get the details of the most recent meeting
    upcoming_meeting = get_upcoming_meetings_list(1)

    formatted_meeting_reminder = f"""
        Hi @everyone! Reminder that we have an upcoming meeting:

        **Date:**: {upcoming_meeting[0]["date"]} | **Time:** {upcoming_meeting[0]["start_time"]}
        **Reason:**: {upcoming_meeting[0]["title"]}
        **Where**: {upcoming_meeting[0]["location"]}
    """

    send_output_to_discord(formatted_meeting_reminder)

    return "The reminder for our nearest meeting has now been sent to Discord"
@tool
def handle_misc_questions() -> str:
    """
    Tells the agent how to handle misclaneous questions that don't perfectly match to the other tools avalible.

    Args:
        None

    Returns:
        string: What to do
    """

    return "Respond IN DISCORD based on your knowledge as an LLM, so long as it is a work appropriate question. Invoke send_output_to_discord after this."

# These are agent helper functions for instantiation
def create_llm_with_tools() -> ChatOpenAI:
    """
    Creates the base agentic AI model

    Args:
        None
    Returns:
        The langchain ChatOpenAI model
    """
    # I dont wanna use an expensive model, use the cheapest gpt LOL
    llm = ChatOpenAI(
        model="gpt-3.5-turbo",
        temperature=0,
        max_tokens=None,
        timeout=None,
        max_retries=2,
    )

    tools = [send_meeting_mins_summary, start_discord_bot, send_output_to_discord, create_meeting_mins, send_meeting_schedule,handle_misc_questions, send_reminder_for_next_meeting]
    prompt = create_langchain_prompt()

    # give the llm access to the tool functions 
    agent = create_tool_calling_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

    return agent_executor

def create_langchain_prompt() -> ChatPromptTemplate:
    """
    Creates a langchain prompt for the chat model.
    
    Args:
        None
    Returns:
        The ChatPromptTemplate of the model
    """
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "You are a helpful assistant. ALWAYS use the `send_output_to_discord` tool to send responses to Discord unless another tool already sends the message."),
            ("user", "{input}"),
            MessagesPlaceholder("agent_scratchpad")
        ]
    )
    return prompt


def run_agent(query: str):
    """
    Runs the LangChain agent with the given query.

    Args:
        query (str): The input query.

    Returns:
        dict: The response from the agent.
    """
    agent_executor = create_llm_with_tools()
    response = agent_executor.invoke({"input": f"{query}"})
    return response


def run_agent_text_only(query: str):
    """
    Runs the LangChain agent in text-only mode (no Discord sending).
    Use this when calling from the Discord bot to avoid event loop issues.

    Args:
        query (str): The input query.

    Returns:
        str: The text response from the agent.
    """
    # Create a modified prompt that doesn't require Discord sending
    from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful assistant. Provide direct, helpful responses to user questions. Do not mention sending messages to Discord or using any Discord tools."),
        ("user", "{input}"),
        MessagesPlaceholder("agent_scratchpad")
    ])
    
    # Create a simple LLM without the Discord tools
    llm = ChatOpenAI(
        model="gpt-3.5-turbo",
        temperature=0,
        max_tokens=None,
        timeout=None,
        max_retries=2,
    )
    
    # Create a simple agent without Discord tools
    from langchain.agents import AgentExecutor, create_tool_calling_agent
    
    # Only include non-Discord tools
    safe_tools = [create_meeting_mins, send_meeting_schedule, handle_misc_questions]
    
    agent = create_tool_calling_agent(llm, safe_tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=safe_tools, verbose=False)
    
    try:
        response = agent_executor.invoke({"input": f"{query}"})
        return response.get("output", "I'm sorry, I couldn't process that request.")
    except Exception as e:
        return f"I'm sorry, I encountered an error: {str(e)}"

async def run_tasks():
    # Start the Discord bot by running the agent with the "Start the discord bot" query
    query = "Start the discord bot"
    result = await run_agent(query)  # Ensure `run_agent` is async
    print(result["output"])  # Print confirmation that the bot has started

    # Add any other async tasks if needed
    
async def send_hourly_message():
    """
    Sends a message to Discord every hour.
    """
    while True:
        query = "Send a message saying 'hi'"
        result = await run_agent(query)
        print(result["output"])  # Confirm message sent
        await asyncio.sleep(3600)  # Wait for 1 hour (3600 seconds)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    print(f"This is the main asybc==")

    try:
        loop.run_until_complete(run_tasks())  # Run the async function without creating a new event loop
    except KeyboardInterrupt:
        print("Shutting down...")
    finally:
        loop.close()