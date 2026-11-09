"""Long-form web write-up of the Q3 2026 earnings experiment, in the style of openroutertokens/blog.html.
Preface, results, why this data, what was tested, then the analysis with interactive figures.

Reads ../season/season.json (python ../season/analysis.py) and ../terminal/data.js (the same data the terminal shows).
Writes index.html, self-contained apart from Google Fonts. Every figure is drawn in the browser from the embedded data,
redraws on theme change and on resize, and works with mouse or touch.

    python build_web.py
"""
import html, json, math, pathlib, re

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
D = json.load(open(ROOT / "season/season.json"))
t = (ROOT / "terminal/data.js").read_text()
SER = json.loads(t[t.index("["):t.rindex("]") + 1])
S = {s["id"]: s for s in SER}
P, B, C = D["prints"], D["board"], D["corr"]
AS_OF = "November 4, 2026"
TITLE = "Can we beat Wall Street using ✨FoundationForecast?"
FF = '<a href="https://docs.timecopilot.dev/foundationforecast/">FoundationForecast</a>'
OR_URL = "https://timecopilot.github.io/experiments/openroutertokens/"
gm = lambda xs: math.exp(sum(math.log(max(x, 1e-9)) for x in xs) / len(xs))
esc = html.escape

PRETTY = {"toto-2-4m": "Toto 2 4M", "toto-2-22m": "Toto 2 22M", "toto-2-313m": "Toto 2 313M", "toto-2-1b": "Toto 2 1B",
          "tirex-2": "TiRex 2", "tirex-2-gifteval-zs": "TiRex 2 (GIFT-Eval zero-shot)", "timestral-5m": "Timestral 5M",
          "timestral-28m": "Timestral 28M", "timestral-123m": "Timestral 123M", "timestral-209m": "Timestral 209M",
          "chronos-bolt-small": "Chronos-Bolt Small", "chronos-bolt-mini": "Chronos-Bolt Mini", "chronos-2": "Chronos-2",
          "chronos-2-small": "Chronos-2 Small", "timesfm-2": "TimesFM 2", "timesfm-2.5-200m": "TimesFM 2.5",
          "timesfm-3": "TimesFM 3", "timeh2o-v1": "TimeH2O v1", "timeh2o-v1-tiny": "TimeH2O v1 Tiny", "t0-alpha": "t0-alpha",
          "t0-beta": "t0-beta", "t0-gamma": "t0-gamma", "tabby": "Tabby", "granite-patchtst-r2": "Granite PatchTST r2",
          "auto-arima": "AutoARIMA", "auto-ets": "AutoETS", "auto-theta": "AutoTheta", "naive": "Naive", "prophet": "Prophet",
          "lightgbm": "LightGBM", "xgboost": "XGBoost", "n-beats": "N-BEATS", "seasonal-naive": "seasonal naive"}
nm = lambda m: PRETTY.get(m, m)
NAME = {"coin_net": "Coinbase net revenue", "apple_iphone": "Apple iPhone net sales", "palantir_total": "Palantir revenue",
        "amd_dc": "AMD Data Center revenue", "mcd_total": "McDonald's total revenues", "mcd_franchised": "McDonald's franchised revenues",
        "disney_exp": "Disney Experiences revenue", "hd_net_sales": "Home Depot net sales", "nvidia_dc": "Nvidia Data Center revenue",
        "walmart_us": "Walmart U.S. net sales", "shopify_gmv": "Shopify GMV"}
SHORT = {"coin_net": "Coinbase", "apple_iphone": "Apple", "palantir_total": "Palantir", "amd_dc": "AMD",
         "mcd_total": "McD total", "mcd_franchised": "McD franchised", "disney_exp": "Disney", "hd_net_sales": "Home Depot",
         "nvidia_dc": "Nvidia", "walmart_us": "Walmart", "shopify_gmv": "Shopify"}
m1 = lambda v: f"${v:,.0f}M" if abs(v) < 10000 else f"${v / 1000:,.2f}B"
sm = lambda v: ("+" if v >= 0 else "&minus;&#8288;") + m1(abs(v))
pc = lambda e, a: f"{e / a * 100:+.1f}%".replace("-", "&minus;&#8288;")
ordn = lambda n: f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"
WORD = {0: "none", 1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten"}
PRT = {p["id"]: p for p in P}
COIN_SRC = "Zacks, Oct 26, 2026"

# ── season numbers (same definitions as season/analysis.py) ────────────
street_rel = gm([abs(p["street_err"]) / abs(p["naive_err"]) for p in P])
board = sorted(B, key=lambda b: b["print"])
for i, b in enumerate(board):
    b["prank"] = i + 1
BR = {b["m"]: b for b in board}
beat_season = [b for b in board if b["print"] < street_rel]
any_beat = sum(p["beat"] > 0 for p in P)
cv1_finish = [p["cv1"]["print_rank"] for p in P]
ens_beat = 0
for p in P:
    f = sorted(r["fcst"] for r in p["rows"] if r["kind"] == "foundation")
    p["tsfm_median"] = (f[len(f) // 2 - 1] + f[len(f) // 2]) / 2
    ens_beat += abs(p["tsfm_median"] - p["actual"]) < abs(p["street_err"])
    bf = next(r for r in p["rows"] if r["kind"] == "foundation")           # best foundation model at this print (hindsight)
    p["bf"] = bf
    p["bf_rank34"] = 1 + sum(abs(r["err"]) < abs(bf["err"]) for r in p["rows"]) + (abs(p["street_err"]) < abs(bf["err"]))
    p["bf_beat"] = abs(bf["err"]) < abs(p["street_err"])
top = board[0]
N = P[0]["n"]
n_found = sum(1 for b in board if b["kind"] == "foundation")
best_stat = next(b for b in board if b["kind"] != "foundation")
amd, apple, coin, pltr = PRT["amd_dc"], PRT["apple_iphone"], PRT["coin_net"], PRT["palantir_total"]
mcd_t, mcd_f = PRT["mcd_total"], PRT["mcd_franchised"]
bf_wins = sum(p["bf_beat"] for p in P)
bf_losses = [p for p in P if not p["bf_beat"]]
classical_wins = [p for p in P if p["best"]["kind"] != "foundation"]
apple_lseg = 56540.0
apple_lseg_beat = sum(abs(r["err"]) < abs(apple_lseg - apple["actual"]) for r in apple["rows"])
amd_prev = S["amd_dc"]["hist"][-1][1]
amd_jump = amd["actual"] / amd_prev - 1
amd_med = amd["tsfm_median"]
amd_minlow = min(abs(r["err"]) for r in amd["rows"]) / amd["actual"]
pending = [s for s in SER if s["result"] is None]
n_pending = len(pending)
cv_worst = sorted(board, key=lambda b: -b["cv"])[:3]
cv1_beat = sum(abs(p["cv1"]["err"]) < abs(p["street_err"]) for p in P)
pred_beat = sum(1 for p in P if p["cv1"]["print_rank"] == 1)
rho = lambda k: f'{C[k]["rho"]:+.2f}'.replace("-", "&minus;")
gpool = [b for b in board if b["kind"] == "foundation" and b["gift"] is not None and b["gift_q"] is not None]
rk = lambda key: {b["m"]: i + 1 for i, b in enumerate(sorted(gpool, key=lambda b: b[key]))}
RK = {k: rk(k) for k in ("gift", "print")}
gift_lead = sorted(gpool, key=lambda b: b["gift"])[:3]
nv = S["nvidia_dc"]["hist"]
NP = WORD.get(len(P), str(len(P)))
companies = list(dict.fromkeys(s["company"] for s in SER))
NC = WORD.get(len(companies), str(len(companies)))
beat_arima = sum(b["print"] < BR["auto-arima"]["print"] for b in board if b["kind"] == "foundation")
beat_ets = sum(b["print"] < BR["auto-ets"]["print"] for b in board if b["kind"] == "foundation")
rep_cos = list(dict.fromkeys(p["company"] for p in P))
rep_txt = ", ".join(rep_cos[:-1]) + " and " + rep_cos[-1]
all_found = all(b["kind"] == "foundation" for b in beat_season)
fell = [p for p in P if p["beat"] > 0]
hardest = min(fell, key=lambda p: p["beat"])
easy = sorted(P, key=lambda p: -p["beat"])[:2]
totos = [b for b in board[:6] if b["m"].startswith("toto")]
most = max(board, key=lambda b: (b["beat_street"], -b["print"]))
bottom3 = [b for b in board if b["m"] != "seasonal-naive"][-3:]
shop = PRT.get("shopify_gmv")
pend_cos = list(dict.fromkeys(s["company"] for s in pending))
loss_txt = ", ".join(SHORT[p["id"]] for p in bf_losses)
bottom_txt = ", ".join(f"{nm(b['m'])} ({b['print']:.3f})" for b in bottom3[:-1]) + f" and {nm(bottom3[-1]['m'])} ({bottom3[-1]['print']:.3f})"
CNBC_LINK = '<a href="https://www.cnbc.com/2026/11/03/shopify-q3-2026-earnings-gmv.html">CNBC</a>'
shop_src = f" Shopify GMV {m1(shop['street'])}, {esc(shop['street_src']).replace('CNBC', CNBC_LINK)}." if shop else ""
bf_place = {}
for p in P:
    bf_place.setdefault(p["bf_rank34"], []).append(SHORT[p["id"]].replace("McD", "McDonald's"))

# ── data for the browser ───────────────────────────────────────────────────
JS_DATA = {
    "series": [{"id": s["id"], "label": NAME[s["id"]], "short": SHORT[s["id"]], "q": s["fut"][0], "fut": s["fut"],
                "hist": s["hist"][-20:], "date": s.get("prints") or "", "result": s["result"],
                "cons": None if not s["consensus"] else {"v": s["consensus"]["value"],
                                                         "src": COIN_SRC if s["id"] == "coin_net" else s["consensus"]["src"]},
                "models": [{"m": m["m"], "k": m["kind"], "cv": m["score"], "bt": m["bt"], "fut": m["fut"]} for m in s["models"]]}
               for s in SER],
    "prints": [{"id": p["id"], "label": NAME[p["id"]], "short": SHORT[p["id"]], "q": p["q"], "a": p["actual"], "st": p["street"],
                "src": COIN_SRC if p["id"] == "coin_net" else p["street_src"], "beat": p["beat"],
                "rows": [{"m": r["m"], "k": r["kind"], "f": r["fcst"], "e": r["err"], "cv": r["cv_rank"]} for r in p["rows"]]}
               for p in P],
    "board": [{"m": b["m"], "k": b["kind"], "p": round(b["print"], 6), "cv": round(b["cv"], 6), "bs": b["beat_street"],
               "gift": b["gift"], "gq": b["gift_q"], "fev": b["fev"],
               "per": [round(next(r for r in p["rows"] if r["m"] == b["m"])["rel"], 3) for p in P]} for b in board],
    "street": round(street_rel, 6),
    "street_per": [round(abs(p["street_err"]) / abs(p["naive_err"]), 3) for p in P],
    "pshort": [SHORT[p["id"]] for p in P],
}

# ── static tables ──────────────────────────────────────────────────────────
rows = ""
for i, p in enumerate(P):
    a, b, c = p["actual"], p["best"], p["cv1"]
    src = COIN_SRC if p["id"] == "coin_net" else esc(p["street_src"])
    rows += (f'<tr data-i="{i}"><th class="f">{NAME[p["id"]]}<small>{p["q"]}</small></th><td>{m1(a)}</td>'
             f'<td class="st">{sm(p["street_err"])}<small>{pc(p["street_err"], a)} · {src}</small></td>'
             f'<td class="mdl">{b["m"]}<small>{sm(b["err"])} · CV #{b["cv_rank"]}</small></td>'
             f'<td class="mdl">{c["m"]}<small>{sm(c["err"])} · finished #{c["print_rank"]}</small></td>'
             f'<td class="bt">{p["beat"]} of {p["n"]}</td></tr>')
SCORE = f"""<figure id="score">
<p class="fn">Table 1</p><h3>Scorecard, {len(P)} prints</h3>
<p class="sub">Locked forecasts against the reported number. A miss is forecast minus actual, so negative means too low.<span class="live"> Tap or click a row to open that print in Figure 1.</span></p>
<div class="wrap"><table class="sc click"><thead><tr><th class="f">Print</th><th>Actual</th><th>Wall Street miss</th><th>Closest model</th>
<th>Cross-validation #1</th><th>Beat Wall St.</th></tr></thead><tbody>{rows}</tbody></table></div>
</figure>"""

ctr = "".join(f'<tr><th class="f">{lab}</th><td>{rho(k + "~cv")}</td><td>{rho(k + "~print")}</td><td>{C[k + "~print"]["n"]}</td></tr>'
              for k, lab in [("gift", "GIFT-Eval, all data"), ("gift_q", "GIFT-Eval, quarterly"), ("fev", "fev-bench")])
ctr += f'<tr><th class="f">Earnings cross-validation</th><td>&middot;</td><td>{rho("cv~print")}</td><td>{C["cv~print"]["n"]}</td></tr>'
CORR = f"""<figure id="corr">
<p class="fn">Table 2</p><h3>Rank correlation with the earnings results</h3>
<p class="sub">Spearman correlation, foundation models only. 1 means the same order, 0 means unrelated.</p>
<div class="wrap"><table class="sc ct"><thead><tr><th class="f">Ranking</th><th>vs earnings CV</th><th>vs the prints</th><th>Models</th></tr></thead><tbody>{ctr}</tbody></table></div>
<figcaption>fev-bench covers fewer of these models, so its row uses a smaller set. With {len(P)} prints, read these as direction, not precision.</figcaption>
</figure>"""

seg_prints = "".join(f'<button data-v="{i}" aria-pressed="{str(i == 0).lower()}">{SHORT[p["id"]]}</button>' for i, p in enumerate(P))
seg_pend = "".join(f'<button data-v="{s["id"]}" aria-pressed="{str(i == 0).lower()}">{SHORT[s["id"]]}</button>' for i, s in enumerate(pending))
opt_rep = "".join(f'<option value="{p["id"]}">{NAME[p["id"]]}, {p["q"]}</option>' for p in P)
opt_pen = "".join(f'<option value="{s["id"]}">{NAME[s["id"]]}, {s["fut"][0]}</option>' for s in pending)

FIG1 = f"""<figure id="fig1" class="res">
<p class="fn">Figure 1</p><h3 id="resTitle">Each print, ranked by closeness</h3>
<p class="sub" id="resSub"></p>
<div class="ctl"><div class="seg" data-ctl="p">{seg_prints}</div></div>
<div class="tiles" id="resTiles"></div>
<div class="rd"><div class="rdc"><div id="resSvg"></div><div class="keys" id="resKeys"></div></div>
<div class="panel rdl"><div class="cols"><span>#</span><span>Closest on report day</span><span>Miss</span></div><ol id="resList"></ol></div></div>
</figure>"""

FIG2 = f"""<figure id="fig2" class="lbfig">
<p class="fn">Figure 2</p><h3>Model performance against Wall Street</h3>
<p class="sub" id="brdSub"></p>
<div class="ctl"><div class="seg" data-ctl="o"><button data-v="p" aria-pressed="true">Forward forecast at the print</button><button data-v="cv" aria-pressed="false">Cross-validation leaderboard</button></div></div>
<div class="panel board"><div class="cols"><span>#</span><span>Model</span><span id="brdCol">Score</span><span>Beat WS</span></div><ol id="brdList"></ol></div>
<button class="more" id="brdMore"></button>
</figure>"""

FIG3 = f"""<figure id="fig3" class="slope">
<p class="fn">Figure 3</p><h3>Benchmark order vs earnings order</h3>
<p class="sub" id="slpSub"></p>
<div class="ctl"><div class="seg" data-ctl="b"><button data-v="gift" aria-pressed="true">GIFT-Eval</button><button data-v="gq" aria-pressed="false">GIFT-Eval quarterly</button><button data-v="fev" aria-pressed="false">fev-bench</button></div>
<div class="seg" data-ctl="t"><button data-v="p" aria-pressed="true">The prints</button><button data-v="cv" aria-pressed="false">Cross-validation</button></div></div>
<div id="slope"></div>
<figcaption>Foundation models only, ranked among the models that have an entry on the chosen benchmark. Benchmark numbers are the public results, each model's MASE divided by seasonal naive's and combined with a geometric mean, the same snapshot used in the OpenRouter study <a class="ref" href="#r11">[11]</a>. GIFT-Eval quarterly uses its M4 quarterly configuration. Colored lines are the benchmark's top 3.<span class="live"> Hover or tap a line to follow a model.</span></figcaption>
</figure>"""

FIG4 = f"""<figure id="fig4" class="drill">
<p class="fn">Figure 4</p><h3 id="hTitle">History, backtest and locked forecasts</h3>
<p class="sub" id="hSub"></p>
<div class="ctl"><select id="hSel" aria-label="Series"><optgroup label="Reported">{opt_rep}</optgroup><optgroup label="Still to come">{opt_pen}</optgroup></select>
<div class="seg" data-ctl="l"><button data-v="cv" aria-pressed="true">CV top 3</button><button data-v="pr" aria-pressed="false">Closest at the print</button></div></div>
<div id="hSvg"></div>
<div class="keys" id="hKeys"></div>
</figure>"""

FIG5 = f"""<figure id="fig5" class="drill">
<p class="fn">Figure 5</p><h3 id="pTitle">Prints still to come</h3>
<p class="sub" id="pSub"></p>
<div class="ctl"><div class="seg" data-ctl="s">{seg_pend}</div></div>
<div id="pSvg"></div>
<div class="keys" id="pKeys"></div>
<div class="panel board pend"><div class="cols"><span>#</span><span>Model</span><span>CV</span><span>Locked</span></div><ol id="pList"></ol></div>
<button class="more" id="pMore"></button>
<figcaption>The chart shows the top 3 models by cross-validation and seasonal naive. The list ranks all {N} models by cross-validation relative MASE (seasonal naive is 1, lower is better), with each model's locked forecast for the coming quarter. Nothing will be refit after the print.<span class="live"> Hover or tap a row or the chart for details.</span></figcaption>
</figure>"""

DG = next(d for d in range(3, 8) if all(f"{b['print']:.{d}f}" != f"{street_rel:.{d}f}" for b in board))
TIE = "" if DG == 3 else f" {nm(beat_season[-1]['m'])} and Wall Street both round to {street_rel:.3f}, and the model is ahead only in the {ordn(DG)} decimal place, so call that one a tie."
beat_names = ", ".join(f"{nm(b['m'])} ({b['print']:.3f})" for b in beat_season[:-1]) + f" and {nm(beat_season[-1]['m'])} ({beat_season[-1]['print']:.3f})"
gl = ", ".join(f"{nm(b['m'])} finished {ordn(RK['print'][b['m']])}" for b in gift_lead[:-1]) + f" and {nm(gift_lead[-1]['m'])} finished {ordn(RK['print'][gift_lead[-1]['m']])}"
mcd_cv = f"#{mcd_t['best']['cv_rank']} and #{mcd_f['best']['cv_rank']}"
place_txt = []
for k in sorted(bf_place):
    names = bf_place[k]
    lst = names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]
    place_txt.append(f"{ordn(k)} on {lst}")
place_txt = ", ".join(place_txt[:-1]) + " and " + place_txt[-1]
bf_list = ", ".join(f"{nm(p['bf']['m'])} on {SHORT[p['id']].replace('McD', 'McDonald' + chr(39) + 's')}" for p in P)
METHOD_REF = {"auto-theta": '<a class="ref" href="#r13">[13]</a>', "auto-arima": '<a class="ref" href="#r14">[14]</a>'}
cw_cited = " and ".join(f"{nm(p['best']['m'])} {METHOD_REF.get(p['best']['m'], '')} on {SHORT[p['id']]}".replace("  ", " ") for p in classical_wins)
cw = " and ".join(f"{nm(p['best']['m'])} on {SHORT[p['id']]}" for p in classical_wins)
loss = bf_losses[0]

SHOP_P = "" if not shop else (f"<p><strong>Shopify.</strong> Gross merchandise volume came in at {m1(shop['actual'])}. The Wall Street figure of {m1(shop['street'])} ({esc(shop['street_src'])}) was {m1(abs(shop['street_err']))} {'high' if shop['street_err'] > 0 else 'low'}, only {abs(shop['street_err']) / shop['actual'] * 100:.1f}%, and just {shop['beat']} of {N} models beat it. {nm(shop['best']['m'])} was closest at {sm(shop['best']['err'])}, after ranking #{shop['best']['cv_rank']} on cross-validation.</p>")
BODY = f"""<div class="top"><a class="term" href="../terminal/" target="_blank" rel="noopener"><svg class="crt" viewBox="0 0 64 58" aria-hidden="true"><defs><linearGradient id="crtCase" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#f4ecd6"/><stop offset=".55" stop-color="#ddd1b2"/><stop offset="1" stop-color="#b9ab86"/></linearGradient><linearGradient id="crtSide" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#c7b994"/><stop offset="1" stop-color="#9a8c69"/></linearGradient><linearGradient id="crtBezel" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#8f8466"/><stop offset="1" stop-color="#c9bd9b"/></linearGradient><radialGradient id="crtGlass" cx=".45" cy=".42" r=".75"><stop offset="0" stop-color="#0f4a24"/><stop offset=".7" stop-color="#05200e"/><stop offset="1" stop-color="#010702"/></radialGradient><linearGradient id="crtGlare" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#fff" stop-opacity=".38"/><stop offset=".45" stop-color="#fff" stop-opacity=".06"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient><pattern id="crtScan" width="2" height="2" patternUnits="userSpaceOnUse"><rect width="2" height="1" fill="#000" opacity=".28"/></pattern><filter id="crtGlow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation=".8" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter><filter id="crtDrop" x="-20%" y="-20%" width="140%" height="160%"><feDropShadow dx="0" dy="1.6" stdDeviation="1.4" flood-color="#000" flood-opacity=".35"/></filter></defs><ellipse cx="32" cy="55.2" rx="20" ry="2.4" fill="#000" opacity=".18"/><g filter="url(#crtDrop)"><path d="M22 44h20l3.5 8.5H18.5Z" fill="url(#crtSide)"/><rect x="16" y="51.2" width="32" height="3.2" rx="1.4" fill="#a99b77"/><rect x="3" y="3" width="58" height="43" rx="7" fill="url(#crtSide)"/><rect x="3" y="2" width="58" height="41" rx="7" fill="url(#crtCase)"/><path d="M10 2.6h44" stroke="#fffaf0" stroke-width="1.2" stroke-linecap="round" opacity=".8"/><rect x="8" y="6.5" width="48" height="30" rx="5" fill="url(#crtBezel)"/><rect x="10.5" y="8.8" width="43" height="25.4" rx="6" ry="5" fill="url(#crtGlass)"/><rect x="10.5" y="8.8" width="43" height="25.4" rx="6" ry="5" fill="url(#crtScan)"/><g filter="url(#crtGlow)" fill="none" stroke="#39ff7a" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 15.5l4.5 4-4.5 4"/></g><rect x="23.5" y="22.2" width="9" height="2.2" rx="1" fill="#39ff7a" filter="url(#crtGlow)"/><path d="M12 10.5c9-1.6 22-1.8 33-.2-11 1.2-21 4-32 9.5Z" fill="url(#crtGlare)"/><circle cx="51" cy="39.6" r="1.4" fill="#39ff7a" filter="url(#crtGlow)"/><g stroke="#a3967a" stroke-width="1" stroke-linecap="round"><path d="M11 39.6h8"/><path d="M11 41.4h8"/></g><rect x="27" y="38.4" width="10" height="2.6" rx="1.2" fill="#c8bb98" stroke="#a3967a" stroke-width=".6"/></g></svg><span>Enter TimeCopilot Terminal</span></a><button class="theme" id="theme">Light / dark</button></div>
<article>
<h1>Can we beat Wall Street using<br>✨FoundationForecast?</h1>
<p class="dek">Q3 2026 earnings from {len(companies)} public companies with {n_found} Time Series Foundation Models, measuring the latest time series foundation models against the Wall Street consensus.</p>
<p class="byline">TimeCopilot · as of {AS_OF}</p>
<figure class="static">
<img src="assets/loop_report_days.gif" alt="Loop through the {len(P)} report days scored so far: actual quarterly history, the reported number, Wall Street and the 3 closest models, with the top 6 and Wall Street ranked by miss" loading="eager">
</figure>

<p class="disclaimer"><strong>This is not investment advice.</strong> Nothing here says anything about whether to buy or sell a stock. It's an exploration of how a new kind of tooling could change who gets to do this kind of analysis.</p>

<h2>Time series foundation models on public markets</h2>
<p>This is the next experiment in a series that tests time series foundation models on real-world data. The first one forecast token usage on OpenRouter <a class="ref" href="#r11">[11]</a>. Now the test is something almost everyone in the U.S. can access, the public financial markets. Quarterly results are public, the filings behind them are free on the SEC's EDGAR system <a class="ref" href="#r12">[12]</a>, and analyst expectations show up in the financial press. Still, turning all that into a forecast takes tools and training most people don't have, so markets that are open on paper are hard for non-experts to dive into. The question here is whether time series foundation models, served through {FF}, can help open that up.</p>
<p>The bar for these models is high, and it should be. Rob Hyndman made the skeptical case really well in a recent post <a class="ref" href="#r1">[1]</a>. He points out that published comparisons often use weak statistical baselines <a class="ref" href="#r2">[2]</a>, that the datasets in public benchmarks keep showing up in the models' training data <a class="ref" href="#r3">[3]</a>, and that a leaderboard averages over so many domains that it can hide how a model does on the series that actually matter. He closes with a key thought.</p>
<blockquote>&ldquo;A model that tops a MASE leaderboard by a small margin but takes an order of magnitude longer to run, or performs poorly on genuinely new data, may be the wrong choice operationally even if it&rsquo;s the &lsquo;best&rsquo; model on paper.&rdquo; <a class="ref" href="#r1">[1]</a></blockquote>
<p>The field needs shared, realistic evaluation, with honest baselines next to the new models and data the models can't have seen. A company's next quarterly revenue is about as fresh as test data gets, since it doesn't exist until the company reports it. Every forecast here was locked before the print, so there's no way for the answer to leak in.</p>

<p>Running that kind of evaluation across dozens of models is the hard part. {FF}, our newly released open-source unified API for time series foundation models, takes care of it. It runs all {n_found} foundation models in this test, plus the seasonal-naive baseline, through one interface, so their actual performance can be checked on the same data in the same way. Its catalog now also includes the classical auto models (AutoARIMA, AutoETS, AutoTheta and AutoCES), and in this test AutoARIMA, AutoETS and AutoTheta were run locally on the same quarters. The rest (Naive, Prophet, LightGBM, XGBoost and N-BEATS) come from the wider TimeCopilot stack. Results are still coming in, with {WORD[len(pend_cos)]} of the {NC} companies yet to report, and there's no definitive answer yet on whether these models beat Wall Street or older methods. In this test, though, the evidence leans their way at the horizon that matters most here, the next quarter. The best foundation model beat the Wall Street consensus on {bf_wins} of {len(P)} prints, and {'all ' + WORD[len(beat_season)] if all_found else 'most'} of the models with a smaller typical miss than Wall Street over the season are foundation models. {'Every one of the ' + str(n_found) if beat_ets == n_found else str(beat_ets) + ' of the ' + str(n_found)} beat AutoETS at the prints. AutoARIMA was the toughest classical baseline, with {beat_arima} of the {n_found} ahead of it, and on {WORD[len(classical_wins)]} prints a classical model was closest of all ({cw_cited}).</p>
<p>That practical angle is the focus here. For investors and for the companies themselves, the next quarter is the number everyone waits for. It shapes guidance, the stock's move on report day and a lot of planning, and it's the one forecast Wall Street publishes for nearly every big company. That makes it a fair place to line these models up against the consensus. And few numbers get as much attention, four times a year, as an earnings print.</p>

<h2>Why stocks</h2>
<p>Earnings make a good test because a lot rides on the forecast, and the forecast is expensive. The Wall Street consensus is the average of what sell-side analysts expect, and getting to it costs money. A single Bloomberg Terminal seat was priced at $31,980 a year for 2025 <a class="ref" href="#r4">[4]</a>. Research has a price tag too. When MiFID II forced banks in Europe to charge for research separately, UBS was reported to ask about $40,000 a year for basic access <a class="ref" href="#r5">[5]</a>, and prices across the industry ranged from $1,600 to $1 million <a class="ref" href="#r6">[6]</a>.</p>
<p>Coverage is also patchy. About a quarter of U.S.-listed companies have no analyst coverage at all, according to a recent Seeking Alpha analysis as summarized by Pluang <a class="ref" href="#r7">[7]</a>. That gap has real effects. Derrien and Kecskés found that companies that lost an analyst because a broker closed or merged went on to cut investment and financing compared with similar companies that didn't <a class="ref" href="#r8">[8]</a>. Even covered companies often get a consensus only for the headline number. For three of the four prints still to come in this test (Disney Experiences, Nvidia Data Center and Walmart U.S.), no segment consensus had been captured at the time of writing.</p>
<p>A forecast that costs an API call instead of an analyst team could fill some of those gaps. Whether it's any good is an empirical question, and an earnings print is a hard, public, dated test of it.</p>

<h2>Why these companies</h2>
<p>The {NC} companies were picked to span big parts of the U.S. economy, with a mix of steady and fast-changing businesses. The test follows one quarterly series for each, and two for McDonald's.</p>
<ul>
<li><strong>Crypto exchange.</strong> Coinbase net revenue, which swings with trading volume.</li>
<li><strong>Consumer tech.</strong> Apple iPhone net sales, with a big holiday quarter every year.</li>
<li><strong>Software and AI.</strong> Palantir revenue, which has grown every quarter for years.</li>
<li><strong>Semiconductors.</strong> AMD Data Center revenue and Nvidia Data Center revenue, both riding the AI buildout.</li>
<li><strong>E-commerce.</strong> Shopify GMV, the gross merchandise volume sold through Shopify merchants, with a big holiday quarter.</li>
<li><strong>Restaurants.</strong> McDonald's total and franchised revenues, the steadiest series in the set.</li>
<li><strong>Media and theme parks.</strong> Disney Experiences revenue.</li>
<li><strong>Home improvement.</strong> Home Depot net sales.</li>
<li><strong>Big-box retail.</strong> Walmart U.S. net sales.</li>
</ul>
<p>{rep_txt} have reported. Disney, Home Depot and Nvidia report on November 17, and Walmart reports on November 19.</p>

<h2>Why publish before all reports are live?</h2>
<p>Publication waited until some of the companies had reported, so the results would have something real behind them, and so far they've been good. The coin is still in the air, though. {WORD[len(pend_cos)].capitalize()} of the {len(companies)} companies tracked ({len(pend_cos) / len(companies) * 100:.0f}%) haven't reported yet ({n_pending} of {len(S)} series), and their forecasts are already locked and shown below. If Nvidia steps up the way AMD did, the picture could change.</p>

<h2>What was tested</h2>
<p>The test covers {len(S)} quarterly series from {len({s['company'] for s in SER})} companies, taken from SEC filings in U.S. dollars. Each series got {N} models.</p>
<ul>
<li><strong>Foundation models ({n_found}).</strong> Chronos-2, Chronos-Bolt, TimesFM, TiRex, Toto, Timestral, t0, TimeH2O, Tabby and Granite PatchTST in their various sizes, all served through {FF}'s hosted API, along with the seasonal naive baseline (same quarter last year).</li>
<li><strong>Statistical, machine learning and deep learning models (8).</strong> AutoARIMA, AutoETS, AutoTheta and Naive from statsforecast, LightGBM and XGBoost from mlforecast on first-differenced values with lags 1 to 4, N-BEATS from neuralforecast, and Prophet with yearly seasonality.</li>
</ul>
<p>The second group mixes two kinds of model. AutoARIMA, AutoETS and AutoTheta are now part of FoundationForecast as well, next to AutoCES, which wasn't in this test, but here they ran locally with statsforecast. Naive, Prophet, LightGBM, XGBoost and N-BEATS come from the wider TimeCopilot stack. Classical models like AutoARIMA, AutoETS and Prophet are also evaluated in Impermanent, a live benchmark for temporal generalization <a class="ref" href="#r15">[15]</a>. All eight ran locally on exactly the same quarters and the same protocol as the API models.</p>
<p>Before any print, every model went through cross-validation on the last 12 quarters. For each one it saw only the data available at the time and forecast one quarter ahead. Each quarter's error was divided by seasonal naive's error and the 12 ratios were combined with a geometric mean. That's relative MASE <a class="ref" href="#r9">[9]</a>, the same scale GIFT-Eval <a class="ref" href="#r10">[10]</a> and fev-bench <a class="ref" href="#r16">[16]</a> use, so 1 means no better than naive and lower is better.</p>
<p>Then every model's next-quarter forecast was locked and scored against the reported number afterwards. The series were forecast on different dates, from October 28 to November 2, 2026, all before the actuals came out. Lock dates are in UTC, so Coinbase shows October 29 for both its lock and its report: the forecasts were locked at 00:11 UTC that day, which is 5:11 p.m. Pacific on October 28, about 20 hours before Coinbase reported after the close. The one exception is Shopify's eight locally run models, which we added on November 4 Pacific time, after its November 3 report, on history ending in Q2 2026, so the reported number was not in their data. Nothing was refit after a print. For the season score, each model's miss on a print is divided by seasonal naive's miss on the same print, and those ratios are combined with a geometric mean. Wall Street's consensus gets scored exactly the same way, which puts it on the same board as the models.</p>
<p>This page uses two rankings. Report-day leaderboards list the models closest to the reported number first, and &ldquo;finished #&rdquo; is a model's place there. Cross-validation is the other one: &ldquo;CV #&rdquo;, &ldquo;ranked on cross-validation&rdquo; and the leaderboard going into a report all refer to the 12-quarter order described above.</p>

<h2>Print by print</h2>
<p>The models beat Wall Street most easily on {NAME[easy[0]['id']]} and {NAME[easy[1]['id']]}, where {easy[0]['beat']} and {easy[1]['beat']} of {N} models beat the consensus. {NAME[hardest['id']]} was the hardest of the ones that fell, since Wall Street was only {abs(hardest['street_err']) / hardest['actual'] * 100:.1f}% off and just {hardest['beat']} models did better. Figure 1 shows every print with all {N} models and Wall Street in the order they finished.</p>
{SCORE}
{FIG1}

<h2>AMD, the miss</h2>
<p>AMD Data Center revenue came in at {m1(amd['actual'])}, up {amd_jump * 100:.0f}% from {m1(amd_prev)} the quarter before. Wall Street was {abs(amd['street_err']) / amd['actual'] * 100:.1f}% low. Every one of the {N} models was at least {amd_minlow * 100:.0f}% low, and the median foundation model forecast was about {m1(amd_med)}. The closest model, {nm(amd['best']['m'])}, was also the cross-validation leader, which makes AMD the only print where the leaderboard got it right, and the right model still missed by {m1(abs(amd['best']['err']))}.</p>
<p>The reason is simple. Analysts had company guidance, customer orders and a sense of the AI buildout to go on. A model that reads one revenue series only sees its past, and when a business steps up faster than its own history suggests, the series is the last to know. Context is Key makes the same point from the research side, showing that forecasts improve when the model gets the background a human forecaster would use <a class="ref" href="#r17">[17]</a>. That's the honest limit of this setup, and a pretty clear pointer to what comes next.</p>

<h2>GIFT-Eval and fev-bench vs the prints</h2>
<p>GIFT-Eval and fev-bench rank foundation models over hundreds of public datasets. The OpenRouter study found their order didn't carry over to token usage <a class="ref" href="#r11">[11]</a>, and earnings look similar. If the benchmark order carried over, the lines in Figure 3 would run straight across. Ranked among these {len(gpool)}, GIFT-Eval's top three landed mid-pack at the prints. {gl}, out of {len(gpool)}. Meanwhile {nm(top['m'])}, {ordn(RK['gift'][top['m']])} of {len(gpool)} on GIFT-Eval, finished first.</p>
{FIG3}
<p>GIFT-Eval's quarterly slice does better, with a correlation of {rho('gift_q~cv')} against the earnings cross-validation, which makes sense since it's closer to this kind of data. Against the prints, it's still only {rho('gift_q~print')}. The overall GIFT-Eval order comes in at {rho('gift~print')} and fev-bench at {rho('fev~print')}, basically no relationship. None of this means the benchmarks are wrong. They average over many domains, and a leaderboard can hide how a model does on the series that actually matter <a class="ref" href="#r1">[1]</a>. Benchmarks are guidance. The data and the setup pick the model.</p>
{CORR}

<h2>Company by company</h2>
<p>Figure 4 shows any of the {len(S)} series with its history, the 12 backtest quarters and the locked forecasts, either for the top 3 models on cross-validation or for the 3 that landed closest at the print.</p>
{FIG4}
<p><strong>Coinbase.</strong> The most volatile series in the set, since revenue follows crypto trading volume. Net revenue came in at {m1(coin['actual'])}. The Wall Street figure here is {m1(coin['street'])}, a miss of {sm(coin['street_err'])}, from Zacks' October 26 preview, which put net revenue down 38.9% year over year. Against it, {coin['beat']} of {N} models did better. The closest was {nm(coin['best']['m'])}, only {m1(abs(coin['best']['err']))} off, even though it ranked #{coin['best']['cv_rank']} on cross-validation.</p>
<p><strong>Apple.</strong> iPhone net sales were {m1(apple['actual'])}. The Zacks consensus of {m1(apple['street'])} missed by {sm(apple['street_err'])}, only {abs(apple['street_err']) / apple['actual'] * 100:.1f}%, a tough bar. {apple['beat']} of {N} models cleared it, led by {nm(apple['best']['m'])} at {sm(apple['best']['err'])}. The answer also depends on which consensus counts. LSEG had {m1(apple_lseg)}, and against that number {apple_lseg_beat} of {N} models beat Wall Street.</p>
<p><strong>Palantir.</strong> Revenue was {m1(pltr['actual'])}, and Wall Street was {m1(abs(pltr['street_err']))} low ({pc(pltr['street_err'], pltr['actual'])}). Palantir has grown every quarter for the past two years, and the models extrapolated that trend better than the consensus did. {pltr['beat']} of {N} models beat Wall Street, with {nm(pltr['best']['m'])} closest at {sm(pltr['best']['err'])}.</p>
<p><strong>AMD.</strong> The one print where no model got close, covered above.</p>
{SHOP_P}
<p><strong>McDonald's.</strong> The steadiest business here. Wall Street was {m1(mcd_t['street_err'])} high on total revenues and {m1(mcd_f['street_err'])} high on franchised revenues. {mcd_t['beat']} of {N} models beat it on total revenues and {mcd_f['beat']} on franchised, and the closest models, {nm(mcd_t['best']['m'])} ({sm(mcd_t['best']['err'])}) and {nm(mcd_f['best']['m'])} ({sm(mcd_f['best']['err'])}), had ranked {mcd_cv} on cross-validation.</p>

<h2>Still to come</h2>
<p>{WORD[n_pending].capitalize()} prints are left, and their forecasts are already locked. Disney Experiences, Home Depot and Nvidia Data Center report on November 17, and Walmart U.S. reports on November 19. Home Depot is the only one with a consensus captured so far. Nvidia is the one to watch after AMD. Its Data Center revenue went from {m1(nv[-5][1])} to {m1(nv[-1][1])} in a year, the kind of step-up that tripped up every model on AMD.</p>
{FIG5}

<h2>Model performance against Wall Street</h2>
<p>Over the season, Wall Street scores {street_rel:.3f}, a typical miss about {1 / street_rel:.0f} times smaller than seasonal naive's. {WORD[len(beat_season)].capitalize()} models scored lower, namely {beat_names}.{TIE} The best model that isn't a foundation model was {nm(best_stat['m'])} in {ordn(best_stat['prank'])} at {best_stat['print']:.3f}.</p>
{FIG2}
<p>Size isn't everything. Datadog's Toto shows up {WORD[len(totos)]} times in the top six, at {', '.join(b['m'].split('-')[-1].upper() for b in totos[:-1])} and {totos[-1]['m'].split('-')[-1].upper()} parameters in that order, and {nm(most['m'])} beat Wall Street on {most['beat_street']} of {len(P)} report days, more than any other model. So far, the scaling laws behind large language models don't seem to carry over to time series foundation models, at least not on short quarterly series with a few dozen points of history. The <a href="{OR_URL}">OpenRouter experiment</a> <a class="ref" href="#r11">[11]</a> pointed the same way. There, Toto 2 4M was the best forecaster on all tokens 1 week ahead, Chronos-2 Small had the lowest error on individual LLMs at 1 week and Chronos-Bolt Mini led on categories at 4 weeks, each ahead of much bigger models. Small doesn't always win, though. Leaving out seasonal naive, the bottom of this board is {bottom_txt}, and Chronos-Bolt Mini, a standout on OpenRouter, is one of them.</p>

<h2>Where this goes next</h2>
<p>So far the answer leans yes. On {bf_wins} of {len(P)} prints the best foundation model beat the consensus, {len(beat_season)} models beat it over the season, and the median foundation model beat it on {ens_beat} of {len(P)}, all from public revenue history.</p>
<p>The next steps follow from that. The {WORD[n_pending]} remaining prints will add to the sample, and feeding the models some of the context analysts use, like guidance or related series, is the obvious way to go after misses like AMD.</p>

<hr>
<h2>Notes</h2>
<ul class="notes">
<li>Series are from each company's SEC filings and quarterly reports, in USD millions. Fiscal quarters follow each company's calendar, so Apple's Q4 FY2026 and Nvidia's Q3 FY2027 line up with the calendar Q3 season.</li>
<li>Wall Street consensus sources. Coinbase {m1(coin['street'])}, Zacks, October 26, 2026, for net revenue. Apple {m1(apple['street'])}, {esc(apple['street_src'])}. LSEG had {m1(apple_lseg)}, and against it {apple_lseg_beat} of {N} models beat Wall Street instead of {apple['beat']}. Palantir {m1(pltr['street'])}, {esc(pltr['street_src'])}. AMD Data Center {m1(amd['street'])}, {esc(amd['street_src'])}. McDonald's {m1(mcd_t['street'])} total and {m1(mcd_f['street'])} franchised, {esc(mcd_t['street_src'])}.{shop_src}</li>
<li>The season score is the geometric mean over the prints of |model miss| ÷ |seasonal-naive miss| on the same print. Cross-validation scores are the geometric mean over all {len(S)} series, including the {n_pending} that haven't reported.</li>
<li>Foundation models and seasonal naive were called through the {FF} API. The other 8 models ran locally on a quarterly calendar (AutoARIMA, AutoETS and AutoTheta are also available in FoundationForecast but were run locally here) with the same 12 cross-validation quarters, each refit on the data before its cutoff, and were scored against the API's seasonal naive on every fold. AutoARIMA, AutoETS and AutoTheta used a season length of 4. N-BEATS used generic stacks with an input of 4 quarters. Prophet used yearly seasonality with 2 Fourier terms.</li>
<li>GIFT-Eval and fev-bench numbers come from their public results, the same snapshot as the OpenRouter tokens study, aggregated the way each leaderboard does (MASE relative to seasonal naive, geometric mean). GIFT-Eval quarterly uses its M4 quarterly configuration. TimeH2O has no public entry on either. Correlations are Spearman, foundation models only.</li>
<li>Nothing here is investment advice.</li>
<li>The interactive companion is the <a href="../terminal/">TimeCopilot Analyst Terminal</a>. Data and code are in <a href="https://github.com/TimeCopilot/experiments/tree/main/earnings">github.com/TimeCopilot/experiments/tree/main/earnings</a>.</li>
</ul>

<h2>References</h2>
<ol class="notes refs">
<li id="r1">Hyndman, R. J. (2026, August 25). Evaluating time series foundation model claims. Hyndsight. <a href="https://robjhyndman.com/hyndsight/foundation_models.html">robjhyndman.com/hyndsight/foundation_models.html</a></li>
<li id="r2">Bergmeir, C. (2024). LLMs and foundational models: Not (yet) as good as hoped. Foresight: The International Journal of Applied Forecasting, 73, 33-38. <a href="https://cbergmeir.com/papers/Bergmeir2024LLMs.pdf">cbergmeir.com/papers/Bergmeir2024LLMs.pdf</a></li>
<li id="r3">Meyer, M., Kaltenpoth, S., Zalipski, K., &amp; M&uuml;ller, O. (2025). Rethinking evaluation in the era of time series foundation models: (Un)known information leakage challenges. arXiv:2510.13654. <a href="https://arxiv.org/abs/2510.13654">arxiv.org/abs/2510.13654</a></li>
<li id="r4">NeuGroup. (2024, October 9). Bloomberg Terminals: How much more you'll pay next year. <a href="https://connect.neugroup.com/public/blogs/bloomberg-terminals-how-much-more-youll-pay-next-year">connect.neugroup.com/public/blogs/bloomberg-terminals-how-much-more-youll-pay-next-year</a></li>
<li id="r5">Bloomberg News. (2017, August 15). UBS is said to charge about $40,000 for basic MiFID research. <a href="https://www.bloomberg.com/news/articles/2017-08-15/ubs-is-said-to-charge-about-40-000-for-basic-mifid-research">bloomberg.com/news/articles/2017-08-15/ubs-is-said-to-charge-about-40-000-for-basic-mifid-research</a></li>
<li id="r6">Bloomberg News. (2019, April 23). From $1,600 to $1 million: What research costs under MiFID II. <a href="https://www.bloomberg.com/news/articles/2019-04-23/from-1-600-to-1-million-what-research-costs-under-mifid-ii">bloomberg.com/news/articles/2019-04-23/from-1-600-to-1-million-what-research-costs-under-mifid-ii</a></li>
<li id="r7">Pluang. (2026, October 2). A quarter of companies have no analyst coverage (summarizing Seeking Alpha). <a href="https://pluang.com/en/news-feed/seperempat-perusahaan-tanpa-analisis-penutup">pluang.com/en/news-feed/seperempat-perusahaan-tanpa-analisis-penutup</a></li>
<li id="r8">Derrien, F., &amp; Kecskés, A. (2013). The real effects of financial shocks: Evidence from exogenous changes in analyst coverage. The Journal of Finance, 68(4), 1407-1440. <a href="https://doi.org/10.1111/jofi.12042">doi.org/10.1111/jofi.12042</a></li>
<li id="r9">Hyndman, R. J., &amp; Koehler, A. B. (2006). Another look at measures of forecast accuracy. International Journal of Forecasting, 22(4), 679-688. <a href="https://robjhyndman.com/papers/mase.pdf">robjhyndman.com/papers/mase.pdf</a></li>
<li id="r10">Aksu, T., Woo, G., Liu, J., Liu, X., Liu, C., Savarese, S., Xiong, C., &amp; Sahoo, D. (2024). GIFT-Eval: A benchmark for general time series forecasting model evaluation. arXiv:2410.10393. <a href="https://arxiv.org/abs/2410.10393">arxiv.org/abs/2410.10393</a> Leaderboard and results at <a href="https://huggingface.co/spaces/Salesforce/GIFT-Eval">huggingface.co/spaces/Salesforce/GIFT-Eval</a></li>
<li id="r11">TimeCopilot. (2026). Can we predict token usage using transformer based models? <a href="{OR_URL}">timecopilot.github.io/experiments/openroutertokens/</a></li>
<li id="r12">U.S. Securities and Exchange Commission. EDGAR full text search and company filings. <a href="https://www.sec.gov/edgar/search/">sec.gov/edgar/search/</a></li>
<li id="r13">Assimakopoulos, V., &amp; Nikolopoulos, K. (2000). The theta model: A decomposition approach to forecasting. International Journal of Forecasting, 16(4), 521-530. <a href="https://doi.org/10.1016/S0169-2070(00)00066-2">doi.org/10.1016/S0169-2070(00)00066-2</a></li>
<li id="r14">Hyndman, R. J., &amp; Khandakar, Y. (2008). Automatic time series forecasting: The forecast package for R. Journal of Statistical Software, 27(3), 1-22. <a href="https://doi.org/10.18637/jss.v027.i03">doi.org/10.18637/jss.v027.i03</a></li>
<li id="r15">Garza, A., Rosillo, R., Mendoza-Smith, R., Salinas, D., Williams, A. R., Ashok, A., Goswami, M., &amp; Ju&aacute;rez, J. M. (2026). Impermanent: A live benchmark for temporal generalization in time series forecasting. arXiv:2603.08707. <a href="https://arxiv.org/abs/2603.08707">arxiv.org/abs/2603.08707</a> Live leaderboard at <a href="https://impermanent.timecopilot.dev">impermanent.timecopilot.dev</a></li>
<li id="r16">Shchur, O., Ansari, A. F., Turkmen, C., Stella, L., Erickson, N., Guerron, P., Bohlke-Schneider, M., &amp; Wang, Y. (2025). fev-bench: A realistic benchmark for time series forecasting. arXiv:2509.26468. <a href="https://arxiv.org/abs/2509.26468">arxiv.org/abs/2509.26468</a> Results at <a href="https://github.com/autogluon/fev">github.com/autogluon/fev</a></li>
<li id="r17">Williams, A. R., Ashok, A., Marcotte, É., Zantedeschi, V., Subramanian, J., Riachi, R., Requeima, J., Lacoste, A., Rish, I., Chapados, N., &amp; Drouin, A. (2024). Context is Key: A benchmark for forecasting with essential textual information. arXiv:2410.18959. <a href="https://arxiv.org/abs/2410.18959">arxiv.org/abs/2410.18959</a></li>
</ol>
</article>
<div class="tip" id="tip"></div>"""

HEAD = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Beating Wall Street</title>
<meta name="description" content="Q3 2026 earnings from {len(companies)} public companies with {n_found} Time Series Foundation Models, measuring the latest time series foundation models against the Wall Street consensus.">
<meta property="og:type" content="article">
<meta property="og:site_name" content="TimeCopilot experiments">
<meta property="og:title" content="{TITLE}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{TITLE}">
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&family=Roboto+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">"""

CSS = r"""<style>
:root{--ink:#171720;--text:#3d3f4c;--muted:#636170;--muted-2:#8b8998;--paper:#f8f8fc;--line:#e3e3ea;--grid:#eeeef3;
 --purple:#5b54e0;--purple-700:#4842c4;--purple-soft:rgba(91,84,224,.07);--blue:#3f8fd4;--pink:#e0679c;--stem:#cdced7;--dot:#9498a3;
 --red:#e5484d;--red-soft:rgba(229,72,77,.08);--orange:#e5732e;
 --surf:linear-gradient(145deg,#fbfcff,#e8eaf5);--card:#f3f4fa;--win:rgba(91,84,224,.08);
 --sh:12px 12px 28px rgba(112,109,145,.17),-12px -12px 28px rgba(255,255,255,.92);--tip:#171720;--tip-ink:#f8f8fc}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--ink:#eceef7;--text:#c9cbe0;--muted:#9a9db2;--muted-2:#7b7e93;
 --paper:#0e0f16;--line:#2b2d3c;--grid:rgba(255,255,255,.07);--purple:#9a92f8;--purple-700:#a9a2ff;--purple-soft:rgba(139,131,245,.12);
 --blue:#6abaf2;--pink:#f08ab5;--stem:#4a4d61;--dot:#6b6e80;--red:#ff6b70;--red-soft:rgba(255,107,112,.1);--orange:#f59a5c;
 --surf:linear-gradient(145deg,#1d1f2b,#14151e);--card:#171822;--win:rgba(154,146,248,.12);
 --sh:12px 12px 28px rgba(0,0,0,.6),-10px -10px 24px rgba(255,255,255,.028);--tip:#eceef7;--tip-ink:#0e0f16}}
:root[data-theme="dark"]{--ink:#eceef7;--text:#c9cbe0;--muted:#9a9db2;--muted-2:#7b7e93;--paper:#0e0f16;--line:#2b2d3c;
 --grid:rgba(255,255,255,.07);--purple:#9a92f8;--purple-700:#a9a2ff;--purple-soft:rgba(139,131,245,.12);--blue:#6abaf2;--pink:#f08ab5;
 --stem:#4a4d61;--dot:#6b6e80;--red:#ff6b70;--red-soft:rgba(255,107,112,.1);--orange:#f59a5c;
 --surf:linear-gradient(145deg,#1d1f2b,#14151e);--card:#171822;--win:rgba(154,146,248,.12);
 --sh:12px 12px 28px rgba(0,0,0,.6),-10px -10px 24px rgba(255,255,255,.028);--tip:#eceef7;--tip-ink:#0e0f16}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--paper);color:var(--text);font-family:'DM Sans',system-ui,sans-serif;font-size:17px;line-height:1.7;padding:0 16px 80px;overflow-x:hidden}
.top{max-width:960px;margin:0 auto;display:flex;justify-content:flex-end;align-items:center;gap:10px;padding:18px 16px 0}
.term{display:inline-flex;align-items:center;gap:9px;font:600 13px 'DM Sans',sans-serif;color:var(--ink);text-decoration:none;border:1px solid var(--line);border-radius:999px;padding:5px 14px 5px 8px;background:var(--surf)}
.term:hover{border-color:#1fae52;box-shadow:0 0 0 3px rgba(57,255,122,.18)}
.term .crt{width:40px;height:36px;margin:-6px 0 -6px -2px}
@media (max-width:480px){.top{justify-content:space-between}.term span{font-size:12px}}
.theme{font:500 12px 'DM Sans',sans-serif;color:var(--muted);background:none;border:1px solid var(--line);border-radius:999px;padding:7px 12px;cursor:pointer}
article{max-width:700px;margin:0 auto}
h1{font-size:clamp(32px,6vw,46px);line-height:1.08;letter-spacing:-.03em;color:var(--ink);margin:36px 0 16px;text-align:center}
.dek{font-size:20px;line-height:1.5;color:var(--muted);margin:0 auto 18px;text-align:center;max-width:640px}
.byline{font-size:13px;color:var(--muted-2);margin:0 0 8px;text-align:center}
h2{font-size:26px;letter-spacing:-.02em;color:var(--ink);margin:52px 0 12px;line-height:1.2}
p{margin:0 0 18px}
strong{color:var(--ink)}
a{color:var(--purple-700)}
ul{padding-left:20px;margin:0 0 18px}
li{margin:0 0 8px}
blockquote{margin:0 0 18px;padding:0;border:0;font-size:inherit;line-height:inherit;color:inherit}
figure{margin:34px -120px;background:var(--surf);box-shadow:var(--sh);border-radius:26px;padding:26px 26px 20px;min-width:0}
@media (max-width:960px){figure{margin:34px 0;padding:20px 14px 16px;border-radius:20px}}
figure h3{font-size:20px;letter-spacing:-.02em;color:var(--ink);margin:0;line-height:1.3}
figure .fn{font:600 11px 'Roboto Mono',monospace;color:var(--purple-700);letter-spacing:.06em;text-transform:uppercase;margin:0 0 4px}
figure .sub{color:var(--muted);font-size:13.5px;margin:4px 0 16px;line-height:1.5}
figcaption{color:var(--muted);font-size:12.5px;line-height:1.55;margin:16px 0 0}
.ctl{display:flex;flex-wrap:wrap;gap:10px;margin:0 0 18px;align-items:center}
.seg{display:inline-flex;flex-wrap:wrap;padding:4px;border-radius:18px;background:var(--card);border:1px solid var(--line);max-width:100%}
.seg button{font:600 12.5px 'DM Sans',sans-serif;color:var(--muted);background:none;border:0;border-radius:999px;padding:7px 12px;cursor:pointer}
.seg button[aria-pressed="true"]{background:var(--purple);color:#fff}
.seg button:disabled{opacity:.4;cursor:default}
select{font:500 13px 'DM Sans',sans-serif;color:var(--ink);background:var(--card);border:1px solid var(--line);border-radius:12px;padding:8px 10px;max-width:100%}
.wrap{overflow-x:auto;-webkit-overflow-scrolling:touch}
.more{font:600 12px 'DM Sans',sans-serif;color:var(--purple-700);background:none;border:0;padding:8px 8px 0;cursor:pointer}
/* tables */
table.sc{border-collapse:collapse;width:100%;min-width:640px;font-size:13px}
.sc th,.sc td{text-align:right;padding:9px 8px;border-bottom:1px solid var(--line);vertical-align:top;font:500 12.5px 'Roboto Mono',monospace;color:var(--text)}
.sc thead th{font:500 10px 'DM Sans',sans-serif;color:var(--muted-2);text-transform:uppercase;letter-spacing:.06em}
.sc th.f{text-align:left;font:600 13.5px 'DM Sans',sans-serif;color:var(--ink)}
.sc thead th.f{font:500 10px 'DM Sans',sans-serif;color:var(--muted-2)}
.sc small{display:block;font:400 11px 'DM Sans',sans-serif;color:var(--muted);margin-top:2px}
.sc td.mdl{text-align:left;color:var(--ink)}
.sc td.st{color:var(--red);font-weight:600}
.sc td.bt{color:var(--ink);font-weight:700}
.sc.click tbody tr{cursor:pointer}
.sc.click tbody tr:hover td,.sc.click tbody tr:hover th{background:var(--purple-soft)}
.ct{min-width:0}
@media (max-width:480px){.ct th,.ct td{padding:8px 4px;font-size:11.5px}.ct thead th{font-size:9px}}
/* leaderboard rows (tokens fig 1 style) */
.panel{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:16px 14px 8px}
.cols,.row{display:grid;grid-template-columns:26px minmax(0,1fr) 58px 64px;align-items:baseline;column-gap:8px}
.cols{font:500 10px 'DM Sans',sans-serif;color:var(--muted-2);text-transform:uppercase;letter-spacing:.06em;padding:0 8px 4px}
.cols span:nth-child(n+3),.row .num{text-align:right}
.panel ol,ol.dv{list-style:none;margin:0;padding:0}
.panel li,ol.dv li{padding:5px 8px;border-radius:10px;margin:0;position:relative;cursor:default}
.panel li.lead,ol.dv li.lead{background:var(--purple-soft)}
li.street{background:var(--red-soft)}
li.cut{margin-top:10px}
li.cut::before{content:"";position:absolute;left:8px;right:8px;top:-5px;border-top:1px dashed var(--line)}
li.gap{font-size:15px;font-weight:600;color:var(--ink);padding:8px 8px 8px 42px}
.rank{font:600 11.5px 'Roboto Mono',monospace;color:var(--dot)}
.lead .rank{color:var(--purple-700);font-weight:700}
.name{font:500 13px 'Roboto Mono',monospace;color:var(--text);min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;line-height:1.35}
.lead .name{font-weight:700;color:var(--ink)}
.street .name{font:700 13.5px 'DM Sans',sans-serif;color:var(--red)}
.disclaimer{margin:18px 0 6px;padding:12px 16px;border-left:3px solid var(--line);background:var(--card,transparent);border-radius:6px}
figure.static img{display:block;width:100%;height:auto;margin:10px 0 0;border-radius:12px}
.tag{font:600 9.5px 'DM Sans',sans-serif;color:var(--muted);border:1px solid var(--line);border-radius:999px;padding:0 6px;margin-left:6px;vertical-align:1px}
.num{font:500 12.5px 'Roboto Mono',monospace;color:var(--text);white-space:nowrap}
.num.sm{font-size:11.5px;color:var(--muted)}
.lead .num{color:var(--purple-700);font-weight:700}
.street .num{color:var(--red);font-weight:700}
.track{height:5px;margin:3px 0 0 34px;position:relative}
.track i{position:absolute;left:0;top:0;height:4px;border-radius:0 4px 4px 0;background:var(--stem)}
.lead .track i{background:var(--purple)}
.street .track i{background:var(--red)}
.base .track i{background:repeating-linear-gradient(90deg,var(--dot) 0 4px,transparent 4px 6px)}
li:hover .name{color:var(--ink)}
/* fig 1: diverging bars */
.tiles{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin:0 0 16px}
.tiles div{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:10px 12px;min-width:0}
.tiles div.w{border-color:var(--purple)}
.tiles span{display:block;font:500 10px 'DM Sans',sans-serif;color:var(--muted-2);text-transform:uppercase;letter-spacing:.06em;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.tiles b{display:block;font:600 17px 'Roboto Mono',monospace;color:var(--ink);letter-spacing:-.02em;margin:2px 0}
.tiles div.s b,.tiles em.s{color:var(--red)}
.tiles div.w b{color:var(--purple-700)}
.tiles em{display:block;font:500 11px 'Roboto Mono',monospace;color:var(--muted);font-style:normal}
@media (max-width:520px){.tiles{grid-template-columns:1fr}}
.axis{display:flex;justify-content:space-around;font-size:11px;color:var(--muted-2);margin:0 0 4px 34px}
ol.dv .row{grid-template-columns:26px minmax(0,1fr) auto}
ol.dv .dtrack{height:8px;margin:3px 0 1px 34px;position:relative}
ol.dv .dtrack::before{content:"";position:absolute;left:50%;top:-3px;bottom:-3px;border-left:1px solid var(--ink);opacity:.5}
ol.dv .dtrack i{position:absolute;top:1px;height:6px;border-radius:3px;background:var(--stem)}
ol.dv .lead .dtrack i{background:var(--purple)}
ol.dv .street .dtrack i{background:var(--red)}
/* svg charts */
#slope svg,.drill svg,#resSvg svg{width:100%;height:auto;display:block;overflow:visible}
#slope text{font-family:'DM Sans',sans-serif}
.drill text,#resSvg text{font-family:'Roboto Mono',monospace;font-size:10.5px}
.keys{display:flex;flex-wrap:wrap;gap:6px 16px;margin:12px 0 0;font-size:12.5px;color:var(--text)}
.keys span{display:inline-flex;align-items:center;gap:7px;white-space:nowrap}
.keys svg{width:22px;height:8px}
.keys b{font:600 12px 'Roboto Mono',monospace;color:var(--ink)}
.pend{margin-top:18px}
.tip{position:fixed;pointer-events:none;background:var(--tip);color:var(--tip-ink);font-size:12px;line-height:1.5;padding:8px 10px;border-radius:10px;opacity:0;transition:opacity .12s;max-width:260px;z-index:9}
.tip .m{font-family:'Roboto Mono',monospace}
@media (max-width:480px){.cols,.row{grid-template-columns:20px minmax(0,1fr) 50px 58px;column-gap:6px}.tag{display:none}.name{font-size:12px}
 .track,ol.dv .dtrack{margin-left:26px}.axis{margin-left:26px}.num{font-size:11.5px}}
/* wide screens: one line per row (rank, model, bar, values), and figures use more of the width */
@media (min-width:641px){
 .panel li:not(.gap),ol.dv li:not(.gap){display:grid;grid-template-columns:26px 250px minmax(0,1fr) 64px 64px;column-gap:10px;align-items:center;padding:3px 8px}
 ol.dv li:not(.gap){grid-template-columns:26px 250px minmax(0,1fr) 64px}
 .panel li .row,ol.dv li .row{display:contents}
 .panel li .rank,ol.dv li .rank{grid-column:1;grid-row:1}.panel li .name,ol.dv li .name{grid-column:2;grid-row:1}
 .panel li .num{grid-column:4;grid-row:1}.panel li .num.sm{grid-column:5}ol.dv li .num{grid-column:4;grid-row:1}
 .panel li .track,ol.dv li .dtrack{grid-column:3;grid-row:1;margin:0;align-self:center}
 .panel .cols{grid-template-columns:26px 250px minmax(0,1fr) 64px 64px;column-gap:10px}
 .panel .cols span:nth-child(3){grid-column:4}.panel .cols span:nth-child(4){grid-column:5}
 .axis{display:grid;grid-template-columns:26px 250px minmax(0,1fr) 64px;column-gap:10px;margin:0 0 4px;padding:0 8px}
 .axis span{grid-column:3;grid-row:1}.axis span:first-child{justify-self:start}.axis span:last-child{justify-self:end}
 li.gap{padding:6px 8px 6px 42px}
}
@media (min-width:1320px){figure:not(.static){margin:34px -220px}}
/* fig 1: chart left, top 6 right */
.rd{display:grid;grid-template-columns:minmax(0,1fr) 370px;gap:18px;align-items:start}
@media (max-width:860px){.rd{grid-template-columns:1fr}}
.rdl{padding:12px 10px 6px}
.panel.rdl li:not(.gap){display:grid;grid-template-columns:24px minmax(0,1fr) 62px;column-gap:8px;align-items:center;padding:5px 8px}
.panel.rdl .cols{grid-template-columns:24px minmax(0,1fr) 62px;column-gap:8px}
.panel.rdl .cols span:nth-child(3){grid-column:3}
.panel.rdl li .row{display:contents}
.panel.rdl li .rank{grid-column:1}.panel.rdl li .name{grid-column:2}.panel.rdl li .num{grid-column:3}
.rdl .dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:7px;vertical-align:1px}
.rdl li.gap{font-size:12.5px;padding:6px 8px 6px 40px}
/* still frames for the GIF: only figure 1, fixed width */
body.still .top,body.still article>*:not(#fig1){display:none}
body.still article{max-width:none;width:1100px;margin:0}
body.still #fig1{margin:0;box-shadow:none;border-radius:0}
body.still #fig1 .ctl,body.still #fig1 .fn{display:none}
.notes{font-size:14px;color:var(--muted);line-height:1.65}
.notes li{margin:0 0 8px}
.notes a{overflow-wrap:anywhere}
.refs{padding-left:22px;word-break:break-word}
.ref{color:var(--purple);text-decoration:none;font-size:.85em}
.flag{font-size:.8em;color:var(--red);font-weight:600}
hr{border:0;border-top:1px solid var(--line);margin:52px 0 0}
</style></head><body>"""

JS = r"""<script>
const D=__DATA__;
const SER={};D.series.forEach(s=>SER[s.id]=s);
const tip=document.getElementById("tip");
const css=v=>getComputedStyle(document.documentElement).getPropertyValue(v).trim();
const money=v=>Math.abs(v)>=10000?"$"+(v/1000).toFixed(2)+"B":"$"+Math.round(v).toLocaleString("en-US")+"M";
const money1=v=>Math.abs(v)>=10000?"$"+(v/1000).toFixed(1)+"B":"$"+Math.round(v).toLocaleString("en-US")+"M";
const moneyT=v=>"$"+v.toLocaleString("en-US",{minimumFractionDigits:1,maximumFractionDigits:1})+"M";
const sgn=v=>(v>=0?"+":"−")+money(Math.abs(v));
const pct=(e,a)=>(e>=0?"+":"−")+Math.abs(e/a*100).toFixed(1)+"%";
const esc=s=>String(s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const KIND={statistical:"statistical",ML:"ML","deep learning":"deep learning",baseline:"baseline"};
function showTip(e,html){tip.innerHTML=html;tip.style.opacity=1;const w=tip.offsetWidth,h=tip.offsetHeight;
 let x=e.clientX+14,y=e.clientY+14;if(x+w>innerWidth-8)x=Math.max(8,e.clientX-w-14);if(y+h>innerHeight-8)y=Math.max(8,e.clientY-h-14);
 tip.style.left=x+"px";tip.style.top=y+"px";}
function hideTip(){tip.style.opacity=0;}
addEventListener("scroll",hideTip,{passive:true});
function hover(el,fn){el.addEventListener("pointermove",e=>showTip(e,fn(e)));el.addEventListener("pointerdown",e=>showTip(e,fn(e)));
 el.addEventListener("pointerleave",e=>{if(e.pointerType==="mouse")hideTip();});}
function seg(fig,name,cb){const g=fig.querySelector(`[data-ctl="${name}"]`);if(!g)return;
 g.querySelectorAll("button").forEach(b=>b.onclick=()=>{if(b.disabled)return;g.querySelectorAll("button").forEach(x=>x.setAttribute("aria-pressed",x===b));cb(b.dataset.v);});}
function setSeg(fig,name,v){fig.querySelectorAll(`[data-ctl="${name}"] button`).forEach(x=>x.setAttribute("aria-pressed",x.dataset.v===v));}
const redraws=[];function onRedraw(f){redraws.push(f);}
new MutationObserver(()=>redraws.forEach(f=>f())).observe(document.documentElement,{attributes:true,attributeFilter:["data-theme"]});
let rz;addEventListener("resize",()=>{clearTimeout(rz);rz=setTimeout(()=>redraws.forEach(f=>f()),120);});
matchMedia("(prefers-color-scheme: dark)").addEventListener("change",()=>redraws.forEach(f=>f()));
const tagOf=k=>k==="foundation"?"":`<span class="tag">${KIND[k]||k}</span>`;

/* fig 1: each report day, the history chart (3 closest models) next to the top 6 with Wall Street slotted in */
(function(){const fig=document.getElementById("fig1"),list=document.getElementById("resList");
const still=location.hash.match(/^#still=(\d+)/);let I=still?+still[1]:0;
const COLS=["--purple","--blue","--pink"];
function draw(){const p=D.prints[I],st=p.st-p.a,s=SER[p.id];
 const rows=p.rows.map(r=>({...r,ws:false})).concat([{m:"Wall Street consensus",k:"street",f:p.st,e:st,ws:true}]).sort((a,b)=>Math.abs(a.e)-Math.abs(b.e));
 rows.forEach((r,i)=>r.r=i+1);
 const wsr=rows.find(r=>r.ws).r,win=rows.find(r=>!r.ws);
 document.getElementById("resTitle").textContent=`${p.label}, ${p.q}`;
 document.getElementById("resSub").textContent=(still?`Report day ${I+1} of ${D.prints.length} · `:"")+`${p.beat} of ${p.rows.length} models beat the Wall Street consensus. Wall Street finished #${wsr} of ${rows.length}.`;
 document.getElementById("resTiles").innerHTML=`<div><span>Actual</span><b>${moneyT(p.a)}</b><em>reported ${p.q}</em></div>`+
  `<div class="s"><span>Wall Street consensus</span><b>${moneyT(p.st)}</b><em class="s">${pct(st,p.a)} · ${sgn(st)}</em><em>${esc(p.src)}</em></div>`+
  `<div class="w"><span>Closest · ${esc(win.m)}</span><b>${moneyT(win.f)}</b><em>${pct(win.e,p.a)} · ${sgn(win.e)}</em><em>CV #${win.cv} before report day</em></div>`;
 histChart(document.getElementById("resSvg"),document.getElementById("resKeys"),s,pickLines(s,"pr"));
 const models=rows.filter(r=>!r.ws),top=models.slice(0,6),ws=rows.find(r=>r.ws);
 let show=rows.filter(r=>r.ws?r.r<=7:top.includes(r));
 list.innerHTML="";
 show.forEach(r=>list.appendChild(row(r,p,rows)));
 if(ws.r>7){const g=document.createElement("li");g.className="gap";g.textContent=`${ws.r-7} more model${ws.r-7===1?"":"s"} closer than Wall Street`;list.appendChild(g);list.appendChild(row(ws,p,rows));}}
function row(r,p,rows){const li=document.createElement("li"),k=r.ws?-1:rows.filter(x=>!x.ws).indexOf(r);
 li.className=[k===0?"lead":"",r.ws?"street":"",(r.k!=="foundation"&&!r.ws)?"base":""].join(" ");
 const dot=k>=0&&k<3?`<i class="dot" style="background:${css(COLS[k])}"></i>`:"";
 li.innerHTML=`<div class="row"><span class="rank">${r.r}</span><span class="name">${dot}${r.ws?"Wall Street":esc(r.m)}${r.ws?"":tagOf(r.k)}</span><span class="num">${pct(r.e,p.a)}</span></div>`;
 hover(li,()=>`<b>${esc(r.m)}</b><br>Forecast <span class="m">${money(r.f)}</span><br>Miss <span class="m">${sgn(r.e)} (${pct(r.e,p.a)})</span>`+(r.ws?`<br>${esc(p.src)}`:`<br>Position <span class="m">#${r.r} of ${rows.length}</span> · CV <span class="m">#${r.cv}</span>`));
 return li;}
seg(fig,"p",v=>{I=+v;draw();});
document.querySelectorAll("#score tbody tr").forEach(tr=>tr.onclick=()=>{I=+tr.dataset.i;setSeg(fig,"p",String(I));draw();fig.scrollIntoView({behavior:"smooth",block:"start"});});
if(still){document.body.classList.add("still");document.fonts.ready.then(()=>{draw();document.title="H"+Math.ceil(fig.getBoundingClientRect().bottom);});}
draw();onRedraw(draw);})();

/* fig 2: season board */
(function(){const fig=document.getElementById("fig2"),list=document.getElementById("brdList"),more=document.getElementById("brdMore");
let O="p",all=false;
function draw(){const key=O;const items=D.board.filter(b=>b.m!=="seasonal-naive").slice().sort((a,b)=>a[key]-b[key]);
 const rows=items.map((b,i)=>({...b,r:i+1,v:b[key]}));
 if(O==="p"){const k=rows.filter(r=>r.v<D.street).length;rows.splice(k,0,{m:"Wall Street consensus",ws:true,v:D.street,per:D.street_per});}
 document.getElementById("brdCol").textContent=O==="p"?"Score":"CV";
 document.getElementById("brdSub").textContent=O==="p"?`Score is MASE relative to seasonal naive, averaged over the ${D.prints.length} prints. Lower is better.`:"The cross-validation leaderboard before the prints, the geometric mean of each model's 12-quarter relative MASE across all __NSER__ series. Lower is better. Wall Street has no cross-validation score.";
 const show=all?rows:rows.slice(0,O==="p"?13:12);const hi=Math.max(...rows.map(r=>r.v))*1.04;
 list.innerHTML="";
 show.forEach(r=>{const li=document.createElement("li");li.className=r.ws?"street":[r.r===1?"lead":"",r.k!=="foundation"?"base":""].join(" ");
  li.innerHTML=`<div class="row"><span class="rank">${r.ws?"·":r.r}</span><span class="name">${esc(r.m)}${r.ws?"":tagOf(r.k)}</span><span class="num">${r.v.toFixed(3)}</span><span class="num sm">${r.ws?"·":r.bs+" of "+D.prints.length}</span></div><div class="track"><i style="width:${(100*r.v/hi).toFixed(1)}%"></i></div>`;
  hover(li,()=>`<b>${esc(r.m)}</b>`+(r.ws?"":`<br>Prints <span class="m">${r.p.toFixed(3)}</span> · CV <span class="m">${r.cv.toFixed(3)}</span>`)+
   r.per.map((v,i)=>`<br>${D.pshort[i]} <span class="m">${v.toFixed(3)}</span>`).join("")+(r.ws?"":`<br>Beat Wall Street on <span class="m">${r.bs} of ${D.prints.length}</span>`));
  list.appendChild(li);});
 more.textContent=all?"Show fewer":`Show all ${rows.length}`;}
more.onclick=()=>{all=!all;draw();};
seg(fig,"o",v=>{O=v;draw();});draw();})();

/* fig 3: benchmark order vs earnings order (tokens slope chart) */
(function(){const fig=document.getElementById("fig3"),box=document.getElementById("slope");let BK="gift",TG="p";
const BN={gift:"GIFT-Eval",gq:"GIFT-Eval quarterly",fev:"fev-bench"},TN={p:"Earnings · the prints",cv:"Earnings · cross-validation"};
function draw(){const pool=D.board.filter(b=>b.k==="foundation"&&b[BK]!=null);
 const rb={},re={};pool.slice().sort((a,b)=>a[BK]-b[BK]).forEach((b,i)=>rb[b.m]=i+1);pool.slice().sort((a,b)=>a[TG]-b[TG]).forEach((b,i)=>re[b.m]=i+1);
 const HL={};pool.slice().sort((a,b)=>rb[a.m]-rb[b.m]).slice(0,3).forEach((b,i)=>HL[b.m]=["--purple","--orange","--pink"][i]);
 document.getElementById("slpSub").textContent=`The ${pool.length} foundation models with a ${BN[BK]} entry. Left is their ${BN[BK]} order, right is their order on the earnings ${TG==="p"?"prints":"cross-validation"}.`;
 const W=Math.max(300,box.clientWidth),narrow=W<560,row=narrow?22:26,top=44,n=pool.length,Hh=top+row*n+6;
 const gap=Math.min(240,W*.26),x1=W/2-gap/2,x2=W/2+gap/2,fs=narrow?10.5:12.5,mono=narrow?9.5:11;
 const cut=s=>narrow&&s.length>16?s.slice(0,15)+"…":s;
 let s=`<svg viewBox="0 0 ${W} ${Hh}" role="img" aria-label="${BN[BK]} order compared with earnings order">`;
 s+=`<text x="${x1}" y="16" text-anchor="end" font-size="12" font-weight="700" fill="${css("--ink")}">${BN[BK]}</text><text x="${x2}" y="16" font-size="12" font-weight="700" fill="${css("--ink")}">${narrow?"Earnings":TN[TG]}</text>`;
 s+=`<text x="${x1}" y="31" text-anchor="end" font-size="10.5" fill="${css("--muted")}">MASE vs naive</text><text x="${x2}" y="31" font-size="10.5" fill="${css("--muted")}">${TG==="p"?"miss vs naive":"rel. MASE"}</text>`;
 const order=pool.slice().sort((a,b)=>(HL[a.m]?1:0)-(HL[b.m]?1:0));
 for(const m of order){const ya=top+row*(rb[m.m]-1)+row/2,yb=top+row*(re[m.m]-1)+row/2,c=HL[m.m]?css(HL[m.m]):css("--stem");
  s+=`<g class="ln" data-f="${m.m}"><path d="M${x1+8},${ya} C${(x1+x2)/2},${ya} ${(x1+x2)/2},${yb} ${x2-8},${yb}" fill="none" stroke="${c}" stroke-width="${HL[m.m]?2.6:1.4}" stroke-linecap="round"/>
  <path d="M${x1+8},${ya} C${(x1+x2)/2},${ya} ${(x1+x2)/2},${yb} ${x2-8},${yb}" fill="none" stroke="transparent" stroke-width="12"/>
  <circle cx="${x1+8}" cy="${ya}" r="3.5" fill="${c}"/><circle cx="${x2-8}" cy="${yb}" r="3.5" fill="${c}"/>
  <text x="${x1-4}" y="${ya+4}" text-anchor="end" font-size="${fs}" font-weight="${HL[m.m]?700:500}" fill="${HL[m.m]?css("--ink"):css("--text")}">${cut(m.m)} <tspan font-family="Roboto Mono" font-size="${mono}" fill="${css("--muted-2")}">${rb[m.m]}</tspan></text>
  <text x="${x2+4}" y="${yb+4}" font-size="${fs}" font-weight="${HL[m.m]?700:500}" fill="${HL[m.m]?css("--ink"):css("--text")}"><tspan font-family="Roboto Mono" font-size="${mono}" fill="${css("--muted-2")}">${re[m.m]}</tspan> ${cut(m.m)}</text></g>`;}
 box.innerHTML=s+"</svg>";
 box.querySelectorAll(".ln").forEach(el=>{const f=el.dataset.f,m=pool.find(x=>x.m===f);
  const on=()=>box.querySelectorAll(".ln").forEach(o=>o.style.opacity=o===el?1:.18);
  el.addEventListener("pointermove",on);el.addEventListener("pointerdown",on);
  hover(el,()=>`<b>${f}</b><br>${BN[BK]} <span class="m">#${rb[f]}</span> · <span class="m">${m[BK].toFixed(3)}</span><br>Earnings ${TG==="p"?"prints":"CV"} <span class="m">#${re[f]} of ${pool.length}</span> · <span class="m">${m[TG].toFixed(3)}</span>`);
  el.addEventListener("pointerleave",()=>box.querySelectorAll(".ln").forEach(o=>o.style.opacity=1));});}
seg(fig,"b",v=>{BK=v;draw();});seg(fig,"t",v=>{TG=v;draw();});draw();onRedraw(draw);})();

/* history chart shared by fig 4 and fig 5 */
function histChart(box,keys,s,lines){
 const W=Math.max(300,box.clientWidth),narrow=W<560,Ht=narrow?250:320,ml=narrow?46:56,mr=10,mt=14,mb=narrow?34:30,iw=W-ml-mr,ih=Ht-mt-mb;
 const H=s.hist.length,nf=s.fut.length,labs=s.hist.map(h=>h[0]).concat(s.fut),n=labs.length,xi=i=>ml+iw*i/(n-1);
 const cols=[css("--purple"),css("--blue"),css("--pink"),css("--dot")],dash=["","","","5 4"];
 let lo=Infinity,hi=-Infinity;const upd=v=>{if(v==null)return;lo=Math.min(lo,v);hi=Math.max(hi,v);};
 s.hist.forEach(h=>upd(h[1]));lines.forEach(l=>{l.bt.forEach(upd);l.fut.forEach(upd);});upd(s.result);if(s.cons)upd(s.cons.v);
 const span=hi-lo||hi,raw=span/4,mag=Math.pow(10,Math.floor(Math.log10(raw))),step=[1,2,2.5,5,10].map(k=>k*mag).find(k=>k>=raw);
 const y0=Math.max(0,Math.floor((lo-span*.06)/step)*step),y1=Math.ceil((hi+span*.04)/step)*step,y=v=>mt+ih*(1-(v-y0)/(y1-y0));
 const bt0=H-12,xb=xi(bt0)-iw/(n-1)/2,xf=xi(H)-iw/(n-1)/2;
 let g=`<svg viewBox="0 0 ${W} ${Ht}" role="img" aria-label="Quarterly history and forecasts for ${esc(s.label)}">`;
 g+=`<rect x="${xb}" y="${mt}" width="${xf-xb}" height="${ih}" fill="${css("--grid")}" rx="4"/><rect x="${xf}" y="${mt}" width="${ml+iw-xf+4}" height="${ih}" fill="${css("--purple-soft")}" rx="4"/>`;
 g+=`<text x="${xb+6}" y="${mt+12}" style="font-family:'DM Sans';font-size:10.5px;fill:${css("--muted")}">backtest</text><text x="${xf+5}" y="${mt+12}" style="font-family:'DM Sans';font-size:10.5px;fill:${css("--muted")}">${narrow?"locked":"locked forecasts"}</text>`;
 for(let v=y0;v<=y1+1e-9;v+=step)g+=`<line x1="${ml}" x2="${ml+iw}" y1="${y(v)}" y2="${y(v)}" stroke="${css("--grid")}"/><text x="${ml-6}" y="${y(v)+3.5}" text-anchor="end" fill="${css("--muted")}">${v?(y1>=10000?"$"+(+(v/1000).toFixed(1))+"B":"$"+v.toLocaleString("en-US")+"M"):"0"}</text>`;
 const every=narrow?4:2;labs.forEach((l,i)=>{if((n-1-i)%every===0){const t=l.replace(/ (FY)?(\d{2})(\d{2})$/,(m,fy,a,b)=>` ${fy?"FY":"'"}${b}`);g+=`<text x="${xi(i)}" y="${Ht-mb+16}" text-anchor="middle" fill="${css("--muted")}">${t}</text>`;}});
 lines.slice().reverse().forEach((l,ri)=>{const i=lines.length-1-ri,c=l.base?cols[3]:cols[i],d=l.base?dash[3]:"";
  const P=l.bt.map((v,j)=>[xi(bt0+j),y(v)]),F=[[xi(H-1),y(s.hist[H-1][1])]].concat(l.fut.map((v,j)=>[xi(H+j),y(v)]));
  g+=`<path d="${P.map((p,j)=>(j?"L":"M")+p[0].toFixed(1)+","+p[1].toFixed(1)).join("")}" fill="none" stroke="${c}" stroke-width="${i===0&&!l.base?2.2:1.6}" stroke-dasharray="${d}" stroke-linejoin="round"/>`;
  g+=`<path d="${F.map((p,j)=>(j?"L":"M")+p[0].toFixed(1)+","+p[1].toFixed(1)).join("")}" fill="none" stroke="${c}" stroke-width="1.8" stroke-dasharray="${l.base?"5 4":"2 3"}" opacity=".9"/>`;
  if(!l.base){P.forEach(p=>g+=`<circle cx="${p[0]}" cy="${p[1]}" r="2.2" fill="${c}"/>`);g+=`<circle cx="${F[1][0]}" cy="${F[1][1]}" r="3.6" fill="${c}"/>`;}});
 g+=`<path d="${s.hist.map((h,j)=>(j?"L":"M")+xi(j).toFixed(1)+","+y(h[1]).toFixed(1)).join("")}" fill="none" stroke="${css("--ink")}" stroke-width="2.4" stroke-linejoin="round"/>`;
 s.hist.forEach((h,j)=>g+=`<circle cx="${xi(j)}" cy="${y(h[1])}" r="2.3" fill="${css("--ink")}"/>`);
 if(s.cons){const cx=xi(H),cy=y(s.cons.v);g+=`<path d="M${cx},${cy-6}L${cx+6},${cy}L${cx},${cy+6}L${cx-6},${cy}Z" fill="${css("--red")}"/>`;}
 if(s.result!=null)g+=`<circle cx="${xi(H)}" cy="${y(s.result)}" r="5.5" fill="none" stroke="${css("--ink")}" stroke-width="2.2"/><circle cx="${xi(H)}" cy="${y(s.result)}" r="2.2" fill="${css("--ink")}"/>`;
 g+=`<line class="xh" x1="0" x2="0" y1="${mt}" y2="${mt+ih}" stroke="${css("--muted-2")}" stroke-dasharray="2 3" opacity="0"/><rect class="hit" x="${ml}" y="${mt}" width="${iw}" height="${ih}" fill="transparent"/></svg>`;
 box.innerHTML=g;
 keys.innerHTML=`<span><svg viewBox="0 0 22 8"><line x1="1" x2="21" y1="4" y2="4" stroke="${css("--ink")}" stroke-width="2.4"/></svg>Actual</span>`+
  lines.map((l,i)=>`<span><svg viewBox="0 0 22 8"><line x1="1" x2="21" y1="4" y2="4" stroke="${l.base?cols[3]:cols[i]}" stroke-width="2.2" stroke-dasharray="${l.base?dash[3]:""}"/></svg>${esc(l.m)} <b>${l.cv.toFixed(3)}</b></span>`).join("")+
  (s.cons?`<span><svg viewBox="0 0 22 8"><path d="M11,0L15,4L11,8L7,4Z" fill="${css("--red")}"/></svg>Wall Street ${money(s.cons.v)}</span>`:"");
 const svg=box.querySelector("svg"),xh=svg.querySelector(".xh"),hit=svg.querySelector(".hit");
 const at=e=>{const r=svg.getBoundingClientRect(),px=(e.clientX-r.left)*W/r.width,i=Math.max(0,Math.min(n-1,Math.round((px-ml)/iw*(n-1))));
  xh.setAttribute("x1",xi(i));xh.setAttribute("x2",xi(i));xh.setAttribute("opacity",1);
  let h=`<b>${labs[i]}</b>`;if(i<H)h+=`<br>Actual <span class="m">${money(s.hist[i][1])}</span>`;
  if(i===H&&s.result!=null)h+=`<br>Actual <span class="m">${money(s.result)}</span>`;
  if(i===H&&s.cons)h+=`<br>Wall Street <span class="m">${money(s.cons.v)}</span>`;
  lines.forEach(l=>{const v=i>=bt0&&i<H?l.bt[i-bt0]:i>=H?l.fut[i-H]:null;if(v!=null)h+=`<br>${esc(l.m)} <span class="m">${money(v)}</span>`;});
  if(i>=H)h+=`<br><span style="opacity:.7">locked forecast, ${i-H+1} quarter${i>H?"s":""} ahead</span>`;else if(i>=bt0)h+=`<br><span style="opacity:.7">backtest, 1 quarter ahead</span>`;return h;};
 hover(hit,at);hit.addEventListener("pointerleave",()=>xh.setAttribute("opacity",0));}
function pickLines(s,mode){let ms;
 if(mode==="pr"){const p=D.prints.find(x=>x.id===s.id);const top=p.rows.slice(0,3).map(r=>r.m);ms=top.map(m=>s.models.find(x=>x.m===m));}
 else ms=s.models.filter(m=>m.m!=="seasonal-naive").slice(0,3);
 const sn=s.models.find(m=>m.m==="seasonal-naive");return ms.map(m=>({...m})).concat([{...sn,base:true}]);}

/* fig 4: any series */
(function(){const fig=document.getElementById("fig4"),sel=document.getElementById("hSel");let ID=D.prints[0].id,L="cv";
function draw(){const s=SER[ID],rep=s.result!=null;
 fig.querySelectorAll('[data-ctl="l"] button').forEach(b=>{if(b.dataset.v==="pr")b.disabled=!rep;});
 if(!rep&&L==="pr"){L="cv";setSeg(fig,"l","cv");}
 document.getElementById("hTitle").textContent=`${s.label}, history and forecasts`;
 document.getElementById("hSub").textContent=rep?`${s.q} reported ${moneyT(s.result)}`+(s.cons?` against a Wall Street consensus of ${moneyT(s.cons.v)} (${s.cons.src}).`:"."):`${s.q} reports ${s.date}. Forecasts are locked.`;
 histChart(document.getElementById("hSvg"),document.getElementById("hKeys"),s,pickLines(s,L));}
sel.onchange=()=>{ID=sel.value;draw();};seg(fig,"l",v=>{L=v;draw();});draw();onRedraw(draw);})();

/* fig 5: prints still to come */
(function(){const fig=document.getElementById("fig5"),list=document.getElementById("pList"),more=document.getElementById("pMore");
const pend=D.series.filter(s=>s.result==null);let ID=pend[0].id,all=false;
function draw(){const s=SER[ID];
 document.getElementById("pTitle").textContent=`${s.label}, ${s.q}`;
 document.getElementById("pSub").textContent=`Reports ${s.date}. `+(s.cons?`Wall Street consensus so far ${money(s.cons.v)} (${s.cons.src}).`:"No Wall Street consensus captured yet.")+` Cross-validation leader ${s.models[0].m} has it at ${money(s.models[0].fut[0])}.`;
 histChart(document.getElementById("pSvg"),document.getElementById("pKeys"),s,pickLines(s,"cv"));
 const rows=s.models.map((m,i)=>({...m,r:i+1})),show=all?rows:rows.slice(0,10),hi=Math.max(...rows.filter(r=>r.m!=="seasonal-naive").map(r=>r.cv))*1.04;
 list.innerHTML="";
 show.forEach(r=>{const li=document.createElement("li");li.className=[r.r===1?"lead":"",r.k!=="foundation"?"base":""].join(" ");
  li.innerHTML=`<div class="row"><span class="rank">${r.r}</span><span class="name">${esc(r.m)}${tagOf(r.k)}</span><span class="num">${r.cv.toFixed(3)}</span><span class="num sm">${money1(r.fut[0])}</span></div><div class="track"><i style="width:${Math.min(100,100*r.cv/hi).toFixed(1)}%"></i></div>`;
  hover(li,()=>`<b>${esc(r.m)}</b><br>CV rel. MASE <span class="m">${r.cv.toFixed(3)}</span> · <span class="m">#${r.r} of ${rows.length}</span><br>Locked ${s.fut[0]} <span class="m">${money(r.fut[0])}</span>`+(s.cons?`<br>vs Wall Street <span class="m">${sgn(r.fut[0]-s.cons.v)}</span>`:""));
  list.appendChild(li);});
 more.textContent=all?"Show top 10":`Show all ${rows.length}`;}
more.onclick=()=>{all=!all;draw();};seg(fig,"s",v=>{ID=v;draw();});draw();onRedraw(draw);})();

document.getElementById("theme").onclick=()=>{const r=document.documentElement;
 const dark=r.dataset.theme?r.dataset.theme==="dark":matchMedia("(prefers-color-scheme: dark)").matches;r.dataset.theme=dark?"light":"dark";};
</script></body></html>
"""

out = HERE / "index.html"
def renumber(page):
    """Number citations [1], [2], ... in order of first use in the text and reorder the reference list to match."""
    cut = page.index('<li id="r1"')
    order = list(dict.fromkeys(int(n) for n in re.findall(r'href="#r(\d+)"', page[:cut])))
    items = dict(re.findall(r'(?s)<li id="r(\d+)">(.*?)</li>', page[cut:]))
    order += [int(n) for n in items if int(n) not in order]          # anything uncited goes last
    new = {old: i + 1 for i, old in enumerate(order)}
    head, rest = page[:cut], page[cut:]
    start, end = rest.index('<li id="r'), rest.rindex("</li>") + len("</li>")
    head = re.sub(r'href="#r(\d+)">\[\d+\]', lambda m: f'href="#r{new[int(m.group(1))]}">[{new[int(m.group(1))]}]', head)
    refs = "\n".join(f'<li id="r{new[o]}">{items[str(o)]}</li>' for o in order)
    return head + rest[:start] + refs + rest[end:]


def renumber_figures(page):
    """Figure numbers follow the order the figures appear in; text mentions follow along."""
    order = list(dict.fromkeys(re.findall(r'<p class="fn">Figure (\d+)</p>', page)))
    new = {o: str(i + 1) for i, o in enumerate(order)}
    return re.sub(r"Figure (\d+)", lambda m: f"Figure {new.get(m.group(1), m.group(1))}", page)


GB, GA = r"""(?<![\w.$"'`])""", r"""(?![\w=(\["'`:])"""   # not code: skip identifiers, quoted keys, properties
WORDING = [                                              # reader-facing "print" becomes "report day"
    (r">The prints<", ">Report day<"), (r"Print by print", "Report by report"), (r"pre-print", "pre-report"),
    (GB + r"earnings print" + GA, "earnings report"), (GB + r"at that print" + GA, "on that report day"),
    (GB + r"(?:at|on) the prints?" + GA, "on report day"), (GB + r"vs\.? the prints" + GA, "vs report day"),
    (GB + r"(before|after) the prints?" + GA, r"\1 report day"),
    (GB + r"the prints" + GA, "the report days"), (GB + r"the print" + GA, "report day"),
    (GB + r"Prints" + GA, "Report days"), (GB + r"prints" + GA, "report days"),
    (GB + r"Print" + GA, "Report day"), (GB + r"print" + GA, "report day")]


def reword(page):
    head, body = page.split("<body", 1)                   # leave <head> (CSS, meta) alone
    for a, b in WORDING:
        body = re.sub(a, b, body)
    return head + "<body" + body


out.write_text(reword(renumber_figures(renumber(HEAD + CSS + BODY + JS.replace("__DATA__", json.dumps(JS_DATA, separators=(",", ":"))).replace("__NSER__", str(len(S)))))))
print("wrote", out, f"{out.stat().st_size / 1e3:.0f} kB")
