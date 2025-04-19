import os
import time
import schedule
import requests
import random
import openai
from flask import Flask, request, redirect
from threading import Thread
from dotenv import load_dotenv

load_dotenv()

# --- Web Server to Keep Render Alive ---
app = Flask(__name__)

@app.route('/')
def home():
    return """
        <h1>🤖 Fantasy NPC Bot</h1>
        <form action="/post-now" method="post">
            <button type="submit" style="font-size:24px;padding:10px 20px;">✨ Post New NPC Now</button>
        </form>
    """

@app.route('/post-now', methods=['POST'])
def post_now():
    Thread(target=job).start()
    return redirect('/')

def run_web():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_web)
    t.start()

# --- Fantasy Trivia & Lore ---
TRIVIA_AND_LORE = [
    "💡 Did you know? Most taverns in Faerûn are built over ley lines, enhancing magical effects!",
    "📜 Lore Drop: The bard Elowen once silenced a tavern brawl with a single lute chord.",
    "🧙‍♂️ Trivia: The term 'Dungeon Master' was first coined in 1975!",
    "🧝‍♀️ Lore Fact: Elves consider tavern gossip an art form.",
    "🍺 Fun Fact: Gnomes ferment ale with magical mushrooms for dream enhancement.",
    "📘 Lore Bit: Baldur’s Gate banned teleportation after a wizard stole sausages!",
]

# --- Generate Dynamic Hashtags ---
def generate_hashtags(race, char_class):
    base_tags = [
        '#DnD', '#FantasyArt', '#TavernLife', '#TabletopGames', 
        '#RPGCharacter', '#Roleplay', '#CharacterArt', '#Adventurer'
    ]
    base_tags.append(f"#{race.replace(' ', '')}")
    base_tags.append(f"#{char_class.replace(' ', '')}")
    return ' '.join(base_tags)

# --- NPC Generator ---
def generate_npc():
    print("🧠 [DEBUG] Generating NPC...")
    try:
        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a creative Dungeons & Dragons NPC generator."},
                {"role": "user", "content": "Generate a creative NPC with:\nName:\nRace & Class:\nPersonality:\nQuirks:\nBackstory:\nIdeal:\nBond:\nFlaw:"}
            ],
            temperature=0.9
        )
        npc_text = response.choices[0].message.content.strip()
        print("✅ [DEBUG] NPC generated.")
        return npc_text
    except Exception as e:
        print(f"❌ [ERROR] Failed to generate NPC: {e}")
        return None

# --- Extract Race and Class ---
def extract_race_and_class(npc):
    try:
        lines = npc.split('\n')
        for line in lines:
            if line.lower().startswith("race & class"):
                parts = line.split(":", 1)
                if len(parts) > 1:
                    race_class = parts[1].strip()
                    if " " in race_class:
                        return race_class.split(" ", 1)
        return "Human", "Fighter"
    except Exception as e:
        print(f"❌ [ERROR] Failed to extract race/class: {e}")
        return "Human", "Fighter"

# --- DALL-E Image Generator ---
def generate_image(prompt, filename):
    print(f"🎨 [DEBUG] Generating image: {prompt}")
    try:
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
        print("🖼️ [DEBUG] Image saved.")
        return filename
    except Exception as e:
        print(f"❌ [ERROR] Failed to generate image: {e}")
        return None

# --- Facebook Poster ---
def post_to_facebook(npc, image_path=None, race="Human", char_class="Fighter"):
    print("🔑 [DEBUG] Preparing Facebook post...")
    try:
        page_id = os.getenv("FB_PAGE_ID")
        token = os.getenv("FB_PAGE_ACCESS_TOKEN")
        if not page_id or not token:
            print("⚠️ Facebook credentials missing. Skipping post.")
            return

        caption = f"{npc}\n\n{generate_hashtags(race, char_class)}"

        if image_path:
            url = f"https://graph.facebook.com/{page_id}/photos"
            files = {"source": open(image_path, "rb")}
            data = {"caption": caption, "access_token": token}
            response = requests.post(url, files=files, data=data)
        else:
            url = f"https://graph.facebook.com/{page_id}/feed"
            data = {"message": caption, "access_token": token}
            response = requests.post(url, data=data)

        if response.status_code == 200:
            print("✅ [SUCCESS] NPC posted to Facebook!")
        else:
            print(f"❌ [ERROR] Facebook post failed: {response.status_code} - {response.text}")

    except Exception as e:
        print(f"❌ [ERROR] Post to Facebook crashed: {e}")

# --- Main Job ---
def job():
    print("🚀 [DEBUG] job() triggered...")
    npc = generate_npc()
    if not npc:
        print("❌ [ERROR] NPC generation failed. Skipping post.")
        return
    race, char_class = extract_race_and_class(npc)
    prompt = f"A fantasy portrait of a {race} {char_class} in a lively medieval tavern, semi-realistic digital painting style."
    image_path = generate_image(prompt, "npc_image.png")
    if not image_path:
        print("⚠️ [WARNING] Image generation failed, posting text only.")
    post_to_facebook(npc, image_path, race, char_class)

# --- Scheduler ---
def run_scheduler():
    print("📅 Bot scheduler is running...")
    schedule.every().monday.at("10:00").do(job)
    schedule.every().thursday.at("10:00").do(job)
    while True:
        schedule.run_pending()
        time.sleep(30)

# --- Start ---
if __name__ == "__main__":
    keep_alive()
    run_scheduler()
