"""Check the article's headline claims against the results files in this repo.

Reads standings.csv (weekly), daily/standings.csv, loop/mase_long.csv, gift_eval.csv and fev.csv, and prints
PASS or DIFF for each claim. Run `make score` first to rebuild the standings from the saved forecasts.
Exit code 1 if any claim differs. After `make rerun`, small API-side differences (the reproducibility check found
12 of the original 17 API models identical and the rest within 0.2%) can move models that are nearly tied.

    python verify.py
"""
import csv, pathlib, statistics, sys
from collections import defaultdict

HERE = pathlib.Path(__file__).resolve().parent
BASE = {"seasonal-naive", "auto-arima"}


def standings(path):
    out = defaultdict(dict)                                  # (level, horizon) -> {forecaster: (position, rel_mase)}
    for r in csv.DictReader(open(path)):
        out[(r["level"], r["horizon"])][r["forecaster"]] = (int(r["position"]), float(r["rel_mase"]))
    return out


W, D = standings(HERE / "standings.csv"), standings(HERE / "daily" / "standings.csv")
fm = lambda board: {f: v for f, v in board.items() if f not in BASE}
beat = lambda board, ref: sum(v[1] < board[ref][1] for v in fm(board).values())
beat_both = lambda board: sum(v[1] < min(board["seasonal-naive"][1], board["auto-arima"][1]) for v in fm(board).values())
winner = lambda board: min(board, key=lambda f: board[f][0])

ser = defaultdict(list)                                      # loop animation: per-LLM winners, 1 week ahead
for r in csv.DictReader(open(HERE / "loop" / "mase_long.csv")):
    ser[(r["series"], r["forecaster"])].append(float(r["mase"]))
llms = sorted({s for s, _ in ser})
loop_win = {s: min({f for t, f in ser if t == s}, key=lambda f: statistics.mean(ser[(s, f)]) / statistics.mean(ser[(s, "seasonal-naive")]))
            for s in llms}
gift = {r["forecaster"]: int(r["gift_rank_ours"]) for r in csv.DictReader(open(HERE / "gift_eval.csv")) if r["gift_rank_ours"]}
fev = {r["forecaster"]: int(r["fev_rank_ours"]) for r in csv.DictReader(open(HERE / "fev.csv")) if r["fev_rank_ours"]}

CLAIMS = [
    ("Daily data, individual LLMs, 7 days: all 21 foundation models beat both baselines", beat_both(D[("model", "d7")]), 21),
    ("Daily data, individual LLMs, 1 day: all 21 foundation models beat seasonal naive", beat(D[("model", "d1")], "seasonal-naive"), 21),
    ("Weekly, all tokens, 1 week: 17 of 21 foundation models beat seasonal naive", beat(W[("total", "h1")], "seasonal-naive"), 17),
    ("Weekly, individual LLMs, 4 weeks: no foundation model beats seasonal naive", beat(W[("model", "h4")], "seasonal-naive"), 0),
    ("TimesFM 3 on all tokens at 1 day, 7 days, 1 week, 4 weeks", [D[("total", "d1")]["timesfm-3"][0], D[("total", "d7")]["timesfm-3"][0],
                                                                    W[("total", "h1")]["timesfm-3"][0], W[("total", "h4")]["timesfm-3"][0]], [10, 20, 20, 9]),
    ("Timestral 209M on all tokens at 1 day, 7 days, 1 week, 4 weeks", [D[("total", "d1")]["timestral-209m"][0], D[("total", "d7")]["timestral-209m"][0],
                                                                         W[("total", "h1")]["timestral-209m"][0], W[("total", "h4")]["timestral-209m"][0]], [11, 14, 10, 12]),
    ("t0-gamma on all tokens at 1 day, 7 days, 1 week, 4 weeks", [D[("total", "d1")]["t0-gamma"][0], D[("total", "d7")]["t0-gamma"][0],
                                                                   W[("total", "h1")]["t0-gamma"][0], W[("total", "h4")]["t0-gamma"][0]], [8, 17, 23, 22]),
    ("All-token winners at 1 day, 7 days, 1 week, 4 weeks", [winner(D[("total", "d1")]), winner(D[("total", "d7")]), winner(W[("total", "h1")]), winner(W[("total", "h4")])],
     ["auto-arima", "chronos-2", "toto-2-4m", "auto-arima"]),
    ("Chronos-2 Small lowest on individual LLMs at 1 week", winner(W[("model", "h1")]), "chronos-2-small"),
    ("Chronos-Bolt Mini lowest on categories at 4 weeks", winner(W[("category", "h4")]), "chronos-bolt-mini"),
    ("Daily individual LLMs: Timestral 28M 1st at 1 day, Granite PatchTST 1st at 7 days", [winner(D[("model", "d1")]), winner(D[("model", "d7")])],
     ["timestral-28m", "granite-patchtst-r2"]),
    ("Timestral 209M 1st and TimesFM 3 4th on GIFT-Eval and fev-bench among the tested models",
     [gift["timestral-209m"], fev["timestral-209m"], gift["timesfm-3"], fev["timesfm-3"]], [1, 1, 4, 4]),
    ("Loop animation: LLMs, distinct winners, TimesFM 3 wins, Timestral 209M wins, seasonal naive wins",
     [len(llms), len(set(loop_win.values())), sum(w == "timesfm-3" for w in loop_win.values()),
      sum(w == "timestral-209m" for w in loop_win.values()), sum(w == "seasonal-naive" for w in loop_win.values())], [33, 14, 0, 0, 5]),
]

bad = 0
for text, got, want in CLAIMS:
    ok = got == want
    bad += not ok
    print(f"{'PASS' if ok else 'DIFF'}  {text}" + ("" if ok else f"\n      expected {want}, got {got}"))
print(f"\n{len(CLAIMS) - bad} of {len(CLAIMS)} claims reproduce.")
sys.exit(1 if bad else 0)
