from flask import Flask, request, jsonify
from sop_v74 import sop_v74
import requests
from datetime import datetime, time
import pytz

app = Flask(__name__)

# Dhan credentials (keep them secret in production: use env vars!)
DHAN_API_KEY = "<from flask import Flask, request, jsonify>"
from sop_v74 import sop_v74
import requests
from datetime import datetime, time
import pytz

app = Flask(__name__)

# Dhan credentials (keep them secret in production: use env vars!)
DHAN_API_KEY = "<eyJhbGciOiJIUzUxMiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbkNvbnN1bWVyVHlwZSI6IlNFTEYiLCJwYXJ0bmVySWQiOiIiLCJkaGFuQ2xpZW50SWQiOiIyNTA3MjU4Mjc1Iiwid2ViaG9va1VybCI6IiIsImlzcyI6ImRoYW4iLCJleHAiOjE3NTYwMjI5MDF9.3hDa7VNM1_SpvBbjwS8GRm0mZHjBSkBnRMxdAgdVAQqdtHylFOAUKbO3mAe290I6adXhDDWBhSoESaWb92pygQ>"
DHAN_ACCOUNT_ID = "<2507258275>"

def is_market_open():
    india = pytz.timezone("Asia/Kolkata")
    now = datetime.now(india).time()
    return time(9, 15) <= now <= time(15, 30)

def fetch_live_from_dhan(symbol):
    # ---- Replace this block with your actual Dhan endpoint and headers ----
    url = f"https://api.dhan.co/marketlive/{symbol}"
    headers = {
        "access-token": DHAN_API_KEY,
        "account-id": DHAN_ACCOUNT_ID
    }
    # You may need to add other headers as per Dhan's API docs
    resp = requests.get(url, headers=headers)
    data = resp.json()
    # Parse your data into the required structure for sop_v74:
    # YOU MUST write this based on your real Dhan data!
    multi_tf_data = ... # Construct this from Dhan API resp
    market_meta = ...   # Construct this from Dhan API resp
    return multi_tf_data, market_meta

def fetch_hist_from_dhan(symbol, date):
    # ---- Replace this block with your actual Dhan historical endpoint and headers ----
    url = f"https://api.dhan.co/markethistory/{symbol}"
    headers = {
        "access-token": DHAN_API_KEY,
        "account-id": DHAN_ACCOUNT_ID
    }
    params = {"date": date}
    resp = requests.get(url, headers=headers, params=params)
    data = resp.json()
    multi_tf_data = ... # Construct this from Dhan API resp
    market_meta = ...   # Construct this from Dhan API resp
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
        date = data.get("date", None)  # format: "YYYY-MM-DD"

        # Step 1: Decide which mode/data to fetch
        if mode == "backtest" or not is_market_open():
            if not date:
                return jsonify({"error": "Date is required for backtest mode."}), 400
            multi_tf_data, market_meta = fetch_hist_from_dhan(symbol, date)
        else:
            multi_tf_data, market_meta = fetch_live_from_dhan(symbol)

        # Step 2: Validate
        if not multi_tf_data or not market_meta:
            return jsonify({"error": "Missing required keys: 'multi_tf_data', 'market_meta'"}), 400

        # Step 3: Run your SOP logic
        result = sop_v74(multi_tf_data, market_meta)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": f"SOP execution failed: {str(e)}"}), 500

# ...rest of your endpoints...

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
>"
DHAN_ACCOUNT_ID = "<YOUR_ACCOUNT_ID_OR_TOKEN>"

def is_market_open():
    india = pytz.timezone("Asia/Kolkata")
    now = datetime.now(india).time()
    return time(9, 15) <= now <= time(15, 30)

def fetch_live_from_dhan(symbol):
    # ---- Replace this block with your actual Dhan endpoint and headers ----
    url = f"https://api.dhan.co/marketlive/{symbol}"
    headers = {
        "access-token": DHAN_API_KEY,
        "account-id": DHAN_ACCOUNT_ID
    }
    # You may need to add other headers as per Dhan's API docs
    resp = requests.get(url, headers=headers)
    data = resp.json()
    # Parse your data into the required structure for sop_v74:
    # YOU MUST write this based on your real Dhan data!
    multi_tf_data = ... # Construct this from Dhan API resp
    market_meta = ...   # Construct this from Dhan API resp
    return multi_tf_data, market_meta

def fetch_hist_from_dhan(symbol, date):
    # ---- Replace this block with your actual Dhan historical endpoint and headers ----
    url = f"https://api.dhan.co/markethistory/{symbol}"
    headers = {
        "access-token": DHAN_API_KEY,
        "account-id": DHAN_ACCOUNT_ID
    }
    params = {"date": date}
    resp = requests.get(url, headers=headers, params=params)
    data = resp.json()
    multi_tf_data = ... # Construct this from Dhan API resp
    market_meta = ...   # Construct this from Dhan API resp
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
        date = data.get("date", None)  # format: "YYYY-MM-DD"

        # Step 1: Decide which mode/data to fetch
        if mode == "backtest" or not is_market_open():
            if not date:
                return jsonify({"error": "Date is required for backtest mode."}), 400
            multi_tf_data, market_meta = fetch_hist_from_dhan(symbol, date)
        else:
            multi_tf_data, market_meta = fetch_live_from_dhan(symbol)

        # Step 2: Validate
        if not multi_tf_data or not market_meta:
            return jsonify({"error": "Missing required keys: 'multi_tf_data', 'market_meta'"}), 400

        # Step 3: Run your SOP logic
        result = sop_v74(multi_tf_data, market_meta)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": f"SOP execution failed: {str(e)}"}), 500

# ...rest of your endpoints...

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
