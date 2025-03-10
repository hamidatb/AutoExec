import os

from dotenv import load_dotenv

from langchain_openai import ChatOpenAI 
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser # to work with strings from a chat model output
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
        ("system", "You are a chatbot who is resposible for summarizing the meeting minutes content, and writing the summary of action tasks in a friendly way"),
        ("user", "{input}")
    ])
    return prompt

def init_langchain_model() -> tuple :
    """"""
    # TODO figure out the prompt refinement needed here 
    prompt = create_langchain_prompt()
    llm = create_langchain_llm()

    # omg lets make the langchain itself!
    chain = prompt | llm

    chain.invoke({"input": "explain Hamidat Bello to me"})
    response = llm.invoke("Explain Hamidat Bello to me")
    print(response)  # Ensure the output is printed

    return (prompt, llm)



file_content = get_file()
print(file_content)
