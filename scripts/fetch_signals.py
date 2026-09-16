#!/usr/bin/env python3
"""
Fetches macro signal data from FRED and writes assets/signals.json.

This runs server-side inside a GitHub Actions runner (not in the browser),
which is why it can call the FRED API directly with a secret key without
any CORS or key-exposure problems. The output JSON is what the static
HTML page on GitHub Pages actually reads.
"""

import json
import os
import sys
from datetime import datetime, timedelta

import requests

FRED_BASE = "https://api.stlouisfed.org/fred/series/observations"
WEEKS_BACK = 8

# series_id -> (friendly name, "lower is improving" or "higher is improving", what to watch for)
SERIES = {
    "GASDESW": (
        "Retail diesel price ($/gal, weekly)", "lower",
        "Watch for the price to stop making new highs and start correcting — "
        "that's the signal demand destruction is working, not the absolute level.",
    ),
    "DCOILWTICO": (
        "WTI crude oil ($/bbl, daily)", "lower",
        "Same idea as diesel: a peak-and-roll-over pattern, not a specific price target.",
    ),
    "BAMLH0A0HYM2": (
        "High-yield credit spread (%, daily)", "lower",
        "One of the best leading indicators historically — spreads often peak "
        "and start narrowing weeks to months before stocks bottom.",
    ),
    "T10Y2Y": (
        "10Y-2Y Treasury spread (%, daily)", "higher",
        "Watch for re-steepening after inversion (short rates falling faster "
        "than long rates as the Fed cuts) — this has historically coincided "
        "with equity bottoms.",
    ),
    "ICSA": (
        "Initial jobless claims (weekly)", "lower",
        "Watch for claims to plateau and roll over, not necessarily fall in "
        "absolute terms yet — the deceleration itself is the signal.",
    ),
    "VIXCLS": (
        "VIX volatility index (daily)", "lower",
        "Elevated and rising = still in the acute/capitulation phase. "
        "Elevated but falling = fear is draining out.",
    ),
}

# Overall read based on how many of the signals above are flashing "improving"
# at once — a simple weight-of-evidence framing, not a trading signal.
PHASE_GUIDANCE = [
    (0, "Acute phase — most signals still getting worse. This is the "
        "'freak out and sell everything' phase. Don't. Just wait."),
    (2, "Early transition — a few signals turning. Maybe buy a little."),
    (4, "Broad turn — most signals improving. Buy low, sell high time."),
]


def phase_read(improving_count):
    label = PHASE_GUIDANCE[0][1]
    for threshold, text in PHASE_GUIDANCE:
        if improving_count >= threshold:
            label = text
    return label


def fetch_series(series_id, api_key, weeks_back=WEEKS_BACK, retries=2):
    start = (datetime.utcnow() - timedelta(weeks=weeks_back)).strftime("%Y-%m-%d")
    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
        "observation_start": start,
        "sort_order": "desc",
    }
    last_err = None
    for attempt in range(retries + 1):
        try:
            resp = requests.get(FRED_BASE, params=params, timeout=20)
            resp.raise_for_status()
            obs = resp.json().get("observations", [])
            return [(o["date"], o["value"]) for o in obs if o["value"] != "."]
        except Exception as e:
            last_err = e
    raise last_err


def main():
    api_key = os.environ.get("FRED_API_KEY")
    if not api_key:
        print("FRED_API_KEY environment variable not set.", file=sys.stderr)
        sys.exit(1)

    results = []
    improving_count = 0

    for series_id, (name, direction, watch_for) in SERIES.items():
        try:
            obs = fetch_series(series_id, api_key)
            if len(obs) < 2:
                results.append({
                    "id": series_id, "name": name, "error": "insufficient data"
                })
                continue

            latest_date, latest_val = obs[0]
            oldest_date, oldest_val = obs[-1]
            latest_val = float(latest_val)
            oldest_val = float(oldest_val)
            change = latest_val - oldest_val
            pct_change = (change / oldest_val * 100) if oldest_val != 0 else 0
            improving = (change < 0) if direction == "lower" else (change > 0)
            if improving:
                improving_count += 1

            results.append({
                "id": series_id,
                "name": name,
                "direction": direction,
                "watch_for": watch_for,
                "latest_date": latest_date,
                "latest_value": round(latest_val, 3),
                "compare_date": oldest_date,
                "compare_value": round(oldest_val, 3),
                "change": round(change, 3),
                "pct_change": round(pct_change, 2),
                "improving": improving,
            })
        except Exception as e:
            results.append({"id": series_id, "name": name, "error": str(e)})

    output = {
        "generated_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "lookback_weeks": WEEKS_BACK,
        "improving_count": improving_count,
        "total_count": len([r for r in results if "error" not in r]),
        "phase_read": phase_read(improving_count),
        "signals": results,
    }

    os.makedirs("assets", exist_ok=True)
    with open("assets/signals.json", "w") as f:
        json.dump(output, f, indent=2)

    print(f"Wrote assets/signals.json — {improving_count}/{output['total_count']} improving")


if __name__ == "__main__":
    main()
