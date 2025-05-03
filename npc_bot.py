import os
import time
import json
import random
import requests
import logging
from flask import Flask
from fpdf import FPDF
from openai import OpenAI
from threading import Thread
from datetime import datetime
import schedule
from npc_video_generator import generate_npc_audio, create_npc_video

# Constants
VOLUME_FOLDER = "npc_volumes"
ARCHIVE_FILE = "npc_archive.txt"
CONVERTKIT_LINK = os.getenv("CONVERTKIT_LINK", "https://fantasy-npc-forge.kit.com/2aa9c10f01")

# Setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')
app = Flask(__name__)

# PDF Generator Class
class PDF(FPDF):
    def header(self):
        self.set_font('Helvetica', 'B', 16)
        self.cell(0, 10, "Fantasy NPC Forge", ln=True)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', '', 8)
        self.cell(0, 10, f"Page {self.page_no()}", align='C')

# Upload video to Google Drive

def upload_video_to_drive(filepath):
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from google.oauth2 import service_account

    logging.info("Uploading video to Google Drive...")
    credentials_json = os.getenv("GOOGLE_CREDENTIALS")
    folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")

    if not credentials_json or not folder_id:
        logging.error("Missing GOOGLE_CREDENTIALS or GOOGLE_DRIVE_FOLDER_ID.")
        return

    credentials_info = json.loads(credentials_json)
    credentials = service_account.Credentials.from_service_account_info(credentials_info)
    service = build("drive", "v3", credentials=credentials)

    file_metadata = {
        "name": os.path.basename(filepath),
        "parents": [folder_id]
    }
    media = MediaFileUpload(filepath, mimetype="video/mp4")
    uploaded = service.files().create(body=file_metadata, media_body=media, fields="id, webViewLink").execute()
    logging.info(f"🎬 Video uploaded to Google Drive: {uploaded.get('webViewLink')}")

# Core NPC generation

def generate_npc():
    logging.info("Calling OpenAI to generate NPC...")
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a fantasy NPC generator for a Dungeons & Dragons campaign."},
            {"role": "user", "content": "Generate a detailed NPC with the following fields: Name, Race & Class, Personality, Quirks, Backstory, Ideal, Bond, Flaw. Format with line breaks and labels."}
        ],
        temperature=0.8
    )
    npc_text = response.choices[0].message.content
    logging.info(f"Generated NPC: {npc_text}")
    if not os.path.exists(ARCHIVE_FILE):
        with open(ARCHIVE_FILE, "w"): pass
    with open(ARCHIVE_FILE, "a") as f:
        f.write(npc_text + "\n---\n")
    return npc_text

# Run scheduler and keep service alive

def run_schedule():
    while True:
        schedule.run_pending()
        time.sleep(60)

@app.route('/')
def home():
    return "✅ Bot is running"

if __name__ == "__main__":
    Thread(target=run_schedule).start()
    app.run(host="0.0.0.0", port=10000)
