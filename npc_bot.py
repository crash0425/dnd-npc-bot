import os
import time
import schedule
import requests
import random
import openai
from flask import Flask, request, redirect
from threading import Thread
from dotenv import load_dotenv
from datetime import datetime

# --- Load environment variables
load_dotenv()

# --- Initialize Flask app
app = Flask(__name__)

# --- Track Bot State
bot_start_time = datetime.now()
last_post_time = None

# --- Comment Templates
COMMENTS = [
    "🍻 What's your favorite tavern drink when adventuring?",
    "🧙‍♂️ If you met this NPC in a tavern, what would you ask them?",
    "📜 Legend says taverns built near ley lines grant better luck. Believe it?",
    "⚔️ Who would win in a bar brawl: this NPC or your last character?",
    "🎲 Roll a d20 — if it's a 20, this NPC buys you a drink!",
    "🧝‍♀️ Fun Fact: Elves prefer wine brewed by druids over anything else!",
    "🐉 A dragon once disguised itself as a tavern owner... true story!",
    "🍺 Gnomish ale is rumored to cause strange dreams... would you try it?",
    "💬 What's your character's go-to tavern story?",
    "🛡️ Would you trust this NPC with your life or your gold?"
]

# --- Home Dashboard
@app.route('/')
def home():
    now = datetime.now()
    uptime = now - bot_start_time
    last_post = last_post_time.strftime("%Y-%m-%d %H:%M:%S") if last_post_time else "Never"

    return f'''
    <html>
    <head>
        <title>🛡️ NPC MasterBot Dashboard</title>
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
        <h1>🧙‍♂️ Welcome to NPC MasterBot Dashboard</h1>
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

# --- Manual Post Button
@app.route('/post-now', methods=['POST'])
def manual_post():
    Thread(target=job).start()
    return redirect("/")

# --- Helper: Extract Race and Class
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
            {"role": "user", "content": "Generate a creative Dungeons & Dragons NPC with the following format:\nName: ...\nRace & Class: ...\nPersonality: ...\nQuirks: ...\nBackstory: ...\nIdeal: ...\nBond: ...\nFlaw: ..."}
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
        return None

    formatted_post = (
        f"{npc}\n\n"
        "#DnD #DungeonsAndDragons #TavernNPC #RPGCharacter #FantasyArt #AIArt #Roleplay #TabletopGames"
    )

    try:
        if image_path:
            print("📸 Posting image to Facebook...")
            url = f"https://graph.facebook.com/{page_id}/photos"
            files = {"source": open(image_path, "rb")}
            data = {"caption": formatted_post.strip(), "access_token": token}
            response = requests.post(url, files=files, data=data)
        else:
            print("📝 Posting text only...")
            url = f"https://graph.facebook.com/{page_id}/feed"
            data = {"message": formatted_post.strip(), "access_token": token}
            response = requests.post(url, data=data)

        print(f"🔎 Facebook API Response: {response.status_code} - {response.text}")

        if response.status_code == 200:
            print("✅ NPC posted to Facebook successfully!")
            response_json = response.json()
            return response_json.get('post_id') or response_json.get('id')
        else:
            print("❌ Failed to post.")
            return None

    except Exception as e:
        print("🚨 An error occurred while posting to Facebook:", e)
        return None

# --- Post a Comment Under Post
def comment_on_post(post_id):
    page_id = os.getenv("FB_PAGE_ID")
    token = os.getenv("FB_PAGE_ACCESS_TOKEN")
    if not post_id:
        print("⚠️ No post ID found for commenting.")
        return

    comment_message = random.choice(COMMENTS)
    url = f"https://graph.facebook.com/{post_id}/comments"
    data = {"message": comment_message, "access_token": token}
    response = requests.post(url, data=data)

    if response.status_code == 200:
        print("💬 Commented successfully!")
    else:
        print(f"❌ Failed to comment: {response.status_code} - {response.text}")

# --- Main Posting Job
def job():
    global last_post_time
    print("🕒 Running bot job...")

    npc = generate_npc()
    race, char_class = extract_race_and_class(npc)

    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    prompt = f"Portrait of a {race} {char_class} inside a fantasy tavern, detailed, cinematic lighting, digital painting"
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

    post_id = post_to_facebook(npc, image_path)
    last_post_time = datetime.now()

    if post_id:
        time.sleep(30)  # Wait before commenting
        comment_on_post(post_id)

# --- Background Scheduler
def run_scheduler():
    print("📅 Bot scheduler is active...")
    schedule.every().monday.at("10:00").do(job)
    schedule.every().thursday.at("10:00").do(job)

    while True:
        schedule.run_pending()
        time.sleep(30)

# --- Keep Alive Server
def keep_alive():
    t = Thread(target=lambda: app.run(host='0.0.0.0', port=8080))
    t.start()

# --- Start Everything
if __name__ == "__main__":
    keep_alive()
    run_scheduler()
