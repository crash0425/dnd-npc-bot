import os
import json
import logging
import requests
from moviepy.editor import ImageClip, AudioFileClip

def generate_npc_audio(npc_text, output_path="npc_audio.mp3"):
    eleven_api_key = os.getenv("ELEVENLABS_API_KEY")
    voice_id = os.getenv("ELEVENLABS_VOICE_ID", "Rachel")

    headers = {
        "xi-api-key": eleven_api_key,
        "Content-Type": "application/json"
    }

    payload = {
        "model_id": "eleven_multilingual_v2",
        "text": npc_text,
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75
        }
    }

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    response = requests.post(url, headers=headers, json=payload)

    if response.status_code == 200:
        with open(output_path, "wb") as f:
            f.write(response.content)
        logging.info(f"🗣️ Audio saved to: {output_path}")
        return output_path
    else:
        logging.error(f"❌ ElevenLabs TTS failed: {response.status_code} {response.text}")
        return None

def create_npc_video(image_path, audio_path, output_path="npc_tiktok.mp4"):
    clip = ImageClip(image_path).set_duration(30).set_fps(1).resize(height=1920).set_position("center")
    audio = AudioFileClip(audio_path)
    video = clip.set_audio(audio).set_duration(audio.duration)
    video.write_videofile(output_path, fps=24)
    logging.info(f"📼 Video saved to: {output_path}")

    # Upload to Google Drive
    credentials_json = os.getenv("GOOGLE_CREDENTIALS")
    folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
    logging.info(f"Drive upload vars - Credentials present: {bool(credentials_json)}, Folder ID: {folder_id}")
    if credentials_json and folder_id:
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
        from google.oauth2 import service_account

        credentials_info = json.loads(credentials_json)
        credentials = service_account.Credentials.from_service_account_info(credentials_info)
        service = build("drive", "v3", credentials=credentials)

        file_metadata = {
            "name": os.path.basename(output_path),
            "parents": [folder_id]
        }
        media = MediaFileUpload(output_path, mimetype="video/mp4")
        uploaded = service.files().create(body=file_metadata, media_body=media, fields="id, webViewLink").execute()
        if uploaded:
            logging.info(f"📤 Video uploaded to Google Drive: {uploaded.get('webViewLink')}")
        else:
            logging.warning("⚠️ Google Drive upload returned no data.")
