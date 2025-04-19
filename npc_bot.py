import os
import time
import schedule
import requests
import random
from flask import Flask, request, redirect
from threading import Thread
from dotenv import load_dotenv
import openai

# --- Load environment variables
load_dotenv()

# --- Flask server (for uptime)
@app.route('/')
def home():
    return '''
    <h1>🧙‍♂️ NPC Bot is Alive!</h1>
    <form action="/post-now" method="post">
        <button type="submit">🚀 Post Now</button>
    </form>
    '''

@app.route('/post-now', methods=['POST'])
def manual_post():
    Thread(target=job).start()
    return redirect("/")

# --- Helper: Extract Race and Class from NPC
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

# --- Main Bot Job
def job():
    print("🕒 Running bot job...")

    # 1. Generate NPC
    npc = generate_npc()

    # 2. Extract for better image prompt
    race, char_class = extract_race_and_class(npc)

    # 3. Generate DALL-E Image
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    prompt = f"Portrait of a {race} {char_class} inside a fantasy tavern, detailed, cinematic lighting, digital painting"
    response = client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        n=1,
        size="1024x1024"
    )
    image_url = response.data[0].url

    # 4. Download Image
    image_data = requests.get(image_url).content
    image_path = "npc_image.png"
    with open(image_path, "wb") as f:
        f.write(image_data)

    # 5. Post to Facebook
    post_to_facebook(npc, image_path)

# --- Schedule Posts
def run_scheduler():
    print("📅 Bot scheduler is active...")
    schedule.every().monday.at("10:00").do(job)
    schedule.every().thursday.at("10:00").do(job)

    while True:
        schedule.run_pending()
        time.sleep(30)

# --- Main Start
if __name__ == "__main__":
    keep_alive()
    run_scheduler()
