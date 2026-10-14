"""Relative MASE for the daily study, the same way as the weekly one (score.py).

MASE per (horizon, series, cutoff, forecaster):
  mean |forecast - actual| over the scored days
  ÷ mean |y_t - y_{t-7}| over the series' days up to and including the cutoff (seasonal naive, season 7)
Horizons: d1 = day 1 of each 7-day forecast, d7 = all 7 days.
Per series: average MASE over the cutoffs ÷ seasonal naive's (seasonal naive = 1); per level: geometric mean of
those ratios over the level's series. Position is sorted by relative MASE.

Reads forecasts_api.csv, forecasts_arima.csv, series.json, tasks.csv. Writes mase_long.csv, standings.csv.

    python daily/score_daily.py
"""
import csv, json, pathlib, statistics
from collections import defaultdict

HERE = pathlib.Path(__file__).resolve().parent
S = json.load(open(HERE / "series.json"))["series"]
TASKS = {(t["series"], t["cutoff"]) for t in csv.DictReader(open(HERE / "tasks.csv"))}
SPAN = {"d1": 1, "d7": 7}

err = defaultdict(dict)                                      # (series, cutoff, forecaster) -> {step: |e|}
for name in ("forecasts_api.csv", "forecasts_arima.csv"):
    for r in csv.DictReader(open(HERE / name)):
        err[(r["series"], r["cutoff"], r["forecaster"])][int(r["step"])] = abs(int(r["forecast_tokens"]) - int(r["actual_tokens"]))
FORECASTERS = sorted({k[2] for k in err})
missing = [(t, f) for t in TASKS for f in FORECASTERS if t + (f,) not in err or len(err[t + (f,)]) != 7]
assert not missing, f"{len(missing)} missing task x forecaster, e.g. {missing[:3]}"


def scale(s, c):
    y = [S[s][d] for d in sorted(S[s]) if d <= c]
    return sum(abs(b - a) for a, b in zip(y, y[7:])) / (len(y) - 7)


mase = [{"horizon": hz, "level": s.split(":")[0], "series": s, "cutoff": c, "forecaster": f,
         "mase": statistics.mean(e[k] for k in range(1, n + 1)) / scale(s, c)}
        for (s, c, f), e in err.items() for hz, n in SPAN.items()]
ser = defaultdict(list)
for r in mase:
    ser[(r["level"], r["horizon"], r["series"], r["forecaster"])].append(r["mase"])

stand = []
for lv in ("total", "model"):
    for hz in SPAN:
        series = sorted({k[2] for k in ser if k[0] == lv and k[1] == hz})
        rows = []
        for f in FORECASTERS:
            ratios = [statistics.mean(ser[(lv, hz, s, f)]) / statistics.mean(ser[(lv, hz, s, "seasonal-naive")]) for s in series]
            rows.append({"level": lv, "horizon": hz, "forecaster": f, "series": len(series),
                         "rel_mase": round(statistics.geometric_mean(ratios), 4),
                         "avg_mase": round(statistics.mean(m for s in series for m in ser[(lv, hz, s, f)]), 4)})
        for k, r in enumerate(sorted(rows, key=lambda r: r["rel_mase"]), 1):
            r["position"] = k
        stand += sorted(rows, key=lambda r: r["position"])

for name, rows in (("mase_long.csv", mase), ("standings.csv", stand)):
    with open(HERE / name, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
for lv in ("total", "model"):
    for hz in SPAN:
        print(f"\n{lv} {hz}")
        for r in (r for r in stand if r["level"] == lv and r["horizon"] == hz):
            print(f"  {r['position']:>2}. {r['forecaster']:<20} rel MASE {r['rel_mase']:.3f}")
