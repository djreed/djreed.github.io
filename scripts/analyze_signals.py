#!/usr/bin/env python3
"""
Reads assets/signals_raw.json and writes assets/signals.json — the
"is this improving/turning/watching" classification the dashboard renders.

Pure function of already-fetched data, so this can be re-run locally
(`make analyze`) against cached data to tune the classification without
hitting the FRED API. See fetch_signals.py for the fetch step.
"""

import json
from datetime import datetime

RAW_PATH = "assets/signals_raw.json"
OUT_PATH = "assets/signals.json"

# How far (as a fraction of the window's own high-low range) the latest
# reading has to have retraced from the window's worst point before we call
# it "turning" rather than just noise around the peak/trough. Averaging the
# last 3 readings (not just the single latest print) further damps day-to-day
# noise on the daily series (VIX, WTI, HY spread) — without it those flip
# watching/turning on ordinary volatility, which defeats the point of a
# weight-of-evidence read.
TURN_THRESHOLD = 0.25
SMOOTHING_WINDOW = 3

# Overall read based on how many of the signals are flashing "improving" at
# once — a simple weight-of-evidence framing, not a trading signal.
PHASE_GUIDANCE = [
    (0, "Acute phase — do NOT freak out and sell everything"),
    (2, "Early transition — maybe buy a little bit"),
    (4, "Broad turn — freak out and buy everything"),
]


def phase_read(improving_count):
    label = PHASE_GUIDANCE[0][1]
    for threshold, text in PHASE_GUIDANCE:
        if improving_count >= threshold:
            label = text
    return label


def classify(values, direction):
    """watching / turning / improving, from the shape of the window alone."""
    worst = max(values) if direction == "lower" else min(values)
    # last occurrence, so a plateau at the extreme still reads as "still there"
    worst_idx = max(i for i, v in enumerate(values) if v == worst)

    if worst_idx == len(values) - 1:
        return "watching"

    recent = values[-min(SMOOTHING_WINDOW, len(values)):]
    latest_avg = sum(recent) / len(recent)
    window_range = max(values) - min(values)
    retrace_frac = abs(latest_avg - worst) / window_range if window_range else 0

    return "improving" if retrace_frac >= TURN_THRESHOLD else "turning"


def main():
    with open(RAW_PATH) as f:
        raw = json.load(f)

    results = []
    improving_count = 0

    for series_id, series in raw["series"].items():
        name = series["name"]
        if "error" in series:
            results.append({"id": series_id, "name": name, "error": series["error"]})
            continue

        obs = series["observations"]
        dates = [o["date"] for o in obs]
        values = [o["value"] for o in obs]

        state = classify(values, series["direction"])
        if state == "improving":
            improving_count += 1

        latest_val, oldest_val = values[-1], values[0]
        change = latest_val - oldest_val
        pct_change = (change / oldest_val * 100) if oldest_val else 0

        results.append({
            "id": series_id,
            "name": name,
            "direction": series["direction"],
            "state": state,
            "latest_date": dates[-1],
            "latest_value": round(latest_val, 3),
            "compare_date": dates[0],
            "compare_value": round(oldest_val, 3),
            "change": round(change, 3),
            "pct_change": round(pct_change, 2),
        })

    output = {
        "generated_at": raw["generated_at"],
        "lookback_weeks": raw["lookback_weeks"],
        "improving_count": improving_count,
        "total_count": len([r for r in results if "error" not in r]),
        "phase_read": phase_read(improving_count),
        "signals": results,
    }

    with open(OUT_PATH, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Wrote {OUT_PATH} — {improving_count}/{output['total_count']} improving")


if __name__ == "__main__":
    main()
