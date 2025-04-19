import os
import time
import schedule
import requests
import openai
import random
import datetime
from flask import Flask, request, redirect
from threading import Thread
from dotenv import load_dotenv
import gspread

# --- Load Secrets ---
load_dotenv()

# --- Web Server to Keep Bot Alive ---
app = Flask(__name__)

@app.route('/')
def home():
    return '''
    <html>
    <head>
        <title>🛡️ NPC MasterBot Pro</title>
        <style>
            body { font-family: Arial, sans-serif; text-align: center; margin-top: 100px; background-color: #f0f0f5; }
            h1 { font-size: 48px; margin-bottom: 20px; }
            .status { background-color: #4CAF50; color: white; padding: 10px 20px; font-size: 24px; border-radius: 8px; display: inline-block; }
            .post-button { margin-top: 40px; }
            button { font-size: 24px; padding: 15px 30px; border: none; background-color: #007BFF; color: white; border-radius: 10px; cursor: pointer; }
            button:hover { background-color: #0056b3; }
        </style>
    </head>
    <body>
        <h1>🛡️ NPC MasterBot Pro</h1>
        <div class="status">✅ Bot Status: Online</div>
        <div class="post-button">
            <form action="/post-now" method="post">
                <button type="submit">🚀 Post New NPC Now</button>
            </form>
        </div>
    </body>
    </html>
    '''

@app.route('/post-now', methods=['POST'])
def post_now():
    Thread(target=job).start()
    return redirect('/')

def run_web():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_web)
    t.start()


# --- Smart Engagement Comment Templates ---
ENGAGEMENT_TEMPLATES = [
    "🎲 Roll a D20! What do you think this {race} {char_class} would do if you rolled a 1?",
    "🧙‍♂️ As a {char_class}, what secret quest might {name} offer you?",
    "🍻 You're sharing an ale with {name}, the {race} {char_class}. What story do they tell first?",
    "🗡️ Would you trust {name} to have your back in a dungeon crawl?",
    "📜 {name} drops a mysterious map at your feet. Do you pick it up?",
    "🎶 If {name} could sing a ballad, what would it be about?",
    "⚔️ Would you fight alongside {name} against a dragon?",
    "🔮 {name} offers you a prophecy. Do you trust it?",
    "🌟 What magical item do you think {name} secretly carries?",
    "🔥 In a tavern brawl, {name} grabs a {char_class}-specific weapon. What is it?"
]

# --- Generate NPC ---
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

# --- Extract Race and Class ---
def extract_race_and_class(npc_text):
    lines = npc_text.split('\n')
    for line in lines:
        if line.lower().startswith("race & class"):
            parts = line.split(':', 1)
            if len(parts) > 1:
                race_class = parts[1].strip()
                if " " in race_class:
                    return race_class.split(' ', 1)
    return "Human", "Fighter"

# --- Generate DALL·E Image ---
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

# --- Post to Facebook ---
def post_to_facebook(npc, image_path=None):
    page_id = os.getenv("FB_PAGE_ID")
    token = os.getenv("FB_PAGE_ACCESS_TOKEN")

    print(f"🔍 Debug: FB_PAGE_ID = {page_id}")
    print(f"🔍 Debug: FB_PAGE_ACCESS_TOKEN present = {bool(token)}")

    if not page_id or not token:
        print("⚠️ Missing Facebook credentials.")
        return

    formatted_post = (
        f"{npc}\n\n"
        "#DnD #DungeonsAndDragons #TavernTales #FantasyNPC #RPGCharacter "
        "#AdventureAwaits #TTRPG #FantasyArt #CharacterDesign"
    )

    url = f"https://graph.facebook.com/{page_id}/photos"
    files = {"source": open(image_path, "rb")}
    data = {"caption": formatted_post.strip(), "access_token": token}
    response = requests.post(url, files=files, data=data)

    if response.status_code == 200:
        result = response.json()
        post_id = result.get("post_id") or result.get("id")
        print(f"✅ NPC posted to Facebook! (Post ID: {post_id})")
        comment_on_facebook_post(post_id, npc)
        save_to_google_sheets(npc, post_id)
    else:
        print(f"❌ Facebook error: {response.status_code} - {response.text}")

# --- Comment on Facebook Post ---
def comment_on_facebook_post(post_id, npc_text=None):
    page_id = os.getenv("FB_PAGE_ID")
    token = os.getenv("FB_PAGE_ACCESS_TOKEN")

    if not post_id or not token:
        print("⚠️ No post ID or Facebook token found. Skipping comment.")
        return

    # Fallback values
    name, race, char_class = "NPC", "Mysterious", "Adventurer"

    if npc_text:
        lines = npc_text.split('\n')
        for line in lines:
            if line.lower().startswith("name:"):
                name = line.split(':', 1)[1].strip()
            if line.lower().startswith("race & class"):
                rc = line.split(':', 1)[1].strip()
                parts = rc.split(' ', 1)
                if len(parts) == 2:
                    race, char_class = parts

    template = random.choice(ENGAGEMENT_TEMPLATES)
    comment_message = template.format(name=name, race=race, char_class=char_class)

    url = f"https://graph.facebook.com/{post_id}/comments"
    data = {"message": comment_message, "access_token": token}
    response = requests.post(url, data=data)

    if response.status_code == 200:
        print(f"💬 Comment posted successfully!")
    else:
        print(f"❌ Failed to comment: {response.status_code} - {response.text}")

# --- Save to Google Sheets (Optional) ---
def save_to_google_sheets(npc_text, post_id=None):
    try:
        gc = gspread.service_account(filename="credentials.json")
        sh = gc.open_by_key(os.getenv("GOOGLE_SHEET_ID"))
        worksheet = sh.sheet1

        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        worksheet.append_row([now, npc_text, post_id or "N/A"])
        print("📈 NPC logged to Google Sheets!")
    except Exception as e:
        print(f"⚠️ Failed to log to Google Sheets: {e}")

# --- Bot Job ---
def job():
    print("🕒 Running bot job...")
    npc = generate_npc()
    race, char_class = extract_race_and_class(npc)
    prompt = f"A beautiful detailed fantasy portrait of a {race} {char_class} in a medieval tavern, oil painting style, glowing candlelight atmosphere."
    image_path = generate_image(prompt, "npc_image.png")
    post_to_facebook(npc, image_path)

# --- Scheduler ---
def run_scheduler():
    print("📅 Bot scheduler is active...")
    # Smart Posting Times: 11AM + 7PM Eastern
    schedule.every().day.at("15:00").do(job)  # 11 AM EST
    schedule.every().day.at("23:00").do(job)  # 7 PM EST

    while True:
        schedule.run_pending()
        time.sleep(30)

# --- Start MasterBot ---
if __name__ == "__main__":
    keep_alive()
    run_scheduler()
