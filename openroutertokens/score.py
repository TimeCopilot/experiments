"""Average MASE per forecaster for the blog benchmark. MASE is the only metric.

MASE per (horizon, series, cutoff, forecaster):
  mean |forecast - actual| over the h forecast weeks
  ÷ mean |y_t - y_{t-1}| over the series' weeks up to and including the cutoff (one-step naive, season 1)
Weekly: for each level, horizon and cutoff, each forecaster's average MASE across that week's series, and its
position that week when sorted by that number (1 = lowest MASE).
Overall: for each level and horizon, each forecaster's relative MASE, the way GIFT-Eval and fev-bench aggregate.
Per series, its average MASE over the cutoffs ÷ seasonal naive's average MASE on that series (so seasonal naive
is 1); then the geometric mean of those ratios over the level's series. Position is sorted by relative MASE.
avg_mase (plain average MASE over every series and cutoff) is kept for reference.

Reads forecasts_api.csv, forecasts_arima.csv, series.json, tasks.csv.
Writes mase_long.csv, weekly.csv, standings.csv.

    python score.py
"""
import csv, json, pathlib, statistics
from collections import defaultdict

HERE = pathlib.Path(__file__).resolve().parent
S = json.load(open(HERE / "series.json"))["series"]
TASKS = {(t["horizon"], t["series"], t["cutoff"]): t for t in csv.DictReader(open(HERE / "tasks.csv"))}
LEVELS = ["total", "category", "language", "model"]

err = defaultdict(list)                                   # (horizon, series, cutoff, forecaster) -> |e|
for name in ("forecasts_api.csv", "forecasts_arima.csv"):
    for r in csv.DictReader(open(HERE / name)):
        err[(r["horizon"], r["series"], r["cutoff"], r["forecaster"])].append(
            abs(int(r["forecast_tokens"]) - int(r["actual_tokens"])))
FORECASTERS = sorted({k[3] for k in err})


def scale(s, c):
    y = [S[s][w] for w in sorted(S[s]) if w <= c]
    return sum(abs(b - a) for a, b in zip(y, y[1:])) / (len(y) - 1)


missing = [(t, f) for t in TASKS for f in FORECASTERS if t + (f,) not in err]
assert not missing, f"{len(missing)} missing task x forecaster, e.g. {missing[:3]}"

mase = []
for (hz, s, c, f), e in err.items():
    mase.append({"horizon": hz, "level": s.split(":")[0], "series": s, "cutoff": c, "forecaster": f,
                 "mase": sum(e) / len(e) / scale(s, c)})

weekly = []
cell = defaultdict(list)
for r in mase:
    cell[(r["level"], r["horizon"], r["cutoff"], r["forecaster"])].append(r["mase"])
for lv in LEVELS:
    for hz in ("h1", "h4"):
        for c in sorted({k[2] for k in cell if k[0] == lv and k[1] == hz}):
            avg = {f: statistics.mean(cell[(lv, hz, c, f)]) for f in FORECASTERS}
            for k, f in enumerate(sorted(FORECASTERS, key=avg.get), 1):
                weekly.append({"level": lv, "horizon": hz, "cutoff": c, "forecaster": f,
                               "series": len(cell[(lv, hz, c, f)]), "avg_mase": round(avg[f], 4), "position": k})

ser = defaultdict(list)                                   # (level, horizon, series, forecaster) -> MASE per cutoff
for r in mase:
    ser[(r["level"], r["horizon"], r["series"], r["forecaster"])].append(r["mase"])


def rel_mase(lv, hz, f):
    series = sorted({k[2] for k in ser if k[0] == lv and k[1] == hz})
    ratios = [statistics.mean(ser[(lv, hz, s, f)]) / statistics.mean(ser[(lv, hz, s, "seasonal-naive")]) for s in series]
    return statistics.geometric_mean(ratios)


stand = []
for lv in LEVELS:
    for hz in ("h1", "h4"):
        rows = []
        for f in FORECASTERS:
            w = [r for r in weekly if r["level"] == lv and r["horizon"] == hz and r["forecaster"] == f]
            all_m = [r["mase"] for r in mase if r["level"] == lv and r["horizon"] == hz and r["forecaster"] == f]
            rows.append({"level": lv, "horizon": hz, "forecaster": f, "tasks": len(all_m),
                         "rel_mase": round(rel_mase(lv, hz, f), 4), "avg_mase": round(statistics.mean(all_m), 4),
                         "weeks_lowest": sum(r["position"] == 1 for r in w),
                         "best_week_position": min(r["position"] for r in w),
                         "worst_week_position": max(r["position"] for r in w)})
        for k, r in enumerate(sorted(rows, key=lambda r: r["rel_mase"]), 1):
            r["position"] = k
        stand += sorted(rows, key=lambda r: r["position"])

for name, rows in (("mase_long.csv", mase), ("weekly.csv", weekly), ("standings.csv", stand)):
    with open(HERE / name, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

for lv in LEVELS:
    for hz in ("h1", "h4"):
        print(f"\n{lv} {hz}")
        for r in (r for r in stand if r["level"] == lv and r["horizon"] == hz):
            print(f"  {r['position']:>2}. {r['forecaster']:<20} rel MASE {r['rel_mase']:>6.3f}  lowest in {r['weeks_lowest']:>2} wks  "
                  f"weekly positions {r['best_week_position']:>2}-{r['worst_week_position']:>2}")
