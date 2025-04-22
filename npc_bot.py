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
from fpdf.enums import XPos, YPos
from gdrive_uploader import upload_to_drive

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
PACK_THEME = "Tavern NPC Pack"
LANDING_PAGE_URL = "https://fantasy-npc-forge.kit.com/2aa9c10f01"

# --- Helper Classes
class PDF(FPDF):
    def header(self):
        if getattr(self, 'cover_page', False):
            return
        self.set_font('DejaVu', 'B', 16)
        self.cell(0, 10, "Fantasy NPC Forge", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def footer(self):
        if getattr(self, 'cover_page', False):
            return
        self.set_y(-15)
        self.set_font('DejaVu', '', 8)
        self.cell(0, 10, f"Page {self.page_no()}", align='C')

def load_fonts(pdf):
    pdf.add_font('DejaVu', '', 'DejaVuSans.ttf')
    pdf.add_font('DejaVu', 'B', 'DejaVuSans-Bold.ttf')

# --- Flask Routes
@app.route('/')
def home():
    now = datetime.now()
    uptime = now - bot_start_time
    last_post = last_post_time.strftime("%Y-%m-%d %H:%M:%S") if last_post_time else "Never"
    return f'''
    <html><head><title>MasterBot Dashboard</title></head>
    <body style="background-color:#121212;color:white;text-align:center;padding:40px;">
        <h1>MasterBot Pro: Audience Mode</h1>
        <form action="/post-now" method="post">
            <button style="padding:15px;font-size:18px;">Post New NPC Now</button>
        </form>
        <div style="margin-top:30px;">
            <p><b>Bot Uptime:</b> {str(uptime).split(".")[0]}</p>
            <p><b>Last NPC Posted:</b> {last_post}</p>
        </div>
    </body>
    </html>
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
            {"role": "system", "content": "You are a creative D&D NPC generator."},
            {"role": "user", "content": "Generate a creative D&D NPC with:\nName\nRace & Class\nPersonality\nQuirks\nBackstory\nIdeal\nBond\nFlaw"}
        ],
        temperature=0.9
    )
    npc = response.choices[0].message.content.strip()
    if len(npc.splitlines()) < 4:
        print("⚠️ Skipped bad NPC generation.")
        return None
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

    npcs = [npc.strip() for npc in content.split("---") if npc.strip() and len(npc.splitlines()) > 4]

    volume_number = len(npcs) // NPCS_PER_VOLUME

    if len(npcs) % NPCS_PER_VOLUME == 0 and len(npcs) > 0:
        volume_npcs = npcs[-NPCS_PER_VOLUME:]
        create_volume_pdf(volume_npcs, volume_number)

def create_volume_pdf(volume_npcs, volume_number):
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    # Generate DALL-E cover
    prompt = "Epic fantasy tavern interior, warm lighting, grand atmosphere, fantasy art, cinematic, ultra-detailed"
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

    # Create PDF
    output_file = os.path.join(VOLUME_FOLDER, f"Fantasy_NPC_Forge_Volume{volume_number}.pdf")
    pdf = PDF()
    load_fonts(pdf)
    pdf.set_auto_page_break(auto=True, margin=15)

    # Cover Page
    pdf.add_page()
    pdf.cover_page = True
    pdf.image(cover_image_path, x=10, y=20, w=190)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("DejaVu", 'B', 36)
    pdf.set_y(150)
    pdf.cell(0, 20, "Fantasy NPC Forge", align='C')
    pdf.set_font("DejaVu", 'B', 24)
    pdf.set_y(185)
    pdf.cell(0, 15, PACK_THEME, align='C')
    pdf.set_font("DejaVu", '', 18)
    pdf.set_y(215)
    pdf.cell(0, 10, f"Volume {volume_number}", align='C')
    pdf.set_text_color(0, 0, 0)

    # Lore Page
    pdf.cover_page = False
    pdf.add_page()
    pdf.set_font("DejaVu", 'B', 24)
    pdf.cell(0, 20, "Lore of the Tavern", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
    pdf.set_font("DejaVu", '', 14)
    pdf.multi_cell(0, 10, "In the heart of a shifting realm stands the Eternal Hearth, a tavern untouched by time, where adventurers from distant lands gather to exchange secrets, treasures, and fates. Every corner holds a whisper of old magic. Here, new legends are born nightly.")

    # NPC Pages
    for npc in volume_npcs:
        pdf.add_page()
        pdf.set_font("DejaVu", 'B', 20)
        pdf.ln(20)
        lines = npc.splitlines()
        for idx, line in enumerate(lines):
            if ":" in line:
                label, content = line.split(":", 1)
                label = label.strip()
                content = content.strip()
                if label.lower() in ["name", "race & class"]:
                    pdf.set_font("DejaVu", 'B', 18)
                    pdf.set_x(18)
                    pdf.cell(0, 10, f"{label}: {content}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                else:
                    pdf.set_font("DejaVu", '', 14)
                    pdf.set_x(18)
                    pdf.multi_cell(174, 8, f"{label}: {content}")
            else:
                pdf.set_font("DejaVu", '', 12)
                pdf.set_x(18)
                pdf.multi_cell(174, 8, line)
        pdf.ln(10)

    # Credits Page
    pdf.add_page()
    pdf.set_font("DejaVu", 'B', 24)
    pdf.cell(0, 20, "Credits", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
    pdf.set_font("DejaVu", '', 14)
    pdf.multi_cell(0, 10, "Created by Matthew Lanning.\n\nFor more NPC packs, visit:\n" + LANDING_PAGE_URL)

    pdf.output(output_file)
    print(f"Volume {volume_number} PDF created!")

    shareable_link = upload_to_drive(output_file)
    post_to_facebook(shareable_link, volume_number)

def post_to_facebook(shareable_link, volume_number):
    page_id = os.getenv("FB_PAGE_ID")
    token = os.getenv("FB_PAGE_ACCESS_TOKEN")
    if not page_id or not token:
        print("⚠️ Facebook credentials missing. Skipping post.")
        return

    message = f"✨ New Fantasy NPC Pack is here!\nGrab your free Tavern NPC Volume {volume_number} here:\n{LANDING_PAGE_URL}"
    url = f"https://graph.facebook.com/{page_id}/feed"
    data = {
        "message": message,
        "access_token": token
    }
    response = requests.post(url, data=data)
    if response.status_code == 200:
        print("✅ Posted to Facebook!")
    else:
        print("❌ Facebook post failed:", response.text)

# --- Bot Job
def job():
    global last_post_time
    print("Running scheduled job...")
    npc = generate_npc()
    if npc:
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
