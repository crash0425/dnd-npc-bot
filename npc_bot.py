# npc_bot.py

import os
import time
import random
import schedule
import requests
import openai
from dotenv import load_dotenv
from flask import Flask, request, redirect
from threading import Thread

# --- Load Environment Variables ---
load_dotenv()

# --- Flask App ---
app = Flask(__name__)

@app.route('/')
def home():
    return "<h1>🤖 NPC Bot is Running!</h1><form action='/post-now' method='post'><button type='submit'>Post Now</button></form>"

@app.route('/post-now', methods=['POST'])
def post_now():
    Thread(target=job).start()
    return redirect("/")

def run_web():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_web)
    t.start()

# --- Fantasy Trivia Pool (for future comments if you want) ---
TRIVIA_AND_LORE = [
    "💡 Did you know? Most taverns in Faerûn are built over ley lines!",
    "📜 Lore Drop: The bard Elowen once silenced a brawl with one chord.",
    "🧝‍♀️ Elves consider tavern gossip an art form worthy of poetry.",
]

# --- Helper: Generate an NPC ---
def generate_npc():
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a creative Dungeons & Dragons NPC generator."},
            {"role": "user", "content": "Generate a detailed D&D NPC. Format:\nName: ...\nRace & Class: ...\nPersonality: ...\nQuirks: ...\nBackstory: ...\nIdeal: ...\nBond: ...\nFlaw: ..."}
        ],
        temperature=0.9
    )
    return response.choices[0].message.content.strip()

# --- Helper: Extract Race and Class ---
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

# --- Helper: Generate Image using DALL·E ---
def generate_image(prompt, filename="npc_image.png"):
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

# --- Post to Facebook ---
def post_to_facebook(npc, image_path=None):
    page_id = os.getenv("FB_PAGE_ID")
    token = os.getenv("FB_PAGE_ACCESS_TOKEN")

    print("🔍 Debug: FB_PAGE_ID =", page_id)
    print("🔍 Debug: FB_PAGE_ACCESS_TOKEN present =", bool(token))

    if not page_id or not token:
        print("⚠️ Facebook credentials missing. Skipping post.")
        return

    formatted_post = (
        f"{npc}\n\n"
        "#DnD #DungeonsAndDragons #TavernNPC #FantasyArt #RPGCharacter #TTRPG #FantasyWorld #Roleplay"
    )

    try:
        if image_path:
            url = f"https://graph.facebook.com/{page_id}/photos"
            files = {"source": open(image_path, "rb")}
            data = {"caption": formatted_post, "access_token": token}
            print("📸 Posting image to:", url)
            response = requests.post(url, files=files, data=data)
        else:
            url = f"https://graph.facebook.com/{page_id}/feed"
            data = {"message": formatted_post, "access_token": token}
            print("📝 Posting text to:", url)
            response = requests.post(url, data=data)

        print(f"🔎 Facebook API response: {response.status_code} - {response.text}")

        if response.status_code == 200:
            print("✅ NPC posted to Facebook successfully!")
        else:
            print(f"❌ Facebook post failed: {response.status_code} - {response.text}")

    except Exception as e:
        print(f"🚨 An error occurred while posting to Facebook: {e}")

# --- Bot Job ---
def job():
    print("🕒 Running bot job...")
    npc = generate_npc()
    race, char_class = extract_race_and_class(npc)
    prompt = f"A fantasy portrait of a {race} {char_class} sitting in a medieval tavern, painted in a semi-realistic digital art style. Include visible character equipment and tavern background details."
    image_path = generate_image(prompt)
    post_to_facebook(npc, image_path)

# --- Scheduler ---
def run_scheduler():
    print("📅 Bot scheduler is running...")
    schedule.every().monday.at("10:00").do(job)
    schedule.every().thursday.at("10:00").do(job)

    while True:
        schedule.run_pending()
        time.sleep(30)

# --- Main ---
if __name__ == "__main__":
    keep_alive()
    run_scheduler()
