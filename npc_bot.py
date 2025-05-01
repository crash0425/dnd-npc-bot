import os
import time
import json
import random
import requests
import logging
from fpdf import FPDF
from openai import OpenAI
from flask import Flask
from threading import Thread
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2 import service_account
from datetime import datetime
import schedule

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')

VOLUME_FOLDER = "npc_volumes"
SCOPES = ['https://www.googleapis.com/auth/drive.file']
GOOGLE_DRIVE_FOLDER_ID = "17s1RSf0fL2Y6-okaY854bojURv0rGMuF"
ARCHIVE_FILE = "npc_archive.txt"

app = Flask(__name__)

class PDF(FPDF):
    def header(self):
        self.set_font('Helvetica', 'B', 16)
        self.cell(0, 10, "Fantasy NPC Forge", ln=True)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', '', 8)
        self.cell(0, 10, f"Page {self.page_no()}", align='C')

def upload_to_drive(filepath):
    logging.info("Preparing to upload to Google Drive...")
    credentials_json = os.getenv('GOOGLE_CREDENTIALS')
    if not credentials_json:
        raise Exception("GOOGLE_CREDENTIALS environment variable not found!")

    credentials_info = json.loads(credentials_json)
    credentials = service_account.Credentials.from_service_account_info(
        credentials_info, scopes=SCOPES)

    service = build('drive', 'v3', credentials=credentials)

    file_metadata = {
        'name': os.path.basename(filepath),
        'parents': [GOOGLE_DRIVE_FOLDER_ID]
    }
    media = MediaFileUpload(filepath, mimetype='application/pdf')
    file = service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
    link = file.get('webViewLink')
    logging.info(f"File uploaded: {link}")
    return link

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
    logging.info(f"Generated NPC:\n{npc_text}")
    if not os.path.exists(ARCHIVE_FILE):
        with open(ARCHIVE_FILE, "w"): pass
    with open(ARCHIVE_FILE, "a") as f:
        f.write(npc_text + "\n---\n")
    return npc_text

def generate_npc_image(npc_text):
    logging.info("Generating NPC image with DALL·E...")
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    # Attempt to extract Race & Class
    race_class = "unique tavern NPC"
    for line in npc_text.splitlines():
        if line.lower().startswith("race & class"):
            parts = line.split(":", 1)
            if len(parts) > 1:
                race_class = parts[1].strip()
                break

    prompt = f"Fantasy portrait of a {race_class}, cinematic lighting, richly detailed, fantasy art style"
    logging.info(f"Image prompt: {prompt}")

    response = client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        n=1,
        size="1024x1024"
    )
    image_url = response.data[0].url
    logging.info(f"Generated image URL: {image_url}")
    return image_url

def send_to_facebook_via_make(npc_text, image_url=None):
    webhook_url = os.getenv("MAKE_WEBHOOK_URL")
    if not webhook_url:
        logging.warning("MAKE_WEBHOOK_URL not set.")
        return

    payload = {
        "npc_text": npc_text,
        "cta": os.getenv("CONVERTKIT_LINK"),
        "image_url": image_url or ""
    }

    try:
        response = requests.post(webhook_url, json=payload)
        if response.status_code == 200:
            logging.info("✅ NPC + image sent to Make for Facebook photo post.")
        else:
            logging.error(f"❌ Failed to send to Make: {response.status_code} {response.text}")
    except Exception as e:
        logging.exception("Error sending NPC to Make.com")

def post_weekly_npc():
    logging.info("Weekly NPC Post Task Started")
    npc = generate_npc()
    image_url = generate_npc_image(npc)
    send_to_facebook_via_make(npc.strip(), image_url=image_url)

    if not os.path.exists(ARCHIVE_FILE):
        with open(ARCHIVE_FILE, "w"): pass
    with open(ARCHIVE_FILE, "a") as f:
        f.write(npc.strip() + "
---
")
