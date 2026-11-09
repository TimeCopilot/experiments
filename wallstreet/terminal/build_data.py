"""Collects every series (Coinbase + the 8 earnings-program series) into data.js for the terminal prototype.

Per series: actual history, the 12 h=1 backtest forecasts and the locked h=4 forecast of every model (API + local),
the rel. MASE board, Street consensus where we have it, and the reported actual where the print is already out.
"""
import csv, json, pathlib, shutil, sys

# report dates for prints still outstanding (earnings_dump_2026-11-04.csv)
# fiscal -> calendar quarter: (quarters to shift, years to shift); calendar-year filers need none
FISCAL = {"apple_iphone": (-1, 0), "disney_exp": (-1, 0), "nvidia_dc": (0, -1), "walmart_us": (0, -1), "hd_net_sales": (0, 0)}


def cal(key, q):
    """'Q4 FY2026' -> "Q3 '26" (calendar quarter the fiscal quarter mostly covers)."""
    n, y = int(q[1]), int(q[-4:])
    dq, dy = FISCAL.get(key, (0, 0))
    n, y = n + dq, y + dy
    if n < 1: n, y = n + 4, y - 1
    return f"Q{n} '{str(y)[2:]}"


PRINTS = {"disney_exp": "Nov 17, 2026", "hd_net_sales": "Nov 17, 2026", "nvidia_dc": "Nov 17, 2026", "walmart_us": "Nov 19, 2026"}

HERE = pathlib.Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent / "pipeline/code"), str(HERE.parent / "source/earnings-tracker/coinbase/code")]
import config, plot_company as pc                         # noqa: E402  (renders nothing on import beyond its own run)
import plot_coinbase_h1 as cb                              # noqa: E402
cb.ML = {"lightgbm", "xgboost", "n-beats", "prophet"}     # the module reuses ML as a chart margin after loading

TICK = {"apple_iphone": "AAPL", "palantir_total": "PLTR", "amd_dc": "AMD", "disney_exp": "DIS", "hd_net_sales": "HD",
        "mcd_total": "MCD", "mcd_franchised": "MCD", "nvidia_dc": "NVDA", "walmart_us": "WMT", "shopify_gmv": "SHOP"}
kind = lambda m: pc.TAG.get(m, "foundation")
out = []

for key, (net_or_total, col) in [("net", cb.SERIES["net"])]:        # total revenue dropped from the site
    actual = {r["quarter"]: float(r[col]) for r in cb.rows}
    locked = cb.locked_of(key)
    models = [{"m": r["model"], "kind": kind(r["model"]), "score": round(float(r["rel_geomean"]), 4),
               "bt": [round(v, 1) for _, v in cb.backtest(key, r["model"], actual)],
               "fut": [round(float(locked[r["model"]][c]), 1) for c in cb.HCOLS]} for r in cb.board_of(key)]
    out.append({"id": f"coin_{key}", "tick": "COIN", "company": "Coinbase", "metric": net_or_total,
                "hist": [[q, actual[q]] for q in cb.QS if q in actual], "fut": cb.FUT, "models": models,
                "consensus": {"value": cb.CONSENSUS[key], "src": "Zacks, Oct 26, 2026"},   # Zacks Q3 preview, net revenue (total-revenue estimate was $1.17B)
                "result": {"net": 1160.5, "total": 1215.6}[key]})

for key in config.SERIES:
    p = pc.series(key)
    local = list(csv.DictReader(open(config.OUT / key / "local_per_fold.csv")))
    models = []
    for r in p["board"]:
        m = r["model"]
        rs = sorted((x for x in (local if m in pc.NONFM - {"seasonal-naive"} else p["folds"]) if x["model"] == m),
                    key=lambda x: int(x["fold"]))
        bt = [round(float(x["forecast"]), 1) for x in rs]
        assert len(bt) == 12, (key, m)
        models.append({"m": m, "kind": kind(m), "score": round(float(r["rel_geomean"]), 4), "bt": bt,
                       "fut": [round(v, 1) for v in p["locked_all"][m]]})
    c = pc.CONSENSUS.get(key)
    out.append({"id": key, "tick": TICK[key], "company": p["company"], "metric": p["metric"], "hist": p["hist"],
                "fut": p["fut"], "models": models, "consensus": {"value": c[0], "src": c[1]} if c else None, "result": pc.RESULTS.get(key), "prints": PRINTS.get(key), "cal": cal(key, p["fut"][0])})

for s in out:
    print(f'{s["tick"]:5} {s["metric"]:28} {len(s["hist"])}q  {len(s["models"])} models  #1 {s["models"][0]["m"]}')
reported = {o["tick"] for o in out if o["result"] is not None}
out.sort(key=lambda o: o["tick"] not in reported)        # tickers that already printed lead the tab bar (stable sort)
(HERE / "data.js").write_text("window.SERIES = " + json.dumps(out, separators=(",", ":")) + ";\n")
