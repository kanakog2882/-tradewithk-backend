from flask import Flask, request, jsonify
from sop_v74 import sop_v74  # Import the correct function from your SOP file

app = Flask(__name__)

@app.route('/', methods=['POST'])
def recommend_trade():
    data = request.get_json()

    # Expecting these two main inputs in the POST body
    multi_tf_data = data.get("multi_tf_data")
    market_meta = data.get("market_meta")

    # Validate input
    if not multi_tf_data or not market_meta:
        return jsonify({"error": "Missing required data"}), 400

    # Call SOP engine
    result = sop_v74(multi_tf_data, market_meta)

    return jsonify(result)

@app.route('/', methods=['GET'])
def root_check():
    return '✅ TradeWithK backend is online and ready.', 200

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=8080)
