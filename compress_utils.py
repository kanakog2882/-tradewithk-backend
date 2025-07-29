# compress_utils.py

def compress_data_for_sop(multi_tf_data, market_meta):
    compressed = {
        "spot": {},
        "ce": {},
        "pe": {},
        "market_meta": {
            "vix": market_meta.get("vix"),
            "atr_14": market_meta.get("atr_14"),
            "atr_median": market_meta.get("atr_median"),
            "ce_vol_spike": market_meta.get("ce_vol_spike"),
            "higher_tf_bars": market_meta.get("higher_tf_bars", [])[-2:]
        }
    }

    for segment in ("spot", "ce", "pe"):
        if segment in multi_tf_data:
            compressed[segment] = {
                tf: bars[-3:] for tf, bars in multi_tf_data[segment].items()
            }
    return compressed
