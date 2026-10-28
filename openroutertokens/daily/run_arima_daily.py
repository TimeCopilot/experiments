"""AutoARIMA baseline on the daily tasks, run locally (not on the TimeCopilot API).

statsforecast AutoARIMA(season_length=7), fit on each task's days up to the cutoff (billions of tokens),
forecasting 7 days. Writes forecasts_arima.csv in the forecasts_api.csv format, forecaster "auto-arima".

    python daily/run_arima_daily.py
"""
import csv, datetime as dt, json, pathlib
import pandas as pd
from statsforecast import StatsForecast
from statsforecast.models import AutoARIMA

HERE = pathlib.Path(__file__).resolve().parent
SCALE, H = 1e9, 7
S = json.load(open(HERE / "series.json"))["series"]
TASKS = list(csv.DictReader(open(HERE / "tasks.csv")))

recs = [(f"{t['series']}@{t['cutoff']}", pd.Timestamp(d), S[t["series"]][d] / SCALE)
        for t in TASKS for d in sorted(S[t["series"]]) if d <= t["cutoff"]]
df = pd.DataFrame(recs, columns=["unique_id", "ds", "y"])
fc = StatsForecast(models=[AutoARIMA(season_length=7)], freq="D", n_jobs=1).forecast(df=df, h=H)
fc = fc.reset_index() if "unique_id" not in fc.columns else fc
rows = []
for uid, g in fc.groupby("unique_id"):
    s, c = uid.rsplit("@", 1)
    for k, (ds, p) in enumerate(zip(g["ds"], g["AutoARIMA"])):
        d = ds.date().isoformat()
        assert d == (dt.date.fromisoformat(c) + dt.timedelta(days=k + 1)).isoformat()
        rows.append({"series": s, "cutoff": c, "forecaster": "auto-arima", "step": k + 1, "day": d,
                     "actual_tokens": S[s][d], "forecast_tokens": round(p * SCALE)})
with open(HERE / "forecasts_arima.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)
print(f"wrote forecasts_arima.csv ({len(rows)} rows, {fc['unique_id'].nunique()} tasks)")
