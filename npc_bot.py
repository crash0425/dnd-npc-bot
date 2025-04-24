import os
import time
import json
import requests
import logging
from fpdf import FPDF
from openai import OpenAI
from flask import Flask
from threading import Thread
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2 import service_account

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')

VOLUME_FOLDER = "npc_volumes"
SCOPES = ['https://www.googleapis.com/auth/drive.file']
GOOGLE_DRIVE_FOLDER_ID = "17s1RSf0fL2Y6-okaY854bojURv0rGMuF"  # Folder where PDFs will be saved

class PDF(FPDF):
    def header(self):
        self.set_font('Helvetica', 'B', 16)
        self.cell(0, 10, "Fantasy NPC Forge", new_x="LMARGIN", new_y="NEXT")

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
    file_id = file.get('id')
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
    pdf.cell(0, 80, "", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 20, "Fantasy NPC Forge", new_x="LMARGIN", new_y="NEXT", align='C')
    pdf.set_font("Helvetica", '', 18)
    pdf.cell(0, 20, f"Tavern NPC Pack - Volume {volume_number}", new_x="LMARGIN", new_y="NEXT", align='C')

    for npc in volume_npcs:
        pdf.add_page()
        lines = npc.splitlines()
        for line in lines:
            safe_line = line.replace("’", "'").replace("–", "-").replace("“", '"').replace("”", '"')

            if ":" in safe_line:
                label, content = safe_line.split(":", 1)
                label = label.strip()
                content = content.strip()

                if label.lower() in ["name", "race & class"]:
                    pdf.set_font("Helvetica", 'B', 14)
                else:
                    pdf.set_font("Helvetica", '', 12)

                try:
                    pdf.cell(50, 8, f"{label}:", new_x="RIGHT", new_y="TOP")
                    pdf.multi_cell(0, 8, content, new_x="LMARGIN", new_y="NEXT")
                except Exception as e:
                    logging.warning(f"Skipping problematic line: {safe_line} | Error: {e}")
            else:
                pdf.set_font("Helvetica", '', 12)
                try:
                    pdf.multi_cell(0, 8, safe_line)
                except Exception as e:
                    logging.warning(f"Skipping problematic line: {safe_line} | Error: {e}")
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
    return npc_text

def job():
    logging.info("Starting job...")
    os.makedirs(VOLUME_FOLDER, exist_ok=True)
    volume_number = len(os.listdir(VOLUME_FOLDER)) + 1
    logging.info(f"Creating Volume {volume_number}...")
    volume_npcs = [generate_npc() for _ in range(2)]
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

def keep_alive():
    Thread(target=lambda: app.run(host="0.0.0.0", port=8080)).start()

if __name__ == "__main__":
    keep_alive()
    Thread(target=job).start()
    while True:
        time.sleep(2592000)  # 30 days
        job()
