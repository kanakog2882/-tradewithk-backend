from flask import Flask, request, jsonify
from sop_v74 import sop_v74  # Make sure sop_v74 is the exact name in sop_v74.py

app = Flask(__name__)

@app.route('/', methods=['GET'])
def health_check():
    return '✅ TradeWithK backend is online.', 200

@app.route('/', methods=['POST'])
def recommend_trade():
    data = request.get_json(force=True)
    if not data:
        return jsonify({"error": "Invalid or missing JSON body"}), 400

    multi_tf_data = data.get("multi_tf_data")
    market_meta = data.get("market_meta")

    if not multi_tf_data or not market_meta:
        return jsonify({
            "error": "Require keys: 'multi_tf_data' and 'market_meta'"
        }), 400

    try:
        result = sop_v74(multi_tf_data, market_meta)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": f"SOP error: {e}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=False)
