import os
from flask import Flask, request, jsonify
from sop_v74 import sop_v74
import requests
from datetime import datetime, time
import pytz
import logging

# =========== CONFIGURE YOUR CREDENTIALS BELOW (for dev; use env vars for prod) ===============
DHAN_API_KEY = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzU2Mjg0NDc0LCJ0b2tlbkNvbnN1bWVyVHlwZSI6IlNFTEYiLCJ3ZWJob29rVXJsIjoiIiwiZGhhbkNsaWVudElkIjoiMTEwMTU2MzEyNiJ9.c960a8vrfw5726OtcMce5vCKZ8CdtPSKHJtIy1iYYiXOgB72EZOf8a4ANixM-sEAAPFJ0myoxkcsszn1xu4cfw"
DHAN_ACCOUNT_ID = "1101563126"

# =========== SETUP FLASK & LOGGING ===========
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =========== MARKET HOURS FILTER ===========
def is_market_open():
    india = pytz.timezone("Asia/Kolkata")
    now = datetime.now(india).time()
    return time(9, 15) <= now <= time(15, 30)

# =========== FETCH LIVE CHART DATA ===========
def fetch_live_from_dhan(symbol, interval='5'):
    """Fetch live OHLC/Volume data."""
    # The API may differ for OHLC endpoints—adjust endpoint and params if needed:
    url = f"https://api.dhan.co/marketlive/{symbol}"
    headers = {
        "access-token": DHAN_API_KEY,
        "account-id": DHAN_ACCOUNT_ID
    }
    params = {
        "interval": interval,  # '1', '5', '15' for minute charts—adjust as per docs
        # Add other parameters if your API needs (range, start/end, etc.)
    }
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        data = resp.json()
        multi_tf_data = data.get("multi_tf_data", {})
        market_meta = data.get("market_meta", {})
        return multi_tf_data, market_meta
    except Exception as e:
        logger.error(f"Dhan API live chart fetch failed: {e}, status={resp.status_code if 'resp' in locals() else 'N/A'}")
        return {}, {}

# =========== HISTORICAL CHART DATA ==============
def fetch_hist_from_dhan(symbol, date, interval='5'):
    url = f"https://api.dhan.co/markethistory/{symbol}"
    headers = {
        "access-token": DHAN_API_KEY,
        "account-id": DHAN_ACCOUNT_ID
    }
    params = {"date": date, "interval": interval}
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        data = resp.json()
        multi_tf_data = data.get("multi_tf_data", {})
        market_meta = data.get("market_meta", {})
        return multi_tf_data, market_meta
    except Exception as e:
        logger.error(f"Dhan API hist chart fetch failed: {e}, status={resp.status_code if 'resp' in locals() else 'N/A'}")
        return {}, {}

# =========== APP ROUTES ===========

@app.route('/', methods=['GET'])
def health():
    return "✅ TradeWithK backend running", 200

@app.route('/run_sop', methods=['POST'])
def run_sop_route():
    try:
        data = request.get_json(force=True) or {}
        mode = data.get("mode", "live")
        symbol = data.get("symbol", "NIFTY")
        interval = data.get("interval", "5")  # Default 5-minute chart
        date = data.get("date")
        if mode == "backtest" or not is_market_open():
            if not date:
                msg = "Date is required for backtest mode."
                logger.error(msg + f" Request: {data}")
                return jsonify({"error": msg}), 400
            multi_tf_data, market_meta = fetch_hist_from_dhan(symbol, date, interval)
        else:
            multi_tf_data, market_meta = fetch_live_from_dhan(symbol, interval)
        if not (multi_tf_data and market_meta):
            logger.error(f"Missing chart keys for {symbol}, mode={mode}, interval={interval}, date={date}. Raw req: {data}")
            return jsonify({"error": "Missing required keys: multi_tf_data, market_meta"}), 400
        result = sop_v74(multi_tf_data, market_meta)
        return jsonify(result), 200
    except Exception as e:
        logger.exception("SOP logic/internal error")
        return jsonify({"error": f"SOP execution failed: {str(e)}"}), 500

@app.route('/get_chart_data', methods=['GET'])
def get_chart_data():
    symbol = request.args.get("symbol", "NIFTY")
    interval = request.args.get("interval", "5")
    multi_tf_data, market_meta = fetch_live_from_dhan(symbol, interval)
    if not (multi_tf_data and market_meta):
        return jsonify({"error": "Missing data from live chart API"}), 500
    return jsonify({
        "symbol": symbol,
        "interval": interval,
        "multi_tf_data": multi_tf_data,
        "market_meta": market_meta,
    }), 200

@app.route('/get_oi_snapshot', methods=['GET'])
def get_oi_snapshot():
    symbol = request.args.get("symbol", "NIFTY")
    # For full implementation, plug in your OI provider/API logic here
    return jsonify({
        "symbol": symbol,
        "oi_change": "placeholder",
        "message": "OI snapshot endpoint—add real OI API logic here"
    }), 200

@app.route('/get_news', methods=['GET'])
def get_news():
    try:
        dummy_news = [
            {"headline": "Nifty ends volatile", "source": "Economic Times"},
            {"headline": "BANKNIFTY OI unwinding at 47000CE", "source": "MoneyControl"},
        ]
        return jsonify({"news": dummy_news}), 200
    except Exception as e:
        logger.exception(f"News fetch failed: {str(e)}")
        return jsonify({"error": f"News fetch failed: {str(e)}"}), 500

@app.route('/get_raw_data', methods=['GET'])
def get_raw_data():
    return jsonify({"message": "Raw data endpoint—plug in your logic here."}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
