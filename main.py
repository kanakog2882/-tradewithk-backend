from flask import Flask, request, jsonify
from sop_v74 import get_trade_signal  # This should be defined in sop_v74.py

app = Flask(__name__)

@app.route('/', methods=['POST'])
def recommend_trade():
    data = request.get_json()
    query = data.get('query', 'NIFTY')  # default fallback
    signal = get_trade_signal(query)    # Your trade suggestion logic
    return jsonify({
        "query": query,
        "recommendation": signal
    })

@app.route('/', methods=['GET'])
def root_check():
    return 'TradeWithK backend is online and running.', 200

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=8080)
