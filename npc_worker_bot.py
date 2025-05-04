import os
import time
import logging
from npc_facebook_post import generate_npc, generate_npc_audio, create_npc_video, upload_video_to_drive

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')

def run_worker():
    while True:
        logging.info("🔄 Starting NPC generation cycle")

        # Step 1: Generate NPC
        npc_text = generate_npc()

        # Step 2: Generate audio from NPC text
        generate_npc_audio(npc_text, output_path="npc_audio.mp3")

        # Step 3: Create video from image and audio
        image_path = "npc_image.png"
        if not os.path.exists(image_path):
            logging.error("❌ Image file missing. Please generate 'npc_image.png' first or add image generation logic here.")
            time.sleep(3600)
            continue

        create_npc_video(image_path, "npc_audio.mp3", output_path="npc_tiktok.mp4")

        # Step 4: Upload to Google Drive
        upload_video_to_drive("npc_tiktok.mp4")

        # Wait 1 hour before next run
        logging.info("🕒 Sleeping for 1 hour before next NPC...")
        time.sleep(3600)

if __name__ == "__main__":
    run_worker()
