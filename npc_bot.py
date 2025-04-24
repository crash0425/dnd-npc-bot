import os
import requests
import openai
import schedule
import time
from flask import Flask, request, redirect
from threading import Thread
from datetime import datetime
from fpdf import FPDF

# --- Config
ARCHIVE_FILE = "npc_archive.txt"
VOLUME_FOLDER = "npc_volumes"
NPCS_PER_VOLUME = 10
FONT_DIR = os.path.dirname(__file__)
CONVERTKIT_LINK = "https://fantasy-npc-forge.kit.com/2aa9c10f01"

# --- Flask Setup
app = Flask(__name__)
start_time = datetime.now()

class PDF(FPDF):
    def header(self):
        self.set_font('DejaVu', 'B', 16)
        self.cell(0, 10, "Fantasy NPC Forge", new_x="LMARGIN", new_y="NEXT")

    def footer(self):
        self.set_y(-15)
        self.set_font('DejaVu', '', 8)
        self.cell(0, 10, f"Page {self.page_no()}", align='C')

# --- Routes
@app.route('/')
def home():
    uptime = datetime.now() - start_time
    return f"""
    <html><body style='font-family:sans-serif;text-align:center;padding:30px;'>
        <h1>Fantasy NPC Forge Bot</h1>
        <p>Uptime: {str(uptime).split('.')[0]}</p>
        <form action='/post-now' method='post'>
            <button style='padding:10px 20px;font-size:16px;'>Post Volume Now</button>
        </form>
    </body></html>
    """

@app.route('/post-now', methods=['POST'])
def post_now():
    Thread(target=job).start()
    return redirect('/')

# --- NPC Generation
openai.api_key = os.getenv("OPENAI_API_KEY")
def generate_npc():
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a D&D NPC generator."},
            {"role": "user", "content": "Generate a creative D&D NPC with:\nName\nRace & Class\nPersonality\nQuirks\nBackstory\nIdeal\nBond\nFlaw"}
        ],
        temperature=0.9
    )
    return response.choices[0].message.content.strip()

def save_npc(npc_text):
    with open(ARCHIVE_FILE, "a", encoding="utf-8") as f:
        f.write(npc_text + "\n---\n")

# --- Volume Creation
def create_volume_pdf(volume_npcs, volume_number):
    prompt = "Epic fantasy tavern interior, warm lighting, cozy but grand, filled with mysterious travelers, fantasy art style"
    image = openai.Image.create(prompt=prompt, n=1, size="1024x1024")
    image_url = image['data'][0]['url']
    image_data = requests.get(image_url).content

    os.makedirs(VOLUME_FOLDER, exist_ok=True)
    cover_path = os.path.join(VOLUME_FOLDER, f"cover_volume{volume_number}.png")
    with open(cover_path, "wb") as f:
        f.write(image_data)

    pdf_path = os.path.join(VOLUME_FOLDER, f"Fantasy_NPC_Forge_Volume{volume_number}.pdf")
    pdf = PDF()
    pdf.add_font('DejaVu', '', os.path.join(FONT_DIR, 'DejaVuSans.ttf'), uni=True)
    pdf.add_font('DejaVu', 'B', os.path.join(FONT_DIR, 'DejaVuSans-Bold.ttf'), uni=True)
    pdf.set_auto_page_break(auto=True, margin=15)

    pdf.add_page()
    pdf.image(cover_path, x=10, y=20, w=190)
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
            line = line.replace("’", "'")
            if ":" in line:
                label, content = line.split(":", 1)
                font_weight = 'B' if label.lower() in ["name", "race & class"] else ''
                pdf.set_font("DejaVu", font_weight, 14)
                pdf.multi_cell(190, 8, f"{label.strip()}: {content.strip()}")
            else:
                pdf.set_font("DejaVu", '', 12)
                pdf.multi_cell(190, 8, line)
        pdf.ln(10)

    pdf.output(pdf_path)
    return cover_path, pdf_path

# --- Main Job
def job():
    npcs = []
    for _ in range(NPCS_PER_VOLUME):
        npc = generate_npc()
        save_npc(npc)
        npcs.append(npc)

    volume_number = len(os.listdir(VOLUME_FOLDER)) + 1
    cover_path, pdf_path = create_volume_pdf(npcs, volume_number)

    print(f"Volume {volume_number} created: {pdf_path}")
    print(f"Promote here: {CONVERTKIT_LINK}")

# --- Scheduler
def run_scheduler():
    schedule.every().monday.at("10:00").do(job)
    schedule.every().thursday.at("10:00").do(job)
    while True:
        schedule.run_pending()
        time.sleep(30)

# --- Run Flask + Scheduler
if __name__ == "__main__":
    Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()
    run_scheduler()
