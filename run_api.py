"""Backtest forecasts from every TimeCopilot API forecaster for every task in tasks.csv.

Each (series, cutoff) task is sent as its own series: the weeks up to the cutoff plus the h actual weeks
after it, with /v1/cross-validation n_windows=1, so the forecaster sees only data through the cutoff.
Parameters: h = 1 or 4, freq W-MON, season_length 1. Values sent in billions of tokens.
Forecasters: the live /v1/models catalog (16 foundation models + seasonal-naive).

Writes raw/<horizon>_<forecaster>_<chunk>.json and forecasts_api.csv
(horizon, series, cutoff, forecaster, step, week, actual_tokens, forecast_tokens). Reuses raw files
already on disk, so it can be rerun after a failure.

    python run_api.py
"""
import csv, datetime as dt, json, pathlib, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "lib"))
from orlib import post, token, BASE, UA, SCALE

CHUNK = 150
H = {"h1": 1, "h4": 4}
S = json.load(open(HERE / "series.json"))["series"]
TASKS = list(csv.DictReader(open(HERE / "tasks.csv")))
req = urllib.request.Request(BASE + "/v1/models", headers={"Authorization": f"Bearer {token()}", "User-Agent": UA})
with urllib.request.urlopen(req, timeout=120) as r:
    FORECASTERS = [m["id"] for m in json.load(r)["models"]]
(HERE / "raw").mkdir(exist_ok=True)


def payload(t):
    weeks = sorted(S[t["series"]])
    k = weeks.index(t["cutoff"]) + 1
    use = weeks[:k + H[t["horizon"]]]
    return {"unique_id": f"{t['series']}@{t['cutoff']}", "start": f"{use[0]}T00:00:00",
            "y": [S[t["series"]][w] / SCALE for w in use]}


JOBS = []
for hz in H:
    ts = [t for t in TASKS if t["horizon"] == hz]
    for f in FORECASTERS:
        for i in range(0, len(ts), CHUNK):
            JOBS.append((hz, f, i // CHUNK, ts[i:i + CHUNK]))


def one(job):
    hz, f, i, ts = job
    out = HERE / "raw" / f"{hz}_{f}_{i}.json"
    if not out.exists():
        for attempt in range(3):
            try:
                r = post("/v1/cross-validation", {"model": f, "series": [payload(t) for t in ts],
                                                  "parameters": {"h": H[hz], "freq": "W-MON", "season_length": 1,
                                                                 "n_windows": 1, "step_size": 1}}, timeout=1800)
                break
            except Exception as e:
                print(f"  retry {hz} {f} {i}: {e}", flush=True)
                time.sleep(20 * (attempt + 1))
        else:
            raise RuntimeError(f"failed {hz} {f} {i}")
        json.dump(r, open(out, "w"))
        print(f"done {hz} {f} chunk {i} ({len(ts)} series)", flush=True)
    return hz, f, json.load(open(out))


rows = []
with ThreadPoolExecutor(max_workers=4) as ex:
    for hz, f, r in ex.map(one, JOBS):
        for fo in r["folds"]:
            s, c = fo["unique_id"].rsplit("@", 1)
            assert fo["cutoff"][:10] == c, (fo["unique_id"], fo["cutoff"])
            a0 = dt.date.fromisoformat(fo["actual"]["start"][:10])
            for k, (a, p) in enumerate(zip(fo["actual"]["y"], fo["forecast"]["y"])):
                rows.append({"horizon": hz, "series": s, "cutoff": c, "forecaster": f, "step": k + 1,
                             "week": (a0 + dt.timedelta(weeks=k)).isoformat(),
                             "actual_tokens": round(a * SCALE), "forecast_tokens": round(p * SCALE)})

with open(HERE / "forecasts_api.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)
print(f"wrote forecasts_api.csv ({len(rows)} rows, {len(FORECASTERS)} forecasters)")
