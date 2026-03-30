import os
from dotenv import load_dotenv
import requests

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def send_alert(message):
    url = f"https://api.telegram.org/bot8656190206:AAGxoy7wEpXIh9TLIe1PM-RW3mSQvj4-97w/sendMessage"

    payload = {
        "chat_id": CHAT_ID,
        "text": message
    }

    try:
        res = requests.post(url, data=payload)
        print("[DEBUG] Telegram response:", res.text)
    except Exception as e:
        print("[ERROR] Telegram failed:", e)
