import functions_framework
import json
import base64
import os
from google.cloud import pubsub_v1
from googleapiclient.discovery import build
from google.oauth2 import service_account
from autoexec_langchain.main_agent import run_agent

@functions_framework.cloud_event
def autoexec_drive_change_listener(cloud_event):
    """
    Google Cloud Function that listens for Google Drive file changes.
    When triggered, it runs the LangChain agent.
    """
    print("🚀 Function triggered!")

    event_data = cloud_event.data
    print(f"Received event from Pub/Sub: {event_data}")

    # Decode the Pub/Sub message (it arrives as Base64)
    # Extract and decode the Pub/Sub message
    try:
        encoded_message = event_data["message"]["data"]
        decoded_bytes = base64.b64decode(encoded_message)  # Decode Base64
        message_json = json.loads(decoded_bytes.decode("utf-8"))  # Convert to JSON
        file_id = message_json.get("file_id")
        file_name = message_json.get("file_name")
    except Exception as e:
        print(f"Error decoding Pub/Sub message: {e}")
        return "Error decoding message."

    if not file_id:
        print("No file ID found in event.")
        return "No file ID found."

    # Log the detected change
    print(f"Detected change in Google Drive: {file_name} (ID: {file_id})")

    # Build a query for the LangChain agent.
    query = f"Start the discord bot"
    
    # Run the LangChain agent
    response = run_agent(query)
    
    print(f"LangChain Agent Response: {response}")
    return "LangChain agent executed successfully!"
