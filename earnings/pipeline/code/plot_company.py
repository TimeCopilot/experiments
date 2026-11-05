"""Per-company report in the Coinbase layout (~/Downloads/coinbase-bundle 2/code/plot_coinbase_h1.py): page 1 is the
actuals, the 12-quarter h=1 backtest of the top 5 foundation models plus AutoARIMA and seasonal naive, joined to their
locked 4-quarter forecasts; page 2 ranks the top 10 by relative MASE, then every other non-foundation model, with the
locked next-quarter forecast and its change from the last two actuals (and the Wall Street consensus where captured).

Needs code/run_local.py output for the series. Styles and footer come from the Coinbase script.
Writes out/<company>/report{,_ranking}.html, light/dark PNGs and <Company>_report.pdf.

    python code/plot_company.py                  # every company
    python code/plot_company.py --company Apple
"""
import csv, math, pathlib, subprocess, sys
from PIL import Image, ImageChops
import config

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "source/earnings-tracker/coinbase/code"))
from plot_coinbase_h1 import CHROME, FOOT_CSS, FOOTER, RANK_CSS, page   # noqa: E402

STATS = {"auto-arima", "auto-ets", "auto-theta", "naive"}
TAG = {**{m: "statistical" for m in STATS | {"prophet"}}, "seasonal-naive": "baseline", "lightgbm": "ML", "xgboost": "ML",
       "n-beats": "deep learning"}
NONFM = set(TAG)                                         # everything that isn't a foundation model
STYLE = {"seasonal-naive": "5 4", "auto-arima": "1.5 3.5"}
SLOTS = ["var(--purple)", "var(--c-blue)", "var(--c-orange)", "var(--c-aqua)", "var(--c-yellow)", "var(--c-magenta)"]
# Street consensus for the next print: Apple/Palantir from street_consensus_nov2.md in the bundle, the rest looked up Nov 2, 2026
CONSENSUS = {"apple_iphone": (57180.0, "Zacks, Oct 31, 2026"), "palantir_total": (2170.0, "Zacks, Oct 31, 2026"),
             "amd_dc": (8270.0, "Zacks, Oct 29, 2026"), "mcd_total": (7280.0, "Zacks, Oct 30, 2026"),
             "mcd_franchised": (4520.0, "Zacks, Oct 30, 2026"), "hd_net_sales": (42740.0, "Yahoo Finance, 25 analysts, Nov 2, 2026"),
             "shopify_gmv": (120030.0, "StreetAccount; Zacks/CIBC pre-print range $117.8-118.7B")}
# Reported actuals for prints that are already out, USD millions (company 8-K press releases, Nov 2, 2026)
RESULTS = {"apple_iphone": 57583.0, "palantir_total": 2313.411, "amd_dc": 8546.0, "mcd_total": 7157.0, "mcd_franchised": 4487.0, "shopify_gmv": 119145.0}
SUBJECT = {"Apple": "Apple iPhone net sales", "Palantir": "Palantir revenue", "AMD": "AMD Data Center revenue",
           "Disney": "Disney Experiences revenue", "Home Depot": "Home Depot net sales",
           "McDonald's": "McDonald's total and franchised revenues", "Nvidia": "Nvidia Data Center revenue",
           "Walmart": "Walmart U.S. net sales", "Shopify": "Shopify GMV"}
HALO = ".ann,.band{paint-order:stroke;stroke:var(--card);stroke-width:4px;stroke-linejoin:round}"
SHOW = 20                                                # actual quarters on the chart (12 backtest + 8 before)

money = lambda v: f"${v / 1000:,.1f}B" if abs(v) >= 1000 else (f"${v:,.0f}M" if v else "$0")
fmt = lambda v: f"${v:,.0f}M"


def series(key):
    s = config.load(key)
    d = config.OUT / key
    board = list(csv.DictReader(open(d / "leaderboard_all.csv")))
    local = list(csv.DictReader(open(d / "local_per_fold.csv")))
    locked = {m: [float(r[c]) for c in s["hcols"]] for m, r in s["locked"].items()}
    locked.update({r["model"]: [float(r[f"h{i}"]) for i in range(1, 5)] for r in csv.DictReader(open(d / "local_locked.csv"))})
    bt_q = [q for q, _ in s["hist"][-12:]]

    def backtest(m):
        src = local if m in NONFM - {"seasonal-naive"} else s["folds"]
        rs = sorted((r for r in src if r["model"] == m), key=lambda r: int(r["fold"]))
        assert len(rs) == 12, (key, m)
        return [(q, float(r["forecast"])) for q, r in zip(bt_q, rs)]

    score = {r["model"]: float(r["rel_geomean"]) for r in board}
    top = [r["model"] for r in board if r["model"] not in NONFM][:5]
    if board[0]["model"] in NONFM and board[0]["model"] not in STYLE:   # a local model leads the board: draw it too
        top = [board[0]["model"]] + top
    lines = [{"m": m, "score": score[m], "bt": backtest(m), "fut": list(zip(s["fut"], locked[m]))}
             for m in top + list(STYLE)[::-1]]
    return {**s, "board": board, "locked_all": locked, "lines": lines}


def svg(p, color):
    hist = p["hist"][-SHOW:]
    while not hist[0][0].startswith("Q1") and len(hist) > SHOW - 3:   # start on a year boundary so the first year label fits
        hist = hist[1:]
    QS = [q for q, _ in hist] + p["fut"]
    X = {q: i for i, q in enumerate(QS)}
    vals = [v for _, v in hist] + [v for l in p["lines"] for _, v in l["bt"] + l["fut"]]
    step = 10 ** math.floor(math.log10((max(vals) - min(vals)) / 4))
    step *= next(k for k in (1, 2, 2.5, 5, 10) if (max(vals) - min(vals)) / (step * k) <= 5)
    lo, hi = math.floor(min(vals) / step) * step, math.ceil(max(vals) / step) * step
    W, H, ML, MR, MT, MB = 1000, 380, 70, 18, 40, 48
    IW, IH = W - ML - MR, H - MT - MB
    xs = lambda q: ML + IW * X[q] / (len(QS) - 1)
    ys = lambda v: MT + IH * (1 - (v - lo) / (hi - lo))
    path = lambda pts: "M" + "L".join(f"{xs(q):.1f},{ys(v):.1f}" for q, v in pts)
    half = IW / (len(QS) - 1) / 2
    b0, b1, f0 = xs(p["hist"][-12][0]), xs(p["hist"][-1][0]), xs(p["fut"][0])
    s = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="{p["company"]} {p["metric"]}: actuals, backtest and locked forecasts">',
         f'<rect x="{f0:.1f}" y="{MT - 34}" width="{ML + IW - f0:.1f}" height="{IH + 34}" fill="var(--purple-soft)"/>',
         f'<text x="{f0 + 6:.1f}" y="{MT - 20}" class="band">forward window</text>',
         f'<path d="M{b0:.1f},{MT - 2}V{MT - 6}H{b1:.1f}V{MT - 2}" fill="none" stroke="var(--line)"/>',
         f'<text x="{b0:.1f}" y="{MT - 11}" class="band">backtest quarters · {p["hist"][-12][0]} to {p["hist"][-1][0]}</text>']
    v = lo
    while v <= hi + 1e-9:
        s.append(f'<line x1="{ML}" x2="{ML + IW}" y1="{ys(v):.1f}" y2="{ys(v):.1f}" stroke="var(--grid)"/>'
                 f'<text x="{ML - 8}" y="{ys(v) + 4:.1f}" text-anchor="end" class="tick">{money(v)}</text>')
        v += step
    for q in QS:
        x = xs(q)
        s.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{MT + IH}" y2="{MT + IH + 4}" stroke="var(--line)"/>'
                 f'<text x="{x:.1f}" y="{MT + IH + 17}" text-anchor="middle" class="tick">{q[:2]}</text>')
        if q.startswith("Q1") and q != QS[0]:
            s.append(f'<line x1="{x - half:.1f}" x2="{x - half:.1f}" y1="{MT + IH}" y2="{H - 2}" stroke="var(--line)"/>')
    for y in dict.fromkeys(q.split()[1] for q in QS):
        xq = [xs(q) for q in QS if q.split()[1] == y]
        s.append(f'<text x="{sum(xq) / len(xq):.1f}" y="{H - 6}" text-anchor="middle" class="year">{y}</text>')
    for l in reversed(p["lines"]):
        base = l["m"] in STYLE
        c = "var(--dot)" if base else color[l["m"]]
        dash = f' stroke-dasharray="{STYLE[l["m"]]}"' if base else ""
        s.append(f'<path d="{path(l["bt"] + l["fut"])}" fill="none" stroke="{c}" stroke-width="1.8"{dash} stroke-linejoin="round"/>')
        if not base:
            for q, v in l["bt"] + l["fut"]:
                s.append(f'<circle cx="{xs(q):.1f}" cy="{ys(v):.1f}" r="2.6" fill="{c}"><title>{l["m"]} · {q} · {fmt(v)}</title></circle>')
    s.append(f'<path d="{path(hist)}" fill="none" stroke="var(--ink)" stroke-width="2.4" stroke-linejoin="round"/>')
    for q, v in hist:
        s.append(f'<circle cx="{xs(q):.1f}" cy="{ys(v):.1f}" r="2.8" fill="var(--ink)"><title>Actual · {q} · {fmt(v)}</title></circle>')
    champ = p["lines"][0]
    q1, v1 = champ["fut"][0]
    low = min(l["fut"][0][1] for l in p["lines"] if l["m"] not in STYLE)
    ty = min(ys(low) + 24, MT + IH - 22)
    s.append(f'<circle cx="{xs(q1):.1f}" cy="{ys(v1):.1f}" r="5.5" fill="none" stroke="{color[champ["m"]]}" stroke-width="1.6"/>'
             f'<text x="{f0 + 6:.1f}" y="{ty:.1f}" class="ann">{short(q1)} {fmt(v1)}</text>'
             f'<text x="{f0 + 6:.1f}" y="{ty + 15:.1f}" class="band">{champ["m"]}</text>')
    return "".join(s) + "</svg>"


def short(q):                                            # "Q3 FY2027" -> "Q3 FY'27", "Q3 2026" -> "Q3 '26"
    n, y = q.split()
    return f"{n} FY'{y[-2:]}" if y.startswith("FY") else f"{n} '{y[-2:]}"


def legend(p, color):
    items = ['<span><i style="background:var(--ink);height:3px"></i>Actual</span>']
    for l in p["lines"]:
        sw = ({"seasonal-naive": '<i class="dash"></i>', "auto-arima": '<i class="dot"></i>'}.get(l["m"])
              or f'<i style="background:{color[l["m"]]}"></i>')
        items.append(f'<span>{sw}{l["m"]} <b>{l["score"]:.3f}</b> <em>{short(l["fut"][0][0])} {fmt(l["fut"][0][1])}</em></span>')
    return "".join(items)


def ranking(p, n=10):
    act = p["hist"]
    (qa, a1), (qb, a0) = act[-1], act[-2]
    nq = short(p["fut"][0])
    pct = lambda v, base: f'<td class="num delta">{round((v / base - 1) * 100, 1) + 0:+.1f}%</td>'.replace("+0.0%", "0.0%")
    cells = lambda v: f'<td class="num q3">{fmt(v)}</td>' + pct(v, a1) + pct(v, a0)

    def row(rank, r, cls=""):
        g = float(r["rel_geomean"])
        tag = f'<span class="tag">{TAG[r["model"]]}</span>' if r["model"] in TAG else ""
        return (f'<tr class="{cls}"><td class="rk">{rank}</td><td class="mdl">{r["model"]}{tag}</td>'
                f'<td class="barc"><span class="bar"><i style="width:{min(g, 1) * 100:.1f}%"></i></span></td>'
                f'<td class="num score">{g:.3f}</td>{cells(p["locked_all"][r["model"]][0])}</tr>')

    body = ""
    if p["key"] in CONSENSUS:
        v, src = CONSENSUS[p["key"]]
        body += (f'<tr class="street"><td class="rk"></td><td class="mdl">Wall Street consensus<span class="tag">{src.split(",")[0]}</span></td>'
                 f'<td class="barc"><span class="na">not backtested</span></td><td class="num score">·</td>{cells(v)}</tr>')
    body += "".join(row(i + 1, r, "top" if i == 0 else "") for i, r in enumerate(p["board"][:n]))
    rest = [(i, r) for i, r in enumerate(p["board"]) if i >= n and r["model"] in NONFM]
    body += "".join(row(i + 1, r, "naive" if k == 0 else "base") for k, (i, r) in enumerate(rest))
    return (f'<section><h2>{p["metric"]}</h2><p class="sub">Top {n} of {len(p["board"])} by relative MASE, then every other '
            f'non-foundation model · actuals {qb} {fmt(a0)}, {qa} {fmt(a1)}</p><table><thead><tr><th>#</th><th>Model</th><th></th>'
            f'<th class="num">rel. MASE</th><th class="num q3">{nq} forecast</th><th class="num">vs {short(qa)}</th>'
            f'<th class="num">vs {short(qb)}</th></tr></thead><tbody>{body}</tbody></table></section>')


def render(pages, out_dir, pdf_name):
    shots = {"light": [], "dark": []}
    for name, html in pages.items():
        src = out_dir / f"{name}.html"
        src.write_text(html)
        for theme in shots:
            png = out_dir / f"{name}_{theme}.png"
            subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--window-size=1112,2800",
                            "--force-device-scale-factor=2", "--virtual-time-budget=4000", f"--screenshot={png}",
                            f"{src.as_uri()}#{theme}"], capture_output=True)
            im = Image.open(png).convert("RGB")
            bg = Image.new("RGB", im.size, im.getpixel((2, im.height - 2)))
            box = ImageChops.difference(im, bg).getbbox()
            im = im.crop((0, 0, im.width, min(im.height, box[3] + 64)))
            im.save(png)
            shots[theme].append(im)
    pdf = out_dir / pdf_name
    shots["light"][0].save(pdf, save_all=True, append_images=shots["light"][1:], resolution=200)
    print("wrote", pdf)


def company(name):
    P = [series(k) for k, v in config.SERIES.items() if v[0] == name]
    color = {}                                           # colour follows the model across panels, never repeats inside one
    for p in P:
        ms = [l["m"] for l in p["lines"] if l["m"] not in STYLE]
        for m in ms:
            if m not in color:
                used = {color[x] for x in ms if x in color}
                color[m] = next(c for c in SLOTS if c not in used)
    street = any(p["key"] in CONSENSUS for p in P)
    title = "Can we beat Wall Street using ✨FoundationForecast?"
    lede = f"{SUBJECT[name]} {P[0]['fut'][0]}"
    chart = "".join(f'<section><h2>{p["metric"]}</h2>{svg(p, color)}<div class="keys">{legend(p, color)}</div></section>' for p in P)
    p0 = P[0]
    note1 = (f"<p class='note'>Backtest: 12 forecasts, each made one quarter ahead with only the data available then. Scores are "
             f"error relative to seasonal naive (dashed, same quarter last year), so lower is better and 1 means no better than "
             f"naive. Shaded: forecasts locked before the {p0['fut'][0]} print. Data: {name} SEC filings, USD millions.</p>")
    cons = "".join(f" Consensus: {c}." for c in dict.fromkeys(CONSENSUS[p["key"]][1] for p in P if p["key"] in CONSENSUS))
    note2 = ("<p class='note'>Rel. MASE: error relative to seasonal naive (the baseline, same quarter last year) over the 12 "
             "backtest quarters, geometric mean, so 1 equals naive and lower is better. Non-foundation models ran locally on the "
             f"same quarters. Deltas compare the next-quarter forecast with the last two actuals.{cons} Data: {name} SEC filings, "
             "USD millions.</p>")
    out = config.OUT / name.lower().replace("'", "").replace(" ", "-")
    out.mkdir(parents=True, exist_ok=True)
    render({"report": page(f"{name} forecasts", f"<h1>{title}</h1><p class='lede'>{lede}</p>" + chart + note1 + FOOTER, FOOT_CSS + HALO),
            "report_ranking": page(f"{name} model ranking", "".join(ranking(p) for p in P) + note2 + FOOTER, RANK_CSS + FOOT_CSS)},
           out, f"Can we beat Wall Street using FoundationForecast - {lede}.pdf")


if __name__ == "__main__":
    names = [sys.argv[sys.argv.index("--company") + 1]] if "--company" in sys.argv else list(dict.fromkeys(v[0] for v in config.SERIES.values()))
    for n in names:
        company(n)
