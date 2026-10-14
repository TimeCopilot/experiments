"""Daily backtest tasks: OpenRouter daily tokens at two levels (categories and languages are weekly only).
  total  all OpenRouter tokens = the daily top 50 + OpenRouter's "other" row
  model  the same 50 models as the weekly study (last complete week's top 50), each on its unbroken daily run
         ending on the last day
OpenRouter has no rows for 2025-06-15 and 2025-07-15; each is filled with the mean of the day before and after
(only for series present on both sides). Both days are months before the first cutoff.
Cutoffs: 12, one per week, LAST-7d … LAST-84d, each forecasting the next 7 days (all observed).
A (series, cutoff) task is used when the series has at least MIN_CONTEXT days up to and including the cutoff.
Writes series.json ({id: {day: tokens}}) and tasks.csv (series, cutoff, context_days).

    python daily/build_data_daily.py
"""
import csv, datetime as dt, glob, json, pathlib
from collections import defaultdict

HERE = pathlib.Path(__file__).resolve().parent
LAST = "2026-10-13"
MIN_CONTEXT = 56
GAPS = ["2025-06-15", "2025-07-15"]
day = lambda d, n: (dt.date.fromisoformat(d) + dt.timedelta(days=n)).isoformat()

raw = defaultdict(dict)                                      # slug -> {day: tokens}
for f in sorted(glob.glob(str(HERE / "raw" / "day_*.json"))):
    for r in json.load(open(f))["data"]:
        raw[r["model_permaslug"]][r["date"]] = int(r["total_tokens"])
for g in GAPS:
    for s, d in raw.items():
        a, b = d.get(day(g, -1)), d.get(day(g, 1))
        if a is not None and b is not None:
            d[g] = round((a + b) / 2)

days = sorted({d for s in raw.values() for d in s})
series = {"total:all": {d: sum(s.get(d, 0) for s in raw.values()) for d in days}}
weekly = json.load(open(HERE.parent / "series.json"))["series"]
for sid in (k for k in weekly if k.startswith("model:")):
    slug, d, run = sid.split(":", 1)[1], LAST, {}
    while d in raw.get(slug, {}):
        run[d] = raw[slug][d]
        d = day(d, -1)
    if run:
        series[sid] = dict(sorted(run.items()))

cutoffs = [day(LAST, -7 * k) for k in range(12, 0, -1)]
tasks = []
for sid, s in series.items():
    for c in cutoffs:
        n = sum(1 for d in s if d <= c)
        if n >= MIN_CONTEXT and all(day(c, k) in s for k in range(1, 8)):
            tasks.append({"series": sid, "cutoff": c, "context_days": n})
json.dump({"last_day": LAST, "series": series}, open(HERE / "series.json", "w"))
with open(HERE / "tasks.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=["series", "cutoff", "context_days"])
    w.writeheader()
    w.writerows(tasks)
models = {t["series"] for t in tasks if t["series"] != "total:all"}
print(f"{len(days)} days {days[0]}..{days[-1]}; {len(series) - 1} models with a run; cutoffs {cutoffs[0]}..{cutoffs[-1]}")
print(f"{len(tasks)} tasks: total {sum(t['series'] == 'total:all' for t in tasks)}, models {len(models)} "
      f"({sum(t['series'] != 'total:all' for t in tasks)} tasks)")
