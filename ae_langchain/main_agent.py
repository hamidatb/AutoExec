"""
This is the file to run the agent from.
It will intialize the discord bot on startup, and any messages to the bot are routed through this agent.
"""
import os
import asyncio
from asyncio import create_task
from dotenv import load_dotenv
from langchain.tools import tool
from langchain.agents import AgentExecutor, create_tool_calling_agent, tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI 

# Load environment variables
load_dotenv()

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
    from discordbot.discord_client import     BOT_INSTANCE


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


# TODO - Cannot be called yet
@tool
def create_meeting_mins():
    """
    Create a new meeting minute document for the meeting today.
    """
    #TODO

@tool
def check_for_upcoming_meeting():
    """
    Checks the given Google Document to see when the next upcoming meeting is.
    If the next meeting in within 4 days, then notify the users.
    """
    #TODO


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

    tools = [send_meeting_mins_summary, start_discord_bot]
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
            ("system", "You a helpful assistant"),
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

# run the agent to start the bot
if __name__ == "__main__":
    query = "Start the discord bot"
    result = run_agent(query)

    print(result["output"])  # Ensure output is displayed