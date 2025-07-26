from flask import Flask, request, jsonify
from sop_v74 import sop_v74  # ✅ Correct function from your strategy file

app = Flask(__name__)

# ✅ Check if backend is alive
@app.route('/', methods=['GET'])
def root_check():
    return '✅ TradeWithK backend is online and ready.', 200

# ✅ Main POST endpoint for SOP strategy
@app.route('/', methods=['POST'])
def recommend_trade():
    try:
        data = request.get_json(force=True)  # 🔍 Handles bad headers too
    except Exception as e:
        return jsonify({"error": "Invalid JSON format", "details": str(e)}), 400

    if not data:
        return jsonify({"error": "No JSON body received"}), 400

    multi_tf_data = data.get("multi_tf_data")
    market_meta = data.get("market_meta")

    if not multi_tf_data or not market_meta:
        return jsonify({
            "error": "Missing required keys: 'multi_tf_data' and/or 'market_meta'"
        }), 400

    try:
        result = sop_v74(multi_tf_data, market_meta)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": "SOP processing failed", "details": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=8080)
