# backend/random_post.py
import os, random, json, requests, sys
from datetime import datetime

# Config from env
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT = os.getenv("TELEGRAM_CHAT")   # -100... or @channel
CONTENT_FILE = "backend/sporex_content.json"
USED_FILE = "backend/used_messages.json"

# Load local content file
def load_content():
    try:
        with open(CONTENT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"messages": []}

# Used messages handling
def load_used():
    try:
        with open(USED_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_used(used):
    with open(USED_FILE, "w", encoding="utf-8") as f:
        json.dump(used, f, ensure_ascii=False, indent=2)

# Get external quote (fallback)
def get_quote():
    try:
        r = requests.get("https://api.quotable.io/random", timeout=8)
        if r.status_code == 200:
            j = r.json()
            return f"💬 «{j.get('content')}» — {j.get('author')}"
    except Exception:
        pass
    return None

# Normalize chat parameter
def normalize_chat(chat):
    if not chat:
        return None
    chat = str(chat).strip()
    if chat.startswith("https://t.me/"):
        return "@" + chat.split("https://t.me/")[-1].strip().lstrip("@")
    return chat

# Choose a unique message (no repetition until all used)
def choose_message(content):
    all_msgs = content.get("messages", [])
    used = load_used()
    available = [m for m in all_msgs if m not in used]
    if not available:
        # reset used
        used = []
        available = all_msgs.copy()
    # occasional quote insertion
    if random.random() < content.get("quote_chance", 0.25):
        quote = get_quote()
        if quote:
            chosen = quote
            # do not add quote to used list (external)
            print("Chosen external quote.")
            return chosen, used, False
    chosen = random.choice(available) if available else None
    if chosen:
        used.append(chosen)
    save_used(used)
    return chosen, used, True

# Send to Telegram
def send_telegram(text, token, chat):
    if not token or not chat:
        print("Missing token or chat")
        return False, "Missing token/chat"
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat, "text": text, "parse_mode": "Markdown", "disable_web_page_preview": True}
    try:
        r = requests.post(url, json=payload, timeout=15)
        return (r.status_code == 200), r.text
    except Exception as e:
        return False, str(e)

def main():
    content = load_content()
    if not content.get("messages"):
        print("No messages found in content file.")
        sys.exit(1)

    msg, used, added_to_used = choose_message(content)
    if not msg:
        print("No message chosen.")
        sys.exit(1)

    # optionally add a timestamp or signature
    now = datetime.utcnow().strftime("%d/%m %H:%M UTC")
    text = f"{msg}\n\n🕘 {now} • #SPOREXZONE"

    chat = normalize_chat(TELEGRAM_CHAT)
    ok, resp = send_telegram(text, TELEGRAM_TOKEN, chat)
    print("Send ok?", ok)
    print("Response:", resp)
    # exit code indicates success/fail
    sys.exit(0 if ok else 2)

if __name__ == "__main__":
    main()
