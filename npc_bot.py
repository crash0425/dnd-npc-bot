import os
import time
import schedule
import requests
import random
import openai
import datetime
from flask import Flask, request, redirect, url_for, render_template_string
from threading import Thread
from dotenv import load_dotenv

load_dotenv()

# --- GLOBALS ---
POST_HISTORY = []
LAST_POST_ID = None

# --- Flask Setup ---
app = Flask(__name__)

HOME_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Fantasy NPC Forge Dashboard</title>
</head>
<body style="font-family: Arial, sans-serif; text-align:center; margin-top:50px;">
    <h1>🛡️ Fantasy NPC Forge Bot</h1>
    <p>Status: ✅ Running</p>
    <p>Last Post: {{ last_post_time }}</p>
    <p>Total Posts: {{ total_posts }}</p>
    <form action="/post-now" method="post">
        <button type="submit" style="font-size:20px;padding:10px 20px;">📤 Post NPC Now</button>
    </form>
    {% if last_post_link %}
    <p><a href="{{ last_post_link }}" target="_blank">View Last Facebook Post</a></p>
    {% endif %}
</body>
</html>
"""

POSTED_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>NPC Posted!</title>
</head>
<body style="font-family: Arial, sans-serif; text-align:center; margin-top:50px;">
    <h1>✅ NPC Posted Successfully!</h1>
    <a href="/">Return to Dashboard</a><br><br>
    {% if last_post_link %}
    <a href="{{ last_post_link }}" target="_blank">View Facebook Post 📄</a>
    {% endif %}
</body>
</html>
"""

@app.route('/')
def home():
    last_post_time = POST_HISTORY[-1] if POST_HISTORY else "Never"
    last_post_link = f"https://www.facebook.com/{LAST_POST_ID}" if LAST_POST_ID else None
    return render_template_string(HOME_PAGE, last_post_time=last_post_time, total_posts=len(POST_HISTORY), last_post_link=last_post_link)

@app.route('/post-now', methods=["POST"])
def post_now():
    job()
    last_post_link = f"https://www.facebook.com/{LAST_POST_ID}" if LAST_POST_ID else None
    return render_template_string(POSTED_PAGE, last_post_link=last_post_link)

def run_web():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_web)
    t.start()

# --- Facebook Posting ---
def post_to_facebook(npc, image_path=None):
    global LAST_POST_ID
    print("🔍 Debug: FB_PAGE_ID =", os.getenv("FB_PAGE_ID"))
    print("🔍 Debug: FB_PAGE_ACCESS_TOKEN present =", bool(os.getenv("FB_PAGE_ACCESS_TOKEN")))
    page_id = os.getenv("FB_PAGE_ID")
    token = os.getenv("FB_PAGE_ACCESS_TOKEN")

    if not page_id or not token:
        print("⚠️ Facebook credentials missing.")
        return

    formatted_post = (
        f"{npc}\n\n"
        "#DnD #DungeonsAndDragons #TabletopRPG #FantasyArt #RPGCharacter "
        "#Roleplay #TavernLife #CharacterArt #TTRPG #FantasyWorld #Adventurer"
    )

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
        print("✅ NPC posted to Facebook successfully!")
        post_id = response.json().get("post_id") or response.json().get("id")
        LAST_POST_ID = post_id
        POST_HISTORY.append(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    else:
        print(f"❌ Facebook Error {response.status_code}: {response.text}")

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

# --- Scheduled Bot Job ---
def job():
    print("🕒 Running bot job...")
    npc = generate_npc()
    race, char_class = extract_race_and_class(npc)
    prompt = f"A detailed fantasy portrait of a {race} {char_class} sitting in a medieval tavern, candlelight, wooden beams, semi-realistic digital art style."
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

# --- Main ---
if __name__ == "__main__":
    keep_alive()
    run_scheduler()
