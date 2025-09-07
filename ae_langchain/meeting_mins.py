"""
get_mm_json.py

This gets the JSON format of the most recent meeting minutes that match the specified template.
"""
from config.config import Config
import os
import json
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI 
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from googledrive.file_handler import getFileContentStr

# load all of the variables needed
Config()

class MeetingMinutesLangchainModel:
    """
    Reusable LangChain model pipeline for meeting minutes summarization
    """

    def __init__(self):
        """Initialize LangChain components once to avoid redundant API calls."""
        self.llm = ChatOpenAI(
            model="gpt-3.5-turbo",
            temperature=0,
            max_tokens=None,
            timeout=None,
            max_retries=2,
        )

        # Tell this llm that all it does is handle the retrieving meeting mins and json activities
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a chatbot responsible for summarizing meeting minutes. Your responses must be structured in JSON."),
            ("system", """FORMAT: 
            Respond ONLY in the following JSON format:
            {{
                "header": "🚀 Hi @everyone. Here's our meeting recap!",
                "meeting_link": "URL to full minutes: _url_here_",
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

        self.output_parser = JsonOutputParser()

        # Create the full processing chain once (instead of rebuilding it every call)
        self.chain = self.prompt | self.llm | self.output_parser

    def process(self, meeting_minutes_text: str) -> dict:
        """
        Processes raw meeting minutes text and returns structured JSON
        """
        return self.chain.invoke({"input": meeting_minutes_text})


# --- singleton to a ---
meeting_minutes_model = MeetingMinutesLangchainModel()


def get_meeting_mins_json() -> dict:
    """
    Fetches the latest meeting minutes, processes them, and returns the JSON representation.
    """
    # get the raw meeting minutes file from Google Drive (this calls the google drive API)
    file_content = getFileContentStr(1) # 1 means it's checking for meeting mins. 

    # get structured JSON response from LangChain
    model_response = meeting_minutes_model.process(file_content)

    return model_response  


# --- Meeting Minutes Formatter ---
class MeetingMinsFormatter:
    """Formats meeting minutes into a readable string for Discord."""

    def __init__(self, meeting_mins_dict: dict):
        """
        Initializes the formatter with a given meeting minutes dictionary.

        Args:
            meeting_mins_dict (dict): JSON-formatted meeting minutes.
        """
        self.meeting_mins_dict = meeting_mins_dict

    def format(self) -> str:
        """Formats the meeting minutes into a user-friendly message."""
        formatted_key_updates = "**Key Updates**:\n"
        for update in self.meeting_mins_dict.get("key_updates", []):
            formatted_key_updates += f"- {update}\n"

        formatted_action_items = "**Action Items**:\n"
        for person, tasks in self.meeting_mins_dict.get("action_items", {}).items():
            formatted_action_items += f"**{person}**\n"
            for task in tasks:
                formatted_action_items += f"- {task}\n"

        message_to_send = f"""
        \n{self.meeting_mins_dict.get("header", "")}
        \n{self.meeting_mins_dict.get("meeting_link", "")}
        \n{formatted_key_updates.rstrip()}
        \n\n{formatted_action_items}
        """
        return message_to_send


if __name__ == "__main__":
    # Fetch latest meeting minutes and format them
    meeting_mins_dict = get_meeting_mins_json()
    formatted_meeting_mins = MeetingMinsFormatter(meeting_mins_dict)
