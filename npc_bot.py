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

def generate_npc_image(npc_text):
    logging.info("Generating NPC image with DALL·E...")
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
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
        "cta": CONVERTKIT_LINK,
        "image_url": image_url or ""
    }

    try:
        response = requests.post(webhook_url, json=payload)
        if response.status_code == 200:
            logging.info("✅ NPC + image + caption sent to Make for Facebook post.")
        else:
            logging.error(f"❌ Failed to send to Make: {response.status_code} {response.text}")
    except Exception as e:
        logging.exception("Error sending to Make.com")

@app.route("/test-make")
def test_make_post():
    npc = generate_npc()
    image_url = generate_npc_image(npc)

    # Save image locally
    image_path = os.path.join("npc_assets", f"npc_{int(time.time())}.png")
    os.makedirs("npc_assets", exist_ok=True)
    with open(image_path, "wb") as f:
        f.write(requests.get(image_url).content)

    # Generate voice + video
    audio_path = generate_npc_audio(npc)
    if audio_path:
        create_npc_video(image_path, audio_path)

    send_to_facebook_via_make(npc, image_url)
    return "✅ Facebook + video creation triggered!"

def create_volume_pdf(volume_npcs, volume_number):
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from google.oauth2 import service_account

    logging.info("Generating PDF Volume...")
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
                pdf.set_font("Helvetica", 'B', 12)
                pdf.multi_cell(0, 8, f"{label.strip()}:")
                pdf.set_font("Helvetica", '', 12)
                pdf.multi_cell(0, 8, content.strip())
                pdf.ln(2)
            else:
                pdf.set_font("Helvetica", '', 12)
                pdf.multi_cell(0, 8, safe_line)
        pdf.ln(5)

    pdf.output(output_file)
    logging.info(f"📘 PDF saved to {output_file}")

    credentials_json = os.getenv("GOOGLE_CREDENTIALS")
    folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
    if credentials_json and folder_id:
        credentials_info = json.loads(credentials_json)
        credentials = service_account.Credentials.from_service_account_info(credentials_info)
        service = build("drive", "v3", credentials=credentials)

        file_metadata = {
            "name": os.path.basename(output_file),
            "parents": [folder_id]
        }
        media = MediaFileUpload(output_file, mimetype="application/pdf")
        uploaded = service.files().create(body=file_metadata, media_body=media, fields="id, webViewLink").execute()
        logging.info(f"📤 PDF uploaded to Google Drive: {uploaded.get('webViewLink')}")

def job():
    logging.info("📚 Starting 6-month volume creation...")
    os.makedirs(VOLUME_FOLDER, exist_ok=True)
    volume_number = len(os.listdir(VOLUME_FOLDER)) + 1
    volume_npcs = [generate_npc() for _ in range(10)]
    create_volume_pdf(volume_npcs, volume_number)

if __name__ == "__main__":
    Thread(target=lambda: app.run(host="0.0.0.0", port=10000)).start()
    schedule.every(180).days.do(job)
    while True:
        schedule.run_pending()
        time.sleep(60)
