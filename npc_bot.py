import os
import time
import schedule
import requests
from flask import Flask, render_template_string, request, redirect
from threading import Thread
import openai
import random
import datetime
from dotenv import load_dotenv

# --- Load .env Variables ---
load_dotenv()

# --- Web Server to Keep Alive ---
app = Flask(__name__)

@app.route('/')
def home():
    return render_template_string('''
        <h1>🧙‍♂️ Fantasy NPC Bot</h1>
        <form action="/post-now" method="post">
            <button type="submit">📤 Post New NPC Now</button>
        </form>
    ''')

@app.route('/post-now', methods=['POST'])
def post_now():
    Thread(target=job).start()
    return render_template_string('''
        <h1>✅ Your NPC has been posted!</h1>
        <a href="/">🔙 Back to Home</a>
    ''')

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
    "🧝‍♀️ Lore Fact: Elves consider tavern gossip an art form worthy of poetry.",
    "🍺 Fun Fact: Gnomes in Waterdeep ferment ale with magical mushrooms for enhanced dreams.",
    "📘 Lore Bit: Baldur’s Gate banned teleportation after a rogue wizard kept stealing sausages.",
    "🔮 Arcane Insight: Tiefling warlocks often see flashes of their patron’s realm when drinking mead.",
    "⚔️ Battle Tale: The Half-Orc hero Ragor once won a duel by reciting poetry mid-swing.",
    "🦴 Necromantic Rumor: Skeletons animated near graveyards dance slightly out of rhythm.",
    "🔥 Hot Lore: A dragon named Emberbelch once opened a tavern just to meet adventurers for gossip."
]

# --- Helper: Extract Race and Class from NPC Text ---
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

# --- Helper: Generate DALL-E Image ---
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

# --- Helper: Post to Facebook ---
def post_to_facebook(npc, image_path=None):
    page_id = os.getenv("FB_PAGE_ID")
    token = os.getenv("FB_PAGE_ACCESS_TOKEN")

    if not page_id or not token:
        print("⚠️ Facebook credentials missing. Skipping FB post.")
        return

    print(f"🔍 Debug: FB_PAGE_ID: {page_id}")
    print(f"🔍 Debug: FB_PAGE_ACCESS_TOKEN present: {bool(token)}")

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

    except Exception as e:
        print(f"🚨 An error occurred while posting to Facebook: {e}")

# --- Helper: Generate Random NPC ---
def generate_npc():
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    today = datetime.datetime.now().strftime("%A")
    prompt = (
        f"Create a fantasy tavern NPC perfect for Dungeons & Dragons. "
        f"Today is {today}. Include Race & Class. "
        f"Make the NPC charming, mysterious, or funny."
    )

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are an expert fantasy storyteller creating lively tavern NPCs."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.8
    )

    npc_text = response.choices[0].message.content
    trivia = random.choice(TRIVIA_AND_LORE)
    full_post = f"{npc_text}\n\n{trivia}"
    return full_post

# --- Main Bot Job ---
def job():
    print("⚙️ Running scheduled bot job...")
    npc = generate_npc()
    race, char_class = extract_race_and_class(npc)
    image_prompt = (
        f"A fantasy portrait of a {race} {char_class} sitting in a lively medieval tavern. "
        "Painted in a semi-realistic digital art style. Include visible gear related to their class."
    )
    image_path = generate_image(image_prompt, "npc_image.png")
    post_to_facebook(npc, image_path)

# --- Scheduler Loop ---
keep_alive()
schedule.every(6).hours.do(job)  # Post every 6 hours

print("📅 Bot scheduler is running...")
while True:
    schedule.run_pending()
    time.sleep(60)
