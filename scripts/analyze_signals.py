#!/usr/bin/env python3
"""
Reads assets/signals_raw.json and writes assets/signals.json — the
flat/worsening/improving/volatile-worsening/volatile-improving
classification the dashboard renders.

Pure function of already-fetched data, so this can be re-run locally
(`make analyze`) against cached data to tune the classification without
hitting the FRED API. See fetch_signals.py for the fetch step.
"""

import json

RAW_PATH = "assets/signals_raw.json"
OUT_PATH = "assets/signals.json"

# A net change smaller than this fraction of the window's own range is noise,
# not a real move either way -- e.g. a credit spread landing 0.01 off where it
# started (3.7% of a 0.27-wide window) shouldn't get called "improving" any
# more confidently than "worsening".
NOISE_THRESHOLD = 0.05

# How much of the window's total travel (its high-low range) has to have been
# given back through round-tripping, rather than a clean run from start to
# end, before we call it volatile -- e.g. a steady climb has ~0 given-back
# travel; a spike that mostly unwound has close to all of it.
VOLATILITY_THRESHOLD = 0.5

# Overall read based on how many of the signals are flashing "improving" or
# "volatile-improving" (net-favorable, see classify()) at once — a simple
# weight-of-evidence framing, not a trading signal.
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
    """
    flat / worsening / improving / volatile-worsening / volatile-improving.

    Two independent reads of the window: has it net moved enough to call a
    direction at all (vs. noise), and how much of its total travel was
    round-tripped rather than a clean trend (volatility).
    """
    latest_val, oldest_val = values[-1], values[0]
    change = latest_val - oldest_val
    window_range = max(values) - min(values)

    if window_range == 0 or abs(change) / window_range < NOISE_THRESHOLD:
        return "flat"

    favorable = (change < 0) if direction == "lower" else (change > 0)
    volatile = (window_range - abs(change)) / window_range >= VOLATILITY_THRESHOLD

    if volatile:
        return "volatile-improving" if favorable else "volatile-worsening"
    return "improving" if favorable else "worsening"


def main():
    with open(RAW_PATH) as f:
        raw = json.load(f)
    weeks = raw["lookback_weeks"]

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
        direction = series["direction"]

        state = classify(values, direction)

        latest_val, oldest_val = values[-1], values[0]
        change = latest_val - oldest_val
        pct_change = (change / oldest_val * 100) if oldest_val else 0

        if state in ("improving", "volatile-improving"):
            improving_count += 1

        results.append({
            "id": series_id,
            "name": name,
            "direction": direction,
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
        "lookback_weeks": weeks,
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
