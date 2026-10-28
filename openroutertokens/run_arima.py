"""AutoARIMA baseline, run locally (not available on the TimeCopilot API), on the same tasks as run_api.py.

statsforecast AutoARIMA(season_length=1), fit on each task's weeks up to the cutoff (billions of tokens),
forecasting h = 1 or 4 weeks. Writes forecasts_arima.csv in the forecasts_api.csv format, forecaster "auto-arima".

    python run_arima.py
"""
import csv, datetime as dt, json, pathlib
import pandas as pd
from statsforecast import StatsForecast
from statsforecast.models import AutoARIMA

HERE = pathlib.Path(__file__).resolve().parent
SCALE = 1e9
H = {"h1": 1, "h4": 4}
S = json.load(open(HERE / "series.json"))["series"]
TASKS = list(csv.DictReader(open(HERE / "tasks.csv")))

rows = []
for hz, h in H.items():
    recs = []
    for t in (t for t in TASKS if t["horizon"] == hz):
        for w in sorted(S[t["series"]]):
            if w <= t["cutoff"]:
                recs.append((f"{t['series']}@{t['cutoff']}", pd.Timestamp(w), S[t["series"]][w] / SCALE))
    df = pd.DataFrame(recs, columns=["unique_id", "ds", "y"])
    fc = StatsForecast(models=[AutoARIMA(season_length=1)], freq="W-MON", n_jobs=1).forecast(df=df, h=h)
    fc = fc.reset_index() if "unique_id" not in fc.columns else fc
    for uid, g in fc.groupby("unique_id"):
        s, c = uid.rsplit("@", 1)
        for k, (ds, p) in enumerate(zip(g["ds"], g["AutoARIMA"])):
            wk = ds.date().isoformat()
            assert wk == (dt.date.fromisoformat(c) + dt.timedelta(weeks=k + 1)).isoformat()
            rows.append({"horizon": hz, "series": s, "cutoff": c, "forecaster": "auto-arima", "step": k + 1,
                         "week": wk, "actual_tokens": S[s][wk], "forecast_tokens": round(p * SCALE)})
    print(f"{hz}: {fc['unique_id'].nunique()} tasks", flush=True)

with open(HERE / "forecasts_arima.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)
print(f"wrote forecasts_arima.csv ({len(rows)} rows)")
