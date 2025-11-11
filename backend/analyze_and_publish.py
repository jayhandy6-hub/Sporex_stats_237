# backend/analyze_and_publish.py
# SPOREX STATS - analyse complète & publication Telegram (version finale prototype)
# Requirements: requests, beautifulsoup4, lxml
# Env secrets expected:
# - TELEGRAM_BOT_TOKEN
# - TELEGRAM_CHAT        (ex: -1001234567890  ou @sporexzone)
# - THE_ODDS_API_KEY     (optional, recommended)
# - GIT_EMAIL, GIT_NAME  (optional for commits)

import os, json, math, time, requests
from datetime import datetime, timezone
from bs4 import BeautifulSoup

MIN_PROB = 0.80
OUTFILE = "matches_today.json"
ODDS_API_KEY = os.environ.get("THE_ODDS_API_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT = os.environ.get("TELEGRAM_CHAT")  # -100... or @channel
TIMEZONE_LABEL = "Africa/Douala"

# Le mapping des ligues qu'on surveille
SPORT_KEYS = {
    "Premier League": "soccer_epl",
    "LaLiga": "soccer_spain_la_liga",
    "Serie A": "soccer_italy_serie_a",
    "Bundesliga": "soccer_germany_bundesliga",
    "Ligue 1": "soccer_france_ligue_one",
    "Primeira Liga": "soccer_portugal_primeira_liga",
    "Eredivisie": "soccer_netherlands_eredivisie"
}

SOFASCORE_BASE = "https://www.sofascore.com"

# ---------- helpers ----------
def decimal_to_prob(o):
    try:
        return 1.0 / float(o)
    except Exception:
        return None

def normalize_channel(chat):
    if not chat: return None
    chat = str(chat).strip()
    if chat.startswith("https://t.me/"):
        return "@" + chat.split("https://t.me/")[-1].strip().lstrip("@")
    return chat

# ---------- SofaScore light scraper ----------
def get_team_summary(team_name):
    # Best effort; structure SofaScore peut changer — en prod utiliser une API officielle
    try:
        q = team_name.replace(" ", "%20")
        search_url = f"{SOFASCORE_BASE}/search/teams?q={q}"
        r = requests.get(search_url, timeout=10)
        if r.status_code != 200:
            return {}
        soup = BeautifulSoup(r.text, "lxml")
        a = soup.find("a", href=True)
        if not a:
            return {}
        team_path = a['href']
        r2 = requests.get(SOFASCORE_BASE + team_path, timeout=10)
        if r2.status_code != 200:
            return {}
        s2 = BeautifulSoup(r2.text, "lxml")
        # Prototype: valeurs par défaut. Tu peux améliorer en ciblant les sélecteurs CSS réels.
        return {
            "last5_wins": 2,
            "last5_draws": 1,
            "last5_losses": 2,
            "avg_rating": 6.9,
            "goals_for_last5": 6,
            "goals_against_last5": 4
        }
    except Exception as e:
        print("SofaScore error for", team_name, e)
        return {}

# ---------- Odds fetching ----------
def fetch_odds_for_sport(sport_key):
    if not ODDS_API_KEY:
        return []
    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds"
    params = {"apiKey": ODDS_API_KEY, "regions": "eu,uk", "markets": "h2h", "oddsFormat": "decimal"}
    r = requests.get(url, params=params, timeout=20)
    if r.status_code != 200:
        print("Odds API status:", r.status_code, r.text[:200])
        return []
    return r.json()

def gather_all_events():
    events = []
    if not ODDS_API_KEY:
        print("No THE_ODDS_API_KEY: running in demo mode (no odds).")
        return events
    for league, key in SPORT_KEYS.items():
        try:
            data = fetch_odds_for_sport(key)
            for ev in data:
                ev["_league"] = league
                events.append(ev)
            time.sleep(1)
        except Exception as e:
            print("Error fetching odds for", league, e)
    return events

# ---------- Model (prototype) ----------
def simple_model_score(features):
    score = 0.0
    score += 0.45 * (features.get("home_last5_wins", 0) - features.get("away_last5_wins", 0))
    score += 0.25 * (features.get("home_avg_rating", 7.0) - features.get("away_avg_rating", 7.0))
    score += 0.20 * (features.get("market_favorite_diff", 0))
    score += 0.05
    p = 1.0 / (1.0 + math.exp(-score))
    return float(p)

# ---------- Format Telegram stylé ----------
def build_message(signals):
    now_local = datetime.now(timezone.utc).astimezone().strftime('%Y-%m-%d %H:%M %Z')
    header = "📊⚽ *SPOREX ZONE ANALYTICS — PRÉDICTIONS DU JOUR* 🇪🇺🔥\n"
    header += f"_Généré le {now_local}_\n\n"
    if not signals:
        return header + "_Aucun signal ≥ 80% aujourd'hui._"
    body = header
    body += f"*Total signaux:* {len(signals)}\n\n"
    for s in signals:
        body += f"⚔️ *{s['home']}* _vs_ *{s['away']}* — _{s['league']}_\n"
        body += f"• Coup d'envoi: {s.get('kickoff_local','?')}\n"
        body += f"• *Prédiction:* {s.get('prediction','Voir')}\n"
        body += f"• *Probabilité:* {int(s['p_model']*100)}%  • *Cote moyenne:* `{s.get('avg_odd','N/A')}`\n"
        # Facteurs & mini-analyse
        factors = s.get('factors', [])
        if factors:
            body += "• *Facteurs clés:* " + ", ".join(factors) + "\n"
        body += f"• *Mini-analyse:* {s.get('short_analysis','—')}\n\n"
    body += "📲 Rejoignez SPOREX ZONE pour le débrief complet !\n#SPOREXZONE #Football #Prédictions"
    return body

def send_telegram(token, chat, text):
    if not token or not chat:
        print("Missing token or chat")
        return False, "missing"
    api = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat, "text": text, "parse_mode": "Markdown"}
    try:
        r = requests.post(api, json=payload, timeout=15)
        print("Telegram send status:", r.status_code, r.text[:200])
        return r.status_code == 200, r.text
    except Exception as e:
        print("Telegram send exception:", e)
        return False, str(e)

# ---------- Main ----------
def process():
    print("Start SPOREX pipeline...")
    events = gather_all_events()
    signals = []
    out = {"generated_at": datetime.now(timezone.utc).isoformat(), "signals": []}

    if not events:
        # No odds key -> write empty JSON and stop gracefully
        with open(OUTFILE, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        print("No events (no odds key). Exiting.")
        return

    for ev in events:
        home = ev.get("home_team")
        away = ev.get("away_team")
        league = ev.get("_league", ev.get("sport_key",""))
        kickoff = ev.get("commence_time")
        kickoff_local = kickoff

        # avg odd for home
        avg_odd = None
        market_prob = None
        try:
            prices = []
            for b in ev.get("bookmakers", []):
                for m in b.get("markets", []):
                    if m.get("key") == "h2h":
                        for o in m.get("outcomes", []):
                            if o.get("name") and home and o.get("name").lower() == home.lower():
                                prices.append(float(o.get("price")))
            if prices:
                avg_odd = sum(prices) / len(prices)
                market_prob = decimal_to_prob(avg_odd)
        except Exception as e:
            print("Odds parse error:", e)

        home_stats = get_team_summary(home) or {}
        away_stats = get_team_summary(away) or {}

        features = {
            "home_last5_wins": home_stats.get("last5_wins", 2),
            "away_last5_wins": away_stats.get("last5_wins", 2),
            "home_avg_rating": home_stats.get("avg_rating", 7.0),
            "away_avg_rating": away_stats.get("avg_rating", 6.8),
            "market_favorite_diff": (market_prob or 0) - 0.33
        }

        p_model = simple_model_score(features)

        record = {
            "home": home, "away": away, "league": league, "kickoff": kickoff,
            "kickoff_local": kickoff_local, "p_model": round(p_model, 3),
            "avg_odd": round(avg_odd,2) if avg_odd else None,
            "market_prob": round(market_prob,3) if market_prob else None,
            "features": features
        }

        # build short factors & analysis
        factors = []
        if features["home_last5_wins"] > features["away_last5_wins"]:
            factors.append("Forme maison")
        if features["home_avg_rating"] > features["away_avg_rating"]:
            factors.append("Meilleure note moyenne")
        if market_prob and market_prob > 0.5:
            factors.append("Favori marché")
        record["factors"] = factors
        record["short_analysis"] = " | ".join(factors) if factors else "Avantage marginal"

        # set textual prediction
        if p_model >= MIN_PROB:
            # simple textual prediction
            record["prediction"] = f"Victoire {home}"
            signals.append(record)
            out["signals"].append(record)

    # write JSON for frontend
    with open(OUTFILE, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print("Wrote", OUTFILE, "signals:", len(out["signals"]))

    # send Telegram if signals and properly configured
    normalized_chat = normalize_channel(TELEGRAM_CHAT)
    msg = build_message(out["signals"])
    if TELEGRAM_TOKEN and normalized_chat:
        ok, resp = send_telegram(TELEGRAM_TOKEN, normalized_chat, msg)
        print("Telegram result:", ok, resp)
    else:
        print("Telegram not configured (token or chat missing). Skipping send.")

if __name__ == "__main__":
    process()
