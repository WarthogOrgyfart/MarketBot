import yfinance as yf
from datetime import datetime
import os
from dotenv import load_dotenv
import tweepy

load_dotenv()

API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
ACCESS_TOKEN_SECRET = os.getenv("ACCESS_TOKEN_SECRET")

MAG7 = ["AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "TSLA"]

def get_stock_performance(tickers):
    print("Downloading Mag 7...")
    results = []
    
    data = yf.download(
        tickers,
        period="ytd",
        group_by="ticker",
        auto_adjust=True,
        progress=False,
        threads=True
    )
    
    for ticker in tickers:
        try:
            df = data[ticker] if len(tickers) > 1 else data
            if df.empty or len(df) < 2:
                continue

            current = df["Close"].iloc[-1]
            prev_close = df["Close"].iloc[-2]
            ytd_start = df["Close"].iloc[0]

            daily_pct = (current - prev_close) / prev_close * 100
            ytd_pct = (current - ytd_start) / ytd_start * 100

            results.append({
                "ticker": ticker,
                "daily": daily_pct,
                "ytd": ytd_pct
            })
        except Exception:
            continue
            
    return results

def get_market_data():
    print("Fetching market data...")
    
    tickers = ["^GSPC", "^NDX", "^VIX", "^TNX", "CL=F", "GC=F", "BTC-USD", "2YY=F"]
    
    data = yf.download(
        tickers,
        period="5d",
        group_by="ticker",
        auto_adjust=True,
        progress=False
    )
    
    result = {}
    
    def daily_change(ticker):
        try:
            series = data[ticker]["Close"].dropna()
            return (series.iloc[-1] - series.iloc[-2]) / series.iloc[-2] * 100
        except:
            return None
    
    def last_value(ticker):
        try:
            return data[ticker]["Close"].dropna().iloc[-1]
        except:
            return None
    
    result["spx"] = daily_change("^GSPC")
    result["ndx"] = daily_change("^NDX")
    result["vix"] = last_value("^VIX")
    
    tnx_raw = last_value("^TNX")
    if tnx_raw is not None:
        result["tnx"] = tnx_raw / 10 if tnx_raw > 15 else tnx_raw
    else:
        result["tnx"] = None
    
    result["ust2y"] = last_value("2YY=F")
    result["oil"] = last_value("CL=F")
    result["gold"] = last_value("GC=F")
    result["btc"] = last_value("BTC-USD")
    
    return result

def format_pct(value):
    if value is None:
        return "n/a"
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.1f}%"

def build_tweet(mag7, market):
    today = datetime.now().strftime("%d %b")
    
    mag_lines = []
    for s in mag7:
        mag_lines.append(f"{s['ticker']}  {format_pct(s['daily'])}  {format_pct(s['ytd'])}")
    mag_text = "\n".join(mag_lines)
    
    vix_text = f"{market['vix']:.1f}" if market.get('vix') is not None else "n/a"
    indices_line = f"SPX {format_pct(market['spx'])}  |  NDX {format_pct(market['ndx'])}  |  VIX {vix_text}"
    
    yields_parts = []
    if market.get("ust2y") is not None:
        yields_parts.append(f"2Y {market['ust2y']:.2f}%")
    if market.get("tnx") is not None:
        yields_parts.append(f"10Y {market['tnx']:.2f}%")
    yields_line = "  |  ".join(yields_parts)
    
    commodities = []
    if market.get("oil"):
        commodities.append(f"Oil ${market['oil']:.1f}")
    if market.get("gold"):
        commodities.append(f"Gold ${market['gold']:,.0f}")
    if market.get("btc"):
        commodities.append(f"BTC ${market['btc']:,.0f}")
    commodities_line = "  |  ".join(commodities)
    
    tweet = (
        f"Market Snapshot – {today}\n\n"
        f"Mag 7  ·  Daily / YTD\n{mag_text}\n\n"
        f"{indices_line}\n"
        f"{yields_line}\n"
        f"{commodities_line}"
    )
    return tweet

def post_tweet(text):
    client = tweepy.Client(
        consumer_key=API_KEY,
        consumer_secret=API_SECRET,
        access_token=ACCESS_TOKEN,
        access_token_secret=ACCESS_TOKEN_SECRET
    )
    response = client.create_tweet(text=text)
    print(f"Posted! Tweet ID: {response.data['id']}")
    return response

if __name__ == "__main__":
    mag7_data = get_stock_performance(MAG7)
    
    mag7_ordered = []
    for t in MAG7:
        for item in mag7_data:
            if item["ticker"] == t:
                mag7_ordered.append(item)
                break
    
    market = get_market_data()
    tweet = build_tweet(mag7_ordered, market)
    
    print(tweet)
    print(f"\nCharacter count: {len(tweet)}")
    
    post_tweet(tweet)
