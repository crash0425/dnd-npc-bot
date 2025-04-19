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
        return

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
        else:
            print("❌ Failed to post.")

    except Exception as e:
        print("🚨 An error occurred while posting to Facebook:", e)

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

    post_to_facebook(npc, image_path)

    last_post_time = datetime.now()  # 🆕 Save last post time

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
