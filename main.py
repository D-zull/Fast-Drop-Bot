import os
import time
import requests
import threading
from yt_dlp import YoutubeDL

TOKEN = '7257872826:AAGL-kldZgVNA4yoyRtbl9iy8F_3K1EA2aU'
API_URL = f'https://api.telegram.org/bot{TOKEN}'
DOWNLOAD_DIR = 'downloads'
USERS_FILE = 'users.txt'

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

ydl_opts = {
    'outtmpl': os.path.join(DOWNLOAD_DIR, '%(title).30s.%(ext)s'),
    'format': 'bestvideo+bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'no_warnings': True,
}

# --- Logging user ID ---

def save_user(chat_id):
    try:
        with open(USERS_FILE, "a") as f:
            f.write(f"{chat_id}\n")
    except Exception as e:
        print(f"[!] Failed to save user: {e}")

def deduplicate_users():
    try:
        with open(USERS_FILE, "r") as f:
            users = set(f.read().splitlines())
        with open(USERS_FILE, "w") as f:
            for user in users:
                f.write(user + "\n")
    except FileNotFoundError:
        pass

# --- Telegram API ---

def get_updates(offset=None):
    params = {'timeout': 30, 'offset': offset}
    response = requests.get(f'{API_URL}/getUpdates', params=params)
    return response.json().get('result', [])

def send_message(chat_id, text):
    requests.post(f'{API_URL}/sendMessage', data={'chat_id': chat_id, 'text': text})

def send_video(chat_id, filepath):
    with open(filepath, 'rb') as f:
        requests.post(f'{API_URL}/sendVideo', files={'video': f}, data={'chat_id': chat_id})

# --- Video Download ---

def download_video(url):
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return ydl.prepare_filename(info)
    except Exception as e:
        print(f"[!] Download failed: {e}")
        return None

# --- Bot Logic ---

def process_message(message):
    chat_id = message['chat']['id']
    save_user(chat_id)  # Simpan ID user

    if 'text' not in message:
        send_message(chat_id, "Send me link from Instagram, TikTok, Twitter, or YouTube.")
        return

    url = message['text'].strip()
    if not any(domain in url for domain in ["instagram.com", "tiktok.com", "twitter.com", "youtu"]):
        send_message(chat_id, "Send me link from Instagram, TikTok, Twitter, or YouTube.")
        return

    threading.Thread(target=handle_download, args=(chat_id, url)).start()

def handle_download(chat_id, url):
    send_message(chat_id, "Downloading...")

    filepath = download_video(url)

    if filepath and os.path.exists(filepath):
        try:
            send_video(chat_id, filepath)
            send_message(chat_id, "Here is your video.")
        except Exception as e:
            send_message(chat_id, "Failed to send video.")
            print(f"[!] Sending error: {e}")
    else:
        send_message(chat_id, "Failed to download.")

# --- Main Loop ---

def main():
    deduplicate_users()
    print("[*] Bot is running...")
    last_update_id = None

    while True:
        updates = get_updates(last_update_id)
        for update in updates:
            last_update_id = update['update_id'] + 1
            if 'message' in update:
                process_message(update['message'])

        time.sleep(1)

if __name__ == '__main__':
    main()
