from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import os

# --- CONFIG ---
CREDENTIALS_FILE = "credentials.json"  # your downloaded Google API key
FOLDER_ID = "17s1RSf0fL2Y6-okaY854bojURv0rGMuF"  # Replace with your Drive folder ID

def upload_to_drive(file_path):
    """Uploads a file to Google Drive and returns the shareable link."""
    credentials = service_account.Credentials.from_service_account_file(
        CREDENTIALS_FILE,
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
