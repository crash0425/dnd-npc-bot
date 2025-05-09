from flask import Flask
import os
import requests
from npc_bot_worker import post_to_facebook_image

app = Flask(__name__)

@app.route("/")
def home():
    return "🧙‍♂️ Fantasy NPC Forge Web Service is live!"

@app.route("/test-facebook", methods=["GET"])
def test_facebook_post():
    caption = "📘 This is a test Facebook image post from the Render web service!"
    image_path = "npc_image.png"

    if not os.path.exists(image_path):
        # Download a placeholder image to simulate a generated one
        placeholder_url = "https://via.placeholder.com/1024"
        img_data = requests.get(placeholder_url).content
        with open(image_path, "wb") as f:
            f.write(img_data)

    post_to_facebook_image(caption, image_path)
    return "✅ Facebook post test triggered!"

# Needed by gunicorn to find the app
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
