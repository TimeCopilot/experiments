"""Exports every number behind the terminal and the write-up as plain CSVs.

  raw/series/<series_id>.csv              quarterly history as reported, with the filing or release it came from
  raw/report_days.csv                     one row per series: report date, lock date, actual and Wall Street consensus
  processed/cross_validation/<id>.csv     12 one-quarter-ahead backtest forecasts per model, scored against seasonal naive
  processed/leaderboards/<id>.csv         cross-validation leaderboard (relative MASE, geometric mean over the 12 quarters)
  processed/locked_forecasts/<id>.csv     each model's forecast for the next 4 quarters, locked before report day
  processed/report_day_scores.csv         every model and Wall Street against the reported number
  processed/season_board.csv              season scores per model, with GIFT-Eval and fev-bench for comparison
  processed/benchmark_correlations.csv    Spearman rank correlations between the rankings

Reads terminal/data.js (built by terminal/build_data.py), season/season.json (season/analysis.py) and, for source links,
the original quarterly CSVs in source/ (not in the repo).

    python3 data/export_data.py
"""
import csv, json, pathlib, re, sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "pipeline/code"))
import config                                             # noqa: E402

t = (ROOT / "terminal/data.js").read_text()
SER = json.loads(t[t.index("["):t.rindex("]") + 1])
SEASON = json.load(open(ROOT / "season/season.json"))
TYPE = {"foundation": "foundation model", "statistical": "statistical", "ML": "machine learning",
        "deep learning": "deep learning", "baseline": "baseline"}
# report dates (company announcements) and the date the foundation-model forecasts were locked
DATES = {"coin_net": ("2026-10-29", "2026-10-29"), "apple_iphone": ("2026-11-02", "2026-11-01"),
         "palantir_total": ("2026-11-02", "2026-11-01"), "shopify_gmv": ("2026-11-03", "2026-10-28"),
         "amd_dc": ("2026-11-03", "2026-11-01"), "mcd_total": ("2026-11-04", "2026-11-02"),
         "mcd_franchised": ("2026-11-04", "2026-11-02"), "disney_exp": ("2026-11-17", "2026-11-01"),
         "hd_net_sales": ("2026-11-17", "2026-11-01"), "nvidia_dc": ("2026-11-17", "2026-11-01"),
         "walmart_us": ("2026-11-19", "2026-11-01")}


def write(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def sources(sid):
    """quarter label -> (quarter end date, source url, notes) from the original extraction files."""
    if sid == "coin_net":
        f, col = ROOT / "source/earnings-tracker/coinbase/raw/coinbase_quarterly.csv", "net_revenue_usd_m"
    else:
        _, _, folder, master, col, *_ = config.SERIES[sid]
        f = config.BUNDLE / folder / master
    out = {}
    for r in csv.DictReader(open(f)):
        if r.get(col) in ("", None):
            continue
        note = re.sub(r"verify_\w+\.md", "an earlier verification note", " ".join((r.get("notes") or "").split()))
        out[config.norm_label(r["quarter"])] = (r.get("quarter_end_date", ""), r.get("source_url", ""), note)
    return out


for s in SER:
    sid = s["id"]
    src = sources(sid)
    write(HERE / f"raw/series/{sid}.csv",
          [{"quarter": q, "quarter_end_date": src.get(q, ("",))[0], "value_usd_m": v,
            "source_url": src.get(q, ("", ""))[1], "notes": src.get(q, ("", "", ""))[2]} for q, v in s["hist"]])
    bt_q = [q for q, _ in s["hist"][-12:]]
    act = dict(s["hist"])
    naive = next(m for m in s["models"] if m["m"] == "seasonal-naive")
    cv = []
    for m in s["models"]:
        for k, q in enumerate(bt_q):
            e, ne = abs(m["bt"][k] - act[q]), abs(naive["bt"][k] - act[q])
            cv.append({"model": m["m"], "model_type": TYPE[m["kind"]], "fold": k + 1, "quarter": q, "actual_usd_m": act[q],
                       "forecast_usd_m": m["bt"][k], "abs_error_usd_m": round(e, 3), "seasonal_naive_abs_error_usd_m": round(ne, 3),
                       "relative_to_naive": round(e / ne, 4) if ne else ""})
    write(HERE / f"processed/cross_validation/{sid}.csv", cv)
    write(HERE / f"processed/leaderboards/{sid}.csv",
          [{"rank": i + 1, "model": m["m"], "model_type": TYPE[m["kind"]], "cv_relative_mase": m["score"]} for i, m in enumerate(s["models"])])
    write(HERE / f"processed/locked_forecasts/{sid}.csv",
          [{"model": m["m"], "model_type": TYPE[m["kind"]], "cv_rank": i + 1, **{f"{q}_usd_m": v for q, v in zip(s["fut"], m["fut"])}}
           for i, m in enumerate(s["models"])])

write(HERE / "raw/report_days.csv", [{
    "series_id": s["id"], "ticker": s["tick"], "company": s["company"], "metric": s["metric"], "quarter": s["fut"][0],
    "calendar_quarter": s.get("cal") or "Q3 '26", "report_date": DATES[s["id"]][0], "foundation_models_locked_on": DATES[s["id"]][1],
    "status": "reported" if s["result"] is not None else "not reported yet", "actual_usd_m": s["result"] if s["result"] is not None else "",
    "wall_street_consensus_usd_m": s["consensus"]["value"] if s["consensus"] else "",
    "consensus_source": s["consensus"]["src"] if s["consensus"] else "no public estimate yet"} for s in SER])

rows = []
for p in SEASON["prints"]:
    entries = [dict(r, ws=False) for r in p["rows"]] + [{"m": "Wall Street consensus", "kind": "street", "fcst": p["street"], "err": p["street_err"], "ws": True}]
    entries.sort(key=lambda r: abs(r["err"]))
    for i, r in enumerate(entries):
        rows.append({"series_id": p["id"], "quarter": p["q"], "entry": r["m"], "model_type": "Wall Street" if r["ws"] else TYPE[r["kind"]],
                     "forecast_usd_m": r["fcst"], "actual_usd_m": p["actual"], "miss_usd_m": round(r["err"], 3),
                     "miss_pct": round(r["err"] / p["actual"] * 100, 3), "rank_of_34": i + 1, "cv_rank": "" if r["ws"] else r["cv_rank"],
                     "relative_to_naive": round(abs(r["err"]) / abs(p["naive_err"]), 4),
                     "beat_wall_street": "" if r["ws"] else abs(r["err"]) < abs(p["street_err"])})
write(HERE / "processed/report_day_scores.csv", rows)

import math                                              # noqa: E402
gm = lambda xs: math.exp(sum(math.log(max(x, 1e-12)) for x in xs) / len(xs))
street = gm([abs(p["street_err"]) / abs(p["naive_err"]) for p in SEASON["prints"]])
board = sorted(SEASON["board"], key=lambda b: b["print"])
write(HERE / "processed/season_board.csv",
      [{"model": b["m"], "model_type": TYPE[b["kind"]], "report_day_score": round(b["print"], 4), "cv_score": round(b["cv"], 4),
        "report_days_beating_wall_street": b["beat_street"], "report_days": len(SEASON["prints"]),
        "gift_eval_all": round(b["gift"], 4) if b.get("gift") else "", "gift_eval_quarterly": round(b["gift_q"], 4) if b.get("gift_q") else "",
        "fev_bench": round(b["fev"], 4) if b.get("fev") else ""} for b in board]
      + [{"model": "Wall Street consensus", "model_type": "Wall Street", "report_day_score": round(street, 4), "cv_score": "",
          "report_days_beating_wall_street": "", "report_days": len(SEASON["prints"]), "gift_eval_all": "", "gift_eval_quarterly": "", "fev_bench": ""}])
NAMES = {"gift": "GIFT-Eval, all data", "gift_q": "GIFT-Eval, quarterly", "fev": "fev-bench", "cv": "earnings cross-validation", "print": "report day"}
write(HERE / "processed/benchmark_correlations.csv",
      [{"ranking": NAMES[k.split("~")[0]], "compared_with": NAMES[k.split("~")[1]], "foundation_models": v["n"], "spearman_rho": v["rho"]}
       for k, v in SEASON["corr"].items()])
print("wrote", sum(1 for _ in (HERE / "raw").rglob("*.csv")), "raw and", sum(1 for _ in (HERE / "processed").rglob("*.csv")), "processed CSVs")
