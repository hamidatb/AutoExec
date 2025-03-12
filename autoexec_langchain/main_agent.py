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

# Load environment variables
load_dotenv()

# if the api key is outdated, run unset OPENAI_API_KEY in terminal
if not os.getenv("OPENAI_API_KEY"):
    raise EnvironmentError("API Key not found. Check your .env file!")



@tool
def add(a: int, b:int) -> int:
    """
    Adds a and b

    Args:
        a: int a
        b: int b
    """
    return a + b

@tool 
def magic_function(a: int, b:int) -> int:
    """
    Multiplies a and b

    Args:
        a: int a
        b: int b
    """
    return a * b


def create_llm_with_tools() -> ChatOpenAI:
    """
    Creates the base llm for the chatting

    Args:
        None
    Returns:
        The langchain ChatOpenAI model
    """
    
    # init a basic langchain OpenAi model 
    llm = ChatOpenAI(
        model="gpt-3.5-turbo",
        temperature=0,
        max_tokens=None,
        timeout=None,
        max_retries=2,
    )

    tools = [add, magic_function]
    

    # give the llm access to the tool functions 
    prompt = create_langchain_prompt()
    #llm_with_tools = llm.bind_tools(tools)
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
    agent_executor = create_llm_with_tools()
    modelResponse = agent_executor.invoke({"input": f"{query}"})
    return modelResponse


# make a basic query
query = "Whats 8*2 and the output 113 of 4 if I used a magic function?"
result = run_agent(query)

print("\n\n\n\n")  # Ensure the output is printed
print(result["output"])  # Ensure the output is printed