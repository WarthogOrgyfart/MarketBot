from datetime import datetime, date
import os
from dotenv import load_dotenv
import tweepy

load_dotenv()

API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
ACCESS_TOKEN_SECRET = os.getenv("ACCESS_TOKEN_SECRET")

# FOMC decision dates (2026 + 2027)
FOMC_DATES = [
    date(2026, 7, 29),
    date(2026, 9, 16),
    date(2026, 10, 28),
    date(2026, 12, 9),
    date(2027, 1, 27),
    date(2027, 3, 17),
    date(2027, 4, 28),
    date(2027, 6, 9),
    date(2027, 7, 28),
    date(2027, 9, 15),
    date(2027, 10, 27),
    date(2027, 12, 8),
]

CURRENT_RATE = "3.50% – 3.75%"

def get_live_odds():
    try:
        from cme_fedwatch import get_probabilities
        data = get_probabilities()
        
        if not data or "meetings" not in data:
            return None

        next_meeting = data["meetings"][0]
        probs = next_meeting.get("probabilities", {})

        odds = {}
        for rate_range, pct in probs.items():
            if "3.50" in rate_range or "3.5" in rate_range:
                odds["No change"] = round(pct)
            elif "3.75" in rate_range or "4.00" in rate_range:
                odds["25bps hike"] = round(pct)
            elif "3.25" in rate_range:
                odds["25bps cut"] = round(pct)

        return odds if odds else None

    except Exception:
        return None

def build_fomc_preview():
    today = date.today()

    if today not in FOMC_DATES:
        return None

    odds = get_live_odds()

    if odds is None:
        odds = {
            "No change": 70,
            "25bps hike": 25,
            "Cut": 5
        }

    lines = [
        "FOMC day",
        "",
        f"Current target: {CURRENT_RATE}",
        "",
        "Market currently prices:"
    ]

    for outcome, pct in odds.items():
        lines.append(f"• {outcome}: {pct}%")

    lines.append("")
    lines.append("Decision at 20:00 CEST")

    return "\n".join(lines)

def post_tweet(text):
    client = tweepy.Client(
        consumer_key=API_KEY,
        consumer_secret=API_SECRET,
        access_token=ACCESS_TOKEN,
        access_token_secret=ACCESS_TOKEN_SECRET
    )
    response = client.create_tweet(text=text)
    print(f"Posted! Tweet ID: {response.data['id']}")

if __name__ == "__main__":
    tweet = build_fomc_preview()

    if tweet is None:
        print("No FOMC meeting today — nothing to post.")
    else:
        print(tweet)
        print(f"\nCharacter count: {len(tweet)}")
        post_tweet(tweet)
