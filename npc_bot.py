# npc_bot.py

import os
import time
import random
import schedule
import requests
import datetime
from flask import Flask, request, redirect
from threading import Thread
import openai
import gspread
from dotenv import load_dotenv

# Load .env
load_dotenv()

# Setup Google Sheets client
gc = gspread.service_account_from_dict({
    "type": "service_account",
    "client_email": os.getenv("GOOGLE_SERVICE_ACCOUNT_EMAIL"),
    "private_key": os.getenv("GOOGLE_PRIVATE_KEY").replace('\\n', '\n'),
    "token_uri": "https://oauth2.googleapis.com/token"
})

# Connect to Google Sheet
SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
worksheet = gc.open_by_key(SHEET_ID).sheet1

# Setup Flask Web Server
app = Flask(__name__)

@app.route('/')
def home():
    return '''
    <h1>MasterBot Pro Control Panel 🚀</h1>
    <form action="/post-now" method="post">
        <button type="submit">📬 Post Now</button>
    </form>
    '''

@app.route('/post-now', methods=['POST'])
def post_now():
    Thread(target=job).start()
    return redirect('/')

def keep_alive():
    t = Thread(target=lambda: app.run(host='0.0.0.0', port=8080))
    t.start()

# Fantasy Trivia
TRIVIA_AND_LORE = [
    "💡 Did you know? Most taverns are built over ley lines!",
    "📜 Lore Drop: Elowen silenced a tavern brawl with one lute chord.",
    "🧙‍♂️ Trivia: 'Dungeon Master' was coined in 1975!",
    "🍺 Fun Fact: Gnomes brew ale with magical mushrooms.",
    "⚔️ Battle Tale: Half-Orc hero Ragor won duels by reciting poetry."
]

# --- NPC + Engagement Generators ---

def generate_npc():
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a creative D&D NPC generator."},
            {"role": "user", "content": "Create a D&D NPC:\nName: ...\nRace & Class: ...\nPersonality: ...\nQuirks: ...\nBackstory: ...\nIdeal: ...\nBond: ...\nFlaw: ..."}
        ],
        temperature=0.85
    )
    return response.choices[0].message.content.strip()

def generate_engagement_question():
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a creative fantasy community manager."},
            {"role": "user", "content": "Write a fun question to spark comments among D&D players. Make it about taverns, adventurers, or fantasy NPCs."}
        ],
        temperature=0.9
    )
    return response.choices[0].message.content.strip()

# --- Facebook Posting Functions ---

def post_to_facebook(npc_text, image_path=None):
    print("🕵️ FB Debug: FB_PAGE_ID =", os.getenv("FB_PAGE_ID"))
    print("🕵️ FB Debug: FB_PAGE_ACCESS_TOKEN present =", bool(os.getenv("FB_PAGE_ACCESS_TOKEN")))
    page_id = os.getenv("FB_PAGE_ID")
    token = os.getenv("FB_PAGE_ACCESS_TOKEN")

    if not page_id or not token:
        print("⚠️ Missing Facebook credentials. Skipping post.")
        return

    formatted_post = f"{npc_text}\n\n#DND #FantasyNPC #RPG #DungeonsAndDragons #FantasyWorld #Roleplay #CharacterCreation"

    try:
        if image_path:
            print("📸 Posting image to Facebook...")
            url = f"https://graph.facebook.com/{page_id}/photos"
            files = {"source": open(image_path, "rb")}
            data = {"caption": formatted_post.strip(), "access_token": token}
            response = requests.post(url, files=files, data=data)
        else:
            print("📝 Posting text post to Facebook...")
            url = f"https://graph.facebook.com/{page_id}/feed"
            data = {"message": formatted_post.strip(), "access_token": token}
            response = requests.post(url, data=data)

        print("🔎 Facebook API Response:", response.status_code, "-", response.text)
        if response.status_code == 200:
            print("✅ NPC posted to Facebook successfully!")
            post_id = response.json().get("post_id") or response.json().get("id")
            if post_id:
                comment_message = random.choice(TRIVIA_AND_LORE) + "\n\n" + generate_engagement_question()
                post_comment(post_id, comment_message)
            return post_id
        else:
            print(f"❌ Facebook error posting: {response.status_code} - {response.text}")

    except Exception as e:
        print(f"🚨 Error posting to Facebook: {e}")

def post_comment(post_id, comment_text):
    page_id = os.getenv("FB_PAGE_ID")
    token = os.getenv("FB_PAGE_ACCESS_TOKEN")

    try:
        url = f"https://graph.facebook.com/{post_id}/comments"
        data = {"message": comment_text, "access_token": token}
        response = requests.post(url, data=data)
        print("💬 Comment API Response:", response.status_code, "-", response.text)
        if response.status_code == 200:
            print("✅ Comment posted successfully!")
        else:
            print(f"❌ Failed to post comment: {response.status_code}")
    except Exception as e:
        print(f"🚨 Error posting comment: {e}")

# --- Google Sheets Logging ---

def log_to_sheet(npc_text, post_id):
    try:
        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        worksheet.append_row([now, npc_text, post_id])
        print("🧾 NPC logged to Google Sheet!")
    except Exception as e:
        print(f"🚨 Error logging to sheet: {e}")

# --- Main Bot Job ---

def job():
    print("🕒 Running bot job...")
    npc = generate_npc()
    post_id = post_to_facebook(npc)
    if post_id:
        log_to_sheet(npc, post_id)

# --- Smart Scheduler (Posting When Engagement Is High) ---

def run_scheduler():
    print("📅 Bot scheduler is active...")
    schedule.every().day.at("10:00").do(job)
    schedule.every().day.at("17:00").do(job)
    schedule.every().day.at("20:00").do(job)

    while True:
        schedule.run_pending()
        time.sleep(30)

# --- Start Everything ---

if __name__ == "__main__":
    keep_alive()
    run_scheduler()

