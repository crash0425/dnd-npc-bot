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

# --- Load environment variables
load_dotenv()

# --- Initialize Flask app
app = Flask(__name__)

# --- Bot State
bot_start_time = datetime.now()
last_post_time = None
next_scheduled_time = None
next_scheduled_day = None
VERIFY_TOKEN = os.getenv("FB_VERIFY_TOKEN")

# --- Archive and Volume Settings
ARCHIVE_FILE = "npc_archive.txt"
VOLUME_FOLDER = "npc_volumes"
NPCS_PER_VOLUME = 2

# --- Lore & Trivia (remove emoji codes!)
TRIVIA_AND_LORE = [
    "Lore Drop: In ancient taverns, tales were traded for ale!",
    "Trivia: Elves believe every tavern has a spirit guardian.",
    "Fun Fact: Gnomes invented sparkling mead during a lost festival.",
    "Battle Tale: The bravest warriors once dueled using only spoons!",
    "Bard’s Wisdom: Every story has truth hidden between the lies.",
    "Did you know? The original D&D tavern was based on a real pub.",
    "Arcane Lore: Wizards often plant hidden portals inside taverns.",
    "Hero Fact: Legendary shields are sometimes auctioned in secret taverns.",
]

# --- Facebook Reactions
REACTIONS = ['LIKE', 'LOVE', 'WOW', 'HAHA']

# --- Helper Classes
class PDF(FPDF):
    def header(self):
        if not hasattr(self, 'cover_page') or not self.cover_page:
            self.set_font('DejaVu', 'B', 16)
            self.cell(0, 10, "Fantasy NPC Forge", new_x="LMARGIN", new_y="NEXT")

    def footer(self):
        if not hasattr(self, 'cover_page') or not self.cover_page:
            self.set_y(-15)
            self.set_font('DejaVu', 'I', 8)
            self.cell(0, 10, f"Page {self.page_no()}", align='C')


# --- Flask Routes
@app.route('/')
def home():
    now = datetime.now()
    uptime = now - bot_start_time
    last_post = last_post_time.strftime("%Y-%m-%d %H:%M:%S") if last_post_time else "Never"

    return f'''
    <html>
    <head><title>MasterBot Dashboard</title></head>
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
        create_volume_pdf(volume_npcs, volume_number)
def create_volume_pdf(volume_npcs, volume_number):
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    # --- Generate DALL-E Cover Art
    print("Generating DALL-E Cover Art...")
    prompt = "Epic fantasy tavern interior, warm lighting, cozy but grand, filled with mysterious travelers, detailed environment, fantasy art style, cinematic, ultra-detailed, vibrant colors"

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

    # --- Build PDF
    output_file = os.path.join(VOLUME_FOLDER, f"Fantasy_NPC_Forge_Volume{volume_number}.pdf")
    pdf = PDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    # --- Cover Page
    pdf.add_page()
    pdf.image(cover_image_path, x=10, y=20, w=190)

    # --- Title Page
    pdf.add_page()
    pdf.set_font("Times", 'B', 32)
    pdf.cell(0, 80, "", new_x="LMARGIN", new_y="NEXT")  # Spacer
    pdf.cell(0, 20, "Fantasy NPC Forge", new_x="LMARGIN", new_y="NEXT", align='C')
    pdf.set_font("Times", '', 20)
    pdf.cell(0, 20, f"Tavern NPC Pack - Volume {volume_number}", new_x="LMARGIN", new_y="NEXT", align='C')

    # --- Add NPCs
    for npc in volume_npcs:
        pdf.add_page()
        pdf.set_font("Times", 'B', 20)
        lines = npc.splitlines()

        for idx, line in enumerate(lines):
            if ":" in line:
                label, content = line.split(":", 1)
                label = label.strip()
                content = content.strip()

                # Header-style for Name and Race & Class
                if label.lower() in ["name", "race & class"]:
                    pdf.set_font("Times", 'B', 18)
                    pdf.cell(0, 10, f"{label}: {content}", new_x="LMARGIN", new_y="NEXT")
                else:
                    pdf.set_font("Times", '', 14)
                    pdf.multi_cell(190, 8, f"{label}: {content}")
            else:
                pdf.set_font("Times", '', 12)
                pdf.multi_cell(190, 8, line)

        pdf.ln(10)

    pdf.output(output_file)

    print(f"Volume {volume_number} PDF created!")
    shareable_link = upload_to_drive(output_file)
    print(f"Volume {volume_number} uploaded to Google Drive: {shareable_link}")



# --- Bot Job
def job():
    global last_post_time
    print("Running scheduled job...")

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
