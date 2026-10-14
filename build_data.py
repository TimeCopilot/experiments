"""Backtest tasks for the blog benchmark: OpenRouter weekly tokens at four levels.

Levels (one series each unless noted, weekly tokens, week label = Monday):
  total     all OpenRouter tokens = the weekly top 50 + OpenRouter's "other" row
  category  12 usage categories (OpenRouter's sampled classifier)
  language  natural vs programming
  model     the 50 models in the last complete week's top 50, each on its unbroken run of weeks
Sources: data/raw/weekly/rankings_week_*.json and data/raw/segments/*.json (pulled 2026-10-12,
last complete week 2026-10-05).

Cutoffs: the last 12 weekly cutoffs whose full horizon is observed.
  h1  forecast 1 week ahead from cutoffs LAST-12w … LAST-1w
  h4  forecast 4 weeks ahead from cutoffs LAST-15w … LAST-4w
A (series, cutoff) task is used when the series has at least MIN_CONTEXT weeks up to and including the
cutoff, so newer models join the scoring once they have enough history.

Writes series.json ({id: {week: tokens}}) and tasks.csv (horizon, level, series, cutoff, context_weeks).

    python build_data.py
"""
import csv, datetime as dt, json, pathlib

HERE = pathlib.Path(__file__).resolve().parent
SRC = HERE / "data" / "raw"
MIN_CONTEXT = 8
CUTOFFS = 12
H = {"h1": 1, "h4": 4}


def weeks_back(d, n):
    return (dt.date.fromisoformat(d) - dt.timedelta(weeks=n)).isoformat()


def unbroken(d, end):
    """Weeks of the unbroken run in d ending at `end`, oldest first."""
    out, w = [], end
    while w in d:
        out.append(w)
        w = weeks_back(w, 1)
    return out[::-1]


R = []
for f in ("2025", "2026"):
    R += json.load(open(SRC / "weekly" / f"rankings_week_{f}.json"))["data"]
LAST = max(r["date"] for r in R)
by_model, total = {}, {}
for r in R:
    by_model.setdefault(r["model_permaslug"], {})[r["date"]] = int(r["total_tokens"])
    total[r["date"]] = total.get(r["date"], 0) + int(r["total_tokens"])

series = {"total:all": total}
seg = {}
for f in sorted((SRC / "segments").glob("*.json")):
    kind, val = f.stem.rsplit("_", 1)[0].split("_", 1)
    if kind in ("category", "language"):
        d = seg.setdefault(f"{kind}:{val}", {})
        for r in json.load(open(f))["data"]:
            d[r["date"]] = d.get(r["date"], 0) + int(r["total_tokens"])
series.update(seg)
top = [r["model_permaslug"] for r in sorted((r for r in R if r["date"] == LAST and r["model_permaslug"] != "other"),
                                            key=lambda r: -int(r["total_tokens"]))]
for m in top:
    series[f"model:{m}"] = by_model[m]
series = {k: {w: v[w] for w in unbroken(v, LAST)} for k, v in series.items()}

tasks = []
for hz, h in H.items():
    for k in range(h, h + CUTOFFS):
        c = weeks_back(LAST, k)
        for s, d in series.items():
            n = sum(w <= c for w in d)
            if n >= MIN_CONTEXT:
                tasks.append({"horizon": hz, "level": s.split(":")[0], "series": s, "cutoff": c, "context_weeks": n})

json.dump({"last_week": LAST, "top50": top, "series": series}, open(HERE / "series.json", "w"))
with open(HERE / "tasks.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(tasks[0]))
    w.writeheader()
    w.writerows(tasks)

print(f"last complete week {LAST}; {len(series)} series; {len(tasks)} tasks")
for hz in H:
    for lv in ("total", "category", "language", "model"):
        t = [x for x in tasks if x["horizon"] == hz and x["level"] == lv]
        per = {}
        for x in t:
            per[x["cutoff"]] = per.get(x["cutoff"], 0) + 1
        print(f"  {hz} {lv:<9} {len(t):>4} tasks, {len({x['series'] for x in t}):>2} series, "
              f"per cutoff {min(per.values())}-{max(per.values())}")
