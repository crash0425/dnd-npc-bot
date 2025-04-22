import os
import requests

PAGE_ACCESS_TOKEN = os.getenv("FB_PAGE_ACCESS_TOKEN")

def post_to_facebook(image_path, message):
    url = f"https://graph.facebook.com/v19.0/me/photos"
    payload = {
        "caption": message,
        "access_token": PAGE_ACCESS_TOKEN
    }
    files = {
        "source": open(image_path, "rb")
    }
    response = requests.post(url, data=payload, files=files)
    
    if response.status_code == 200:
        print("✅ Successfully posted to Facebook!")
    else:
        print(f"❌ Failed to post to Facebook: {response.text}")
