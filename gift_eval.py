"""GIFT-Eval MASE for the forecasters we test, from the public results in SalesforceAIResearch/gift-eval
(results/<model>/all_results.csv, sparse clone in gift_eval_repo/, commit noted in the output).

Aggregate as on the GIFT-Eval leaderboard: per dataset configuration, MASE[0.5] ÷ Seasonal_Naive's MASE on that
configuration, then the geometric mean over all configurations. Ranks are by that value:
  gift_rank_all      among every model in the repo with testdata_leakage "No" and all configurations present
  gift_rank_ours     among the forecasters in this benchmark that have a GIFT-Eval entry

Writes gift_eval.csv (forecaster, gift_eval_model, configs, gift_mase, gift_rank_all, gift_rank_ours).

    python gift_eval.py
"""
import csv, json, math, pathlib, subprocess

HERE = pathlib.Path(__file__).resolve().parent
RES = HERE / "gift_eval_repo" / "results"
OURS = {"seasonal-naive": "Seasonal_Naive", "auto-arima": "Auto_Arima", "chronos-bolt-small": "chronos_bolt_small",
        "chronos-2": "Chronos-2", "timesfm-2": "timesfm_2_0_500m", "timesfm-2.5-200m": "TimesFM-2.5",
        "timesfm-3": "TimesFM-3", "tirex-2": "TiRex-2-Pretrained", "tirex-2-gifteval-zs": "TiRex-2-Zeroshot",
        "granite-patchtst-r2": "Granite-PatchTST-FM-r2", "toto-2-4m": "Toto-2.0-4m", "toto-2-22m": "Toto-2.0-22m",
        "toto-2-313m": "Toto-2.0-313m", "toto-2-1b": "Toto-2.0-1B", "t0-alpha": "t0-alpha", "t0-beta": "t0-beta",
        "t0-gamma": "t0-gamma", "timestral-5m": "Timestral-5M", "timestral-28m": "Timestral-28M",
        "timestral-123m": "Timestral-123M", "timestral-209m": "Timestral-209M", "chronos-bolt-mini": None, "chronos-2-small": None}


def load(m):
    return {r["dataset"]: float(r["eval_metrics/MASE[0.5]"]) for r in csv.DictReader(open(RES / m / "all_results.csv"))}


base = load("Seasonal_Naive")
score = {}
for d in sorted(RES.iterdir()):
    try:
        cfg = json.load(open(d / "config.json"))
        m = load(d.name)
    except (OSError, ValueError, KeyError):
        continue
    if set(base) - set(m):
        continue
    gm = math.exp(sum(math.log(m[k] / base[k]) for k in base) / len(base))
    score[d.name] = (gm, cfg.get("testdata_leakage", "").strip().lower() == "no")

clean = sorted((m for m, (_, ok) in score.items() if ok), key=lambda m: score[m][0])
ours = sorted((f for f, g in OURS.items() if g in score), key=lambda f: score[OURS[f]][0])
rows = []
for f, g in OURS.items():
    rows.append({"forecaster": f, "gift_eval_model": g or "", "configs": len(base) if g in score else "",
                 "gift_mase": round(score[g][0], 4) if g in score else "",
                 "gift_rank_all": clean.index(g) + 1 if g in clean else "",
                 "gift_rank_ours": ours.index(f) + 1 if f in ours else ""})
rows.sort(key=lambda r: r["gift_rank_ours"] or 99)
with open(HERE / "gift_eval.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)
commit = subprocess.run(["git", "-C", str(RES.parent), "log", "-1", "--format=%h %cd"], capture_output=True, text=True).stdout.strip()
print(f"GIFT-Eval results at {commit}; {len(base)} configurations; {len(clean)} models without test leakage")
for r in rows:
    print(f"  {r['gift_rank_ours'] or '-':>2}  {r['forecaster']:<20} {r['gift_eval_model']:<24} "
          f"MASE {r['gift_mase'] or '-':<7} overall #{r['gift_rank_all'] or '-'}")
