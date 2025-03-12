import discord
import os
import asyncio
from dotenv import load_dotenv
from autoexec_langchain.get_mm_json import get_meeting_mins_json

from langchain.tools import tool
from langchain.agents import AgentExecutor, create_tool_calling_agent, tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser # to work with strings from a chat model output
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec
from langchain_openai import ChatOpenAI 

from discordbot.main_bot import run_bot

# Load environment variables
load_dotenv()

# if the api key is outdated, run unset OPENAI_API_KEY in terminal
if not os.getenv("OPENAI_API_KEY"):
    raise EnvironmentError("API Key not found. Check your .env file!")

# The tools that the agent has access to are all here
@tool
def start_discord_bot():
    """
    Starts the Discord bot, which is then live to handle questions.

    Args:
        None
    Returns:
        None
    """
    run_bot()


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

    tools = [start_discord_bot]
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
    # TODO figure out the prompt refinement needed here 
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
    This takes in a query and then runs the AutoExec agent on top of that query
    """
    agent_executor = create_llm_with_tools()
    modelResponse = agent_executor.invoke({"input": f"{query}"})
    return modelResponse


query = "Can you start the discord bot?"
result = run_agent(query)

print(result["output"])  # Ensure the output is printed