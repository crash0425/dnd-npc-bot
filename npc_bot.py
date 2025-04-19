import os
import time
import schedule
import requests
import random
from flask import Flask, request, redirect
from threading import Thread
from dotenv import load_dotenv
import openai

# Load .env secrets
load_dotenv()

# --- Flask Web Server ---
app = Flask(__name__)

@app.route('/')
def home():
    return '''
        <h1>MasterBot Pro</h1>
        <form action="/post-now" method="post">
            <button type="submit" style="font-size:20px;padding:10px 20px;">Post NPC Now</button>
        </form>
    '''

@app.route('/post-now', methods=["POST"])
def post_now():
    Thread(target=job).start()
    return redirect('/')

def run_web():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_web)
    t.start()

# --- Dynamic Hashtags ---
def generate_dynamic_hashtags():
    hashtag_pool = [
        "#DnD", "#DungeonsAndDragons", "#FantasyRPG", "#TavernLife",
        "#RPGCharacter", "#FantasyArt", "#TabletopGames", "#TTRPG",
        "#AdventureAwaits", "#RPGCommunity", "#Storytelling", "#FantasyWorld",
        "#CharacterDesign", "#EpicQuest", "#RPGArt", "#RPGMagic"
    ]
    selected_tags = random.sample(hashtag_pool, k=random.randint(6, 8))
    return ' '.join(selected_tags)

# --- Engagement Questions ---
def generate_engagement_question():
    questions = [
        "🧙‍♂️ What's the wildest NPC your party has ever met?",
        "⚔️ Would you trust this character in your campaign?",
        "🍻 How would this NPC fit into your world?",
        "🗺️ What backstory would you give this NPC?",
        "🐉 Would you hire this adventurer for a quest?",
        "🏰 What tavern specialty would this NPC order?",
        "🧝‍♀️ Which race/class combo is your favorite?",
        "🎲 What would be this NPC's most dangerous secret?"
    ]
    return random.choice(questions)

# --- NPC Generation ---
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

# --- Image Generation ---
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
    print("🔍 Debug: FB_PAGE_ID =", os.getenv("FB_PAGE_ID"))
    print("🔍 Debug: FB_PAGE_ACCESS_TOKEN present =", bool(os.getenv("FB_PAGE_ACCESS_TOKEN")))

    page_id = os.getenv("FB_PAGE_ID")
    token = os.getenv("FB_PAGE_ACCESS_TOKEN")

    if not page_id or not token:
        print("⚠️ Facebook credentials missing. Skipping post.")
        return

    formatted_post = (
        f"{npc}\n\n"
        f"{generate_dynamic_hashtags()}\n\n"
        f"{generate_engagement_question()}"
    )

    try:
        if image_path:
            print("📸 Posting image to Facebook...")
            url = f"https://graph.facebook.com/{page_id}/photos"
            files = {"source": open(image_path, "rb")}
            data = {"caption": formatted_post.strip(), "access_token": token}
            response = requests.post(url, files=files, data=data)
        else:
            print("📝 Posting text to Facebook...")
            url = f"https://graph.facebook.com/{page_id}/feed"
            data = {"message": formatted_post.strip(), "access_token": token}
            response = requests.post(url, data=data)

        print(f"🔎 Facebook API Response: {response.status_code} - {response.text}")

        if response.status_code == 200:
            print("✅ NPC posted to Facebook successfully!")
        else:
            print("🚨 Failed to post NPC to Facebook.")

    except Exception as e:
        print(f"🚨 Exception while posting to Facebook: {e}")

# --- Bot Job ---
def job():
    print("🕒 Running Smart Scheduled Post...")
    npc = generate_npc()
    race, char_class = extract_race_and_class(npc)
    prompt = f"A fantasy portrait of a {race} {char_class} sitting in a medieval tavern, painted in a semi-realistic style, vivid and detailed."
    image_path = generate_image(prompt, "npc_image.png")
    post_to_facebook(npc, image_path)

# --- Scheduler Loop ---
def run_scheduler():
    print("📅 Bot scheduler is active...")
    schedule.every().monday.at("18:45").do(job)
    schedule.every().thursday.at("18:45").do(job)

    while True:
        schedule.run_pending()
        time.sleep(30)

# --- MAIN ---
if __name__ == "__main__":
    keep_alive()
    run_scheduler()
