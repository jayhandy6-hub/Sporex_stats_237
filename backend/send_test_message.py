# backend/send_test_message.py
import os, requests
from datetime import datetime, timezone

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT = os.environ.get("TELEGRAM_CHAT")

def normalize_channel(chat):
    if not chat: return None
    chat = str(chat).strip()
    if chat.startswith("https://t.me/"):
        return "@" + chat.split("https://t.me/")[-1].strip().lstrip("@")
    return chat

def send_test():
    chat = normalize_channel(TELEGRAM_CHAT)
    print("DEBUG: token present?", bool(TELEGRAM_TOKEN))
    print("DEBUG: chat present?", bool(chat))
    if not TELEGRAM_TOKEN or not chat:
        print("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT")
        return
    text = (
        "🔔 *SPOREX STATS — MESSAGE TEST*\n"
        f"_Date_: {datetime.now(timezone.utc).astimezone().strftime('%Y-%m-%d %H:%M %Z')}\n\n"
        "✅ Ceci est un message de test envoyé par @sporex_analysis_bot.\n\n"
        "Si vous voyez ce message, la configuration Telegram est correcte."
    )
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": chat, "text": text, "parse_mode": "Markdown"}
    r = requests.post(url, json=payload, timeout=15)
    print("Status:", r.status_code)
    print("Response:", r.text[:400])

if __name__ == "__main__":
    send_test()
