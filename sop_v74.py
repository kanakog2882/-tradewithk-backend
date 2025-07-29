import os
import requests
import numpy as np
import logging
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
    if score >= 4: return 1.00
    if score >= 2: return 0.70
    if score >= 1: return 0.40
    return 0.00

# ───── PATTERNS ─────
def pin_bar(o, h, l, c, v, prev_v):
    rng, body = h-l, abs(c-o)
    up, lo = h-max(o,c), min(o,c)-l
    if rng == 0 or v <= 1.1 * prev_v: return None
    if lo > 2*body and up < 0.3*rng: return "hammer"
    if up > 2*body and lo < 0.3*rng: return "shooting_star"
    return None

def engulfing(o, c, prev_o, prev_c):
    if c > o and o < prev_c and c > prev_o: return "bull_engulf"
    if c < o and o > prev_c and c < prev_o: return "bear_engulf"
    return None

def inside_break(prev_h, prev_l, h, l, o2, c2):
    return h <= prev_h and l >= prev_l and abs(c2-o2) > 0.6*(h-l)

def fvg(b1, b2):
    if (b2["high"]-b2["low"]) > 1.25*(b1["high"]-b1["low"]) and b2["volume"] > 1.3*b1["volume"]:
        return "fvg"
    return None

def order_blocks(lows, highs):
    return min(lows[-3:-1]), max(highs[-3:-1])

def bos(prev_swing, close, direction):
    if direction == 'up' and close > prev_swing: return "bos_up"
    if direction == 'down' and close < prev_swing: return "bos_down"
    return None

# ───── SIGNAL EXTRACTION ─────
def extract(bars: List[dict]) -> Dict:
    if len(bars) < 3:
        return {"direction": None, "score": 0.0, "patterns": []}
    b0, b1, b2 = bars[-3], bars[-2], bars[-1]
    p, score = [], 0.0
    for fn, s in [
        (pin_bar(b2['open'], b2['high'], b2['low'], b2['close'], b2['volume'], b1['volume']), 1.2),
        (engulfing(b2['open'], b2['close'], b1['open'], b1['close']), 1.2),
        ("inside_break" if inside_break(b1['high'], b1['low'], b2['high'], b2['low'], b2['open'], b2['close']) else None, 1.0),
        (fvg(b1, b2), 0.9),
        ("liq_bull" if b2['low'] < order_blocks([b0['low'], b1['low'], b2['low']], [b0['high'], b1['high'], b2['high']])[0] < b2['close'] else None, 1.0),
        ("liq_bear" if b2['high'] > order_blocks([b0['low'], b1['low'], b2['low']], [b0['high'], b1['high'], b2['high']])[1] > b2['close'] else None, 1.0),
        (bos(b1['high'], b2['close'], "up"), 1.0),
        (bos(b1['low'], b2['close'], "down"), 1.0)
    ]:
        if fn:
            p.append(fn)
            score += s
    dir_val = sum(1 if x in {"hammer", "bull_engulf", "inside_break", "liq_bull", "bos_up", "fvg"} else -1 for x in p if x)
    direction = "bullish" if dir_val > 0 else "bearish" if dir_val < 0 else None
    return {"direction": direction, "score": round(score, 2), "patterns": p}

# ───── ALIGNMENT ─────
def align_signals(sig_spot, sig_ce, sig_pe, ce_vol_bonus=0.0):
    score = 0.0
    if sig_spot["direction"] == sig_ce["direction"] == "bullish":
        score += sig_spot["score"] + sig_ce["score"] + 1.5 + ce_vol_bonus
    elif sig_spot["direction"] == sig_pe["direction"] == "bearish":
        score += sig_spot["score"] + sig_pe["score"] + 1.5
    elif sig_spot["direction"] in ("bullish", "bearish"):
        score += 0.5 * sig_spot["score"]
    if (sig_ce["direction"] == sig_pe["direction"] and sig_pe["score"] - sig_ce["score"] >= 1.0):
        score -= 0.5
    return round(score, 2)

# ───── SOP SINGLE TF ─────
def sop_single_tf(spot_bars, ce_bars, pe_bars, md):
    regime = classify_regime(md["vix"], md["atr_14"], md["atr_median"])
    bull_th, bear_th = thresholds(regime, md["vix"])
    sig_spot = extract(spot_bars)
    sig_ce = extract(ce_bars)
    sig_pe = extract(pe_bars)
    vol_bonus = 0.5 if sig_spot["direction"] == "bullish" and md.get("ce_vol_spike") else 0.0
    score = align_signals(sig_spot, sig_ce, sig_pe, vol_bonus)
    trend = htf_trend(md.get("higher_tf_bars", []))
    if trend == "up" and sig_spot["direction"] == "bullish": score += 0.5
    if trend == "down" and sig_spot["direction"] == "bearish": score += 0.5
    pos_pct = int(position_frac(score) * 100)
    if score >= bull_th and sig_spot["direction"] == sig_ce["direction"] == "bullish":
        action, conf = "BUY_CALL", "HIGH" if score >= 4 else "MEDIUM"
    elif score >= bear_th and sig_spot["direction"] == sig_pe["direction"] == "bearish":
        action, conf = "BUY_PUT", "HIGH" if score >= 4 else "MEDIUM"
    else:
        action, conf, pos_pct = "NO_TRADE", "INSUFFICIENT", 0
    return {"action": action, "confidence": conf, "position_size_pct": pos_pct, "alignment_score": score}

# ───── FINAL SOP MULTI-TF ─────
def sop_v74(multi_tf_data, market_meta, evaluated_tfs=("3min", "5min", "15min"), consensus_needed=2):
    tf_results = {
        tf: sop_single_tf(
            multi_tf_data["spot"][tf],
            multi_tf_data["ce"][tf],
            multi_tf_data["pe"][tf],
            market_meta
        )
        for tf in evaluated_tfs
    }
    actions = [tf_results[tf]["action"] for tf in evaluated_tfs]
    trade = next((a for a in ("BUY_CALL", "BUY_PUT") if actions.count(a) >= consensus_needed), None)
    if not trade:
        return {"action": "NO_TRADE", "confidence": "INSUFFICIENT", "position_size_pct": 0, "alignment_score": 0.0}
    best_tf = max([tf for tf in evaluated_tfs if tf_results[tf]["action"] == trade], key=lambda t: tf_results[t]["alignment_score"])
    return tf_results[best_tf]
