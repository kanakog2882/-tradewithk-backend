from flask import Flask, request, jsonify
from sop_v74 import sop_v74  # This is your SOP logic in a separate file
import json

app = Flask(__name__)

@app.route("/")
def home():
    return "SOP v7.4 backend is running."

@app.route("/signal", methods=["POST"])
def signal():
    try:
        data = request.json
        symbol = data.get("symbol")
        expiry = data.get("expiry")
        timeframe = data.get("timeframe")

        # --- Load dummy data (later replaced with live Dhan data) ---
        with open("dummy_market_data.json") as f:
            market_data = json.load(f)

        result = sop_v74(
            multi_tf_data=market_data["multi_tf_data"],
            market_meta=market_data["market_meta"],
            evaluated_tfs=["3min", "5min", "15min"]
        )

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
