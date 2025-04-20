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
next_scheduled_time = None
next_scheduled_day = None
VERIFY_TOKEN = os.getenv("FB_VERIFY_TOKEN")

# --- Lore & Trivia
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

# --- Facebook Reactions
REACTIONS = ['LIKE', 'LOVE', 'WOW', 'HAHA']

# --- Home Dashboard
@app.route('/')
def home():
    now = datetime.now()
    uptime = now - bot_start_time
    last_post = last_post_time.strftime("%Y-%m-%d %H:%M:%S") if last_post_time else "Never"

    return f'''
    <html>
    <head><title>🛡️ MasterBot Dashboard</title></head>
    <body style="background-color:#121212;color:white;text-align:center;padding:40px;">
        <h1>🧙‍♂️ MasterBot Pro: Audience Mode</h1>
        <form action="/post-now" method="post">
            <button style="padding:15px;font-size:18px;">🚀 Post New NPC Now</button>
        </form>
        <div style="margin-top:30px;">
            <p><b>🕒 Bot Uptime:</b> {str(uptime).split(".")[0]}</p>
            <p><b>📝 Last NPC Posted:</b> {last_post}</p>
            <p><b>📅 Next Scheduled Post:</b> {next_scheduled_day if next_scheduled_day else "Loading..."} at {next_scheduled_time if next_scheduled_time else "Loading..."}</p>
            <p><b>🌐 Server Status:</b> Online ✅</p>
        </div>
    </body>
    </html>
    '''

# --- Manual Post
@app.route('/post-now', methods=['POST'])
def manual_post():
    Thread(target=job).start()
    return redirect("/")

# --- Facebook Webhook Verification
@app.route('/incoming-message', methods=['GET'])
def verify():
    if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.challenge"):
        if request.args.get("hub.verify_token") == VERIFY_TOKEN:
            return request.args.get("hub.challenge"), 200
        return "Verification token mismatch", 403
    return "Hello world", 200

# --- Facebook Incoming Message (DMs)
@app.route('/incoming-message', methods=['POST'])
def incoming_message():
    data = request.get_json()
    print("📥 Incoming message data:", data)

    if data["object"] == "page":
        for entry in data["entry"]:
            for messaging_event in entry["messaging"]:
                if messaging_event.get("message"):
                    sender_id = messaging_event["sender"]["id"]
                    message_text = messaging_event["message"].get("text")

                    if message_text:
                        npc = generate_custom_npc(message_text)
                        send_message(sender_id, npc)

    return "ok", 200

# --- Save
