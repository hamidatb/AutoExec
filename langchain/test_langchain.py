import getpass
import os
import time
import langchain

from dotenv import load_dotenv

from pinecone import Pinecone, ServerlessSpec
from langchain_openai import ChatOpenAI # type: ignore

# get the Pinecone and openAI api kets
if not load_dotenv():
    raise EnvironmentError("Failed to load .env file")
    
llm = ChatOpenAI(
    model="gpt-3.5-turbo",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=2,
)

llm("Explain Hamidat Bello to me")