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
CONVERTKIT_LINK = "https://fantasy-npc-forge.kit.com/2aa9c10f01"
ARCHIVE_FILE = "npc_archive.txt"

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
    logging.info(f"Uploading file: {filepath} to folder ID: {GOOGLE_DRIVE_FOLDER_ID}")
    file = service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
    link = file.get('webViewLink')
    logging.info(f"File uploaded: {link}")

    with open("upload_log.txt", "a") as log_file:
        log_file.write(f"{os.path.basename(filepath)} → {link}\n")

    return link

def create_volume_pdf(volume_npcs, volume_number):
    logging.info("Generating cover image with OpenAI...")
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    prompt = "Epic fantasy tavern interior, warm lighting, cozy but grand, filled with mysterious travelers, detailed environment, fantasy art style, cinematic, ultra-detailed"
    image_response = client.images.generate(model="dall-e-3", prompt=prompt, n=1, size="1024x1024")
    image_url = image_response.data[0].url
    image_data = requests.get(image_url).content

    os.makedirs(VOLUME_FOLDER, exist_ok=True)
    cover_image_path = os.path.join(VOLUME_FOLDER, f"cover_volume{volume_number}.png")
    with open(cover_image_path, "wb") as f:
        f.write(image_data)

    output_file = os.path.join(VOLUME_FOLDER, f"Fantasy_NPC_Forge_Volume{volume_number}.pdf")
    pdf = PDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    pdf.add_page()
    pdf.image(cover_image_path, x=10, y=20, w=190)

    pdf.add_page()
    pdf.set_font("Helvetica", 'B', 24)
    pdf.cell(0, 80, "", ln=True)
    pdf.cell(0, 20, "Fantasy NPC Forge", ln=True, align='C')
    pdf.set_font("Helvetica", '', 18)
    pdf.cell(0, 20, f"Tavern NPC Pack - Volume {volume_number}", ln=True, align='C')

    for npc in volume_npcs:
        pdf.add_page()
        lines = npc.splitlines()
        for line in lines:
            safe_line = (line.replace("’", "'")
                              .replace("–", "-")
                              .replace("“", '"')
                              .replace("”", '"')
                              .replace("…", "...")
                              .replace("•", "-")
                              .replace("̈", ""))

            if ":" in safe_line:
                label, content = safe_line.split(":", 1)
                label = label.strip()
                content = content.strip()

                pdf.set_font("Helvetica", 'B', 12)
                pdf.multi_cell(0, 8, f"{label}:")
                pdf.set_font("Helvetica", '', 12)
                pdf.multi_cell(0, 8, content)
                pdf.ln(2)
            else:
                pdf.set_font("Helvetica", '', 12)
                try:
                    pdf.multi_cell(0, 8, safe_line)
                except Exception as e:
                    logging.warning(f"Skipping line: {safe_line} | Error: {e}")
        pdf.ln(5)

    pdf.output(output_file)

    if not os.path.exists(output_file):
        logging.error(f"PDF was not created at: {output_file}")
    else:
        logging.info(f"PDF ready to upload: {output_file}")

    drive_link = upload_to_drive(output_file)
    logging.info(f"Uploaded to Google Drive: {drive_link}")
    return cover_image_path, output_file

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

def post_to_twitter(text):
    logging.info("Attempting to post to Twitter (v2)...")
    try:
        bearer_token = os.getenv("TWITTER_BEARER_TOKEN")
        if not bearer_token:
            raise ValueError("TWITTER_BEARER_TOKEN environment variable missing!")

        headers = {
            "Authorization": f"Bearer {bearer_token}",
            "Content-Type": "application/json"
        }
        payload = {
            "text": text[:280]
        }
        response = requests.post(
            "https://api.twitter.com/2/tweets",
            headers=headers,
            json=payload
        )

        if response.status_code == 201:
            logging.info("✅ Tweet posted successfully (v2)!")
        else:
            logging.error(f"❌ Twitter post failed: {response.status_code} {response.text}")
    except Exception as e:
        logging.exception("❌ Unexpected error posting to Twitter")

def post_weekly_npc():
    logging.info("Weekly NPC Post Task Started")
    if not os.path.exists(ARCHIVE_FILE):
        logging.warning("Archive file not found.")
        return
    with open(ARCHIVE_FILE, "r") as f:
        npcs = f.read().split("---")
    if npcs:
        npc = random.choice([x for x in npcs if x.strip()])
        post_text = f"🧙 New NPC from Fantasy NPC Forge!\n\n{npc.strip()}\n\n📥 Download Volume 1 free and grow your campaign: {CONVERTKIT_LINK}"
        post_to_twitter(post_text)
    else:
        logging.warning("No NPCs found in archive.")

def job():
    logging.info("Starting job...")
    os.makedirs(VOLUME_FOLDER, exist_ok=True)
    volume_number = len(os.listdir(VOLUME_FOLDER)) + 1
    logging.info(f"Creating Volume {volume_number}...")
    volume_npcs = [generate_npc() for _ in range(10)]
    logging.info("NPCs generated")
    try:
        cover_path, pdf_path = create_volume_pdf(volume_npcs, volume_number)
        if os.path.exists(pdf_path):
            logging.info(f"Generated Volume {volume_number}: {pdf_path}")
        else:
            logging.error(f"PDF not found: {pdf_path}")
    except Exception as e:
        logging.exception("Error during volume generation")

app = Flask(__name__)

@app.route('/')
def home():
    return "NPC Bot is alive!"

@app.route('/post-test')
def post_test():
    Thread(target=post_weekly_npc).start()
    return "Triggered a manual Twitter post!"

def keep_alive():
    Thread(target=lambda: app.run(host="0.0.0.0", port=8080)).start()

def volume_and_then_post():
    job()
    time.sleep(5)
    post_weekly_npc()

if __name__ == "__main__":
    keep_alive()
    Thread(target=volume_and_then_post).start()
    schedule.every().monday.at("10:00").do(post_weekly_npc)
    schedule.every().thursday.at("10:00").do(post_weekly_npc)
    schedule.every(30).days.do(job)

    while True:
        schedule.run_pending()
        time.sleep(60)
