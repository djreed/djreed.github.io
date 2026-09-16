#!/usr/bin/env python3
"""
Fetches raw macro signal observations from FRED and writes
assets/signals_raw.json.

This runs server-side inside a GitHub Actions runner (not in the browser),
which is why it can call the FRED API directly with a secret key without
any CORS or key-exposure problems.

This script only fetches — it doesn't interpret the data. See
analyze_signals.py for the "is this improving/turning/watching" logic,
which reads this file's output and can be re-run locally against cached
data without hitting the FRED API.
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
    "GASDESW": ("Retail diesel price ($/gal, weekly)", "lower"),
    "DCOILWTICO": ("WTI crude oil ($/bbl, daily)", "lower"),
    "BAMLH0A0HYM2": ("High-yield credit spread (%, daily)", "lower"),
    "T10Y2Y": ("10Y-2Y Treasury spread (%, daily)", "higher"),
    "ICSA": ("Initial jobless claims (weekly)", "lower"),
    "VIXCLS": ("VIX volatility index (daily)", "lower"),
}


def fetch_series(series_id, api_key, weeks_back=WEEKS_BACK, retries=2):
    start = (datetime.utcnow() - timedelta(weeks=weeks_back)).strftime("%Y-%m-%d")
    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
        "observation_start": start,
        "sort_order": "asc",
    }
    last_err = None
    for attempt in range(retries + 1):
        try:
            resp = requests.get(FRED_BASE, params=params, timeout=20)
            resp.raise_for_status()
            obs = resp.json().get("observations", [])
            return [(o["date"], float(o["value"])) for o in obs if o["value"] != "."]
        except Exception as e:
            last_err = e
    raise last_err


def main():
    api_key = os.environ.get("FRED_API_KEY")
    if not api_key:
        print("FRED_API_KEY environment variable not set.", file=sys.stderr)
        sys.exit(1)

    series_out = {}

    for series_id, (name, direction) in SERIES.items():
        try:
            obs = fetch_series(series_id, api_key)
            if len(obs) < 2:
                series_out[series_id] = {
                    "name": name, "direction": direction,
                    "error": "insufficient data",
                }
                continue
            series_out[series_id] = {
                "name": name,
                "direction": direction,
                "observations": [{"date": d, "value": v} for d, v in obs],
            }
        except Exception as e:
            series_out[series_id] = {
                "name": name, "direction": direction, "error": str(e),
            }

    output = {
        "generated_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "lookback_weeks": WEEKS_BACK,
        "series": series_out,
    }

    os.makedirs("assets", exist_ok=True)
    with open("assets/signals_raw.json", "w") as f:
        json.dump(output, f, indent=2)

    ok = len([s for s in series_out.values() if "error" not in s])
    print(f"Wrote assets/signals_raw.json — {ok}/{len(series_out)} series fetched")


if __name__ == "__main__":
    main()
