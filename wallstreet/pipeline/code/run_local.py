"""Local non-foundation models for every series in config.py, same protocol as the Coinbase bundle
(code/run_baselines.py + code/run_ml.py there): 12 rolling h=1 forecasts on the API's 12 test quarters, each refit on
the data before it, scored as |error| / the API seasonal-naive |error| on that quarter, geomean over the 12. Locked
forecast: h=4 from the full history.

Models: AutoARIMA, AutoETS, AutoTheta (season 4), Naive (statsforecast); LightGBM, XGBoost (mlforecast, first
differences, lags 1-4); N-BEATS (identity stacks, input 4); Prophet (yearly seasonality, 2 Fourier terms).
Series run on a synthetic quarterly calendar (QS from 2000) so fiscal year ends don't matter; a local SeasonalNaive
must equal the API's on every fold, which checks the alignment.

Each model family runs in its own process (OpenMP clash between LightGBM/XGBoost and torch on macOS).
Writes out/<series>/local_per_fold.csv, local_locked.csv, local_timing.csv and leaderboard_all.csv (API + local).

    python code/run_local.py                 # every series
    python code/run_local.py --series amd_dc
"""
import csv, json, logging, math, subprocess, sys, time, warnings
import pandas as pd
import config

FAMILIES = {"stats": ["auto-arima", "auto-ets", "auto-theta", "naive", "seasonal-naive-local"],
            "lightgbm": ["lightgbm"], "xgboost": ["xgboost"], "n-beats": ["n-beats"], "prophet": ["prophet"]}


def frame(y):
    return pd.DataFrame({"unique_id": "s", "ds": pd.date_range("2000-01-01", periods=len(y), freq="QS"), "y": y})


def forecaster(fam):
    """predict(df, h) -> {model: [h values]} for one model family."""
    warnings.filterwarnings("ignore")
    for name in ("prophet", "cmdstanpy", "pytorch_lightning", "lightning", "lightning.pytorch", "lightning_fabric"):
        logging.getLogger(name).setLevel(logging.ERROR)
    if fam == "stats":
        from statsforecast import StatsForecast
        from statsforecast.models import AutoARIMA, AutoETS, AutoTheta, Naive, SeasonalNaive
        names = dict(zip(["AutoARIMA", "AutoETS", "AutoTheta", "Naive", "SeasonalNaive"], FAMILIES["stats"]))

        def predict(df, h):
            sf = StatsForecast(models=[AutoARIMA(season_length=4), AutoETS(season_length=4), AutoTheta(season_length=4),
                                       Naive(), SeasonalNaive(season_length=4)], freq="QS", n_jobs=1)
            p = sf.forecast(df=df, h=h)
            p = p.reset_index() if "unique_id" not in p.columns else p
            return {m: p[c].tolist() for c, m in names.items()}
    elif fam in ("lightgbm", "xgboost"):
        from mlforecast import MLForecast
        from mlforecast.target_transforms import Differences
        if fam == "lightgbm":
            import lightgbm as lgb
            reg = lgb.LGBMRegressor(n_estimators=100, learning_rate=0.05, num_leaves=4, min_child_samples=1,
                                    min_data_in_bin=1, verbose=-1, random_state=1)
        else:
            import xgboost as xgb
            reg = xgb.XGBRegressor(n_estimators=100, learning_rate=0.05, max_depth=2, random_state=1)

        def predict(df, h):
            p = MLForecast(models={fam: reg}, freq="QS", lags=[1, 2, 3, 4],
                           target_transforms=[Differences([1])]).fit(df).predict(h)
            return {fam: p.sort_values("ds")[fam].tolist()}
    elif fam == "n-beats":
        from neuralforecast import NeuralForecast
        from neuralforecast.models import NBEATS

        def predict(df, h):
            nf = NeuralForecast(models=[NBEATS(h=h, input_size=4, stack_types=["identity"] * 3, max_steps=300, random_seed=1,
                                               scaler_type="robust", accelerator="cpu", devices=1, enable_progress_bar=False,
                                               enable_model_summary=False, logger=False)], freq="QS")
            nf.fit(df)
            p = nf.predict()
            p = p.reset_index() if "unique_id" not in p.columns else p
            return {"n-beats": p.sort_values("ds")["NBEATS"].tolist()}
    else:
        from prophet import Prophet

        def predict(df, h):
            m = Prophet(yearly_seasonality=2, weekly_seasonality=False, daily_seasonality=False).fit(df[["ds", "y"]])
            return {"prophet": m.predict(m.make_future_dataframe(periods=h, freq="QS", include_history=False))["yhat"].tolist()}
    return predict


def child(key, fam):
    y = [v for _, v in config.load(key)["hist"]]
    predict, out = forecaster(fam), {"folds": [], "locked": None, "timing": []}
    for k in range(12):
        n = len(y) - 12 + k
        t = time.perf_counter()
        out["folds"].append({m: v[0] for m, v in predict(frame(y[:n]), 1).items()})
        out["timing"].append({"family": fam, "stage": f"fold {k + 1}", "train_quarters": n, "seconds": round(time.perf_counter() - t, 3)})
    t = time.perf_counter()
    out["locked"] = predict(frame(y), 4)
    out["timing"].append({"family": fam, "stage": "locked h=4", "train_quarters": len(y), "seconds": round(time.perf_counter() - t, 3)})
    d = config.OUT / key / "parts"
    d.mkdir(parents=True, exist_ok=True)
    json.dump(out, open(d / f"{fam}.json", "w"))


def write(path, rows):
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def collect(key):
    s = config.load(key)
    d = config.OUT / key
    naive = sorted((r for r in s["folds"] if r["model"] == "seasonal-naive"), key=lambda r: int(r["fold"]))
    rows, locked, timing = [], [], []
    for fam in FAMILIES:
        part = json.load(open(d / "parts" / f"{fam}.json"))
        timing += part["timing"]
        for k, preds in enumerate(part["folds"]):
            nv, a = naive[k], float(naive[k]["actual"])
            if "seasonal-naive-local" in preds:               # alignment check against the API baseline
                assert abs(preds["seasonal-naive-local"] - float(nv["forecast"])) < 1e-3, (key, k, preds["seasonal-naive-local"], nv["forecast"])
            for m, f in preds.items():
                if m == "seasonal-naive-local":
                    continue
                e = abs(f - a)
                rows.append({"model": m, "fold": k + 1, "test_quarter": s["hist"][len(s["hist"]) - 12 + k][0], "actual": a,
                             "forecast": round(f, 3), "abs_error": round(e, 3), "naive_abs_error": float(nv["naive_abs_error"]),
                             "rel_to_naive": e / float(nv["naive_abs_error"]) if float(nv["naive_abs_error"]) else float("nan")})
        for m, v in part["locked"].items():
            if m != "seasonal-naive-local":
                locked.append({"model": m, **{f"h{i + 1}": round(x, 1) for i, x in enumerate(v)}})
    write(d / "local_per_fold.csv", rows)
    write(d / "local_locked.csv", locked)
    write(d / "local_timing.csv", timing)
    board = [{"model": r["model"], "rel_geomean": float(r["rel_geomean"]), "rel_arith": float(r["rel_arith"]),
              "raw_mae": float(r["raw_mae"]), "source": "api"} for r in s["board"]]
    for m in sorted({r["model"] for r in rows}):
        rel = [r["rel_to_naive"] for r in rows if r["model"] == m]
        board.append({"model": m, "rel_geomean": math.exp(sum(math.log(max(x, 1e-12)) for x in rel) / len(rel)),
                      "rel_arith": sum(rel) / len(rel), "raw_mae": sum(r["abs_error"] for r in rows if r["model"] == m) / len(rel),
                      "source": "local"})
    board.sort(key=lambda r: r["rel_geomean"])
    write(d / "leaderboard_all.csv", board)
    print(f"{key}: " + ", ".join(f"{r['model']} #{i + 1} {r['rel_geomean']:.3f}" for i, r in enumerate(board)
                                 if r["source"] == "local" or i == 0))


if "--child" in sys.argv:
    child(sys.argv[sys.argv.index("--child") + 1], sys.argv[sys.argv.index("--child") + 2])
    sys.exit()

keys = [sys.argv[sys.argv.index("--series") + 1]] if "--series" in sys.argv else list(config.SERIES)
for key in keys:
    for fam in FAMILIES:
        t = time.perf_counter()
        subprocess.run([sys.executable, "-u", __file__, "--child", key, fam], check=True)
        print(f"  {key} {fam}: {time.perf_counter() - t:.1f}s", flush=True)
    collect(key)
