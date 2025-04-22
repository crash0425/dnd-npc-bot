import os
import time
import random
import requests
import schedule
import openai
from flask import Flask, request, redirect
from threading import Thread
from dotenv import load_dotenv
from datetime import datetime
from fpdf import FPDF
from gdrive_uploader import upload_to_drive
from facebook_uploader import post_to_facebook

# --- Load environment variables
load_dotenv()

# --- Initialize Flask app
app = Flask(__name__)

# --- Bot State
bot_start_time = datetime.now()
last_post_time = None
VERIFY_TOKEN = os.getenv("FB_VERIFY_TOKEN")

# --- Settings
ARCHIVE_FILE = "npc_archive.txt"
VOLUME_FOLDER = "npc_volumes"
NPCS_PER_VOLUME = 10
VOLUME_THEME = "Tavern Tales"  # Set your current volume theme

# --- Helper Classes
class PDF(FPDF):
    def header(self):
        if getattr(self, 'cover_page', False):
            return
        self.set_font('Times', 'B', 16)
        self.cell(0, 10, "Fantasy NPC Forge", new_x="LMARGIN", new_y="NEXT", align='C')

    def footer(self):
        if getattr(self, 'cover_page', False):
            return
        self.set_y(-15)
        self.set_font('Times', 'I', 8)
        self.cell(0, 10, f"Page {self.page_no()}", align='C')

# --- Flask Routes
@app.route('/')
def home():
    now = datetime.now()
    uptime = now - bot_start_time
    last_post = last_post_time.strftime("%Y-%m-%d %H:%M:%S") if last_post_time else "Never"
    return f'''
    <html><head><title>NPC Bot Dashboard</title></head><body style="background-color:#121212;color:white;text-align:center;padding:40px;">
        <h1>Fantasy NPC Forge</h1>
        <form action="/post-now" method="post">
            <button style="padding:15px;font-size:18px;">Post New NPC Now</button>
        </form>
        <div style="margin-top:30px;">
            <p><b>Bot Uptime:</b> {str(uptime).split(".")[0]}</p>
            <p><b>Last NPC Posted:</b> {last_post}</p>
        </div>
    </body></html>
    '''

@app.route('/post-now', methods=['POST'])
def manual_post():
    Thread(target=job).start()
    return redirect("/")

# --- Bot Functions
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
    with open(ARCHIVE_FILE, "a", encoding="utf-8") as f:
        f.write(npc_text + "\n---\n")

def check_and_create_volume():
    if not os.path.exists(VOLUME_FOLDER):
        os.makedirs(VOLUME_FOLDER)

    with open(ARCHIVE_FILE, "r", encoding="utf-8") as f:
        content = f.read()
    npcs = [npc.strip() for npc in content.split("---") if npc.strip()]

    volume_number = len(npcs) // NPCS_PER_VOLUME

    if len(npcs) % NPCS_PER_VOLUME == 0 and len(npcs) > 0:
        volume_npcs = npcs[-NPCS_PER_VOLUME:]
        cover_path, pdf_path = create_volume_pdf(volume_npcs, volume_number)

        # Upload and Post
        share_link = upload_to_drive(pdf_path)
        post_to_facebook(cover_path, f"Volume {volume_number} is live!\nTheme: {VOLUME_THEME}\nDownload here: {share_link}")

def create_volume_pdf(volume_npcs, volume_number):
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    # --- Generate DALL-E Cover Art
    print("Generating DALL-E Cover Art...")
    prompt = f"Epic fantasy tavern scene for a D&D NPC pack, cinematic, grand, cozy, detailed travelers - Theme: {VOLUME_THEME}"

    image_response = client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        n=1,
        size="1024x1024"
    )
    image_url = image_response.data[0].url

    image_data = requests.get(image_url).content
    cover_image_path = os.path.join(VOLUME_FOLDER, f"cover_volume{volume_number}.png")
    with open(cover_image_path, "wb") as f:
        f.write(image_data)

    output_file = os.path.join(VOLUME_FOLDER, f"Fantasy_NPC_Forge_Volume{volume_number}.pdf")
    pdf = PDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    # --- Cover
    pdf.cover_page = True
    pdf.add_page()
    pdf.image(cover_image_path, x=10, y=20, w=190)
    pdf.set_xy(0, 250)
    pdf.set_font("Times", 'B', 24)
    pdf.cell(0, 10, f"Volume {volume_number} - {VOLUME_THEME}", align='C')

    # --- NPCs
    pdf.cover_page = False
    for npc in volume_npcs:
        pdf.add_page()
        pdf.set_font("Times", '', 14)
        lines = npc.splitlines()
        for line in lines:
            pdf.multi_cell(190, 8, line)
        pdf.ln(10)

    pdf.output(output_file)
    print(f"Volume {volume_number} PDF created!")

    return cover_image_path, output_file

# --- Bot Job
def job():
    global last_post_time
    print("Running job...")
    npc = generate_npc()
    check_and_create_volume()
    last_post_time = datetime.now()

# --- Scheduler
def run_scheduler():
    schedule.every().monday.at("10:00").do(job)
    schedule.every().thursday.at("10:00").do(job)
    while True:
        schedule.run_pending()
        time.sleep(30)

# --- Keep Alive
def keep_alive():
    t = Thread(target=lambda: app.run(host='0.0.0.0', port=8080))
    t.start()

# --- Main
if __name__ == "__main__":
    keep_alive()
    run_scheduler()
