import os
import time
import random
import requests
import schedule
import openai
from flask import Flask, request, redirect
from threading import Thread
from dotenv import load_dotenv
from datetime import datetime

# --- Load environment variables
load_dotenv()

# --- Initialize Flask app
app = Flask(__name__)

# --- Bot State
bot_start_time = datetime.now()
last_post_time = None

# --- Lore & Trivia for comments
TRIVIA_AND_LORE = [
    "🧙‍♂️ Lore Drop: In ancient taverns, tales were traded for ale!",
    "📜 Trivia: Elves believe every tavern has a spirit guardian.",
    "🍺 Fun Fact: Gnomes invented sparkling mead during a lost festival.",
    "⚔️ Battle Tale: The bravest warriors once dueled using only spoons!",
    "🎭 Bard’s Wisdom: Every story has truth hidden between the lies.",
    "🌟 Did you know? The original D&D tavern was based on a real pub.",
    "🔮 Arcane Lore: Wizards often plant hidden portals inside taverns.",
    "🛡️ Hero Fact: Legendary shields are sometimes auctioned in secret taverns.",
]

# --- Facebook Reactions pool
REACTIONS = ['LIKE', 'LOVE', 'WOW', 'HAHA']

# --- Home Dashboard
@app.route('/')
def home():
    now = datetime.now()
    uptime = now - bot_start_time
    last_post = last_post_time.strftime("%Y-%m-%d %H:%M:%S") if last_post_time else "Never"

    return f'''
    <html>
    <head>
        <title>🛡️ MasterBot Pro Dashboard</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                background-color: #121212;
                color: #f1f1f1;
                text-align: center;
                padding: 40px;
            }}
            .button {{
                background-color: #4CAF50;
                border: none;
                color: white;
                padding: 15px 32px;
                text-align: center;
                text-decoration: none;
                display: inline-block;
                font-size: 16px;
                margin: 20px;
                cursor: pointer;
                border-radius: 8px;
                transition: background-color 0.3s ease;
            }}
            .button:hover {{
                background-color: #45a049;
            }}
            .stats {{
                margin-top: 30px;
                font-size: 18px;
                line-height: 1.6;
            }}
        </style>
    </head>
    <body>
        <h1>🧙‍♂️ MasterBot Pro: CHAOS MODE++</h1>
        <form action="/post-now" method="post">
            <button class="button" type="submit">🚀 Post New NPC Now</button>
        </form>
        <div class="stats">
            <p><b>🕒 Bot Uptime:</b> {str(uptime).split(".")[0]}</p>
            <p><b>📝 Last NPC Posted:</b> {last_post}</p>
            <p><b>📅 Scheduled Posts:</b> Mondays & Thursdays @ 10:00am</p>
            <p><b>🌐 Server Status:</b> <span style="color:lightgreen;">Online ✅</span></p>
        </div>
    </body>
    </html>
    '''

# --- Manual Post
@app.route('/post-now', methods=['POST'])
def manual_post():
    Thread(target=job).start()
    return redirect("/")

# --- Extract race and class
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

# --- Generate NPC
def generate_npc():
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a creative Dungeons & Dragons NPC generator."},
            {"role": "user", "content": "Generate a creative Dungeons & Dragons NPC with:\nName\nRace & Class\nPersonality\nQuirks\nBackstory\nIdeal\nBond\nFlaw"}
        ],
        temperature=0.9
    )
    return response.choices[0].message.content.strip()

# --- Post to Facebook
def post_to_facebook(npc, image_path=None):
    print("🔍 Debug: FB_PAGE_ID =", os.getenv("FB_PAGE_ID"))
    print("🔍 Debug: FB_PAGE_ACCESS_TOKEN present =", bool(os.getenv("FB_PAGE_ACCESS_TOKEN")))

    page_id = os.getenv("FB_PAGE_ID")
    token = os.getenv("FB_PAGE_ACCESS_TOKEN")

    if not page_id or not token:
        print("⚠️ Facebook credentials missing. Skipping FB post.")
        return

    formatted_post = (
        f"{npc}\n\n"
        "#DnD #DungeonsAndDragons #TavernNPC #FantasyArt #RPGCharacter #AIArt #Roleplay"
    )

    try:
        if image_path:
            print("📸 Posting image...")
            url = f"https://graph.facebook.com/{page_id}/photos"
            files = {"source": open(image_path, "rb")}
            data = {"caption": formatted_post, "access_token": token}
            response = requests.post(url, files=files, data=data)
        else:
            print("📝 Posting text...")
            url = f"https://graph.facebook.com/{page_id}/feed"
            data = {"message": formatted_post, "access_token": token}
            response = requests.post(url, data=data)

        print(f"🔎 Facebook API Response: {response.status_code} - {response.text}")

        if response.status_code == 200:
            print("✅ Post Successful!")
            post_id = response.json().get("post_id") or response.json().get("id")
            if post_id:
                Thread(target=chaos_engagement, args=(post_id,)).start()
        else:
            print("❌ Post Failed!")

    except Exception as e:
        print("🚨 Error posting to Facebook:", e)

# --- Chaos Engagement: Comment + Reaction
def chaos_engagement(post_id):
    page_id = os.getenv("FB_PAGE_ID")
    token = os.getenv("FB_PAGE_ACCESS_TOKEN")

    # 1. Auto-Comment
    comment = random.choice(TRIVIA_AND_LORE)
    comment_url = f"https://graph.facebook.com/{post_id}/comments"
    comment_data = {"message": comment, "access_token": token}
    requests.post(comment_url, data=comment_data)
    print(f"💬 Posted Comment: {comment}")

    # 2. Auto-Reaction
    reaction = random.choice(REACTIONS)
    reaction_url = f"https://graph.facebook.com/{post_id}/reactions"
    reaction_data = {"type": reaction, "access_token": token}
    requests.post(reaction_url, data=reaction_data)
    print(f"🎭 Reacted with: {reaction}")

# --- Full Bot Job
def job():
    global last_post_time
    print("🕒 Running bot job...")

    npc = generate_npc()
    race, char_class = extract_race_and_class(npc)

    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    prompt = f"Portrait of a {race} {char_class} in a fantasy tavern, cinematic lighting, detailed, digital art"
    response = client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        n=1,
        size="1024x1024"
    )
    image_url = response.data[0].url

    image_data = requests.get(image_url).content
    image_path = "npc_image.png"
    with open(image_path, "wb") as f:
        f.write(image_data)

    post_to_facebook(npc, image_path)
    last_post_time = datetime.now()

# --- Scheduler
def run_scheduler():
    print("📅 Scheduler running...")
    schedule.every().monday.at("10:00").do(job)
    schedule.every().thursday.at("10:00").do(job)
    while True:
        schedule.run_pending()
        time.sleep(30)

# --- Keep Alive
def keep_alive():
    t = Thread(target=lambda: app.run(host='0.0.0.0', port=8080))
    t.start()

# --- Main
if __name__ == "__main__":
    keep_alive()
    run_scheduler()
