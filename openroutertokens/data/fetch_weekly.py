"""Fresh OpenRouter weekly top-50 rankings, full history 2025-01-06 → last complete week.

GET openrouter.ai/api/v1/datasets/rankings-daily?period=week, in two calls (the API caps a
request at 366 days). Key: OPENROUTER_API_KEY environment variable.
Writes data/raw/weekly/rankings_week_2025.json and rankings_week_2026.json.

Source: OpenRouter (openrouter.ai/rankings), CC BY 4.0, as of meta.as_of in each file.

    python data/fetch_weekly.py
"""
import json, os, pathlib, re, subprocess, sys, urllib.request

HERE = pathlib.Path(__file__).resolve().parent
KEY = os.environ.get("OPENROUTER_API_KEY") or sys.exit("Set OPENROUTER_API_KEY (an OpenRouter API key) first.")
URL = "https://openrouter.ai/api/v1/datasets/rankings-daily?period=week&start_date={}&end_date={}"

for name, (a, b) in {"2025": ("2025-01-06", "2025-12-28"), "2026": ("2025-12-29", "2026-10-11")}.items():
    req = urllib.request.Request(URL.format(a, b), headers={"Authorization": f"Bearer {KEY}"})
    with urllib.request.urlopen(req, timeout=120) as r:
        d = json.load(r)
    json.dump(d, open(HERE / "raw" / "weekly" / f"rankings_week_{name}.json", "w"))
    weeks = sorted({x["date"] for x in d["data"]})
    print(f"{name}: {len(d['data'])} rows, {len(weeks)} weeks {weeks[0]} → {weeks[-1]}, as_of {d['meta']['as_of']}")
