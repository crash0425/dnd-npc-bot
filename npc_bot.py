# npc_bot.py

import os
import time
import random
import schedule
import requests
from dotenv import load_dotenv
from flask import Flask, render_template_string, request, redirect, url_for
from threading import Thread
import openai

# Load .env secrets
load_dotenv()

# Setup Flask web server
app = Flask(__name__)

@app.route('/')
def home():
    return render_template_string('''
    <html>
    <head><title>NPC Bot</title></head>
    <body style="text-align:center; padding-top:50px;">
        <h1>🤖 NPC Bot Control Panel</h1>
        <form action="/post-now" method="post">
            <button style="font-size:24px; padding:10px 30px;" type="submit">Post NPC Now 🚀</button>
        </form>
    </body>
    </html>
    ''')

@app.route('/post-now', methods=['POST'])
def post_now():
    print("🖱️ POST NOW button clicked!")
    job()  # <-- DIRECTLY call job()
    return redirect('/')
)

def run_web():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_web)
    t.start()

# Trivia & Lore pool
TRIVIA_AND_LORE = [
    "💡 Did you know? Most taverns in Faerûn are built over ley lines, enhancing magical effects!",
    "📜 Lore Drop: The infamous bard Elowen once silenced a tavern brawl with a single lute chord.",
    "🧙‍♂️ Trivia: The term 'Dungeon Master' was first coined in 1975.",
    "🧝‍♀️ Lore Fact: Elves consider tavern gossip an art form worthy of poetry.",
    "🍺 Gnome Fun Fact: Waterdeep gnomes ferment ale with magical mushrooms!",
]

# Helper: Refresh Facebook token (stub)
def refresh_facebook_token():
    pass

# Helper: Generate an NPC
def generate_npc():
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a creative Dungeons & Dragons NPC generator."},
            {"role": "user", "content": "Generate a creative Dungeons & Dragons NPC with the format:\nName: ...\nRace & Class: ...\nPersonality: ...\nQuirks: ...\nBackstory: ...\nIdeal: ...\nBond: ...\nFlaw: ..."}
        ],
        temperature=0.9
    )
    return response.choices[0].message.content.strip()

# Helper: Extract race and class
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

# Helper: Generate DALL·E image
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

# Helper: Post to Facebook
def post_to_facebook(npc, image_path=None):
    refresh_facebook_token()

    print("🔍 Debug: FB_PAGE_ID:", os.getenv("FB_PAGE_ID"))
    print("🔍 Debug: FB_PAGE_ACCESS_TOKEN present:", bool(os.getenv("FB_PAGE_ACCESS_TOKEN")))

    page_id = os.getenv("FB_PAGE_ID")
    token = os.getenv("FB_PAGE_ACCESS_TOKEN")

    if not page_id or not token:
        print("⚠️ Facebook credentials missing. Skipping FB post.")
        return

    formatted_post = (
        f"{npc}\n\n"
        "#DnD #DungeonsAndDragons #TabletopRPG #FantasyArt #RPGCharacter "
        "#Roleplay #TavernLife #CharacterArt #TTRPG #FantasyWorld #Adventurer"
    )

    try:
        if image_path:
            url = f"https://graph.facebook.com/{page_id}/photos"
            files = {"source": open(image_path, "rb")}
            data = {"caption": formatted_post.strip(), "access_token": token}
            response = requests.post(url, files=files, data=data)
        else:
            url = f"https://graph.facebook.com/{page_id}/feed"
            data = {"message": formatted_post.strip(), "access_token": token}
            response = requests.post(url, data=data)

        if response.status_code == 200:
            print("✅ NPC posted to Facebook!")
        else:
            print(f"❌ Facebook error: {response.status_code} - {response.text}")
            print(f"📜 Full Facebook Response JSON: {response.json()}")

    except Exception as e:
        print(f"🚨 An unexpected error occurred while posting to Facebook: {e}")







# Main Bot Job
def job():
    print("🕒 Running scheduled bot job...")
    npc = generate_npc()
    race, char_class = extract_race_and_class(npc)
    prompt = (
        f"A fantasy portrait of a {race} {char_class} sitting in a lively medieval tavern. "
        "Painted in a semi-realistic digital art style. Include visible gear related to their class."
    )
    image_path = generate_image(prompt, "npc_image.png")
    post_to_facebook(npc, image_path)

# Scheduler loop
def run_scheduler():
    print("📅 Bot scheduler is running...")
    schedule.every().monday.at("10:00").do(job)
    schedule.every().thursday.at("10:00").do(job)

    while True:
        schedule.run_pending()
        time.sleep(30)

# Start everything
if __name__ == "__main__":
    keep_alive()
    run_scheduler()
