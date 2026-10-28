"""OpenRouter weekly rankings split by category and language type, 2025-01-06 → last complete week.

GET openrouter.ai/api/v1/datasets/rankings-daily?period=week&category=… / &language_type=…
Two date chunks per segment (366-day cap), spaced to stay under 30 requests/minute.
  category  sampled, upsampled estimates (OpenRouter's classifier); weekly only
  language_type  natural vs programming; sampled like category
Writes data/raw/segments/<kind>_<value>_<chunk>.json. Source: OpenRouter (openrouter.ai/rankings), CC BY 4.0.

    python data/fetch_segments.py
"""
import os, sys, json, pathlib, re, subprocess, time, urllib.parse, urllib.request

HERE = pathlib.Path(__file__).resolve().parent
KEY = os.environ.get("OPENROUTER_API_KEY") or sys.exit("Set OPENROUTER_API_KEY (an OpenRouter API key) first.")
SEGMENTS = {"category": ["programming", "roleplay", "marketing", "marketing/seo", "technology", "science",
                         "translation", "legal", "finance", "health", "trivia", "academia"],
            "language_type": ["natural", "programming"]}
PREFIX = {"context_bucket": "context", "language_type": "language"}   # file names: one "_" between kind and value
CHUNKS = {"2025": ("2025-01-06", "2025-12-28"), "2026": ("2025-12-29", "2026-10-11")}

for kind, values in SEGMENTS.items():
    for v in values:
        for name, (a, b) in CHUNKS.items():
            out = HERE / "raw" / "segments" / f"{PREFIX.get(kind, kind)}_{v.replace('/', '-')}_{name}.json"
            if out.exists():
                continue
            q = urllib.parse.urlencode({"period": "week", kind: v, "start_date": a, "end_date": b})
            req = urllib.request.Request(f"https://openrouter.ai/api/v1/datasets/rankings-daily?{q}",
                                         headers={"Authorization": f"Bearer {KEY}"})
            with urllib.request.urlopen(req, timeout=120) as r:
                d = json.load(r)
            json.dump(d, open(out, "w"))
            weeks = sorted({x["date"] for x in d["data"]})
            print(f"{kind}={v:<14} {name}: {len(d['data']):>5} rows, {len(weeks)} weeks "
                  f"{weeks[0] if weeks else '-'} → {weeks[-1] if weeks else '-'}", flush=True)
            time.sleep(2.2)
