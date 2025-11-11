import os, json, math, requests, time
from datetime import datetime, timezone
from fetch_odds import gather_all
from fetch_sofascore import get_team_summary

MIN_PROB = 0.80
OUTFILE = "matches_today.json"
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def decimal_to_prob(odd):
    try:
        return 1.0 / float(odd)
    except:
        return None

def simple_model(features):
    score = 0.0
    score += 0.4 * (features.get("home_last5_wins",0) - features.get("away_last5_wins",0))
    score += 0.2 * (features.get("home_avg_rating",7.0) - features.get("away_avg_rating",7.0))
    score += 0.25 * (features.get("market_favorite_diff",0))
    p = 1.0/(1.0+math.exp(-score))
    return p

def process():
    events = gather_all()
    signals = []
    output = {"generated_at": datetime.now(timezone.utc).isoformat(), "signals": []}
    for ev in events:
        home = ev.get("home_team")
        away = ev.get("away_team")
        league = ev.get("_league")
        kickoff = ev.get("commence_time")

        market_prob = None
        avg_odd = None
        try:
            markets = ev.get("bookmakers", [])
            prices = []
            for b in markets:
                for m in b.get("markets", []):
                    if m.get("key") == "h2h":
                        for o in m.get("outcomes", []):
                            if o.get("name") and o.get("name").lower() == home.lower():
                                prices.append(o.get("price"))
            if prices:
                avg_odd = sum(prices)/len(prices)
                market_prob = decimal_to_prob(avg_odd)
        except Exception:
            pass

        home_stats = get_team_summary(home)
        away_stats = get_team_summary(away)

        features = {
            "home_last5_wins": home_stats.get("last5_wins", 2),
            "away_last5_wins": away_stats.get("last5_wins", 2),
            "home_avg_rating": home_stats.get("avg_rating", 7.0),
            "away_avg_rating": away_stats.get("avg_rating", 6.8),
            "market_favorite_diff": (market_prob or 0) - 0.33
        }

        p_model = simple_model(features)

        record = {
            "home": home, "away": away, "league": league, "kickoff": kickoff,
            "p_model": round(p_model, 3), "avg_odd": avg_odd, "market_prob": round(market_prob,3) if market_prob else None,
            "features": features
        }

        if p_model >= MIN_PROB:
            output["signals"].append(record)

    with open(OUTFILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID and output["signals"]:
        text = "🔥 SPOREX STATS – Signaux du jour (≥80%)\n\n"
        for s in output["signals"]:
            text += f"⚽ {s['home']} vs {s['away']} ({s['league']}) — {int(s['p_model']*100)}% — cote ≈ {s['avg_odd']}\n"
        send_telegram(text)

    print(f"Finish. Signals: {len(output['signals'])}")

def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text}
    r = requests.post(url, json=payload, timeout=10)
    print("Telegram:", r.status_code, r.text)

if __name__ == "__main__":
    process()
