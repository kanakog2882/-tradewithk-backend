from flask import Flask, request, jsonify
from sop_v74 import sop_v74
import requests
from datetime import datetime, time
import pytz

# --- PLACE YOUR CREDENTIALS BELOW ---
DHAN_API_KEY = "eyJhbGciOiJIUzUxMiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbkNvbnN1bWVyVHlwZSI6IlNFTEYiLCJwYXJ0bmVySWQiOiIiLCJkaGFuQ2xpZW50SWQiOiIyNTA3MjU4Mjc1Iiwid2ViaG9va1VybCI6IiIsImlzcyI6ImRoYW4iLCJleHAiOjE3NTYwMjI5MDF9.3hDa7VNM1_SpvBbjwS8GRm0mZHjBSkBnRMxdAgdVAQqdtHylFOAUKbO3mAe290I6adXhDDWBhSoESaWb92pygQ"
DHAN_ACCOUNT_ID = "2507258275"

app = Flask(__name__)

def is_market_open():
    """Check if Indian equity markets are open now (09:15 to 15:30 IST)."""
    india = pytz.timezone("Asia/Kolkata")
    now = datetime.now(india).time()
    return time(9, 15) <= now <= time(15, 30)

def fetch_live_from_dhan(symbol):
    """Fetch live OHLC or LTP data. You must replace with your real Dhan API endpoint and fields."""
    url = f"https://api.dhan.co/marketlive/{symbol}"
    headers = {
        "access-token": DHAN_API_KEY,
        "account-id": DHAN_ACCOUNT_ID
    }
    # --- You'll need the correct url/headers per Dhan documentation.
    resp = requests.get(url, headers=headers)
    data = resp.json()
    # --- Example parse logic. Adjust to match your Dhan API shape.
    multi_tf_data = data.get("multi_tf_data", {})
    market_meta = data.get("market_meta", {})
    return multi_tf_data, market_meta

def fetch_hist_from_dhan(symbol, date):
    """Fetch historical OHLC data for backtest (date as 'YYYY-MM-DD'). Replace endpoint/params accordingly."""
    url = f"https://api.dhan.co/markethistory/{symbol}"
    headers = {
        "access-token": DHAN_API_KEY,
        "account-id": DHAN_ACCOUNT_ID
    }
    params = {"date": date}
    resp = requests.get(url, headers=headers, params=params)
    data = resp.json()
    multi_tf_data = data.get("multi_tf_data", {})
    market_meta = data.get("market_meta", {})
    return multi_tf_data, market_meta

@app.route('/', methods=['GET'])
def health_check():
    return '✅ TradeWithK backend is running.', 200

@app.route('/run_sop', methods=['POST'])
def run_sop():
    try:
        data = request.get_json(force=True) or {}
        mode = data.get("mode", "live")
        symbol = data.get("symbol", "NIFTY")
        date = data.get("date")
        # Decide what data to fetch
        if mode == "backtest" or not is_market_open():
            if not date:
                return jsonify({"error": "Date is required for backtest mode."}), 400
            multi_tf_data, market_meta = fetch_hist_from_dhan(symbol, date)
        else:
            multi_tf_data, market_meta = fetch_live_from_dhan(symbol)
        # Validate
        if not multi_tf_data or not market_meta:
            return jsonify({"error": "Missing required keys: 'multi_tf_data', 'market_meta'"}), 400
        # Run logic
        result = sop_v74(multi_tf_data, market_meta)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": f"SOP execution failed: {str(e)}"}), 500

@app.route('/get_chart_data', methods=['GET'])
def get_chart_data():
    symbol = request.args.get("symbol")
    timeframe = request.args.get("timeframe", "5min")
    if not symbol:
        return jsonify({"error": "Missing 'symbol' parameter"}), 400
    # Add real chart fetch logic here if needed
    return jsonify({"symbol": symbol, "timeframe": timeframe, "data": []}), 200

@app.route('/get_oi_snapshot', methods=['GET'])
def get_oi_snapshot():
    symbol = request.args.get("symbol", "NIFTY")
    # Placeholder - add Dhan/broker API call if desired
    oi_data = {
        "symbol": symbol,
        "oi_change": "placeholder",
        "message": "OI snapshot endpoint - replace with live OI API logic"
    }
    return jsonify(oi_data), 200

@app.route('/get_news', methods=['GET'])
def get_news():
    try:
        dummy_news = [
            {"headline": "Nifty ends flat amid volatility", "source": "Economic Times"},
            {"headline": "BANKNIFTY sees unwinding in 47000 CE", "source": "MoneyControl"},
            {"headline": "FII data suggests cautious stance ahead of Fed meeting", "source": "Mint"}
        ]
        return jsonify({"news": dummy_news}), 200
    except Exception as e:
        return jsonify({"error": f"News fetch failed: {str(e)}"}), 500

@app.route('/get_raw_data', methods=['GET'])
def get_raw_data():
    return jsonify({"message": "Raw data endpoint—replace with your logic."}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
