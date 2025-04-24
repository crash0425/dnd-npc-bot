import os
import time
import random
import requests
import schedule
import openai
from flask import Flask, request, redirect
from threading import Thread
from datetime import datetime
from fpdf import FPDF
from dotenv import load_dotenv
from facebook_uploader import post_to_facebook
from gdrive_uploader import upload_to_drive

# ✅ Add this block right after imports
if not os.path.exists("npc_volumes"):
    os.makedirs("npc_volumes")

if not os.path.exists("npc_archive.txt"):
    with open("npc_archive.txt", "w", encoding="utf-8") as f:
        f.write("")  # create an empty file
# --- Load environment variables
load_dotenv()

# --- Constants
ARCHIVE_FILE = "npc_archive.txt"
VOLUME_FOLDER = "npc_volumes"
FONT_DIR = os.path.join(os.path.dirname(__file__), "fonts")
NPCS_PER_VOLUME = 10

# --- Flask setup
app = Flask(__name__)
bot_start_time = datetime.now()
last_post_time = None

# --- Facebook settings
CONVERTKIT_LINK = "https://fantasy-npc-forge.kit.com/2aa9c10f01"

class PDF(FPDF):
    def header(self):
        self.set_font('DejaVu', 'B', 16)
        self.cell(0, 10, "Fantasy NPC Forge", new_x="LMARGIN", new_y="NEXT")

    def footer(self):
        self.set_y(-15)
        self.set_font('DejaVu', '', 8)
        self.cell(0, 10, f"Page {self.page_no()}", align='C')

# --- Utility Functions
def generate_npc():
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a creative Dungeons & Dragons NPC generator."},
            {"role": "user", "content": "Generate a creative D&D NPC with:\nName\nRace & Class\nPersonality\nQuirks\nBackstory\nIdeal\nBond\nFlaw"}
        ],
        temperature=0.9
    )
    npc = response.choices[0].message.content.strip()
    save_npc(npc)
    return npc

def save_npc(npc_text):
    os.makedirs(VOLUME_FOLDER, exist_ok=True)
    if not os.path.exists(ARCHIVE_FILE):
        with open(ARCHIVE_FILE, "w", encoding="utf-8") as f:
            f.write("")
    with open(ARCHIVE_FILE, "a", encoding="utf-8") as f:
        f.write(npc_text + "\n---\n")

def create_volume_pdf(volume_npcs, volume_number):
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
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
    pdf.add_font('DejaVu', '', os.path.join(FONT_DIR, 'DejaVuSans.ttf'), uni=True)
    pdf.add_font('DejaVu', 'B', os.path.join(FONT_DIR, 'DejaVuSans-Bold.ttf'), uni=True)
    pdf.set_auto_page_break(auto=True, margin=15)

    pdf.add_page()
    pdf.image(cover_image_path, x=10, y=20, w=190)

    pdf.add_page()
    pdf.set_font("DejaVu", 'B', 24)
    pdf.cell(0, 80, "", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 20, "Fantasy NPC Forge", new_x="LMARGIN", new_y="NEXT", align='C')
    pdf.set_font("DejaVu", '', 18)
    pdf.cell(0, 20, f"Tavern NPC Pack - Volume {volume_number}", new_x="LMARGIN", new_y="NEXT", align='C')

    for npc in volume_npcs:
        pdf.add_page()
        lines = npc.splitlines()
        for line in lines:
            line = line.replace("’", "'")  # Replace curly apostrophes
            if ":" in line:
                label, content = line.split(":", 1)
                pdf.set_font("DejaVu", 'B' if label.lower() in ["name", "race & class"] else '', 14)
                pdf.multi_cell(190, 8, f"{label.strip()}: {content.strip()}")
            else:
                pdf.set_font("DejaVu", '', 12)
                pdf.multi_cell(190, 8, line)
        pdf.ln(10)

    pdf.output(output_file)
    return cover_image_path, output_file

def check_and_create_volume():
    if not os.path.exists(ARCHIVE_FILE):
        return
    with open(ARCHIVE_FILE, "r", encoding="utf-8") as f:
        content = f.read()
    npcs = [npc.strip() for npc in content.split("---") if npc.strip()]
    volume_number = len(npcs) // NPCS_PER_VOLUME

    if len(npcs) % NPCS_PER_VOLUME == 0 and len(npcs) >= NPCS_PER_VOLUME:
        volume_npcs = npcs[-NPCS_PER_VOLUME:]
        cover_path, pdf_path = create_volume_pdf(volume_npcs, volume_number)
        post_text = f"📘 **Tavern NPC Pack - Volume {volume_number}**\nDiscover unique characters for your campaign!\nDownload this volume and unlock inspiration for your next session.\n\nGet more here: {CONVERTKIT_LINK}"
        post_to_facebook(post_text, image_path=cover_path)

# --- Bot Job
def job():
    global last_post_time
    for _ in range(NPCS_PER_VOLUME):
        generate_npc()
    check_and_create_volume()
    last_post_time = datetime.now()

# --- Flask Routes
@app.route('/')
def home():
    now = datetime.now()
    uptime = now - bot_start_time
    last_post = last_post_time.strftime("%Y-%m-%d %H:%M:%S") if last_post_time else "Never"
    return f'''
    <html><head><title>NPC Bot</title></head>
    <body style="background-color:#111;color:white;text-align:center;padding:40px;">
    <h1>Fantasy NPC Forge</h1>
    <form action="/post-now" method="post">
        <button style="padding:15px;font-size:18px;">📦 Post Volume Now</button>
    </form>
    <p><b>Bot Uptime:</b> {str(uptime).split('.')[0]}</p>
    <p><b>Last Posted:</b> {last_post}</p>
    </body></html>
    '''

@app.route('/post-now', methods=['POST'])
def manual_post():
    Thread(target=job).start()
    return redirect("/")

# --- Main
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
