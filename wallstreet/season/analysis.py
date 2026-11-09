"""Season-wide numbers for the unified report, from terminal/data.js (same data the site shows) plus the public
GIFT-Eval and fev-bench results already used in the OpenRouter article.

  cv        geomean over the 10 series of each model's 12-fold cross-validation rel. MASE (seasonal naive = 1)
  print     geomean over the reported prints of |locked h1 error| / |seasonal-naive locked h1 error|
  gift      GIFT-Eval overall (openroutertokens/gift_eval.csv) and quarterly (m4_quarterly/Q/short ÷ Seasonal_Naive)
  fev       fev-bench overall (openroutertokens/fev.csv)

Writes season.json.
"""
import csv, json, math, pathlib

HERE = pathlib.Path(__file__).resolve().parent
EXP = pathlib.Path.home() / "Documents/GitHub/experiments/openroutertokens"
GREPO = pathlib.Path.home() / "Documents/GitHub/openrouter-tsfm-benchmark-fork/gift_eval_repo/results"
GIFT_NAME = {"tabby": "Tabby"}                                  # extra GIFT-Eval entries not in the OpenRouter set

t = (HERE.parent / "terminal/data.js").read_text()
S = json.loads(t[t.index("["):t.rindex("]") + 1])
gm = lambda xs: math.exp(sum(math.log(max(x, 1e-9)) for x in xs) / len(xs))

prints = []
for s in S:
    if s["result"] is None:
        continue
    a = s["result"]
    naive = next(m for m in s["models"] if m["m"] == "seasonal-naive")
    ne = abs(naive["fut"][0] - a)
    rows = sorted(({"m": m["m"], "kind": m["kind"], "fcst": m["fut"][0], "err": m["fut"][0] - a,
                    "rel": abs(m["fut"][0] - a) / ne, "cv": m["score"], "cv_rank": i + 1} for i, m in enumerate(s["models"])),
                  key=lambda r: abs(r["err"]))
    for i, r in enumerate(rows):
        r["print_rank"] = i + 1
    st = s["consensus"]["value"] - a if s["consensus"] else None
    cv1 = next(r for r in rows if r["cv_rank"] == 1)
    prints.append({"id": s["id"], "tick": s["tick"], "company": s["company"], "metric": s["metric"], "q": s["fut"][0],
                   "actual": a, "street": s["consensus"]["value"] if s["consensus"] else None, "street_err": st,
                   "street_src": s["consensus"]["src"] if s["consensus"] else None,
                   "best": rows[0], "cv1": cv1, "naive_err": naive["fut"][0] - a,
                   "beat": sum(abs(r["err"]) < abs(st) for r in rows) if st is not None else None,
                   "n": len(rows), "median_err": sorted(r["fcst"] for r in rows)[len(rows) // 2] - a, "rows": rows})

models = sorted({m["m"] for s in S for m in s["models"]})
kind = {m["m"]: m["kind"] for s in S for m in s["models"]}
board = []
for m in models:
    cv = [next(x["score"] for x in s["models"] if x["m"] == m) for s in S]
    pr = [next(r["rel"] for r in p["rows"] if r["m"] == m) for p in prints]
    board.append({"m": m, "kind": kind[m], "cv": gm(cv), "print": gm(pr),
                  "beat_street": sum(abs(next(r["err"] for r in p["rows"] if r["m"] == m)) < abs(p["street_err"]) for p in prints)})

gift = {r["forecaster"]: float(r["gift_mase"]) for r in csv.DictReader(open(EXP / "gift_eval.csv")) if r["gift_mase"]}
fev = {r["forecaster"]: float(r["fev_mase"]) for r in csv.DictReader(open(EXP / "fev.csv")) if r["fev_mase"]}
names = {**{r["forecaster"]: r["gift_eval_model"] for r in csv.DictReader(open(EXP / "gift_eval.csv")) if r["gift_eval_model"]}, **GIFT_NAME}


def q_mase(name):
    rows = {r["dataset"]: float(r["eval_metrics/MASE[0.5]"]) for r in csv.DictReader(open(GREPO / name / "all_results.csv"))}
    return rows.get("m4_quarterly/Q/short")


base_q = q_mase("Seasonal_Naive")
for b in board:
    b["gift"] = gift.get(b["m"])
    b["fev"] = fev.get(b["m"])
    n = names.get(b["m"])
    b["gift_q"] = (q_mase(n) / base_q) if n and (GREPO / n).exists() and q_mase(n) else None
    if b["m"] == "tabby" and b["gift"] is None:                # overall GIFT-Eval for Tabby, same aggregation as gift_eval.py
        base = {r["dataset"]: float(r["eval_metrics/MASE[0.5]"]) for r in csv.DictReader(open(GREPO / "Seasonal_Naive/all_results.csv"))}
        mm = {r["dataset"]: float(r["eval_metrics/MASE[0.5]"]) for r in csv.DictReader(open(GREPO / "Tabby/all_results.csv"))}
        if not set(base) - set(mm):
            b["gift"] = gm([mm[k] / base[k] for k in base])


def spearman(xs, ys):
    rk = lambda v: {x: i for i, x in enumerate(sorted(range(len(v)), key=lambda j: v[j]))}
    rx, ry = rk(xs), rk(ys)
    n = len(xs)
    return 1 - 6 * sum((rx[i] - ry[i]) ** 2 for i in range(n)) / (n * (n * n - 1))


corr = {}
for a in ("gift", "gift_q", "fev", "cv"):
    for b_ in ("cv", "print"):
        if a == b_:
            continue
        both = [b for b in board if b.get(a) is not None and b["kind"] == "foundation"]
        corr[f"{a}~{b_}"] = {"n": len(both), "rho": round(spearman([b[a] for b in both], [b[b_] for b in both]), 3)}

json.dump({"prints": prints, "board": board, "corr": corr}, open(HERE / "season.json", "w"), indent=1)
for p in prints:
    print(f"{p['tick']:5} {p['metric'][:22]:22} street {p['street_err']:+9.1f}  best {p['best']['m']:20} {p['best']['err']:+8.1f} (cv#{p['best']['cv_rank']})"
          f"  cv#1 {p['cv1']['m']:18} {p['cv1']['err']:+8.1f} (print#{p['cv1']['print_rank']})  beat {p['beat']}/{p['n']}")
print()
for b in sorted(board, key=lambda b: b["print"])[:12]:
    print(f"{b['m']:22} {b['kind']:13} print {b['print']:.3f}  cv {b['cv']:.3f}  gift {b['gift'] or 0:.3f}  gift_q {b['gift_q'] or 0:.3f}  fev {b['fev'] or 0:.3f}  beatSt {b['beat_street']}")
print(corr)
