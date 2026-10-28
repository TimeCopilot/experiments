"""OpenRouter daily rankings (top 50 models + "other" per day), 2025-01-06 → END.

GET openrouter.ai/api/v1/datasets/rankings-daily?period=day&start_date=…&end_date=…, one request per calendar
month (larger windows sometimes return 500), spaced to stay under 30 requests/minute, retried on errors.
Categories and language_type are weekly only (the API refuses period=day for them).
Writes raw/day_<YYYY-MM>.json. Reuses files already on disk. Source: OpenRouter (openrouter.ai/rankings), CC BY 4.0.

    python daily/fetch_daily.py
"""
import os, sys, datetime as dt, json, pathlib, re, subprocess, time, urllib.error, urllib.parse, urllib.request

HERE = pathlib.Path(__file__).resolve().parent
START, END = dt.date(2025, 1, 6), dt.date(2026, 10, 13)       # END = last complete day when pulled (2026-10-14)
KEY = os.environ.get("OPENROUTER_API_KEY") or sys.exit("Set OPENROUTER_API_KEY (an OpenRouter API key) first.")

a = START
while a <= END:
    b = min((a.replace(day=28) + dt.timedelta(days=4)).replace(day=1) - dt.timedelta(days=1), END)
    out = HERE / "raw" / f"day_{a:%Y-%m}.json"
    if not out.exists():
        q = urllib.parse.urlencode({"period": "day", "start_date": a.isoformat(), "end_date": b.isoformat()})
        for attempt in range(5):
            try:
                req = urllib.request.Request(f"https://openrouter.ai/api/v1/datasets/rankings-daily?{q}",
                                             headers={"Authorization": f"Bearer {KEY}"})
                d = json.load(urllib.request.urlopen(req, timeout=120))
                break
            except urllib.error.HTTPError as e:
                print(f"  {a}: HTTP {e.code}, retry", flush=True)
                time.sleep(10 * (attempt + 1))
        else:
            raise RuntimeError(f"failed {a}..{b}")
        json.dump(d, open(out, "w"))
        days = {r["date"] for r in d["data"]}
        print(f"{a}..{b}: {len(d['data'])} rows, {len(days)} days", flush=True)
        time.sleep(2.5)
    a = b + dt.timedelta(days=1)
