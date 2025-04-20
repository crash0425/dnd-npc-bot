import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# --- CONFIG ---
FOLDER_ID = "YOUR_GOOGLE_DRIVE_FOLDER_ID_HERE"  # Replace with your real Drive folder ID

def upload_to_drive(file_path):
    """Uploads a file to Google Drive and returns the shareable link."""
    
    # Load credentials from environment variable
    credentials_json = os.getenv('GOOGLE_CREDENTIALS')
    if not credentials_json:
        raise Exception("GOOGLE_CREDENTIALS environment variable not found!")
    
    credentials_info = json.loads(credentials_json)
    credentials = service_account.Credentials.from_service_account_info(
        credentials_info,
        scopes=["https://www.googleapis.com/auth/drive"]
    )

    service = build('drive', 'v3', credentials=credentials)

    file_metadata = {
        'name': os.path.basename(file_path),
        'parents': [FOLDER_ID]
    }
    media = MediaFileUpload(file_path, mimetype='application/pdf')

    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id'
    ).execute()

    file_id = file.get('id')
    shareable_link = f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"

    print(f"✅ Uploaded to Google Drive! Link: {shareable_link}")
    return shareable_link
