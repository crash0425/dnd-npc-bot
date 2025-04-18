import os
import time
import schedule
import requests
from flask import Flask
from threading import Thread
import openai
import random
from dotenv import load_dotenv
load_dotenv()

# --- Web Server to Keep Alive ---
app = Flask('')

@app.route('/')
def home():
    return "NPC MasterBot is alive!"

def run_web():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_web)
    t.start()

# --- Content Pools ---
TRIVIA_AND_LORE = [
    "\ud83d\udca1 Did you know? Most taverns in Faer\u00fbn are built over ley lines, enhancing magical effects!",
    "\ud83d\udcdc Lore Drop: The infamous bard Elowen once silenced a tavern brawl with a single lute chord.",
    "\ud83e\uddd9\u200d\u2642\ufe0f Trivia: The term 'Dungeon Master' was first coined in 1975 with the original D&D release.",
    "\ud83e\uddd5\u200d\u2640\ufe0f Lore Fact: Elves consider tavern gossip an art form worthy of poetry.",
    "\ud83c\udf7a Fun Fact: Gnomes in Waterdeep ferment ale with magical mushrooms for enhanced dreams."
]

MINI_STORIES = [
    "\ud83c\udf1f Story Hook: A bard offers a quest in exchange for a memory. Would you accept?",
    "\u2694\ufe0f Adventure: An abandoned tavern houses a whispering ghost with ancient secrets.",
    "\ud83e\uddd9\u200d\u2642\ufe0f Magical Mystery: Drinking ale in the Dragon's Breath Inn grants wild visions.",
    "\ud83d\udc51 Royal Decree: A bounty is placed on a cursed relic hidden deep underground.",
    "\ud83d\udc09 Dragon Sighting: A young copper dragon seen gambling with village children!"
]

POLL_QUESTIONS = [
    "\ud83c\udf7a Favorite Tavern Drink: Mead \ud83c\udf6f or Ale \ud83c\udf7a?",
    "\ud83e\uddd9\u200d\u2640\ufe0f Preferred Class: Wizard \ud83d\udc9a or Rogue \ud83d\udd2b?",
    "\ud83c\udfdb\ufe0f Best Adventure Setting: Haunted Castle \ud83d\udc7b or Lost Jungle \ud83d\udc12?",
    "\ud83d\udc09 Dream Companion: Dragon \ud83d\udc09 or Griffin \ud83e\udc85?",
    "\u2694\ufe0f Ultimate Weapon: Enchanted Sword \u2694\ufe0f or Bow of Stars \ud83c\udf20?"
]

# --- Facebook Posting ---
def post_to_facebook(message, image_path=None):
    print("\ud83d\udd0d Debug: FB_PAGE_ID:", os.getenv("FB_PAGE_ID"))
    print("\ud83d\udd0d Debug: FB_PAGE_ACCESS_TOKEN present:", bool(os.getenv("FB_PAGE_ACCESS_TOKEN")))
    page_id = os.getenv("FB_PAGE_ID")
    token = os.getenv("FB_PAGE_ACCESS_TOKEN")

    if not page_id or not token:
        print("\u26a0\ufe0f Facebook credentials missing. Skipping FB post.")
        return

    hashtags = "#DnD #TavernNPC #RPGCharacter #FantasyArt #DungeonsAndDragons #TabletopRPG #TavernLife #TTRPG"
    formatted_post = f"{message}\n\n{hashtags}"

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
        print("\u2705 Posted to Facebook!")
    else:
        print(f"\u274c Facebook error: {response.status_code} - {response.text}")

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

# --- Bot Jobs ---
def job_npc():
    print("\ud83d\udd52 Posting NPC...")
    npc = generate_npc()
    race, char_class = extract_race_and_class(npc)
    prompt = f"A fantasy portrait of a {race} {char_class} sitting in a medieval tavern, painted in a semi-realistic style."
    image_path = generate_image(prompt, "npc_image.png")
    post_to_facebook(npc, image_path)

def job_story():
    print("\ud83d\udd52 Posting Story...")
    story = random.choice(MINI_STORIES)
    prompt = "A cozy medieval tavern with adventurers sharing tales by firelight, in semi-realistic fantasy art style."
    image_path = generate_image(prompt, "story_image.png")
    post_to_facebook(story, image_path)

def job_poll():
    print("\ud83d\udd52 Posting Poll...")
    poll = random.choice(POLL_QUESTIONS)
    prompt = "A fantasy tavern bulletin board covered with parchment polls and posters, semi-realistic fantasy art."
    image_path = generate_image(prompt, "poll_image.png")
    post_to_facebook(poll, image_path)

def job_engagement():
    print("\ud83d\udd52 Posting Engagement Question...")
    question = generate_engagement_question()
    prompt = "An adventurer pondering their destiny inside a bustling medieval tavern, warm lighting, semi-realistic style."
    image_path = generate_image(prompt, "engagement_image.png")
    post_to_facebook(question, image_path)

# --- NPC & Helpers ---
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

def generate_engagement_question():
    questions = [
        "What would your dream tavern be named?",
        "Which fantasy creature would you trust to guard your treasure?",
        "If you could brew a magical potion, what would it do?",
        "What's your favorite D&D alignment?",
        "Describe your ideal adventuring party in 3 words!"
    ]
    return random.choice(questions)

# --- Scheduler ---
def run_scheduler():
    print("\ud83d\udcc5 Bot scheduler is running...")
    schedule.every().monday.at("10:00").do(job_npc)
    schedule.every().wednesday.at("12:00").do(job_engagement)
    schedule.every().friday.at("14:00").do(job_story)
    schedule.every().sunday.at("17:00").do(job_poll)

    while True:
        schedule.run_pending()
        time.sleep(30)

# --- Main ---
if __name__ == "__main__":
   if __name__ == "__main__":
    keep_alive()
    job()
