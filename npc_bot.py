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

# --- Setup Flask App to Keep Alive ---
app = Flask(__name__)

@app.route('/')
def home():
    return "MasterBot Ultra Pro is alive!"

@app.route('/post-now', methods=['POST'])
def manual_post():
    Thread(target=job).start()
    return redirect("/")

def run_web():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_web)
    t.start()

# --- Setup Facebook ---
FB_PAGE_ID = os.getenv("FB_PAGE_ID")
FB_PAGE_ACCESS_TOKEN = os.getenv("FB_PAGE_ACCESS_TOKEN")

# --- Setup Google Sheets ---
gc = gspread.service_account(filename="service_account.json")
sh = gc.open_by_key(os.getenv("SPREADSHEET_ID"))
worksheet = sh.sheet1

# --- Trivia & Lore ---
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

# --- Utilities ---
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

def extract_race_and_class(npc_text):
    lines = npc_text.split('\n')
    for line in lines:
        if line.lower().startswith("race & class"):
            parts = line.split(":", 1)
            if len(parts) > 1:
                race_class = parts[1].strip()
                if " " in race_class:
                    return race_class.split(" ", 1)
    return "Human", "Adventurer"

def generate_prompt(npc):
    race, char_class = extract_race_and_class(npc)
    return (
        f"A detailed fantasy portrait of a {race} {char_class} "
        f"in a medieval tavern, lit by candlelight, full of character and mystery. "
        f"Painted in a semi-realistic digital art style, high detail."
    )

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

def generate_engagement_comment(npc):
    return random.choice(TRIVIA_AND_LORE)

def post_to_facebook(npc, image_path):
    try:
        print("🖼 Posting image to Facebook...")

        url = f"https://graph.facebook.com/{FB_PAGE_ID}/photos"
        files = {"source": open(image_path, "rb")}
        data = {
            "caption": f"{npc}\n\n#DnD #TavernLife #FantasyArt #RPGCharacter #AdventureAwaits",
            "access_token": FB_PAGE_ACCESS_TOKEN
        }
        response = requests.post(url, files=files, data=data)

        print(f"🔎 Facebook API Response: {response.status_code} - {response.text}")

        if response.status_code == 200:
            post_id = response.json().get("post_id") or response.json().get("id")
            print(f"✅ NPC posted successfully! Post ID: {post_id}")

            # Step 1: Post a comment
            comment_message = generate_engagement_comment(npc)
            comment_on_post(post_id, comment_message)

            # Step 2: Log to spreadsheet
            save_to_spreadsheet(post_id, npc, comment_message)

        else:
            print(f"❌ Failed to post to Facebook.")

    except Exception as e:
        print(f"🚨 An error occurred while posting: {e}")

def comment_on_post(post_id, message):
    try:
        url = f"https://graph.facebook.com/{post_id}/comments"
        data = {
            "message": message,
            "access_token": FB_PAGE_ACCESS_TOKEN
        }
        response = requests.post(url, data=data)

        if response.status_code == 200:
            print(f"💬 Comment posted successfully!")
        else:
            print(f"❌ Failed to post comment: {response.status_code} - {response.text}")

    except Exception as e:
        print(f"🚨 Comment error: {e}")

def save_to_spreadsheet(post_id, npc, comment):
    try:
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        worksheet.append_row([now, post_id, npc[:50] + "...", comment])
        print(f"📋 Post logged to Google Sheets!")

    except Exception as e:
        print(f"🚨 Spreadsheet log error: {e}")

# --- Main Bot Job ---
def job():
    print("🕒 Running bot job...")
    npc = generate_npc()
    prompt = generate_prompt(npc)
    image_path = generate_image(prompt, "npc_image.png")
    post_to_facebook(npc, image_path)

# --- Scheduler ---
def run_scheduler():
    print("📅 Bot scheduler is active...")
    schedule.every().monday.at("10:00").do(job)
    schedule.every().thursday.at("10:00").do(job)

    while True:
        schedule.run_pending()
        time.sleep(30)

# --- Start ---
if __name__ == "__main__":
    keep_alive()
    run_scheduler()
