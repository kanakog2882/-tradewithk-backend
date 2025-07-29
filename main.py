import os
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
from sop_v74 import sop_v74
from compress_utils import compress_data_for_sop
import requests
from datetime import datetime, time, timedelta
import pytz

# ========== SECURE CREDENTIALS FROM ENV ==========
DHAN_API_KEY = os.getenv("DHAN_ACCESS_TOKEN")
DHAN_ACCOUNT_ID = os.getenv("DHAN_ACCOUNT_ID")

# ========== FLASK APP & LOGGING ==========
app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger("twk-backend")

# ========== MARKET HOURS ==========
def is_market_open():
    india = pytz.timezone("Asia/Kolkata")
    now = datetime.now(india).time()
    return time(9, 15) <= now <= time(15, 30)

# ========== DHAN API GETTER ==========
def fetch_from_dhan(endpoint, symbol, interval="5", date=None):
    url = f"https://api.dhan.co/{endpoint}/{symbol}"
    headers = {
        "access-token": DHAN_API_KEY,
        "account-id": DHAN_ACCOUNT_ID
    }
    params = {"interval": interval}
    if date:
        params["date"] = date
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        logger.info(f"Fetched raw response from {endpoint}: {data}")
        return data.get("multi_tf_data", {}), data.get("market_meta", {})
    except Exception as e:
        logger.error(f"Dhan API ({endpoint}) failed: {e} | resp={getattr(resp, 'text', None)}")
        return {}, {}

# ========== ROUTES ==========

@app.route("/", methods=["GET"])
def health():
    return "✅ TradeWithK backend running", 200

@app.route("/run_sop", methods=["POST"])
def run_sop_route():
    try:
        data = request.get_json(force=True) or {}
        mode = data.get("mode", "live")
        symbol = data.get("symbol", "NIFTY")
        interval = data.get("interval", "5")
        date = data.get("date")
        start_date = data.get("start_date")
        end_date = data.get("end_date")

        logger.info(f"SOP request | Mode: {mode} | Symbol: {symbol} | Interval: {interval} | Date: {date} | Range: {start_date} to {end_date} | Market Open: {is_market_open()}")

        if mode == "backtest":
            results = []
            if start_date and end_date:
                start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                end_dt = datetime.strptime(end_date, "%Y-%m-%d")
                while start_dt <= end_dt:
                    dt_str = start_dt.strftime("%Y-%m-%d")
                    multi_tf_data, market_meta = fetch_from_dhan("markethistory", symbol, interval, dt_str)
                    if multi_tf_data and market_meta:
                        compressed = compress_data_for_sop(multi_tf_data, market_meta)
                        result = sop_v74(compressed["spot"], compressed["market_meta"])
                        results.append({"date": dt_str, "result": result})
                    else:
                        results.append({"date": dt_str, "error": "Data unavailable"})
                    start_dt += timedelta(days=1)
                return jsonify({"symbol": symbol, "mode": "backtest", "results": results}), 200
            elif date:
                multi_tf_data, market_meta = fetch_from_dhan("markethistory", symbol, interval, date)
            else:
                return jsonify({"error": "Date or date range required for backtest mode."}), 400
        else:
            multi_tf_data, market_meta = fetch_from_dhan("marketlive", symbol, interval)

        if not (multi_tf_data and market_meta):
            logger.error(f"❌ Chart data missing | {symbol} | {mode} | {interval} | {date}")
            return jsonify({
                "error": "Missing required keys: multi_tf_data, market_meta",
                "details": {
                    "symbol": symbol,
                    "mode": mode,
                    "interval": interval,
                    "date": date,
                    "reason": "Chart API returned empty or invalid structure"
                }
            }), 400

        compressed = compress_data_for_sop(multi_tf_data, market_meta)
        result = sop_v74(compressed["spot"], compressed["market_meta"])
        return jsonify({
            "mode": mode,
            "is_market_open": is_market_open(),
            "symbol": symbol,
            "interval": interval,
            "result": result
        }), 200

    except Exception as e:
        logger.exception("SOP execution failed")
        return jsonify({"error": f"SOP logic error: {str(e)}"}), 500

@app.route("/get_chart_data", methods=["GET"])
def get_chart_data():
    symbol = request.args.get("symbol", "NIFTY")
    interval = request.args.get("interval", "5")
    multi_tf_data, market_meta = fetch_from_dhan("marketlive", symbol, interval)
    if not (multi_tf_data and market_meta):
        return jsonify({"error": "Missing data from live chart API"}), 500
    return jsonify({
        "symbol": symbol,
        "interval": interval,
        "multi_tf_data": multi_tf_data,
        "market_meta": market_meta
    }), 200

@app.route("/get_raw_data", methods=["GET"])
def get_raw_data():
    return jsonify({"message": "Raw data endpoint—plug in your logic here."}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
