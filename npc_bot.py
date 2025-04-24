import os
import time
import json
import requests
from fpdf import FPDF
from openai import OpenAI
from flask import Flask
from threading import Thread
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2 import service_account

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
    return file.get('webViewLink')

def create_volume_pdf(volume_npcs, volume_number):
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
                safe_text = f"{label.strip()}: {content.strip()}"
                pdf.set_font("Helvetica", 'B' if label.lower() in ["name", "race & class"] else '', 14)
                pdf.multi_cell(190, 8, safe_text)
            else:
                pdf.set_font("Helvetica", '', 12)
                pdf.multi_cell(190, 8, safe_line)
        pdf.ln(10)

    pdf.output(output_file)
    drive_link = upload_to_drive(output_file)
    print(f"Uploaded to Google Drive: {drive_link}")
    return cover_image_path, output_file

def generate_npc():
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a creative Dungeons & Dragons NPC generator."},
                {"role": "user", "content": "Generate a creative D&D NPC with:\nName\nRace & Class\nPersonality\nQuirks\nBackstory\nIdeal\nBond\nFlaw"}
            ],
            temperature=0.9
        )
        npc_text = response.choices[0].message.content.strip()
        if not npc_text:
            raise ValueError("NPC content is empty!")
        return npc_text
    except Exception as e:
        print(f"❌ Failed to generate NPC: {e}")
        return "Name: Error\nRace & Class: Unknown\nPersonality: Glitched\nQuirks: N/A\nBackstory: There was an error generating this NPC.\nIdeal: Survival\nBond: None\nFlaw: Corrupted"

def job():
    os.makedirs(VOLUME_FOLDER, exist_ok=True)
    volume_number = len(os.listdir(VOLUME_FOLDER)) + 1
    volume_npcs = [generate_npc() for _ in range(10)]
    cover_path, pdf_path = create_volume_pdf(volume_npcs, volume_number)
    print(f"Generated Volume {volume_number} → {pdf_path}")

app = Flask(__name__)

@app.route('/')
def home():
    return "NPC Bot is alive!"

def keep_alive():
    Thread(target=lambda: app.run(host="0.0.0.0", port=8080)).start()

if __name__ == "__main__":
    keep_alive()
    job()
    while True:
        time.sleep(2592000)  # 30 days
        job()
