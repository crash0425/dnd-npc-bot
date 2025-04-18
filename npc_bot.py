import os
import time
import schedule
import random
import datetime
import requests
from flask import Flask, request
from threading import Thread
from dotenv import load_dotenv
import openai

# --- Load Environment Variables ---
load_dotenv()

# --- Web Server to Keep Replit/Render Alive ---
from flask import Flask, request, redirect, url_for

app = Flask('')

@app.route('/')
def home():
    return '''
        <h1>🛡️ D&D NPC Bot is Alive!</h1>
        <form action="/post-now" method="POST">
            <button type="submit" style="font-size:20px;padding:10px 20px;">🚀 Post New NPC Now</button>
        </form>
    '''

@app.route('/post-now', methods=['POST'])
def post_now():
    # Run your job
    from threading import Thread
    Thread(target=job).start()
    return '''
        <h1>✅ Your NPC has been posted!</h1>
        <a href="/">🔙 Back to Home</a>
    '''

def run_web():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_web)
    t.start()

# --- Fantasy Trivia & Lore Pool ---
TRIVIA_AND_LORE = [
    "💡 Did you know? Most taverns in Faerûn are built over ley lines, enhancing magical effects!",
    "📜 Lore Drop: The infamous bard Elowen once silenced a tavern brawl with a single lute chord.",
    "🧙‍♂️ Trivia: The term 'Dungeon Master' was first coined in 1975 with the original D&D release.",
    "🍺 Fun Fact: Gnomes in Waterdeep ferment ale with magical mushrooms for enhanced dreams.",
    "🔥 Hot Lore: A dragon named Emberbelch once opened a tavern just to meet adventurers for gossip.",
]

# --- Helper Functions ---
def refresh_facebook_token():
    # Placeholder for future Facebook token refreshing
    pass

def generate_npc():
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a creative Dungeons & Dragons NPC generator."},
            {"role": "user", "content": (
                "Generate a highly detailed, colorful D&D NPC using this format:\n"
                "Name: ...\nRace & Class: ...\nPersonality: ...\nQuirks: ...\nBackstory: ...\nIdeal: ...\nBond: ...\nFlaw: ...\n"
                "Make quirks vivid to inspire illustration prompts."
            )}
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

def generate_image(npc_text, filename):
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    race, char_class = extract_race_and_class(npc_text)
    quirks_line = next((line for line in npc_text.split('\n') if line.lower().startswith("quirks")), None)
    quirks = quirks_line.split(":", 1)[1].strip() if quirks_line else ""
    prompt = (
        f"A fantasy portrait of a {race} {char_class} in a lively medieval tavern. "
        f"Character traits: {quirks}. Semi-realistic digital art style, warm tavern lighting, detailed background."
    )
    prompt = prompt[:950]  # Limit to avoid exceeding API limits

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

def post_to_facebook(npc, image_path=None):
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

    if image_path:
        url = f"https://graph.facebook.com/{page_id}/photos"
        files = {"source": open(image_path, "rb")}
        data = {"caption": formatted_post.strip(), "access_token": token}
        response = requests.post(url, files=files, data=data)
    else:
        url = f"https://graph.facebook.com/{page_id}/feed"
        data = {"message": formatted_post.strip(), "access_token": token}
        response = requests.post(url, data=data)

    print(f"📬 Facebook POST response: {response.status_code}")
    print(f"📬 Facebook POST response body: {response.text}")

    if response.status_code == 200:
        print("✅ NPC posted to Facebook!")
    else:
        print(f"❌ Facebook error: {response.status_code} - {response.text}")


# --- Main Job ---
def job():
    print("🕒 Running bot job...")
    npc = generate_npc()
    image_path = generate_image(npc, "npc_image.png")
    post_to_facebook(npc, image_path)

# --- Scheduler ---
def run_scheduler():
    print("📅 Bot scheduler is running...")
    schedule.every().monday.at("11:00").do(job)      # Peak engagement
    schedule.every().thursday.at("18:00").do(job)    # Evening gaming crowd

    while True:
        schedule.run_pending()
        time.sleep(30)

# --- Main Run ---
if __name__ == "__main__":
    keep_alive()
    run_scheduler()
