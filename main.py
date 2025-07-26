from flask import Flask, request, jsonify

app = Flask(__name__)

# === SOP v7.4 engine logic directly here ===
def sop_v74(multi_tf_data, market_meta):
    try:
        # Extract required fields
        spot_data = multi_tf_data.get("spot", [])
        ce_data = multi_tf_data.get("ce", [])
        pe_data = multi_tf_data.get("pe", [])
        bias_score = market_meta.get("bias_score", 0)
        event_weight = market_meta.get("event_weight", 0)

        # Dummy logic for testing (you will replace this with your actual SOP logic)
        if bias_score > 3 and event_weight > 1:
            return {
                "action": "BUY_CALL",
                "alignment_score": bias_score + event_weight,
                "confidence": "HIGH",
                "chart_reference": {
                    "spot": spot_data,
                    "ce": ce_data,
                    "pe": pe_data
                }
            }
        else:
            return {
                "action": "NO_TRADE",
                "alignment_score": bias_score + event_weight,
                "confidence": "LOW",
                "chart_reference": {
                    "spot": spot_data,
                    "ce": ce_data,
                    "pe": pe_data
                }
            }
    except Exception as e:
        return {"error": str(e)}

# === ROUTES ===

@app.route('/', methods=['GET'])
def root_check():
    return '✅ TradeWithK backend is online and ready.', 200

@app.route('/signal', methods=['POST'])  # Correct route for GPT action
def run_sop_logic():
    data = request.get_json(force=True)
    if not data:
        return jsonify({"error": "No JSON body received"}), 400

    multi_tf_data = data.get("multi_tf_data")
    market_meta = data.get("market_meta")

    if not multi_tf_data or not market_meta:
        return jsonify({"error": "Missing required keys: 'multi_tf_data' and/or 'market_meta'"}), 400

    try:
        result = sop_v74(multi_tf_data, market_meta)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=8080)
