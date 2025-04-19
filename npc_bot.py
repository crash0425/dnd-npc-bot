import os
import time
import schedule
import requests
from flask import Flask, request, redirect
from threading import Thread
import openai
import random
import datetime
import gspread
from dotenv import load_dotenv
load_dotenv()

# --- Web Server ---
app = Flask(__name__)

@app.route('/')
def home():
    return '''
        <h1>MasterBot Pro</h1>
        <form action="/post-now" method="post">
            <button type="submit">Post Now 🚀</button>
        </form>
    '''

@app.route('/post-now', methods=['POST'])
def post_now():
    Thread(target=job).start()
    return redirect('/')

def run_web():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_web)
    t.start()

# --- Facebook Posting ---
def post_to_facebook(npc_text, image_path):
    page_id = os.getenv("FB_PAGE_ID")
    token = os.getenv("FB_PAGE_ACCESS_TOKEN")

    if not page_id or not token:
        print("⚠️ Facebook credentials missing. Skipping post.")
        return

    formatted_post = (
        f"{npc_text}\n\n"
        "#DnD #DungeonsAndDragons #TabletopRPG #FantasyArt #RPGCharacter "
        "#Roleplay #TavernLife #CharacterArt #TTRPG #FantasyWorld #Adventurer"
    )

    try:
        print("📸 Posting image to Facebook...")
        url = f"https://graph.facebook.com/{page_id}/photos"
        files = {"source": open(image_path, "rb")}
        data = {"caption": formatted_post.strip(), "access_token": token}
        response = requests.post(url, files=files, data=data)

        if response.status_code == 200:
            print(f"✅ NPC posted to Facebook successfully!")
            post_id = response.json().get('post_id')
            if post_id:
                log_to_sheet(post_id, npc_text)
        else:
            print(f"❌ Facebook post failed: {response.status_code} - {response.text}")

    except Exception as e:
        print(f"🚨 Error posting to Facebook: {e}")

# --- Generate NPC ---
def generate_npc():
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a creative Dungeons & Dragons NPC generator."},
            {"role": "user", "content": "Generate a Dungeons & Dragons NPC with this format:\nName: ...\nRace & Class: ...\nPersonality: ...\nQuirks: ...\nBackstory: ...\nIdeal: ...\nBond: ...\nFlaw: ..."}
        ],
        temperature=0.9
    )
    return response.choices[0].message.content.strip()

def extract_race_and_class(npc_text):
    lines = npc_text.split('\n')
    for line in lines:
        if line.lower().startswith("race & class"):
            parts = line.split(":", 1)
            if len(parts) > 1:
                race_class = parts[1].strip()
                if " " in race_class:
                    return race_class.split(" ", 1)
    return "Human", "Fighter"

# --- Generate Image ---
def generate_image(prompt, filename):
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        n=1,
        size="1024x1024"
    )
    image_url = response.data[0].url
    image_data = requests.get(image_url).content
    with open(filename, "wb") as f:
        f.write(image_data)
    return filename

# --- Log to Google Sheets ---
def log_to_sheet(post_id, npc_text):
    try:
        gc = gspread.service_account(filename=os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE"))
        sheet = gc.open_by_key(os.getenv("GOOGLE_SHEET_ID"))
        worksheet = sheet.sheet1

        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        worksheet.append_row([now, post_id, npc_text])

        print("📝 NPC post logged to Google Sheets!")

    except Exception as e:
        print(f"🚨 Error logging to Google Sheets: {e}")

# --- Scheduled Job ---
def job():
    print("🕒 Running bot job...")
    npc = generate_npc()
    race, char_class = extract_race_and_class(npc)
    prompt = f"A fantasy portrait of a {race} {char_class} inside a medieval tavern, colorful, detailed, semi-realistic digital painting."
    image_path = generate_image(prompt, "npc_image.png")
    post_to_facebook(npc, image_path)

# --- Scheduler ---
def run_scheduler():
    print("📅 Bot scheduler is active...")
    # Post at best engagement times (can be adjusted later)
    schedule.every().monday.at("10:00").do(job)
    schedule.every().wednesday.at("10:00").do(job)
    schedule.every().friday.at("10:00").do(job)

    while True:
        schedule.run_pending()
        time.sleep(30)

# --- Main ---
if __name__ == "__main__":
    keep_alive()
    run_scheduler()
