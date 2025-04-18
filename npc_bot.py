import os
import time
import schedule
import requests
import openai
import random
import datetime
from flask import Flask, render_template_string
from threading import Thread
from dotenv import load_dotenv

load_dotenv()

# --- Flask App (for Uptime Robot / Preview Page) ---
app = Flask('')

@app.route('/')
def home():
    return "🛡️ NPC Bot is alive!"

@app.route('/preview')
def preview():
    next_post_time = get_next_post_time()
    return render_template_string("""
    <html>
        <head>
            <title>🧙 NPC Bot Preview</title>
            <style>
                body { font-family: Arial, sans-serif; text-align: center; padding: 50px; background-color: #f5f5f5; }
                h1 { color: #333; }
                img { max-width: 400px; border-radius: 12px; margin-top: 20px; }
                .countdown { margin-top: 20px; font-size: 1.2em; color: #555; }
                footer { margin-top: 40px; font-size: 0.8em; color: #999; }
            </style>
        </head>
        <body>
            <h1>🛡️ Fantasy NPC Bot</h1>
            <p>Next post scheduled at:</p>
            <div class="countdown">{{ next_post_time }}</div>
            <img src="https://placehold.co/400x400?text=Preview+NPC" alt="Preview NPC">
            <footer>Maintained by Masterbot 🛡️</footer>
        </body>
    </html>
    """, next_post_time=next_post_time)

def run_web():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_web)
    t.start()

def get_next_post_time():
    now = datetime.datetime.now()
    today_monday = now.weekday() == 0
    today_thursday = now.weekday() == 3

    next_post = None
    if today_monday and now.hour < 10:
        next_post = now.replace(hour=10, minute=0, second=0, microsecond=0)
    elif today_thursday and now.hour < 10:
        next_post = now.replace(hour=10, minute=0, second=0, microsecond=0)
    else:
        # Set next Monday or Thursday
        days_ahead = 0
        if now.weekday() < 3:
            days_ahead = 3 - now.weekday()
        else:
            days_ahead = (7 - now.weekday() + 0)  # Next Monday
        next_post = now + datetime.timedelta(days=days_ahead)
        next_post = next_post.replace(hour=10, minute=0, second=0, microsecond=0)

    return next_post.strftime("%A, %B %d at %I:%M %p")

# --- Fantasy Trivia & Lore ---
TRIVIA_AND_LORE = [
    "💡 Did you know? Most taverns in Faerûn are built over ley lines, enhancing magical effects!",
    "📜 Lore Drop: The infamous bard Elowen once silenced a tavern brawl with a single lute chord.",
    "🧙‍♂️ Trivia: 'Dungeon Master' was first coined in 1975!",
    "🍺 Fun Fact: Gnomes ferment ale with magical mushrooms for enhanced dreams.",
    "🔮 Arcane Insight: Tieflings often glimpse their patron's realm while drinking.",
]

# --- NPC and Image Generation ---
def generate_npc():
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a creative Dungeons & Dragons NPC generator."},
            {"role": "user", "content": "Generate a creative Dungeons & Dragons NPC:\nName: ...\nRace & Class: ...\nPersonality: ...\nQuirks: ...\nBackstory: ...\nIdeal: ...\nBond: ...\nFlaw: ..."}
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
    if not page_id or not token:
        print("⚠️ Facebook credentials missing.")
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

    if response.status_code == 200:
        print("✅ NPC posted to Facebook!")
    else:
        print(f"❌ Facebook error: {response.status_code} - {response.text}")

# --- Scheduled Job ---
def job():
    print("🕒 Running bot job...")
    npc = generate_npc()
    race, char_class = extract_race_and_class(npc)
    prompt = (
        f"A fantasy portrait of a {race} {char_class} sitting in a medieval tavern. "
        f"Depicted in a semi-realistic, digital painting style with atmospheric candlelight."
    )
    image_path = generate_image(prompt, "npc_image.png")
    post_to_facebook(npc, image_path)

# --- Scheduler Loop ---
def run_scheduler():
    print("📅 Bot scheduler is running...")
    schedule.every().monday.at("10:00").do(job)
    schedule.every().thursday.at("10:00").do(job)

    while True:
        schedule.run_pending()
        time.sleep(30)

# --- Start Bot ---
if __name__ == "__main__":
    keep_alive()
    run_scheduler()
