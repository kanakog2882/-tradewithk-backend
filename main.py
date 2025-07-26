from flask import Flask, request, jsonify
from sop_v74 import sop_v74  # This should match your actual function name

app = Flask(__name__)

@app.route('/', methods=['POST'])
def recommend_trade():
    try:
        data = request.get_json(force=True)

        multi_tf_data = data.get("multi_tf_data")
        market_meta = data.get("market_meta")

        if not multi_tf_data or not market_meta:
            return jsonify({"error": "Missing 'multi_tf_data' or 'market_meta' in body"}), 400

        result = sop_v74(multi_tf_data, market_meta)
        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/', methods=['GET'])
def root_check():
    return '✅ TradeWithK backend is online and ready.', 200

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=8080)
