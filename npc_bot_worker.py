import os
import time
import json
import random
import requests
import logging
import base64
from fpdf import FPDF
from openai import OpenAI
from datetime import datetime
from moviepy.editor import ImageClip, AudioFileClip
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2 import service_account
from google.cloud import texttospeech_v1 as texttospeech
import schedule

# Constants
VOLUME_FOLDER = "npc_volumes"
ARCHIVE_FILE = "npc_archive.txt"
CONVERTKIT_LINK = os.getenv("CONVERTKIT_LINK", "https://fantasy-npc-forge.kit.com/2aa9c10f01")
MAKE_WEBHOOK_URL = "https://hook.us2.make.com/rhwkubxkf96d8fe6ppowtkskxs46i7ei"

# Setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')

# PDF Generator Class
class PDF(FPDF):
    def header(self):
        self.set_font('Helvetica', 'B', 16)
        self.cell(0, 10, "Fantasy NPC Forge", ln=True)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', '', 8)
        self.cell(0, 10, f"Page {self.page_no()}", align='C')

# Convert Google Drive Share Link to Direct Download

def convert_to_direct_drive_link(share_url):
    import re
    match = re.search(r'/d/([a-zA-Z0-9_-]+)', share_url)
    if match:
        file_id = match.group(1)
        return f'https://drive.google.com/uc?export=download&id={file_id}'
    else:
        raise ValueError("Invalid Google Drive share link format.")

# Upload file to Google Drive

def upload_to_drive(filepath, mimetype):
    logging.info("Uploading file to Google Drive...")
    credentials_json = os.getenv("GOOGLE_CREDENTIALS")
    folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")

    if not credentials_json or not folder_id:
        logging.error("Missing GOOGLE_CREDENTIALS or GOOGLE_DRIVE_FOLDER_ID.")
        return

    try:
        credentials_info = json.loads(credentials_json)
        if isinstance(credentials_info, str):
            credentials_info = json.loads(credentials_info)
    except json.JSONDecodeError as e:
        logging.error(f"Failed to decode GOOGLE_CREDENTIALS: {e}")
        return

    credentials = service_account.Credentials.from_service_account_info(credentials_info)
    service = build("drive", "v3", credentials=credentials)

    file_metadata = {
        "name": os.path.basename(filepath),
        "parents": [folder_id]
    }
    media = MediaFileUpload(filepath, mimetype=mimetype)
    uploaded = service.files().create(body=file_metadata, media_body=media, fields="id, webViewLink").execute()
    public_url = uploaded.get("webViewLink")
    logging.info(f"\U0001F4C1 File uploaded to Google Drive: {public_url}")
    direct_url = convert_to_direct_drive_link(public_url)
    logging.info(f"\U0001F517 Direct download URL: {direct_url}")
    return direct_url

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

# Generate Audio with Google Cloud Text-to-Speech
def generate_npc_audio(text, output_path="npc_audio.mp3"):
    try:
        logging.info("\U0001F3A4 Using Google Cloud TTS...")
        credentials_json = os.getenv("GOOGLE_CREDENTIALS")
        if not credentials_json:
            raise ValueError("Missing GOOGLE_CREDENTIALS")

        if isinstance(credentials_json, str):
            try:
                credentials_info = json.loads(credentials_json)
                if not isinstance(credentials_info, dict):
                    raise ValueError("Parsed GOOGLE_CREDENTIALS is not a dict")
            except json.JSONDecodeError:
                raise ValueError("GOOGLE_CREDENTIALS is not valid JSON")
        else:
            raise ValueError("GOOGLE_CREDENTIALS must be a JSON string")

        required_keys = {"type", "private_key", "client_email", "token_uri"}
        if not required_keys.issubset(credentials_info.keys()):
            raise ValueError(f"GOOGLE_CREDENTIALS missing keys: {required_keys - credentials_info.keys()}")

        credentials = service_account.Credentials.from_service_account_info(credentials_info)
        client = texttospeech.TextToSpeechClient(credentials=credentials)

        synthesis_input = texttospeech.SynthesisInput(text=text)
        voice = texttospeech.VoiceSelectionParams(
            language_code="en-GB",
            name="en-GB-Wavenet-B"
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            pitch=2.0,
            speaking_rate=0.92,
            volume_gain_db=3.0
        )

        response = client.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)
        with open(output_path, "wb") as out:
            out.write(response.audio_content)
        logging.info(f"\U0001F5E3️ Audio saved to {output_path} (via Google Cloud TTS)")
    except Exception as e:
        logging.error(f"❌ Google Cloud TTS failed: {e}")

# Generate Video
def create_npc_video(image_path, audio_path, output_path="npc_tiktok.mp4"):
    logging.info("\U0001F39E️ Creating video clip...")
    try:
        clip = ImageClip(image_path).set_duration(10).resize(height=720)
        audio = AudioFileClip(audio_path)
        clip = clip.set_audio(audio)
        clip.write_videofile(output_path, fps=12, codec="libx264", audio_codec="aac", preset="ultrafast", threads=2, logger=None)
        logging.info(f"✅ Video written to {output_path}")
    except Exception as e:
        logging.error(f"❌ Error creating video: {e}")

# Post image and caption to Facebook via Make webhook
def post_to_facebook_image(caption, image_url):
    logging.info("\U0001F4E4 Posting to Facebook via Make webhook...")
    try:
        payload = {
            "caption": caption,
            "image_url": image_url
        }
        headers = {"Content-Type": "application/json"}
        response = requests.post(MAKE_WEBHOOK_URL, data=json.dumps(payload), headers=headers)
        response.raise_for_status()
        logging.info("✅ Facebook image post triggered successfully")
    except Exception as e:
        logging.error(f"❌ Failed to post to Facebook: {e}")

# Background Worker Logic
def run_worker():
    logging.info("\U0001F501 Running scheduled NPC workflow")
    npc_text = generate_npc()

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    image_prompt = "Fantasy portrait of a unique tavern NPC, cinematic lighting, richly detailed, fantasy art style"
    image_response = client.images.generate(model="dall-e-3", prompt=image_prompt, n=1, size="1024x1024")
    image_url = image_response.data[0].url
    image_path = "npc_image.png"
    img_data = requests.get(image_url).content
    with open(image_path, "wb") as handler:
        handler.write(img_data)

    generate_npc_audio(npc_text, output_path="npc_audio.mp3")
    create_npc_video("npc_image.png", "npc_audio.mp3", output_path="npc_tiktok.mp4")
    video_url = upload_to_drive("npc_tiktok.mp4", "video/mp4")
    image_drive_url = upload_to_drive("npc_image.png", "image/png")

    caption = f"""\U0001F4D8 Here's your latest NPC!
Download the full volume at {CONVERTKIT_LINK}
#dnd #ttrpg #fantasy #npc"""
    post_to_facebook_image(caption, image_drive_url)
    logging.info("\U0001F389 Worker completed successfully")

# Trigger for manual testing or scheduled run
def schedule_worker():
    schedule.every().sunday.at("10:00").do(run_worker)
    schedule.every().wednesday.at("10:00").do(run_worker)
    while True:
        schedule.run_pending()
        time.sleep(60)

    if __name__ == "__main__":
    schedule_worker()

