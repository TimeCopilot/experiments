"""fev-bench MASE for the forecasters we test, from the public per-task results in autogluon/fev
(benchmarks/fev_bench/results/*.csv, sparse clone in fev_repo/, commit noted in the output).

Aggregate as the fev-bench leaderboard does for its MASE skill score: per task, MASE ÷ Seasonal Naive's MASE on
that task; on tasks a model reports it was trained on, Chronos-Bolt's ratio is used instead; ratios clipped to
[0.01, 100]; failed tasks count as 1 (Seasonal Naive); then the geometric mean over all tasks. Ranks are by that
value among the forecasters in this benchmark that have a fev-bench entry. "hidden" marks results that are in the
repo but not on the public leaderboard.

Writes fev.csv (forecaster, fev_model, tasks, fev_mase, fev_rank_ours, hidden, leak_tasks, failed_tasks).

    python fev.py
"""
import csv, math, pathlib, re, subprocess

HERE = pathlib.Path(__file__).resolve().parent
BENCH = HERE / "fev_repo" / "benchmarks" / "fev_bench"
RES = BENCH / "results"
OURS = {"seasonal-naive": "seasonal_naive", "auto-arima": "autoarima", "chronos-2": "chronos-2",
        "timesfm-2.5-200m": "timesfm-2_5", "timesfm-3": "timesfm-3", "tirex-2": "tirex-2", "t0-beta": "t0-beta",
        "toto-2-4m": "toto-2_0-4m", "toto-2-22m": "toto-2_0-22m", "toto-2-313m": "toto-2_0-313m",
        "toto-2-1b": "toto-2_0-1b", "t0-gamma": "t0-gamma", "timestral-5m": "timestral-5m", "timestral-28m": "timestral-28m",
        "timestral-123m": "timestral-123m", "timestral-209m": "timestral-209m", "tirex-2-gifteval-zs": None, "granite-patchtst-r2": None, "t0-alpha": None,
        "chronos-2-small": None, "chronos-bolt-small": None, "chronos-bolt-mini": None, "timesfm-2": None}


def load(f):
    rows = list(csv.DictReader(open(RES / f"{f}.csv")))
    return (rows[0]["model_name"], {r["task_name"]: float(r["MASE"]) for r in rows},
            {r["task_name"] for r in rows if r.get("trained_on_this_dataset", "").strip().lower() == "true"})


_, base, _ = load("seasonal_naive")
_, bolt, _ = load("chronos-bolt")
hidden = set(re.findall(r"^([\w.-]+):\n(?:  .*\n)*?  hidden: true", open(BENCH / "models.yaml").read(), re.M))
score = {}
for f, fid in OURS.items():
    if not fid:
        continue
    name, m, leak = load(fid)
    logs = []
    for t, b in base.items():
        r = bolt[t] / b if t in leak else m[t] / b if t in m else 1.0
        logs.append(math.log(min(max(r, 0.01), 100)))
    score[f] = {"fev_model": name, "tasks": len(base), "fev_mase": round(math.exp(sum(logs) / len(logs)), 4),
                "hidden": fid in hidden, "leak_tasks": len(leak & set(base)), "failed_tasks": len(set(base) - set(m))}

ranked = sorted(score, key=lambda f: score[f]["fev_mase"])
rows = [{"forecaster": f, **{k: "" for k in ("fev_model", "tasks", "fev_mase")}, "fev_rank_ours": "",
         "hidden": "", "leak_tasks": "", "failed_tasks": "", **score.get(f, {})} for f in OURS]
for r in rows:
    if r["forecaster"] in score:
        r["fev_rank_ours"] = ranked.index(r["forecaster"]) + 1
rows.sort(key=lambda r: r["fev_rank_ours"] or 99)
fields = ["forecaster", "fev_model", "tasks", "fev_mase", "fev_rank_ours", "hidden", "leak_tasks", "failed_tasks"]
with open(HERE / "fev.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=fields)
    w.writeheader()
    w.writerows({k: r[k] for k in fields} for r in rows)
commit = subprocess.run(["git", "-C", str(BENCH), "log", "-1", "--format=%h %cd"], capture_output=True, text=True).stdout.strip()
print(f"fev-bench results at {commit}; {len(base)} tasks; hidden on the leaderboard: {sorted(hidden)}")
for r in rows:
    print(f"  {r['fev_rank_ours'] or '-':>2}  {r['forecaster']:<20} {r['fev_model']:<16} MASE {r['fev_mase'] or '-':<7}"
          f"{'  hidden' if r['hidden'] else ''}{'  leak ' + str(r['leak_tasks']) if r['leak_tasks'] else ''}"
          f"{'  failed ' + str(r['failed_tasks']) if r['failed_tasks'] else ''}")
