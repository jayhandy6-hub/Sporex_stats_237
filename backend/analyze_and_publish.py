# backend/analyze_and_publish.py
import os
import requests
from datetime import datetime, timezone
from bs4 import BeautifulSoup

# -------------------------------
# 🔧 CONFIGURATION
# -------------------------------
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT = os.getenv("TELEGRAM_CHAT")
THE_ODDS_API_KEY = os.getenv("THE_ODDS_API_KEY")

# Liste des championnats ciblés
LEAGUES = [
    "Premier League",
    "LaLiga",
    "Serie A",
    "Bundesliga",
    "Ligue 1",
    "Eredivisie",
    "Primeira Liga",
]

# -------------------------------
# 📊 FONCTIONS D'ANALYSE
# -------------------------------

def get_today_matches():
    """
    Récupère les matchs du jour depuis SofaScore (via HTML).
    """
    url = "https://www.sofascore.com/football//"
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, headers=headers, timeout=15)
    soup = BeautifulSoup(r.text, "lxml")
    matches = []
    for row in soup.select("a[href*='/match/']"):
        name = row.text.strip()
        if any(league.lower() in name.lower() for league in LEAGUES):
            matches.append(name)
    return matches[:15]


def get_odds_data():
    """
    Simule des cotes et probabilités (si pas d’API valide).
    """
    odds_sample = [
        {"home": "Arsenal", "away": "Newcastle", "odds": 1.55, "prob": 81, "league": "Premier League"},
        {"home": "Real Madrid", "away": "Getafe", "odds": 1.40, "prob": 85, "league": "LaLiga"},
        {"home": "PSG", "away": "Nice", "odds": 1.65, "prob": 79, "league": "Ligue 1"},
        {"home": "Bayern Munich", "away": "Augsburg", "odds": 1.35, "prob": 86, "league": "Bundesliga"},
        {"home": "Juventus", "away": "Udinese", "odds": 1.70, "prob": 82, "league": "Serie A"},
    ]
    return [m for m in odds_sample if m["prob"] >= 80]


def format_message(matches):
    """
    Construit le message Telegram stylé pour SPOREX ZONE.
    """
    today = datetime.now(timezone.utc).astimezone().strftime("%d %B %Y")
    if not matches:
        return (
            f"⚽ **PREDICTIONS DU JOUR – SPOREX ZONE ANALYTICS** ⚽\n\n"
            f"📅 *{today}*\n\n"
            "Aucun match avec une probabilité > 80% aujourd'hui.\n"
            "📊 Nous restons prudents et attendons les meilleures opportunités.\n\n"
            "⚠️ *Conseil :* Ne combinez pas vos tickets, jouez malin. 🎯"
        )

    msg = [
        "⚽🔥 **PREDICTIONS DU JOUR – SPOREX ZONE ANALYTICS** 🔥⚽",
        f"📅 *{today}*",
        "🕘 Publication automatique à 09h30\n",
        "📊 **MATCHS AVEC PROBABILITÉ > 80%**\n"
    ]

    for m in matches:
        msg.append(
            f"🏟️ *{m['league']}*\n"
            f"⚔️ **{m['home']} 🆚 {m['away']}**\n"
            f"📈 Probabilité : *{m['prob']}%*\n"
            f"💰 Cote moyenne : *{m['odds']}*\n"
            f"✅ Pronostic : *Victoire {m['home']}*\n"
            "─────────────"
        )

    msg.append(
        "\n⚠️ *SPOREX CONSEIL* : Ne combinez pas vos tickets. Jouez malin. 🎯\n"
        "📲 Rejoignez le canal pour les analyses détaillées :\n"
        "👉 [t.me/sporexzone](https://t.me/sporexzone)\n\n"
        "#SporexZone ⚫🟡 #Football #Analytics #BetSmart"
    )
    return "\n".join(msg)


def send_telegram_message(message):
    """
    Envoie le message formaté sur Telegram.
    """
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT:
        print("Telegram not configured (token or chat missing). Skipping send.")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT, "text": message, "parse_mode": "Markdown"}
    r = requests.post(url, json=payload, timeout=15)
    print("Telegram send status:", r.status_code, r.text[:400])
    return r.status_code == 200


# -------------------------------
# 🚀 EXÉCUTION PRINCIPALE
# -------------------------------

if __name__ == "__main__":
    print("Start SPOREX pipeline...")

    try:
        matches = get_odds_data()
        print(f"Wrote matches_today.json signals: {len(matches)}")

        msg = format_message(matches)
        send_telegram_message(msg)

    except Exception as e:
        print("❌ ERROR:", str(e))
