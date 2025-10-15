# -*- coding: utf-8 -*-
import os
import time
import threading
import requests
from flask import Flask

# --- Configuration ---
TWITCH_CLIENT_ID = os.environ.get("TWITCH_CLIENT_ID", "<your_client_id>")
TWITCH_CLIENT_SECRET = os.environ.get("TWITCH_CLIENT_SECRET", "<your_client_secret>")
REDEPLOY_URL = os.environ.get("REDEPLOY_URL", "<your_render_redeploy_webhook>")
STREAMERS = ["GranaDyy", "Shengar", "jxliano"]  # your target streamers
CHECK_INTERVAL = 180  # seconds (3 minutes)

# --- Global state ---
ACCESS_TOKEN = None
TOKEN_EXPIRES_AT = 0

# --- Flask setup ---
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Twitch Auto-Redeploy Bot is running!"

def get_access_token():
    """Get an OAuth token from Twitch API."""
    global ACCESS_TOKEN, TOKEN_EXPIRES_AT
    print("🔑 Getting new Twitch access token...")
    url = "https://id.twitch.tv/oauth2/token"
    data = {
        "client_id": TWITCH_CLIENT_ID,
        "client_secret": TWITCH_CLIENT_SECRET,
        "grant_type": "client_credentials",
    }
    response = requests.post(url, data=data).json()
    ACCESS_TOKEN = response["access_token"]
    TOKEN_EXPIRES_AT = time.time() + response["expires_in"] - 60
    print("✅ Got token successfully.")

def check_token():
    """Refresh token if expired."""
    if ACCESS_TOKEN is None or time.time() > TOKEN_EXPIRES_AT:
        get_access_token()

def get_stream_status(user_logins):
    """Check if any of the given Twitch users are live."""
    check_token()
    headers = {
        "Client-ID": TWITCH_CLIENT_ID,
        "Authorization": f"Bearer {ACCESS_TOKEN}",
    }
    url = "https://api.twitch.tv/helix/streams"
    params = [("user_login", name) for name in user_logins]
    response = requests.get(url, headers=headers, params=params).json()
    return [stream["user_login"].lower() for stream in response.get("data", [])]

def trigger_redeploy():
    """Trigger the Render redeploy webhook."""
    print("🚀 Triggering redeploy...")
    res = requests.post(REDEPLOY_URL)
    if res.status_code == 200:
        print("✅ Successfully triggered redeploy!")
    else:
        print(f"⚠️ Redeploy failed: {res.status_code} - {res.text}")

def monitor_streamers():
    """Main background loop checking for live streamers."""
    print("🤖 Twitch Auto-Redeploy Monitor started.")
    live_before = set()

    while True:
        try:
            live_now = set(get_stream_status(STREAMERS))
            if live_now:
                print(f"🎥 Streamers live now: {', '.join(live_now)}")
                # Trigger redeploy only if newly live
                if not live_before:
                    trigger_redeploy()
            else:
                print("📴 No streamers live.")
            live_before = live_now
        except Exception as e:
            print(f"❌ Error checking streams: {e}")
        time.sleep(CHECK_INTERVAL)

# --- Start both Flask and background thread ---
def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    # Start monitoring thread
    threading.Thread(target=monitor_streamers, daemon=True).start()

    # Start Flask web server
    run_flask()

