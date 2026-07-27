import yfinance as yf
from datetime import datetime
import os
import json
import pandas as pd
from dotenv import load_dotenv
import tweepy

load_dotenv()

API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
ACCESS_TOKEN_SECRET = os.getenv("ACCESS_TOKEN_SECRET")

STATE_FILE = "alerts_state.json"

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

def get_daily_change_and_price(ticker):
    try:
        data = yf.download(ticker, period="5d", progress=False, auto_adjust=True)
        if data.empty or len(data) < 2:
            return None, None

        if isinstance(data.columns, pd.MultiIndex):
            close = data["Close"][ticker]
        else:
            close = data["Close"]

        current = float(close.iloc[-1])
        prev = float(close.iloc[-2])
        change = (current - prev) / prev * 100
        return change, current
    except Exception:
        return None, None

def get_ath(ticker):
    try:
        data = yf.download(ticker, period="max", progress=False, auto_adjust=True)
        if data.empty:
            return None
        if isinstance(data.columns, pd.MultiIndex):
            close = data["Close"][ticker]
        else:
            close = data["Close"]
        return float(close.max())
    except:
        return None

def is_us_market_hours():
    hour = datetime.now().hour
    return 15 <= hour <= 22

def post_tweet(text):
    client = tweepy.Client(
        consumer_key=API_KEY,
        consumer_secret=API_SECRET,
        access_token=ACCESS_TOKEN,
        access_token_secret=ACCESS_TOKEN_SECRET
    )
    response = client.create_tweet(text=text)
    print(f"Posted: {text[:50]}... | ID: {response.data['id']}")

def check_alerts():
    today = datetime.now().strftime("%Y-%m-%d")
    state = load_state()

    if state.get("date") != today:
        state = {"date": today, "posted": []}

    print(f"Checking alerts for {today}...")

    # ===== OIL (Futures) =====
    change, price = get_daily_change_and_price("CL=F")
    if change is not None and abs(change) >= 5.0 and "oil_big_move" not in state["posted"]:
        text = f"Oil futures {change:+.1f}%\nNow at ${price:.2f}"
        post_tweet(text)
        state["posted"].append("oil_big_move")

    # ===== GOLD (Futures) =====
    change, price = get_daily_change_and_price("GC=F")
    if change is not None:
        if abs(change) >= 5.0 and "gold_big_move" not in state["posted"]:
            text = f"Gold futures {change:+.1f}%\nNow at ${price:,.0f}"
            post_tweet(text)
            state["posted"].append("gold_big_move")

        ath = get_ath("GC=F")
        if ath and price and price >= ath * 0.999 and "gold_ath" not in state["posted"]:
            text = f"Gold futures new ATH\n${price:,.0f}"
            post_tweet(text)
            state["posted"].append("gold_ath")

    # ===== BITCOIN =====
    change, price = get_daily_change_and_price("BTC-USD")
    if change is not None:
        if abs(change) >= 5.0 and "btc_big_move" not in state["posted"]:
            text = f"Bitcoin {change:+.1f}%\nNow at ${price:,.0f}"
            post_tweet(text)
            state["posted"].append("btc_big_move")

        ath = get_ath("BTC-USD")
        if ath and price and price >= ath * 0.999 and "btc_ath" not in state["posted"]:
            text = f"Bitcoin new ATH\n${price:,.0f}"
            post_tweet(text)
            state["posted"].append("btc_ath")

    # ===== SPX (only during market hours) =====
    if is_us_market_hours():
        change, price = get_daily_change_and_price("^GSPC")
        if change is None or (isinstance(change, float) and change != change):
            change, price = get_daily_change_and_price("SPY")

        if change is not None and (not isinstance(change, float) or change == change):
            if abs(change) >= 2.0 and "spx_big_move" not in state["posted"]:
                text = f"SPX {change:+.1f}%"
                post_tweet(text)
                state["posted"].append("spx_big_move")

            if price:
                for level in [8000, 8500, 9000, 9500, 10000]:
                    key = f"spx_{level}"
                    if price >= level and key not in state["posted"]:
                        text = f"SPX closes above {level}\nFirst time"
                        post_tweet(text)
                        state["posted"].append(key)

    save_state(state)
    print("Check complete.")

if __name__ == "__main__":
    check_alerts()
