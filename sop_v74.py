import numpy as np
from typing import List, Dict

# ───── UTILITIES ─────
def median(lst):
    return float(np.median(lst)) if lst else 0.0

def classify_regime(vix, atr, atr_median):
    if vix > 18 or atr > 1.5 * atr_median:
        return "High_Volatility"
    if vix < 13 or atr < 0.9 * atr_median:
        return "Low_Volatility"
    return "Normal_Market"

def thresholds(regime, vix):
    if regime == "High_Volatility":
        bull, bear = 2.3, 3.0
    elif regime == "Low_Volatility":
        bull, bear = 1.7, 2.5
    else:
        bull, bear = 1.5, 2.5
    if vix < 11:
        bull = max(1.2, bull - 0.3)
    return bull, bear

def htf_trend(htf_bars):
    if len(htf_bars) < 2:
        return None
    if htf_bars[-1]['close'] > htf_bars[-2]['close']:
        return 'up'
    if htf_bars[-1]['close'] < htf_bars[-2]['close']:
        return 'down'
    return None

def position_frac(score):
    if score >= 4:
        return 1.00
    if score >= 2:
        return 0.70
    if score >= 1:
        return 0.40
    return 0.00

# ───── PATTERNS ─────
def pin_bar(o, h, l, c, v, prev_v):
    rng, body = h-l, abs(c-o)
    up, lo = h-max(o,c), min(o,c)-l
    strong = v > 1.1*prev_v
    if rng == 0 or not strong:
        return None
    if lo > 2*body and up < 0.3*rng:
        return "hammer"
    if up > 2*body and lo < 0.3*rng:
        return "shooting_star"
    return None

def engulfing(o, c, prev_o, prev_c):
    if c > o and o < prev_c and c > prev_o:
        return "bull_engulf"
    if c < o and o > prev_c and c < prev_o:
        return "bear_engulf"
    return None

def inside_break(prev_h, prev_l, h, l, o2, c2):
    if h <= prev_h and l >= prev_l:
        if abs(c2-o2) > 0.6*(h-l):
            return True
    return False

def fvg(b1, b2):
    if (b2["high"]-b2["low"]) > 1.25*(b1["high"]-b1["low"]) and b2["volume"] > 1.3*b1["volume"]:
        return "fvg"
    return None

def order_blocks(lows, highs):
    return min(lows[-3:-1]), max(highs[-3:-1])

def bos(prev_swing, close, direction):
    if direction == 'up' and close > prev_swing:
        return "bos_up"
    if direction == 'down' and close < prev_swing:
        return "bos_down"
    return None

# ───── SIGNAL EXTRACTION ─────
def extract(bars: List[dict]) -> Dict:
    if len(bars) < 3:
        return {"direction": None, "score": 0.0, "patterns": []}
    b0, b1, b2 = bars[-3], bars[-2], bars[-1]
    p, score = [], 0.0
    pb = pin_bar(b2['open'], b2['high'], b2['low'], b2['close'], b2['volume'], b1['volume'])
    if pb:
        p.append(pb); score += 1.2
    eng = engulfing(b2['open'], b2['close'], b1['open'], b1['close'])
    if eng:
        p.append(eng); score += 1.2
    if inside_break(b1['high'], b1['low'], b2['high'], b2['low'], b2['open'], b2['close']):
        p.append("inside_break"); score += 1.0
    fvg_tag = fvg(b1, b2)
    if fvg_tag:
        p.append(fvg_tag); score += 0.9
    lows = [b0['low'], b1['low'], b2['low']]
    highs = [b0['high'], b1['high'], b2['high']]
    bull_ob, bear_ob = order_blocks(lows, highs)
    if b2['low'] < bull_ob < b2['close']:
        p.append("liq_bull"); score += 1.0
    if b2['high'] > bear_ob > b2['close']:
        p.append("liq_bear"); score += 1.0
    bos_up = bos(highs[-2], b2['close'], "up")
    bos_dn = bos(lows[-2], b2['close'], "down")
    if bos_up:
        p.append(bos_up); score += 1.0
    if bos_dn:
        p.append(bos_dn); score += 1.0
    dir_val = 0
    bull = {"hammer", "bull_engulf", "inside_break", "liq_bull", "bos_up", "fvg"}
    bear = {"shooting_star", "bear_engulf", "liq_bear", "bos_down", "fvg"}
    for tag in p:
        dir_val += 1 if tag in bull else 0
        dir_val -= 1 if tag in bear else 0
    direction = "bullish" if dir_val > 0 else "bearish" if dir_val < 0 else None
    return {"direction": direction, "score": round(score, 2), "patterns": p}

# ───── ALIGNMENT ─────
def align_signals(sig_spot, sig_ce, sig_pe, ce_vol_bonus=0.0):
    score, reasons = 0.0, []
    if sig_spot["direction"] == sig_ce["direction"] == "bullish":
        score += sig_spot["score"] + sig_ce["score"] + 1.5 + ce_vol_bonus
        reasons.append("Spot+CE bullish alignment")
    if sig_spot["direction"] == sig_pe["direction"] == "bearish":
        score += sig_spot["score"] + sig_pe["score"] + 1.5
        reasons.append("Spot+PE bearish alignment")
    if sig_spot["direction"] == "bullish" and sig_ce["direction"] != "bullish":
        score += 0.5 * sig_spot["score"]
    if sig_spot["direction"] == "bearish" and sig_pe["direction"] != "bearish":
        score += 0.5 * sig_spot["score"]
    if (sig_ce["direction"] == sig_pe["direction"] != None and
            sig_pe["score"] - sig_ce["score"] >= 1.0):
        score -= 0.5
        reasons.append("Strong opposite-option conflict")
    return round(score, 2), reasons

# ───── SOP SINGLE TIMEFRAME ─────
def sop_single_tf(spot_bars, ce_bars, pe_bars, md):
    regime = classify_regime(md["vix"], md["atr_14"], md["atr_median"])
    bull_th, bear_th = thresholds(regime, md["vix"])
    sig_spot = extract(spot_bars)
    sig_ce = extract(ce_bars)
    sig_pe = extract(pe_bars)
    vol_bonus = 0.5 if (sig_spot["direction"] == "bullish" and md["ce_vol_spike"]) else 0.0
    score, reasons = align_signals(sig_spot, sig_ce, sig_pe, vol_bonus)
    trend = htf_trend(md["higher_tf_bars"])
    if trend == "up" and sig_spot["direction"] == "bullish":
        score += 0.5; reasons.append("HTF up-trend support")
    if trend == "down" and sig_spot["direction"] == "bearish":
        score += 0.5; reasons.append("HTF down-trend support")
    pos_pct = int(position_frac(score) * 100)
    if score >= bull_th and sig_spot["direction"] == sig_ce["direction"] == "bullish":
        action, conf = "BUY_CALL", "HIGH" if score >= 4 else "MEDIUM"
    elif score >= bear_th and sig_spot["direction"] == sig_pe["direction"] == "bearish":
        action, conf = "BUY_PUT", "HIGH" if score >= 4 else "MEDIUM"
    else:
        action, conf, pos_pct = "NO_TRADE", "INSUFFICIENT", 0
    return {
        "action": action, "confidence": conf, "position_size_pct": pos_pct,
        "alignment_score": score,
        "patterns": {"spot": sig_spot["patterns"], "ce": sig_ce["patterns"], "pe": sig_pe["patterns"]},
        "reasons": reasons
    }

# ───── FINAL SOP MULTI-TF ─────
def sop_v74(multi_tf_data, market_meta, evaluated_tfs=("3min", "5min", "15min"), consensus_needed=2):
    tf_results = {}
    for tf in evaluated_tfs:
        res = sop_single_tf(
            multi_tf_data["spot"][tf],
            multi_tf_data["ce"][tf],
            multi_tf_data["pe"][tf],
            market_meta
        )
        tf_results[tf] = res
    actions = [tf_results[tf]["action"] for tf in evaluated_tfs]
    trade = None
    for candidate in ("BUY_CALL", "BUY_PUT"):
        if actions.count(candidate) >= consensus_needed:
            trade = candidate; break
    if not trade:
        return {
            "action": "NO_TRADE",
            "confidence": "INSUFFICIENT",
            "position_size_pct": 0,
            "alignment_score": 0.0
        }
    agree_tfs = [tf for tf in evaluated_tfs if tf_results[tf]["action"] == trade]
    best_tf = max(agree_tfs, key=lambda t: tf_results[t]["alignment_score"])
    best_res = tf_results[best_tf]
    return {
        "action": best_res["action"],
        "confidence": best_res["confidence"],
        "position_size_pct": best_res["position_size_pct"],
        "alignment_score": best_res["alignment_score"]
    }
