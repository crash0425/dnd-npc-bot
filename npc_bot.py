import os
import sys
import time
import schedule
import requests
from flask import Flask, render_template_string, request, redirect
from threading import Thread
import openai
import random
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- Web Server to Keep Render Alive ---
app = Flask(__name__)

@app.route('/')
def home():
    return '''
    <h1>Fantasy NPC Forge</h1>
    <form action="/post-now" method="post">
        <button type="submit" style="padding: 10px 20px; font-size: 20px;">✨ Post Now ✨</button>
    </form>
    '''

@app.route('/post-now', methods=['POST'])
def manual_post():
    Thread(target=job).start()
    return redirect('/')

def run_web():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_web)
    t.start()

# --- Trivia / Engagement Content ---
TRIVIA_AND_LORE = [
    "💡 Did you know? Most taverns in Faerûn are built over ley lines, enhancing magical effects!",
    "📜 Lore Drop: The bard Elowen once silenced a tavern brawl with a single lute chord.",
    "🧙‍♂️ Trivia: 'Dungeon Master' was first coined in 1975!",
    "🍺 Fun Fact: Gnomes brew ale with magical mushrooms to enhance dreams!",
    "🔥 Hot Lore: A dragon named Emberbelch opened a tavern to collect adventurer gossip!"
]

# --- NPC & Image Generation ---
def generate_npc():
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a creative Dungeons & Dragons NPC generator."},
            {"role": "user", "content": "Generate a unique D&D tavern NPC. Format: Name, Race & Class, Personality, Quirks, Backstory, Ideal, Bond, Flaw."}
        ],
        temperature=0.9
    )
    return response.choices[0].message.content.strip()

def extract_race_and_class(npc):
    lines = npc.split('\n')
    for line in lines:
        if line.lower().startswith("race & class"):
            parts = line.split(":", 1)
            if len(parts) > 1:
                race_class = parts[1].strip()
                if " " in race_class:
                    return race_class.split(" ", 1)
    return "Human", "Fighter"

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

# --- Facebook Posting ---
def post_to_facebook(npc, image_path=None):
    page_id = os.getenv("FB_PAGE_ID")
    token = os.getenv("FB_PAGE_ACCESS_TOKEN")

    print("🔍 Debug: FB_PAGE_ID =", page_id)
    print("🔍 Debug: FB_PAGE_ACCESS_TOKEN present =", bool(token))
    sys.stdout.flush()

    if not page_id or not token:
        print("⚠️ Facebook credentials missing. Skipping post.")
        sys.stdout.flush()
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
            print("📸 Posting image to Facebook...")
            sys.stdout.flush()
            response = requests.post(url, files=files, data=data)
        else:
            url = f"https://graph.facebook.com/{page_id}/feed"
            data = {"message": formatted_post, "access_token": token}
            print("📝 Posting text post to Facebook...")
            sys.stdout.flush()
            response = requests.post(url, data=data)

        print(f"🔎 Facebook API Response: {response.status_code} - {response.text}")
        sys.stdout.flush()

        if response.status_code == 200:
            print("✅ NPC posted to Facebook successfully!")
            sys.stdout.flush()
        else:
            print(f"❌ Facebook post failed: {response.status_code} - {response.text}")
            sys.stdout.flush()

    except Exception as e:
        print(f"🚨 An unexpected error occurred while posting to Facebook: {e}")
        sys.stdout.flush()

# --- Full Job ---
def job():
    print("🕒 Running bot job...")
    sys.stdout.flush()
    try:
        npc = generate_npc()
        race, char_class = extract_race_and_class(npc)
        prompt = f"A detailed fantasy portrait of a {race} {char_class} in a cozy medieval tavern, candle-lit, rustic, semi-realistic style."
        image_path = generate_image(prompt, "npc_image.png")
        post_to_facebook(npc, image_path)
    except Exception as e:
        print(f"🚨 Error running job: {e}")
        sys.stdout.flush()

# --- Scheduler Setup ---
def run_scheduler():
    print("📅 Bot scheduler is active...")
    sys.stdout.flush()
    schedule.every().monday.at("09:00").do(job)
    schedule.every().wednesday.at("09:00").do(job)
    schedule.every().friday.at("09:00").do(job)

    while True:
        schedule.run_pending()
        time.sleep(30)

# --- Main ---
if __name__ == "__main__":
    keep_alive()
    run_scheduler()
