import os
import time
import json
import random
import requests
import logging
from flask import Flask
from fpdf import FPDF
from openai import OpenAI
from datetime import datetime
import schedule
from moviepy.editor import ImageClip, AudioFileClip, CompositeVideoClip
from elevenlabs.client import ElevenLabs

# Constants
VOLUME_FOLDER = "npc_volumes"
ARCHIVE_FILE = "npc_archive.txt"
CONVERTKIT_LINK = os.getenv("CONVERTKIT_LINK", "https://fantasy-npc-forge.kit.com/2aa9c10f01")

# Setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')
app = Flask(__name__)

# PDF Generator Class
class PDF(FPDF):
    def header(self):
        self.set_font('Helvetica', 'B', 16)
        self.cell(0, 10, "Fantasy NPC Forge", ln=True)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', '', 8)
        self.cell(0, 10, f"Page {self.page_no()}", align='C')

# Upload video to Google Drive

def upload_video_to_drive(filepath):
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from google.oauth2 import service_account

    logging.info("Uploading video to Google Drive...")
    credentials_json = os.getenv("GOOGLE_CREDENTIALS")
    folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")

    if not credentials_json or not folder_id:
        logging.error("Missing GOOGLE_CREDENTIALS or GOOGLE_DRIVE_FOLDER_ID.")
        return

    credentials_info = json.loads(credentials_json)
    credentials = service_account.Credentials.from_service_account_info(credentials_info)
    service = build("drive", "v3", credentials=credentials)

    file_metadata = {
        "name": os.path.basename(filepath),
        "parents": [folder_id]
    }
    media = MediaFileUpload(filepath, mimetype="video/mp4")
    uploaded = service.files().create(body=file_metadata, media_body=media, fields="id, webViewLink").execute()
    logging.info(f"🎬 Video uploaded to Google Drive: {uploaded.get('webViewLink')}")

# Generate NPC

def generate_npc():
    logging.info("Calling OpenAI to generate NPC...")
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a fantasy NPC generator for a Dungeons & Dragons campaign."},
            {"role": "user", "content": "Generate a detailed NPC with the following fields: Name, Race & Class, Personality, Quirks, Backstory, Ideal, Bond, Flaw. Format with line breaks and labels."}
        ],
        temperature=0.8
    )
    npc_text = response.choices[0].message.content
    logging.info(f"Generated NPC: {npc_text}")
    if not os.path.exists(ARCHIVE_FILE):
        with open(ARCHIVE_FILE, "w"): pass
    with open(ARCHIVE_FILE, "a") as f:
        f.write(npc_text + "\n---\n")
    return npc_text

# Generate Audio with ElevenLabs

def generate_npc_audio(text, output_path="npc_audio.mp3"):
    client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))
    audio = client.text_to_speech.convert(
        voice_id="21m00Tcm4TlvDq8ikWAM",
        model_id="eleven_monolingual_v1",
        text=text
    )
    with open(output_path, "wb") as f:
        f.write(audio)
    logging.info(f"🗣️ Audio saved to {output_path}")

# Generate Video

def create_npc_video(image_path, audio_path, output_path="npc_tiktok.mp4"):
    logging.info("🎞️ Creating video clip...")
    try:
        clip = ImageClip(image_path).set_duration(10).resize(height=720)
        audio = AudioFileClip(audio_path)
        clip = clip.set_audio(audio)
        clip.write_videofile(output_path, fps=12, codec="libx264", audio_codec="aac", preset="ultrafast", threads=2, logger=None)
        logging.info(f"✅ Video written to {output_path}")
    except Exception as e:
        logging.error(f"❌ Error creating video: {e}")

@app.route('/')
def home():
    return "✅ Bot is running"

@app.route('/test-video')
def test_video_flow():
    npc_text = generate_npc()

    # Generate image and save locally
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    image_prompt = "Fantasy portrait of a unique tavern NPC, cinematic lighting, richly detailed, fantasy art style"
    image_response = client.images.generate(model="dall-e-3", prompt=image_prompt, n=1, size="1024x1024")
    image_url = image_response.data[0].url

    image_path = "npc_image.png"
    img_data = requests.get(image_url).content
    with open(image_path, "wb") as handler:
        handler.write(img_data)

    audio_path = "npc_audio.mp3"
    video_path = "npc_tiktok.mp4"

    generate_npc_audio(npc_text, output_path=audio_path)
    create_npc_video(image_path=image_path, audio_path=audio_path, output_path=video_path)
    upload_video_to_drive(video_path)

    return "🎥 Video generation and upload triggered!"

# Start Flask app (Render-friendly)
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
