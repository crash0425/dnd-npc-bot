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

# --- Initialize Flask App
app = Flask(__name__)

# --- Bot State Tracking
bot_start_time = datetime.now()
last_post_time = None

# --- Flask Web Dashboard
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
                background-color: #1c1c1c;
                color: #f1f1f1;
                font-family: Arial, sans-serif;
                text-align: center;
                padding-top: 40px;
            }}
            .button {{
                background-color: #4CAF50;
                color: white;
                padding: 15px 32px;
                font-size: 18px;
                margin: 20px;
                border: none;
                border-radius: 8px;
                cursor: pointer;
                transition: 0.3s;
            }}
            .button:hover {{
                background-color: #45a049;
            }}
            .stats {{
                margin-top: 30px;
                font-size: 20px;
            }}
        </style>
    </head>
    <body>
        <h1>🧙‍♂️ NPC MasterBot Dashboard</h1>
        <form action="/post-now" method="post">
            <button class="button" type="submit">🚀 Post NPC Now</button>
        </form>
        <div class="stats">
            <p><b>🕒 Uptime:</b> {str(uptime).split('.')[0]}</p>
            <p><b>📅 Last Post:</b> {last_post}</p>
            <p><b>📆 Schedule:</b> Mon & Thurs @ 10:00am</p>
            <p><b>🌐 Server:</b> Online ✅</p>
        </div>
    </body>
    </html>
    '''

# --- Manual Post Trigger
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
            {"role": "user", "content": "Generate a D&D NPC in the format:\nName: ...\nRace & Class: ...\nPersonality: ...\nQuirks: ...\nBackstory: ...\nIdeal: ...\nBond: ...\nFlaw: ..."}
        ],
        temperature=0.9
    )
    return response.choices[0].message.content.strip()

# --- Post to Facebook
def post_to_facebook(npc, image_path=None):
    page_id = os.getenv("FB_PAGE_ID")
    token = os.getenv("FB_PAGE_ACCESS_TOKEN")

    if not page_id or not token:
        print("⚠️ Facebook credentials missing.")
        return

    formatted_post = f"{npc}\n\n#DnD #DungeonsAndDragons #FantasyNPC #Roleplay #TavernNPC #AIArt"

    try:
        if image_path:
            print("📸 Uploading photo...")
            url = f"https://graph.facebook.com/{page_id}/photos"
            files = {"source": open(image_path, "rb")}
            data = {"caption": formatted_post.strip(), "access_token": token}
            response = requests.post(url, files=files, data=data)
        else:
            print("📝 Uploading text post...")
            url = f"https://graph.facebook.com/{page_id}/feed"
            data = {"message": formatted_post.strip(), "access_token": token}
            response = requests.post(url, data=data)

        print(f"🔎 Facebook Response: {response.status_code} - {response.text}")

        if response.status_code == 200:
            print("✅ Post successful!")
        else:
            print("❌ Post failed!")

    except Exception as e:
        print("🚨 Facebook Post Error:", e)

# --- Bot Main Job
def job():
    global last_post_time
    print("🕒 Starting job...")

    npc = generate_npc()
    race, char_class = extract_race_and_class(npc)

    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    prompt = f"Portrait of a {race} {char_class} sitting in a medieval tavern, highly detailed, fantasy art, cinematic lighting"
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

# --- Schedule Tasks
def run_scheduler():
    print("📅 Scheduler started...")
    schedule.every().monday.at("10:00").do(job)
    schedule.every().thursday.at("10:00").do(job)
    while True:
        schedule.run_pending()
        time.sleep(30)

# --- Keep Flask Server Alive
def keep_alive():
    t = Thread(target=lambda: app.run(host='0.0.0.0', port=8080))
    t.start()

# --- Main Entry
if __name__ == "__main__":
    keep_alive()
    run_scheduler()
