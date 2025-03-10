import getpass
import os
import time
import langchain

from dotenv import load_dotenv

from pinecone import Pinecone, ServerlessSpec
from langchain_openai import ChatOpenAI 

# get the Pinecone and openAI api keys
load_dotenv()

# if the api key is outdated, run unset OPENAI_API_KEY in terminal
if not os.getenv("OPENAI_API_KEY"):
    raise EnvironmentError("API Key not found. Check your .env file!")


llm = ChatOpenAI(
    model="gpt-3.5-turbo",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=2,
)

response = llm.invoke("Explain Hamidat Bello to me")
print(response)  # Ensure the output is printed