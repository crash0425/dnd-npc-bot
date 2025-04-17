import os
from dotenv import load_dotenv
load_dotenv()
import time
import schedule
import requests
from flask import Flask
from threading import Thread
import openai
import random

# --- Web Server to Keep Replit Alive ---
app = Flask('')

@app.route('/')
def home():
    return "NPC bot is alive!"



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
    "📘 Lore Bit: The city of Baldur’s Gate banned teleportation after a rogue wizard kept stealing sausages.",
    "🔮 Arcane Insight: Tiefling warlocks often see flashes of their patron’s realm when drinking mead.",
    "⚔️ Battle Tale: The Half-Orc hero Ragor once won a duel by reciting poetry mid-swing.",
    "🦴 Necromantic Rumor: Skeletons animated near graveyards dance slightly out of rhythm.",
    "🔥 Hot Lore: A dragon named Emberbelch once opened a tavern just to meet adventurers for gossip."
]

# --- Post to Facebook ---
def post_to_facebook(npc, image_path=None):
    print("🔍 Debug: FB_PAGE_ID:", os.getenv("FB_PAGE_ID"))
    print("🔍 Debug: FB_PAGE_ACCESS_TOKEN present:", bool(os.getenv("FB_PAGE_ACCESS_TOKEN")))
    page_id = os.getenv("FB_PAGE_ID")
    token = os.getenv("FB_PAGE_ACCESS_TOKEN")

    if not page_id or not token:
        print("⚠️ Facebook credentials missing. Skipping FB post.")
        return

    formatted_post = formatted_post = f"{npc}\n\n{generate_hashtags(npc)}"


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

# --- DALL·E Image Generation ---
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

# --- Scheduled Job ---
def job():
    print("🕒 Running bot job...")
    npc = generate_npc()
    race, char_class = extract_race_and_class(npc)
    prompt = f"A fantasy portrait of a {race} {char_class} sitting in a medieval tavern, painted in a semi-realistic style."
    image_path = generate_image(prompt, "npc_image.png")
    post_to_facebook(npc, image_path)

# --- Helpers ---
def generate_npc():
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a creative Dungeons & Dragons NPC generator."},
            {"role": "user", "content": "Generate a creative Dungeons & Dragons NPC with the following format:\nName: ...\nRace & Class: ...\nPersonality: ...\nQuirks: ...\nBackstory: ...\nIdeal: ...\nBond: ...\nFlaw: ..."}
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
def generate_hashtags(npc):
    hashtags = ['#DnD', '#TavernNPC', '#FantasyRPG']

    race, char_class = extract_race_and_class(npc)

    if race:
        hashtags.append(f"#{race.replace(' ', '')}")
    if char_class:
        hashtags.append(f"#{char_class.replace(' ', '')}")

    # Add bonus general fantasy tags
    hashtags += ['#FantasyArt', '#CharacterDesign', '#Adventure']

    return ' '.join(hashtags)

# --- Scheduler Loop ---
def run_scheduler():
    print("📅 Bot scheduler is running...")
    schedule.every().monday.at("10:00").do(job)
    schedule.every().thursday.at("10:00").do(job)

    while True:
        schedule.run_pending()
        time.sleep(30)

if __name__ == "__main__":
    keep_alive()
    job()  
    run_scheduler()
