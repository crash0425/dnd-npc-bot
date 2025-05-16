import os, time, json, requests, logging
from openai import OpenAI
from moviepy.editor import ImageClip, AudioFileClip
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2 import service_account
from google.cloud import texttospeech_v1 as texttospeech

CONVERTKIT_LINK = os.getenv("CONVERTKIT_LINK", "https://fantasy-npc-forge.kit.com/2aa9c10f01")
MAKE_WEBHOOK_URL = "https://hook.us2.make.com/rhwkubxkf96d8fe6ppowtkskxs46i7ei"

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')

# Upload to Google Drive and make public
def upload_to_drive(filepath):
    creds = json.loads(os.getenv("GOOGLE_CREDENTIALS"))
    folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
    service = build("drive", "v3", credentials=service_account.Credentials.from_service_account_info(creds))
    file_metadata = {"name": os.path.basename(filepath), "parents": [folder_id]}
    media = MediaFileUpload(filepath, mimetype="video/mp4")
    file = service.files().create(body=file_metadata, media_body=media, fields="id").execute()
    service.permissions().create(fileId=file["id"], body={"type": "anyone", "role": "reader"}).execute()
    return f"https://drive.google.com/uc?export=download&id={file['id']}"

# Generate NPC text

def generate_npc():
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    res = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a fantasy NPC generator for Dungeons & Dragons."},
            {"role": "user", "content": "Generate a detailed NPC with Name, Race & Class, Personality, Quirks, Backstory, Ideal, Bond, Flaw."}
        ]
    )
    return res.choices[0].message.content

# Text-to-speech

def generate_audio(text, out="npc_audio.mp3"):
    creds = json.loads(os.getenv("GOOGLE_CREDENTIALS"))
    client = texttospeech.TextToSpeechClient(credentials=service_account.Credentials.from_service_account_info(creds))
    response = client.synthesize_speech(
        input=texttospeech.SynthesisInput(text=text),
        voice=texttospeech.VoiceSelectionParams(language_code="en-GB", name="en-GB-Wavenet-B"),
        audio_config=texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3, pitch=2.0, speaking_rate=0.92, volume_gain_db=3.0)
    )
    with open(out, "wb") as f: f.write(response.audio_content)

# Image + audio to video

def create_video(image_path, audio_path, out="npc_tiktok.mp4"):
    audio = AudioFileClip(audio_path)
    clip = ImageClip(image_path).set_duration(min(audio.duration, 25)).resize(width=640).set_audio(audio)
    clip.write_videofile(out, fps=15, codec="libx264", audio_codec="aac", preset="ultrafast", threads=2, bitrate="300k", ffmpeg_params=["-pix_fmt", "yuv420p"])

# Post to Make webhook

def post_to_make(caption, url):
    logging.info("✅ NPC video posted and workflow complete.")
    requests.post(MAKE_WEBHOOK_URL, json={"caption": caption, "video_url": url})

# Main flow

def run_worker():
    full_npc = generate_npc()
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    lines = full_npc.splitlines()
    race_class = lines[1].split(':', 1)[-1].strip().replace("**", "").replace('[', '').replace(']', '').replace('—', '').strip()
    description = lines[2].split(':', 1)[-1].strip().replace("**", "").replace('[', '').replace(']', '').replace('—', '').lower()
    gender_keywords = ["she", "her", "woman", "female"] if any(w in description for w in ["she", "her"]) else ["he", "him", "man", "male"] if any(w in description for w in ["he", "him"]) else []
    gender_text = "female" if any(g in gender_keywords for g in ["she", "her", "woman", "female"]) else "male" if any(g in gender_keywords for g in ["he", "him", "man", "male"]) else "person"
    backstory_line = next((line for line in lines if line.lower().startswith("backstory")), full_npc)
    backstory_line = backstory_line.replace("Backstory:", "").strip().replace('"', '').replace("'", "").replace('[', '').replace(']', '').replace('—', '')
    backstory_line = (backstory_line[:100] + "...") if len(backstory_line) > 100 else backstory_line
    backstory_clean = backstory_line.replace("Backstory:", "").strip().replace('"', '').replace("'", "").replace('[', '').replace(']', '').replace('—', '')
    backstory_clean = (backstory_clean[:100] + "...") if len(backstory_clean) > 100 else backstory_clean
    prompt = f"Portrait of a {gender_text} {race_class}, {backstory_clean.lower()}, fantasy art, richly detailed, cinematic lighting"
    img_url = client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        n=1,
        size="1024x1024"
    ).data[0].url
    with open("npc_image.png", "wb") as f: f.write(requests.get(img_url).content)
    backstory_line = next((line for line in lines if line.lower().startswith("backstory")), full_npc)
    generate_audio(backstory_line)
    create_video("npc_image.png", "npc_audio.mp3")
    url = upload_to_drive("npc_tiktok.mp4")
    caption = f"""📖 {backstory_line}
Download the full volume at [fantasy-npc-forge.kit.com](https://fantasy-npc-forge.kit.com/2aa9c10f01)
Want more NPCs like this? Follow us and grab Volume 1 for free!
#dnd #ttrpg #npc #backstory"""
    post_to_make(caption, url)

if __name__ == "__main__":
    if os.getenv("MODE", "run") == "schedule":
        import schedule
        schedule.every().sunday.at("10:00").do(run_worker)
        schedule.every().wednesday.at("10:00").do(run_worker)
        while True:
            schedule.run_pending()
            time.sleep(60)
    else:
        run_worker()
