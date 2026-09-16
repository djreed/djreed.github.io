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

# series_id -> (friendly name, "lower is improving" or "higher is improving")
SERIES = {
    "GASDESW":      ("Retail diesel price ($/gal, weekly)", "lower"),
    "DCOILWTICO":   ("WTI crude oil ($/bbl, daily)",         "lower"),
    "BAMLH0A0HYM2": ("High-yield credit spread (%, daily)",  "lower"),
    "T10Y2Y":       ("10Y-2Y Treasury spread (%, daily)",    "higher"),
    "ICSA":         ("Initial jobless claims (weekly)",      "lower"),
    "VIXCLS":       ("VIX volatility index (daily)",         "lower"),
}


def fetch_series(series_id, api_key, weeks_back=WEEKS_BACK):
    start = (datetime.utcnow() - timedelta(weeks=weeks_back)).strftime("%Y-%m-%d")
    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
        "observation_start": start,
        "sort_order": "desc",
    }
    resp = requests.get(FRED_BASE, params=params, timeout=15)
    resp.raise_for_status()
    obs = resp.json().get("observations", [])
    return [(o["date"], o["value"]) for o in obs if o["value"] != "."]


def main():
    api_key = os.environ.get("FRED_API_KEY")
    if not api_key:
        print("FRED_API_KEY environment variable not set.", file=sys.stderr)
        sys.exit(1)

    results = []
    improving_count = 0

    for series_id, (name, direction) in SERIES.items():
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
        "signals": results,
    }

    os.makedirs("assets", exist_ok=True)
    with open("assets/signals.json", "w") as f:
        json.dump(output, f, indent=2)

    print(f"Wrote assets/signals.json — {improving_count}/{output['total_count']} improving")


if __name__ == "__main__":
    main()
