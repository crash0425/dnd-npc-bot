import os
import time
import json
import random
import requests
import logging
from fpdf import FPDF
from openai import OpenAI
from flask import Flask
from threading import Thread
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2 import service_account
from datetime import datetime
import schedule
import tweepy

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')

VOLUME_FOLDER = "npc_volumes"
SCOPES = ['https://www.googleapis.com/auth/drive.file']
GOOGLE_DRIVE_FOLDER_ID = "17s1RSf0fL2Y6-okaY854bojURv0rGMuF"
CONVERTKIT_LINK = "https://fantasy-npc-forge.kit.com/2aa9c10f01"
ARCHIVE_FILE = "npc_archive.txt"

class PDF(FPDF):
    def header(self):
        self.set_font('Helvetica', 'B', 16)
        self.cell(0, 10, "Fantasy NPC Forge", ln=True)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', '', 8)
        self.cell(0, 10, f"Page {self.page_no()}", align='C')

# Other functions remain unchanged

# Updated post_to_twitter using Tweepy with OAuth1

def post_to_twitter(text):
    logging.info("Attempting to post to Twitter (OAuth1)...")
    try:
        api_key = os.getenv("TWITTER_API_KEY")
        api_secret = os.getenv("TWITTER_API_SECRET")
        access_token = os.getenv("TWITTER_ACCESS_TOKEN")
        access_token_secret = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")

        if not all([api_key, api_secret, access_token, access_token_secret]):
            raise ValueError("One or more Twitter environment variables are missing!")

        auth = tweepy.OAuth1UserHandler(api_key, api_secret, access_token, access_token_secret)
        api = tweepy.API(auth)

        api.update_status(status=text[:280])
        logging.info("✅ Tweet posted successfully!")
    except Exception as e:
        logging.exception("❌ Twitter post failed.")

# Other functions and Flask setup remain unchanged
