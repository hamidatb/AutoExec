"""
get_mm_json.py

This gets the json format of the most recent meeting minutes that match the specified template.
Note: I have not wrote testing code for this yet so beware
"""


import os

from dotenv import load_dotenv
from rich import print_json
import json

from langchain_openai import ChatOpenAI 
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser # to work with strings from a chat model output
from googledrive.main import get_file

# get all of my API keys as needed
load_dotenv()

# if the api key is outdated, run unset OPENAI_API_KEY in terminal
if not os.getenv("OPENAI_API_KEY"):
    raise EnvironmentError("API Key not found. Check your .env file!")

def create_langchain_llm() -> ChatOpenAI:
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

    return llm

def create_langchain_prompt() -> ChatPromptTemplate:
    """
    Creates a langchain prompt for the chat model.
    
    Args:
        None
    Returns:
        The ChatPromptTemplate of the model
    """
    # TODO figure out the prompt refinement needed here 
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a chatbot responsible for summarizing meeting minutes. Your responses must be structured in JSON."),
        ("system", """FORMAT: 
        Respond ONLY in the following JSON format:
        {{
            "header": "🚀 Meeting Recap!",
            "meeting_link": "URL to full minutes",
            "key_updates": [
                "✅ Key Update 1",
                "✅ Key Update 2"
            ],
            "action_items": {{
                "Person A": ["Task 1", "Task 2"],
                "Person B": ["Task 1"]
            }}
        }}"""),
        ("user", "{input}")
    ])
    return prompt


def get_model_response(meetingMinStr:str) -> str :
    """
    Get a response on a string from the model that's been initialized

    Args:
        meetingMinStr (string): The string representation of the meeting minutes document to be summarized.
    Returns:
        modelResponseStr (string): The models summary response
    """
    # TODO figure out the prompt refinement needed here 
    prompt = create_langchain_prompt()
    llm = create_langchain_llm()
    outputParser = JsonOutputParser() # for making the output an easy to work with string
    
    # omg lets make the langchain itself!
    chain = prompt | llm | outputParser

    modelResponse = chain.invoke({"input": f"{meetingMinStr}"})
    return modelResponse


def main():
    file_content = get_file()
    modelResponse = get_model_response(file_content)

    # for testing when I don't want to retrieve an actual file
    #modelResponse = get_model_response("Intro to UAIS meeting")

    # the model response is a Json string to be parsed later by the discord bot of the autoExec agent 
    print_json(data=modelResponse)


if __name__ == "__main__":
    main()