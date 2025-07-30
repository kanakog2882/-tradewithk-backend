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
def fetch_from_dhan(symbol, interval="5", date=None, mode="live"):
    endpoint = "v2/charts/intraday" if mode == "backtest" else "v2/marketfeed/ohlc"
    url = f"https://api.dhan.co/{endpoint}"
    headers = {
        "access-token": DHAN_API_KEY,
        "client-id": DHAN_ACCOUNT_ID,
        "Content-Type": "application/json"
    }

    body = {
        "securityId": symbol,
        "exchangeSegment": "IDX_I",
        "instrument": "EQUITY",
        "interval": interval,
        "fromDate": date if date else datetime.now().strftime("%Y-%m-%d"),
        "toDate": date if date else datetime.now().strftime("%Y-%m-%d")
    }

    try:
        resp = requests.post(url, headers=headers, json=body, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        logger.info(f"Fetched response from Dhan: {data}")
        return data
    except Exception as e:
        logger.error(f"Dhan API fetch failed: {e} | Response: {getattr(resp, 'text', None)}")
        return {}

# ========== ROUTES ==========
@app.route("/", methods=["GET"])
def health():
    return "✅ TradeWithK backend running", 200

@app.route("/run_sop", methods=["POST"])
def run_sop_route():
    try:
        data = request.get_json(force=True) or {}
        mode = data.get("mode", "live")
        symbol = data.get("symbol", "13")  # "13" is NIFTY IDX_I
        interval = data.get("interval", "5")
        date = data.get("date")
        start_date = data.get("start_date")
        end_date = data.get("end_date")

        logger.info(f"SOP request | Mode: {mode} | Symbol: {symbol} | Interval: {interval} | Date: {date}")

        if mode == "backtest" and start_date and end_date:
            results = []
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")

            while start_dt <= end_dt:
                dt_str = start_dt.strftime("%Y-%m-%d")
                raw_data = fetch_from_dhan(symbol, interval, dt_str, mode="backtest")
                if raw_data:
                    compressed = compress_data_for_sop(raw_data)
                    result = sop_v74(compressed["spot"], compressed["market_meta"])
                    results.append({"date": dt_str, "result": result})
                else:
                    results.append({"date": dt_str, "error": "Data unavailable"})
                start_dt += timedelta(days=1)

            return jsonify({"symbol": symbol, "mode": mode, "results": results}), 200

        else:
            raw_data = fetch_from_dhan(symbol, interval, date, mode="live")

            if not raw_data:
                logger.error(f"❌ Chart data missing | {symbol} | {mode} | {interval}")
                return jsonify({"error": "Missing chart data from live API"}), 400

            compressed = compress_data_for_sop(raw_data)
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
    symbol = request.args.get("symbol", "13")
    interval = request.args.get("interval", "5")

    raw_data = fetch_from_dhan(symbol, interval, mode="live")

    if not raw_data:
        return jsonify({"error": "Missing data from live chart API"}), 500

    return jsonify(raw_data), 200

@app.route("/get_raw_data", methods=["GET"])
def get_raw_data():
    return jsonify({"message": "Raw data endpoint—plug in your logic here."}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
