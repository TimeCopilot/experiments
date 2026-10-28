"""Data for the per-LLM loop animation only: the weekly study's individual OpenRouter LLMs, 1 week ahead, with a
4-week minimum history (the main study uses 8), so short-lived LLMs get more backtest windows and more LLMs qualify.

Same 12 weekly cutoffs as the main study. Forecasts already in ../forecasts_api.csv and ../forecasts_arima.csv are
reused; only the new (series, cutoff) windows are sent to the TimeCopilot API (/v1/cross-validation, n_windows=1,
freq W-MON, season_length 1) and to a local AutoARIMA(season_length=1).
Scoring as score.py: MASE per window, then per LLM its average MASE ÷ seasonal naive's.

Writes series.json, tasks.csv, forecasts_api.csv, forecasts_arima.csv, mase_long.csv and standings.csv here, in the
shape build_blog.py's load() reads.

    python loop/run_loop.py
"""
import csv, datetime as dt, json, pathlib, shutil, statistics, sys, time, urllib.request
from collections import defaultdict
import pandas as pd
from statsforecast import StatsForecast
from statsforecast.models import AutoARIMA

HERE = pathlib.Path(__file__).resolve().parent
UP = HERE.parent
sys.path.insert(0, str(UP / "lib"))
from orlib import post, token, BASE, UA, SCALE

MIN_CONTEXT = 4
S = json.load(open(UP / "series.json"))["series"]
CUTS = sorted({t["cutoff"] for t in csv.DictReader(open(UP / "tasks.csv")) if t["horizon"] == "h1"})
tasks = []
for s in (k for k in S if k.startswith("model:")):
    weeks = sorted(S[s])
    for c in CUTS:
        n = sum(1 for w in weeks if w <= c)
        nxt = (dt.date.fromisoformat(c) + dt.timedelta(weeks=1)).isoformat()
        if n >= MIN_CONTEXT and nxt in S[s]:
            tasks.append({"horizon": "h1", "level": "model", "series": s, "cutoff": c, "context_weeks": n})
shutil.copy(UP / "series.json", HERE / "series.json")
with open(HERE / "tasks.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(tasks[0]))
    w.writeheader()
    w.writerows(tasks)
want = {(t["series"], t["cutoff"]) for t in tasks}

old = defaultdict(list)                                     # reuse the main study's forecasts
for name in ("forecasts_api.csv", "forecasts_arima.csv"):
    for r in csv.DictReader(open(UP / name)):
        if r["horizon"] == "h1" and (r["series"], r["cutoff"]) in want:
            old[name].append(r)
have = {(r["series"], r["cutoff"]) for r in old["forecasts_api.csv"]}
new = [t for t in tasks if (t["series"], t["cutoff"]) not in have]
print(f"{len(tasks)} windows on {len({t['series'] for t in tasks})} LLMs; {len(have)} reused, {len(new)} new", flush=True)

req = urllib.request.Request(BASE + "/v1/models", headers={"Authorization": f"Bearer {token()}", "User-Agent": UA})
with urllib.request.urlopen(req, timeout=120) as r:
    FORECASTERS = [m["id"] for m in json.load(r)["models"]]
(HERE / "raw").mkdir(exist_ok=True)


def payload(t):
    weeks = sorted(S[t["series"]])
    use = weeks[:weeks.index(t["cutoff"]) + 2]
    return {"unique_id": f"{t['series']}@{t['cutoff']}", "start": f"{use[0]}T00:00:00",
            "y": [S[t["series"]][w] / SCALE for w in use]}


api = list(old["forecasts_api.csv"])
for f in FORECASTERS:
    out = HERE / "raw" / f"h1_{f}.json"
    if not out.exists():
        for attempt in range(3):
            try:
                r = post("/v1/cross-validation", {"model": f, "series": [payload(t) for t in new],
                                                  "parameters": {"h": 1, "freq": "W-MON", "season_length": 1,
                                                                 "n_windows": 1, "step_size": 1}}, timeout=1800)
                break
            except Exception as e:
                print(f"  retry {f}: {e}", flush=True)
                time.sleep(20 * (attempt + 1))
        else:
            raise RuntimeError(f"failed {f}")
        json.dump(r, open(out, "w"))
        print(f"done {f}", flush=True)
    for fo in json.load(open(out))["folds"]:
        s, c = fo["unique_id"].rsplit("@", 1)
        assert fo["cutoff"][:10] == c, fo["unique_id"]
        api.append({"horizon": "h1", "series": s, "cutoff": c, "forecaster": f, "step": 1,
                    "week": fo["actual"]["start"][:10], "actual_tokens": round(fo["actual"]["y"][0] * SCALE),
                    "forecast_tokens": round(fo["forecast"]["y"][0] * SCALE)})

recs = [(f"{t['series']}@{t['cutoff']}", pd.Timestamp(w), S[t["series"]][w] / SCALE)
        for t in new for w in sorted(S[t["series"]]) if w <= t["cutoff"]]
fc = StatsForecast(models=[AutoARIMA(season_length=1)], freq="W-MON", n_jobs=1).forecast(
    df=pd.DataFrame(recs, columns=["unique_id", "ds", "y"]), h=1)
fc = fc.reset_index() if "unique_id" not in fc.columns else fc
arima = list(old["forecasts_arima.csv"])
for _, row in fc.iterrows():
    s, c = row["unique_id"].rsplit("@", 1)
    wk = row["ds"].date().isoformat()
    arima.append({"horizon": "h1", "series": s, "cutoff": c, "forecaster": "auto-arima", "step": 1, "week": wk,
                  "actual_tokens": S[s][wk], "forecast_tokens": round(row["AutoARIMA"] * SCALE)})
for name, rows in (("forecasts_api.csv", api), ("forecasts_arima.csv", arima)):
    with open(HERE / name, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["horizon", "series", "cutoff", "forecaster", "step", "week",
                                           "actual_tokens", "forecast_tokens"])
        w.writeheader()
        w.writerows(rows)


def scale(s, c):
    y = [S[s][w] for w in sorted(S[s]) if w <= c]
    return sum(abs(b - a) for a, b in zip(y, y[1:])) / (len(y) - 1)


mase = [{"horizon": "h1", "level": "model", "series": r["series"], "cutoff": r["cutoff"], "forecaster": r["forecaster"],
         "mase": abs(int(r["forecast_tokens"]) - int(r["actual_tokens"])) / scale(r["series"], r["cutoff"])}
        for r in api + arima]
keys = {(m["series"], m["cutoff"], m["forecaster"]) for m in mase}
fs = sorted({m["forecaster"] for m in mase})
assert all((s, c, f) in keys for s, c in want for f in fs), "missing forecasts"
ser = defaultdict(list)
for m in mase:
    ser[(m["series"], m["forecaster"])].append(m["mase"])
series = sorted({m["series"] for m in mase})
rows = [{"level": "model", "horizon": "h1", "forecaster": f,
         "rel_mase": round(statistics.geometric_mean([statistics.mean(ser[(s, f)]) / statistics.mean(ser[(s, "seasonal-naive")])
                                                      for s in series]), 4)} for f in fs]
for k, r in enumerate(sorted(rows, key=lambda r: r["rel_mase"]), 1):
    r["position"] = k
for name, out in (("mase_long.csv", mase), ("standings.csv", sorted(rows, key=lambda r: r["position"]))):
    with open(HERE / name, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
print(f"wrote loop data: {len(series)} LLMs, {len(want)} windows, {len(fs)} forecasters")
