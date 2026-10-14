"""The blog post: copy + four interactive figures, MASE only, TimeCopilot landing-page style.

  Fig 1  MASE relative to seasonal naive by level (all tokens, category, language, models), 1 or 4 weeks ahead
  Fig 2  GIFT-Eval order vs OpenRouter order for the 16 forecasters with a GIFT-Eval entry
  Fig 2b fev-bench order vs OpenRouter order for the 11 forecasters with a fev-bench entry
  Fig 3  each forecaster's position by MASE in each of the 12 weeks
  Fig 4  any series: actual weekly tokens vs backtest forecasts, best 3 forecasters for it + both baselines,
         legend shows relative MASE (avg MASE ÷ seasonal naive's on that series)

Reads standings.csv, weekly.csv, mase_long.csv, gift_eval.csv, fev.csv, series.json, forecasts_api.csv,
forecasts_arima.csv. Writes blog.html (self-contained apart from Google Fonts).

    python openrouter/blog_2026-10-14/build_blog.py
"""
import csv, json, pathlib, statistics
from collections import defaultdict

HERE = pathlib.Path(__file__).resolve().parent
ORG = {"chronos": "Amazon", "timesfm": "Google", "tirex": "NXAI", "granite": "IBM", "toto": "Datadog",
       "t0": "The Forecasting Company", "seasonal": "Baseline", "auto": "Baseline, run locally"}
HIST = 28                                                    # weeks of actuals in the drill-down

SJ = json.load(open(HERE / "series.json"))
LAST = SJ["last_week"]

week = defaultdict(dict)
for r in csv.DictReader(open(HERE / "weekly.csv")):
    d = week[r["horizon"]].setdefault(r["level"], {"weeks": [], "pos": defaultdict(list)})
    if r["cutoff"] not in d["weeks"]:
        d["weeks"].append(r["cutoff"])
    d["pos"][r["forecaster"]].append(int(r["position"]))

gift = [{"f": r["forecaster"], "g": float(r["gift_mase"]), "gr": int(r["gift_rank_ours"]),
         "leak": r["gift_rank_all"] == ""} for r in csv.DictReader(open(HERE / "gift_eval.csv")) if r["gift_mase"]]
fev = [{"f": r["forecaster"], "g": float(r["fev_mase"]), "gr": int(r["fev_rank_ours"]), "leak": r["leak_tasks"] != "0",
        "hid": r["hidden"] == "True"} for r in csv.DictReader(open(HERE / "fev.csv")) if r["fev_mase"]]

def label(s):
    kind, v = s.split(":", 1)
    if kind == "total":
        return "All OpenRouter tokens"
    if kind == "language":
        return {"natural": "Natural language", "programming": "Programming languages"}[v]
    if kind == "category":
        return v.replace("marketing-seo", "marketing/seo").capitalize().replace("Marketing/seo", "Marketing / SEO")
    return v


def load(base, steps, key, hist, path_hz=()):
    """Standings and drill-down for one study (weekly in HERE, daily in HERE/daily).
    steps: horizon -> forecast step shown in the drill-down; horizons in path_hz show every step instead."""
    ser = json.load(open(base / "series.json"))["series"]
    stand = defaultdict(lambda: defaultdict(list))
    for r in csv.DictReader(open(base / "standings.csv")):
        stand[r["horizon"]][r["level"]].append({"f": r["forecaster"], "org": ORG[r["forecaster"].split("-")[0]],
                                                "m": float(r["rel_mase"]), "p": int(r["position"])})
    per = defaultdict(list)                                 # (horizon, series, forecaster) -> MASE per cutoff
    for r in csv.DictReader(open(base / "mase_long.csv")):
        per[(r["horizon"], r["series"], r["forecaster"])].append(float(r["mase"]))
    fc = defaultdict(dict)                                  # (horizon, series, forecaster) -> {target date: B}
    for name in ("forecasts_api.csv", "forecasts_arima.csv"):
        for r in csv.DictReader(open(base / name)):
            for hz, k in steps.items():
                if ("horizon" not in r or r["horizon"] == hz or hz in path_hz) and (int(r["step"]) == k or hz in path_hz):
                    if "horizon" in r and r["horizon"] != hz:
                        continue
                    fc[(hz, r["series"], r["forecaster"])][r[key]] = round(int(r["forecast_tokens"]) / 1e9, 3)
    drill = {}
    for s in ser:
        dates = sorted(ser[s])[-hist:]
        d = {"label": label(s), "level": s.split(":")[0], "weeks": dates, "y": [round(ser[s][w] / 1e9, 3) for w in dates],
             "h": {}, "per": {hz: (7 if hz in path_hz else 1) for hz in steps}}
        for hz in steps:
            fs = {f: statistics.mean(v) for (h, ss, f), v in per.items() if h == hz and ss == s}
            if not fs:
                continue
            best = sorted((f for f in fs if f not in ("seasonal-naive", "auto-arima")), key=fs.get)[:3]
            sn = fs["seasonal-naive"]                       # relative MASE: model's avg MASE on the series ÷ seasonal naive's
            d["h"][hz] = [{"f": f, "m": round(fs[f] / sn, 3), "pts": fc[(hz, s, f)]} for f in best + ["seasonal-naive", "auto-arima"]]
            d.setdefault("rank", {})[hz] = [[f, round(fs[f] / sn, 3)] for f in sorted(fs, key=fs.get)]   # every forecaster, best first
        if d["h"]:
            drill[s] = d
    return stand, drill


stand, drill = load(HERE, {"h1": 1, "h4": 4}, "week", HIST)
dstand, ddrill = load(HERE / "daily", {"d1": 1, "d7": 7}, "day", 112, path_hz=("d7",))

DATA = {"stand": stand, "week": week, "gift": gift, "fev": fev, "drill": drill, "last": LAST,
        "hz": {"h1": "1 week", "h4": "4 weeks"}, "unit": "week", "levels": ["total", "category", "language", "model"]}
DDATA = {"stand": dstand, "week": {}, "gift": gift, "fev": fev, "drill": ddrill, "last": "2026-10-13",
         "hz": {"d1": "1 day", "d7": "7 days"}, "unit": "day", "levels": ["total", "model"]}

HTML = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Predicting Token Usage</title>
<meta name="description" content="We backtested 18 forecasting models on OpenRouter token usage to see if GIFT-Eval results hold on a real-world task.">
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&family=Roboto+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
:root{--ink:#171720;--text:#3d3f4c;--muted:#636170;--muted-2:#8b8998;--paper:#f8f8fc;--line:#e3e3ea;--grid:#eeeef3;
 --purple:#5b54e0;--purple-700:#4842c4;--purple-soft:rgba(91,84,224,.07);--blue:#3f8fd4;--pink:#e0679c;--stem:#cdced7;--dot:#9498a3;
 --heat:91,84,224;--surf:linear-gradient(145deg,#fbfcff,#e8eaf5);--card:#f3f4fa;
 --sh:12px 12px 28px rgba(112,109,145,.17),-12px -12px 28px rgba(255,255,255,.92);--tip:#171720;--tip-ink:#f8f8fc}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--ink:#eceef7;--text:#c9cbe0;--muted:#9a9db2;--muted-2:#7b7e93;
 --paper:#0e0f16;--line:#2b2d3c;--grid:rgba(255,255,255,.07);--purple:#9a92f8;--purple-700:#a9a2ff;--purple-soft:rgba(139,131,245,.12);
 --blue:#6abaf2;--pink:#f08ab5;--stem:#4a4d61;--dot:#6b6e80;--heat:154,146,248;--surf:linear-gradient(145deg,#1d1f2b,#14151e);--card:#171822;
 --sh:12px 12px 28px rgba(0,0,0,.6),-10px -10px 24px rgba(255,255,255,.028);--tip:#eceef7;--tip-ink:#0e0f16}}
:root[data-theme="dark"]{--ink:#eceef7;--text:#c9cbe0;--muted:#9a9db2;--muted-2:#7b7e93;--paper:#0e0f16;--line:#2b2d3c;
 --grid:rgba(255,255,255,.07);--purple:#9a92f8;--purple-700:#a9a2ff;--purple-soft:rgba(139,131,245,.12);--blue:#6abaf2;--pink:#f08ab5;
 --stem:#4a4d61;--dot:#6b6e80;--heat:154,146,248;--surf:linear-gradient(145deg,#1d1f2b,#14151e);--card:#171822;
 --sh:12px 12px 28px rgba(0,0,0,.6),-10px -10px 24px rgba(255,255,255,.028);--tip:#eceef7;--tip-ink:#0e0f16}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--paper);color:var(--text);font-family:'DM Sans',system-ui,sans-serif;font-size:17px;line-height:1.7;padding:0 16px 80px}
.top{max-width:960px;margin:0 auto;display:flex;justify-content:flex-end;padding:18px 0 0}
.theme{font:500 12px 'DM Sans',sans-serif;color:var(--muted);background:none;border:1px solid var(--line);border-radius:999px;padding:7px 12px;cursor:pointer}
article{max-width:700px;margin:0 auto}
.kicker{font:600 12px 'Roboto Mono',monospace;color:var(--purple-700);letter-spacing:.06em;text-transform:uppercase;margin:36px 0 12px}
h1{font-size:clamp(32px,6vw,46px);line-height:1.08;letter-spacing:-.03em;color:var(--ink);margin:0 0 16px}
.dek{font-size:20px;line-height:1.5;color:var(--muted);margin:0 0 18px}
.byline{font-size:13px;color:var(--muted-2);margin:0 0 36px}
h2{font-size:26px;letter-spacing:-.02em;color:var(--ink);margin:52px 0 12px;line-height:1.2}
p{margin:0 0 18px}
strong{color:var(--ink)}
a{color:var(--purple-700)}
ul{padding-left:20px;margin:0 0 18px}
li{margin:0 0 8px}
code{font-family:'Roboto Mono',monospace;font-size:.86em;background:var(--grid);padding:1px 5px;border-radius:5px}
.facts{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:26px 0 8px}
.facts div{background:var(--surf);box-shadow:var(--sh);border-radius:18px;padding:16px}
.facts b{display:block;font:600 28px 'Roboto Mono',monospace;color:var(--ink);letter-spacing:-.03em}
.facts span{font-size:12.5px;color:var(--muted);line-height:1.4;display:block}
@media (max-width:640px){.facts{grid-template-columns:repeat(2,minmax(0,1fr))}}
figure{margin:34px -120px;background:var(--surf);box-shadow:var(--sh);border-radius:26px;padding:26px 26px 20px}
@media (max-width:960px){figure{margin:34px 0;padding:20px 16px 16px;border-radius:20px}}
figure h3{font-size:20px;letter-spacing:-.02em;color:var(--ink);margin:0;line-height:1.3}
figure .sub{color:var(--muted);font-size:13.5px;margin:4px 0 16px;line-height:1.5}
figcaption{color:var(--muted);font-size:12.5px;line-height:1.55;margin:16px 0 0}
.ctl{display:flex;flex-wrap:wrap;gap:10px;margin:0 0 18px;align-items:center}
.seg{display:inline-flex;flex-wrap:wrap;padding:4px;border-radius:999px;background:var(--card);border:1px solid var(--line)}
.seg button{font:600 12.5px 'DM Sans',sans-serif;color:var(--muted);background:none;border:0;border-radius:999px;padding:7px 13px;cursor:pointer}
.seg button[aria-pressed="true"]{background:var(--purple);color:#fff}
select{font:500 13px 'DM Sans',sans-serif;color:var(--ink);background:var(--card);border:1px solid var(--line);border-radius:12px;padding:8px 10px;max-width:100%}
/* fig 1 */
.lb{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}
@media (max-width:760px){.lb{grid-template-columns:1fr}}
.panel{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:16px 14px 8px}
.panel h4{font-size:15px;color:var(--ink);margin:0;letter-spacing:-.01em}
.panel .meta{font-size:11.5px;color:var(--muted);margin:2px 0 10px}
.cols,.row{display:grid;grid-template-columns:24px minmax(0,1fr) 64px;align-items:baseline;column-gap:8px}
.cols{font:500 10px 'DM Sans',sans-serif;color:var(--muted-2);text-transform:uppercase;letter-spacing:.06em;padding:0 8px 4px}
.cols span:last-child,.row .num{text-align:right}
.panel ol{list-style:none;margin:0;padding:0}
.panel li{padding:6px 8px;border-radius:10px;margin:0;position:relative}
.panel li.lead{background:var(--purple-soft)}
.panel li.cut{margin-top:10px}
.panel li.cut::before{content:"";position:absolute;left:8px;right:8px;top:-5px;border-top:1px dashed var(--line)}
.rank{font:600 11.5px 'Roboto Mono',monospace;color:var(--dot)}
.lead .rank{color:var(--purple-700);font-weight:700}
.name{font-size:13.5px;font-weight:500;color:var(--text);min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;line-height:1.35}
.lead .name{font-weight:700;color:var(--ink)}
.name small{font-size:11px;color:var(--muted-2);font-weight:400;margin-left:6px}
.tag{font:600 9.5px 'DM Sans',sans-serif;color:var(--muted);border:1px solid var(--line);border-radius:999px;padding:0 6px;margin-left:6px;vertical-align:1px}
.num{font:500 12.5px 'Roboto Mono',monospace;color:var(--text)}
.lead .num{color:var(--purple-700);font-weight:700}
.track{grid-column:2/4;height:5px;margin-top:4px;position:relative}
.track i{position:absolute;left:0;top:0;height:4px;border-radius:0 4px 4px 0;background:var(--stem);transition:width .5s cubic-bezier(.22,1,.36,1)}
.lead .track i{background:var(--purple)}
.base .track i{background:repeating-linear-gradient(90deg,var(--dot) 0 4px,transparent 4px 6px)}
.more{font:600 12px 'DM Sans',sans-serif;color:var(--purple-700);background:none;border:0;padding:6px 8px;cursor:pointer}
/* fig 2 */
.slope svg{width:100%;height:auto;display:block}
.slope text{font-family:'DM Sans',sans-serif}
/* fig 3 */
.heatwrap{overflow-x:auto;-webkit-overflow-scrolling:touch}
table.heat{border-collapse:separate;border-spacing:2px;font-size:12px;min-width:520px;width:100%}
.heat th{font:500 10.5px 'DM Sans',sans-serif;color:var(--muted-2);text-align:center;padding:0 0 4px;white-space:nowrap}
.heat th.f{text-align:left;font-size:12.5px;color:var(--text);font-weight:500;padding:0 8px 0 0;white-space:nowrap}
.heat th.f small{color:var(--muted-2);font-family:'Roboto Mono',monospace;font-size:10.5px;margin-left:4px}
.heat td{text-align:center;font:500 11px 'Roboto Mono',monospace;height:24px;min-width:24px;border-radius:5px;color:var(--ink)}
.heat td.hi{color:#fff;font-weight:700}
.heat tr.base th.f{color:var(--muted)}
.legend{display:flex;align-items:center;gap:8px;font-size:11.5px;color:var(--muted);margin:12px 0 0}
.legend .ramp{display:inline-flex}
.legend .ramp i{width:18px;height:10px}
/* fig 4 */
.drill svg{width:100%;height:auto;display:block;overflow:visible}
.drill text{font-family:'Roboto Mono',monospace;font-size:10.5px;fill:var(--muted)}
.keys{display:flex;flex-wrap:wrap;gap:6px 18px;margin:12px 0 0;font-size:12.5px;color:var(--text)}
.keys span{display:inline-flex;align-items:center;gap:7px;white-space:nowrap}
.keys svg{width:22px;height:8px}
.keys b{font:600 12px 'Roboto Mono',monospace;color:var(--ink)}
.tip{position:fixed;pointer-events:none;background:var(--tip);color:var(--tip-ink);font-size:12px;line-height:1.5;padding:8px 10px;border-radius:10px;opacity:0;transition:opacity .12s;max-width:280px;z-index:9}
.tip .m{font-family:'Roboto Mono',monospace}
.notes{font-size:14px;color:var(--muted);line-height:1.65}
.notes li{margin:0 0 8px}
figure.offpage{display:none}
p.note{font-size:13px;color:var(--muted);margin-top:-6px}
figure.static img{display:block;width:100%;height:auto;margin:10px 0 0;border-radius:12px}
.refs{padding-left:22px;word-break:break-word}
.ref{color:var(--purple);text-decoration:none;font-size:.85em}
blockquote{margin:0 0 18px;padding:0;border:0;font-size:inherit;line-height:inherit;color:inherit}
hr{border:0;border-top:1px solid var(--line);margin:52px 0 0}
body.still{padding:24px}
body.still .top,body.still article>*:not(figure.show){display:none}
body.still article{max-width:none;width:1000px}
body.still figure.show{display:block;margin:0;box-shadow:none}
body.still .ctl,body.still .live,body.still .more{display:none}
</style></head><body>
<div class="top"><button class="theme" id="theme">Light / dark</button></div>
<article>
<h1>Can we predict token usage using transformer based models?</h1>
<p class="dek">OpenRouter's top 50 with 16 Time Series Foundation Models, measuring the latest time series foundation models against real-world patterns.</p>
<figure class="static">
<img src="assets/fig4_loop_models_1week.gif" alt="Loop through OpenRouter's top 50 LLMs: actual weekly tokens, the best 3 forecasters 1 week ahead, and all 18 forecasters ranked" loading="eager">
<figcaption>Each frame is one LLM from OpenRouter's top 50, in rank order. The chart shows actual weekly tokens and the best 3 forecasters 1 week ahead, and the list ranks all 18 forecasters by MASE relative to seasonal naive. For this animation an LLM needs 4 weeks of history instead of 8, so newer LLMs are included and a few scores differ from the tables below.</figcaption>
</figure>

<h2>Time Series Foundation models or classical methods?</h2>
<p>Time series foundation models are one of the newest ideas in forecasting. Like a lot of things in machine learning and AI right now, there's a heated debate over whether they actually work.</p>
<p>Rob Hyndman made the skeptical case really well in a recent post <a class="ref" href="#r1">[1]</a>. He points out that published comparisons often use weak statistical baselines <a class="ref" href="#r2">[2]</a>, that the datasets in public benchmarks keep showing up in the models' training data <a class="ref" href="#r3">[3]</a>, and that a leaderboard averages over so many domains that it can hide how a model does on the series that actually matter. He closes with a line worth repeating.</p>
<blockquote>&ldquo;A model that tops a MASE leaderboard by a small margin but takes an order of magnitude longer to run, or performs poorly on genuinely new data, may be the wrong choice operationally even if it&rsquo;s the &lsquo;best&rsquo; model on paper.&rdquo; <a class="ref" href="#r1">[1]</a></blockquote>
<p>Hyndman's advice to backtest properly on real data, with well-implemented baselines, points at the part that's easy to underestimate. Much of the hard work in testing time series foundation models is the engineering pipeline. Every model comes with its own requirements, architecture and input format, and until recently it was hard to test them at scale or to recreate the conditions behind a benchmark score like GIFT-Eval <a class="ref" href="#r4">[4]</a> or fev-bench <a class="ref" href="#r5">[5]</a>.</p>

<p>FoundationForecast, our newly released open-source unified API for time series foundation models, takes care of that part. It runs every model in this test through one interface, so their actual performance can be checked on the same data in the same way. Results are still coming in, and there's no definitive answer yet on whether these models beat older methods. In this test, though, the evidence leans their way at the horizons that matter most in practice. On daily data, every one of the 16 foundation models beat both statistical baselines on individual LLMs over a 7-day horizon.</p>

<p>That practical angle is the focus here. For most companies a forecast 1 day out is too short to act on, and 4 weeks out is often too long to trust, so a week ahead is where a lot of planning happens. That makes it interesting that some of these models do well at 7 days and 1 week ahead. And few series are moving as fast right now as token usage.</p>

<h2>Why tokens</h2>
<p>Tokens make a good test because they're turning into a unit of economic activity. They're what AI providers sell, what cloud companies count, and more and more, what companies budget for. Google said it processed 9.7 trillion tokens a month across its products in 2024, roughly 480 trillion a year later, and over 3.2 quadrillion a month by May 2026 <a class="ref" href="#r6">[6]</a>. In the same talk Sundar Pichai said &ldquo;many companies are already blowing through their annual token budgets, and it&rsquo;s only May.&rdquo; Satya Nadella told Microsoft investors that the key metric the company optimizes for is &ldquo;tokens per watt per dollar,&rdquo; and that over 250 customers were on track to process over a trillion tokens each on its Foundry platform that year <a class="ref" href="#r7">[7]</a>.</p>
<p>The mix is changing fast too. A study of over 100 trillion tokens on OpenRouter found that reasoning models went from a negligible share in early 2025 to more than half of all tokens by late 2025, and that the average prompt grew about fourfold <a class="ref" href="#r8">[8]</a>. Agentic coding tasks can use about 1,000 times more tokens than code chat, and the same task can vary by up to 30x in tokens from one run to the next <a class="ref" href="#r9">[9]</a>. Meanwhile the price of a fixed level of performance has been falling anywhere from 9x to 900x per year, depending on the task <a class="ref" href="#r10">[10]</a>.</p>
<p>Put together, that makes token volume a number worth forecasting. It drives compute bills, capacity planning and pricing, and it moves fast enough that last quarter's trend can be wrong by next quarter. It's also a real-world series that isn't part of GIFT-Eval or fev-bench, which makes it a fair test of whether benchmark results carry over.</p>

<h2>What was tested</h2>
<p>OpenRouter publishes weekly token totals for its top 50 models, plus breakdowns by use case and by language. The data runs from January 2025 through the week of October 5, 2026, and the test looks at it at four levels.</p>
<ul>
<li><strong>All OpenRouter tokens.</strong> One series, the whole platform.</li>
<li><strong>By category.</strong> 12 series like programming, roleplay, marketing and science.</li>
<li><strong>By language.</strong> Natural language vs programming languages.</li>
<li><strong>By model.</strong> The current top 50 models. Many of them are only a few weeks old, so a model joins the test once it has 8 weeks of history. That left 24 models for 1-week-ahead forecasts and 19 for 4 weeks ahead.</li>
</ul>
<p>Sixteen foundation models and seasonal naive (which repeats last week's value) ran through FoundationForecast. AutoARIMA isn't on the API, so it ran locally with statsforecast. For each of the last 12 weeks, every model saw only the data up to that week and forecast the weeks after it, 1 week ahead and 4 weeks ahead. That's the rolling-origin backtest Hyndman recommends <a class="ref" href="#r1">[1]</a>, and the scored weeks run from mid-July to early October 2026.</p>
<p>Everything is scored with <strong>MASE</strong> and nothing else. By the way, MASE, the mean absolute scaled error, also comes from Rob Hyndman. He and Anne Koehler introduced it and argued that it should &ldquo;become the standard measure for comparing forecast accuracy across multiple time series&rdquo; <a class="ref" href="#r11">[11]</a>. MASE is one metric among many. It's used here because it puts a large series like all OpenRouter tokens and a small one like a single model on the same scale. To keep it comparable with GIFT-Eval and fev-bench, it's reported the way they do it. For each series, a model's average MASE over the 12 weeks is divided by seasonal naive's, so seasonal naive is 1 and lower is better. When a level has several series, those ratios are combined with a geometric mean. Earlier API requests were also rerun to check that the numbers reproduce. 12 of the 17 API models returned identical forecasts, and the rest differed by less than 0.2%, which didn't change any ordering.</p>

<h2>Day by day and week by week</h2>

<p>The middle horizons are where foundation models look strongest. On daily data every foundation model beat seasonal naive on individual LLMs at both horizons, and over 7 days every one also beat AutoARIMA. At 1 week ahead on all tokens, 13 of the 16 beat seasonal naive. A likely reason is that these series are short and change fast. A model that has already seen thousands of other series can pick up a new LLM's ramp and its weekday pattern from a few weeks of history, while a statistical model fit on that history alone has little to go on. Further out the edge fades. At 4 weeks ahead on individual LLMs, none of the foundation models beat seasonal naive.</p>


<figure class="static">
<h3>Actual vs backtest forecasts, all OpenRouter tokens, 1 day, 7 days, 1 week and 4 weeks ahead</h3>
<img src="assets_daily/fig4_actual_vs_forecast_alltokens_1day.gif" alt="fig4 actual vs forecast alltokens 1day" loading="lazy">
<img src="assets_daily/fig4_actual_vs_forecast_alltokens_7days.gif" alt="fig4 actual vs forecast alltokens 7days" loading="lazy">
<img src="assets/fig4_actual_vs_forecast_alltokens_1week.gif" alt="fig4 actual vs forecast alltokens 1week" loading="lazy">
<img src="assets/fig4_actual_vs_forecast_alltokens_4weeks.gif" alt="fig4 actual vs forecast alltokens 4weeks" loading="lazy">
</figure>
<p class="note">These animations play through the 12 backtest weeks for all OpenRouter tokens. Each one shows the three forecasters with the lowest MASE plus both baselines, next to the actual tokens, at 1 day, 7 days, 1 week and 4 weeks ahead.</p>


<h2>Your data is your context</h2>

<p>Context is Key <a class="ref" href="#r12">[12]</a> makes a related point from another direction. Its benchmark pairs each series with the background knowledge a human forecaster would use, and the forecasts that use that context come out ahead. The lesson carries over to practice. Every business has its own context, so choosing the right data to test on matters as much as choosing the model.</p>

<p>It's also a reason to test models the leaderboards don't highlight. Chronos-2 Small and Chronos-Bolt Mini aren't on GIFT-Eval or fev-bench at all, yet Chronos-2 Small has the lowest error on individual LLMs at 1 week ahead and Chronos-Bolt Mini has the lowest on categories at 4 weeks. Granite PatchTST isn't on fev-bench, and it's 1st on daily individual LLMs at both horizons. A shortlist built only from the top of a leaderboard would miss most of them.</p>

<h2>The leaderboard rankings don't hold up</h2>

<p>Comparing these results with GIFT-Eval <a class="ref" href="#r4">[4]</a> and fev-bench <a class="ref" href="#r5">[5]</a> is where it gets interesting, because the rankings don't hold up. In each chart below, the left column is a model's position on the benchmark and the right column is its position out of 18 on all OpenRouter tokens, at 1 day, 7 days, 1 week and 4 weeks ahead. If the benchmark order carried over, the lines would run straight across. The animations start from that picture and move each model to where it actually finished. Dashed lines are the two baselines, and light grey names have no benchmark entry.</p>

<figure class="static">
<h3>GIFT-Eval order vs OpenRouter order, all OpenRouter tokens, 1 day, 7 days, 1 week and 4 weeks ahead</h3>
<img src="assets_daily/fig2_gift_eval_vs_openrouter_alltokens_1day.gif" alt="fig2 gift eval vs openrouter alltokens 1day" loading="lazy">
<img src="assets_daily/fig2_gift_eval_vs_openrouter_alltokens_7days.gif" alt="fig2 gift eval vs openrouter alltokens 7days" loading="lazy">
<img src="assets/fig2_gift_eval_vs_openrouter_alltokens_1week.gif" alt="fig2 gift eval vs openrouter alltokens 1week" loading="lazy">
<img src="assets/fig2_gift_eval_vs_openrouter_alltokens_4weeks.gif" alt="fig2 gift eval vs openrouter alltokens 4weeks" loading="lazy">
</figure>

<figure class="static">
<h3>fev-bench order vs OpenRouter order, all OpenRouter tokens, 1 day, 7 days, 1 week and 4 weeks ahead</h3>
<img src="assets_daily/fig2b_fev_vs_openrouter_alltokens_1day.gif" alt="fig2b fev vs openrouter alltokens 1day" loading="lazy">
<img src="assets_daily/fig2b_fev_vs_openrouter_alltokens_7days.gif" alt="fig2b fev vs openrouter alltokens 7days" loading="lazy">
<img src="assets/fig2b_fev_vs_openrouter_alltokens_1week.gif" alt="fig2b fev vs openrouter alltokens 1week" loading="lazy">
<img src="assets/fig2b_fev_vs_openrouter_alltokens_4weeks.gif" alt="fig2b fev vs openrouter alltokens 4weeks" loading="lazy">
</figure>

<p>TimesFM 3 is first on both leaderboards. On all OpenRouter tokens it finishes 7th at 1 day, 15th at 7 days, 16th at 1 week and 9th at 4 weeks, and across the 33 LLMs in the animation at the top it isn't the best forecaster on any of them. The winners on all tokens are AutoARIMA at 1 day, Chronos-2 at 7 days, Toto 4M at 1 week and AutoARIMA again at 4 weeks.</p>

<p>GIFT-Eval also publishes leaderboards by domain and by frequency <a class="ref" href="#r4">[4]</a>, so it's worth checking whether a narrower view would have done better. The closest domain to this data is Web/CloudOps. TimesFM 3 is first on every view that fits (overall, Web/CloudOps, daily and weekly), so even the most relevant GIFT-Eval view would have pointed to it. Some models do move. Chronos-2 is 2nd on GIFT-Eval's weekly view, and on OpenRouter it wins all tokens over 7 days and categories at 1 week. Granite PatchTST is 2nd on GIFT-Eval's daily view and 1st on OpenRouter's daily individual LLMs. So the narrower views help for some models, just not for the leader. They still don't match this data well. GIFT-Eval's Web/CloudOps configurations are machine telemetry sampled every 10 seconds to every hour, its weekly view has only 8 configurations, and none of them are market demand like this.</p>

<p>None of this means the benchmarks are wrong. They average over many domains, and token usage is one domain with fast growth over this period. Hyndman's point about aggregate scores hiding variance on the series a business actually needs <a class="ref" href="#r1">[1]</a> is what that looks like in practice.</p>

<h2>Where this goes next</h2>

<p>Bridging research and day-to-day execution is what TimeCopilot and FoundationForecast are for, and testing more domains comes next. The early picture is encouraging and humbling at the same time. Foundation models did well at the horizons that matter most here, and seasonal naive still won some of the boards outright. Rankings also move over time, as the live Impermanent benchmark on GitHub activity shows <a class="ref" href="#r13">[13]</a>, so a choice that's right today may need checking again next quarter.</p>

<p>It's also worth remembering what these models were working with. This is public data, with no fine-tuning, no curated features and only a few weeks of history for many LLMs. If they hold up this well here, it's worth asking what they can do on the carefully prepared data a company has for its own problem.</p>

<h2>Interactive charts</h2>
<p>Pick any of the 65 weekly series below, from all OpenRouter tokens down to a single LLM, to see its actual tokens next to the backtest forecasts from the three best forecasters and both baselines, 1 or 4 weeks ahead.</p>

<figure id="fig4" class="drill">
<h3 id="drillTitle">Actual vs backtest forecasts</h3>
<p class="sub" id="drillSub"></p>
<div class="ctl"><select id="drillSel" aria-label="Series"></select>
<div class="seg" data-ctl="h"><button data-v="h1" aria-pressed="true">1 week ahead</button><button data-v="h4" aria-pressed="false">4 weeks ahead</button></div>
<button class="theme" id="replay">Replay</button></div>
<div id="drillSvg"></div>
<div class="keys" id="drillKeys"></div>
<figcaption><span class="live">The chart plays through the backtest weeks when it scrolls into view. </span>Each forecast point was made 1 week (or 4 weeks) before the week it lands on, using only the data available then. The number in the legend is relative MASE, the model's average MASE on this series divided by seasonal naive's, so seasonal naive is 1 and anything below 1 beat it. For 4 weeks ahead, MASE covers all four weeks of each forecast and the chart shows the 4th.</figcaption>
</figure>

<h2>Full scores (appendix)</h2>

<p>Every forecaster's MASE relative to seasonal naive at each level, ordered from lowest to highest. Seasonal naive is 1, so anything below 1 beat it. The weekly boards come first (1 week ahead, then 4 weeks ahead), followed by the daily boards (1 day ahead, then 7 days ahead).</p>

<figure class="static">
<h3>MASE vs seasonal naive by level, weekly and daily data</h3>
<img src="assets/fig1_avg_mase_1week_all_a.png" alt="fig1 avg mase 1week all a" loading="lazy">
<img src="assets/fig1_avg_mase_1week_all_b.png" alt="fig1 avg mase 1week all b" loading="lazy">
<img src="assets/fig1_avg_mase_4weeks_all_a.png" alt="fig1 avg mase 4weeks all a" loading="lazy">
<img src="assets/fig1_avg_mase_4weeks_all_b.png" alt="fig1 avg mase 4weeks all b" loading="lazy">
<img src="assets_daily/fig1_avg_mase_1day_all.png" alt="fig1 avg mase 1day all" loading="lazy">
<img src="assets_daily/fig1_avg_mase_7days_all.png" alt="fig1 avg mase 7days all" loading="lazy">
</figure>

<figure class="offpage" id="fig1">
<h3>MASE vs seasonal naive by level</h3>
<p class="sub">Lower is better, and seasonal naive is 1. All 18 models, ordered by MASE relative to seasonal naive. Dashed bars are the two baselines.</p>
<div class="ctl"><div class="seg" data-ctl="h"><button data-v="h1" aria-pressed="true">1 week ahead</button><button data-v="h4" aria-pressed="false">4 weeks ahead</button></div></div>
<div class="lb" id="lb"></div>
<figcaption>Each model's average MASE on each series divided by seasonal naive's, combined across the level's series with a geometric mean. Bars start at zero. Seasonal naive repeats last week. AutoARIMA ran locally with statsforecast. Data from OpenRouter (CC BY 4.0).</figcaption>
</figure>
<figure class="offpage" id="fig2">
<h3>GIFT-Eval order vs OpenRouter order</h3>
<p class="sub">The 16 models with a GIFT-Eval entry. Left is their GIFT-Eval order, right is their position out of 18 on OpenRouter. Dashed lines are the two baselines, and light grey names have no GIFT-Eval entry.<span class="live"> Hover a line to follow a model.</span></p>
<div class="ctl"><div class="seg" data-ctl="lv"><button data-v="total" aria-pressed="true">All tokens</button><button data-v="category" aria-pressed="false">Category</button><button data-v="language" aria-pressed="false">Language</button><button data-v="model" aria-pressed="false">Models</button></div>
<div class="seg" data-ctl="h"><button data-v="h1" aria-pressed="true">1 week</button><button data-v="h4" aria-pressed="false">4 weeks</button></div></div>
<div class="slope" id="slope"></div>
<figcaption>GIFT-Eval side uses the public results (97 configurations), each model's MASE divided by seasonal naive's and combined with a geometric mean, the way the GIFT-Eval leaderboard does. * GIFT-Eval flags this model for overlap with its test data. Chronos-Bolt Mini and Chronos-2 Small have no GIFT-Eval entry, so they're left out here.</figcaption>
</figure>
<figure class="offpage" id="fig2b">
<h3>fev-bench order vs OpenRouter order</h3>
<p class="sub">The 11 models with a fev-bench entry. Left is their fev-bench order, right is their position out of 18 on OpenRouter. Dashed lines are the two baselines, and light grey names have no fev-bench entry.<span class="live"> Hover a line to follow a model.</span></p>
<div class="ctl"><div class="seg" data-ctl="lv"><button data-v="total" aria-pressed="true">All tokens</button><button data-v="category" aria-pressed="false">Category</button><button data-v="language" aria-pressed="false">Language</button><button data-v="model" aria-pressed="false">Models</button></div>
<div class="seg" data-ctl="h"><button data-v="h1" aria-pressed="true">1 week</button><button data-v="h4" aria-pressed="false">4 weeks</button></div></div>
<div class="slope" id="slopeFev"></div>
<figcaption>fev-bench side uses the public per-task results (100 tasks), each model's MASE divided by seasonal naive's and combined with a geometric mean, the way the fev-bench skill score does. * TimesFM 2.5 reports training on 10 of the tasks, and those use Chronos-Bolt's result, as fev-bench does. † In the fev-bench results but hidden from its public leaderboard. The fev-bench TiRex 2 result is a checkpoint retrained to avoid its tasks, not the public weights tested here. TiRex 2 zero-shot, Granite PatchTST, t0-alpha, Chronos-2 Small, Chronos-Bolt Small and Mini, and TimesFM 2 aren't on fev-bench.</figcaption>
</figure>


<hr>
<h2>Notes</h2>
<ul class="notes">
<li>Data comes from OpenRouter's public rankings (CC BY 4.0), pulled October 12, 2026. The last full week is October 5. Category and language numbers are OpenRouter's own estimates from sampled requests.</li>
<li>MASE scales each forecast's average error by the average week-to-week change in that series' history up to the forecast week. Usage grew so much during the test weeks that raw MASE runs large (seasonal naive itself is about 6.6 on all tokens 1 week ahead), which is one more reason to report it relative to seasonal naive.</li>
<li>All tokens is a single series, so its results vary more than the levels with many series.</li>
<li>These results cover 12 weeks of one data source. A different period or a different domain could produce a different order.</li>
<li>Models were called through the FoundationForecast API with default settings, weekly frequency and season length 1. AutoARIMA used statsforecast with season length 1.</li>
<li>t0-gamma isn't available through the API yet, so it isn't in this test.</li>
<li>Daily data comes from the same OpenRouter rankings, January 6, 2025 through October 13, 2026. OpenRouter has no daily rows for June 15 and July 15, 2025, so each is filled with the average of the day before and after. Both are months before the first cutoff. Daily seasonal naive and AutoARIMA use season length 7.</li>
<li>Most of the 16 foundation models are transformer-based. TiRex 2 and its GIFT-Eval zero-shot version are the exceptions, built on xLSTM.</li>
<li>Data, forecasts and code to reproduce every result are at <a href="https://github.com/friscobrisco/openrouter-tsfm-benchmark">github.com/friscobrisco/openrouter-tsfm-benchmark</a>.</li>
</ul>

<h2>References</h2>
<ol class="notes refs">
<li id="r1">Hyndman, R. J. (2026, August 25). Evaluating time series foundation model claims. Hyndsight. <a href="https://robjhyndman.com/hyndsight/foundation_models.html">robjhyndman.com/hyndsight/foundation_models.html</a></li>
<li id="r2">Bergmeir, C. (2024). LLMs and foundational models: Not (yet) as good as hoped. Foresight: The International Journal of Applied Forecasting, 73, 33-38. <a href="https://cbergmeir.com/papers/Bergmeir2024LLMs.pdf">cbergmeir.com/papers/Bergmeir2024LLMs.pdf</a></li>
<li id="r3">Meyer, M., Kaltenpoth, S., Zalipski, K., &amp; M&uuml;ller, O. (2025). Rethinking evaluation in the era of time series foundation models: (Un)known information leakage challenges. arXiv:2510.13654. <a href="https://arxiv.org/abs/2510.13654">arxiv.org/abs/2510.13654</a></li>
<li id="r4">Aksu, T., Woo, G., Liu, J., Liu, X., Liu, C., Savarese, S., Xiong, C., &amp; Sahoo, D. (2024). GIFT-Eval: A benchmark for general time series forecasting model evaluation. arXiv:2410.10393. <a href="https://arxiv.org/abs/2410.10393">arxiv.org/abs/2410.10393</a> Leaderboard and results at <a href="https://huggingface.co/spaces/Salesforce/GIFT-Eval">huggingface.co/spaces/Salesforce/GIFT-Eval</a></li>
<li id="r5">Shchur, O., Ansari, A. F., Turkmen, C., Stella, L., Erickson, N., Guerron, P., Bohlke-Schneider, M., &amp; Wang, Y. (2025). fev-bench: A realistic benchmark for time series forecasting. arXiv:2509.26468. <a href="https://arxiv.org/abs/2509.26468">arxiv.org/abs/2509.26468</a> Results at <a href="https://github.com/autogluon/fev">github.com/autogluon/fev</a></li>
<li id="r6">Pichai, S. (2026, May 19). I/O 2026: Welcome to the agentic Gemini era. Google. <a href="https://blog.google/innovation-and-ai/sundar-pichai-io-2026/">blog.google/innovation-and-ai/sundar-pichai-io-2026/</a></li>
<li id="r7">Microsoft. (2026, January 28). FY26 Q2 earnings conference call transcript. <a href="https://cdn-dynmedia-1.microsoft.com/is/content/microsoftcorp/TranscriptQandAFY26q2">cdn-dynmedia-1.microsoft.com/is/content/microsoftcorp/TranscriptQandAFY26q2</a></li>
<li id="r8">Aubakirova, M., Atallah, A., Clark, C., Summerville, J., &amp; Midha, A. (2026). State of AI: An empirical 100 trillion token study with OpenRouter. a16z and OpenRouter. arXiv:2601.10088. <a href="https://arxiv.org/abs/2601.10088">arxiv.org/abs/2601.10088</a></li>
<li id="r9">Bai, L., Huang, Z., Wang, X., Sun, J., Mihalcea, R., Brynjolfsson, E., Pentland, A., &amp; Pei, J. (2026). How do AI agents spend your money? Analyzing and predicting token consumption in agentic coding tasks. arXiv:2604.22750. <a href="https://arxiv.org/abs/2604.22750">arxiv.org/abs/2604.22750</a></li>
<li id="r10">Cottier, B., Snodin, B., Owen, D., &amp; Adamczewski, T. (2025, March 12). LLM inference prices have fallen rapidly but unequally across tasks. Epoch AI. <a href="https://epoch.ai/data-insights/ai-inference-price-trends">epoch.ai/data-insights/ai-inference-price-trends</a></li>
<li id="r11">Hyndman, R. J., &amp; Koehler, A. B. (2006). Another look at measures of forecast accuracy. International Journal of Forecasting, 22(4), 679-688. <a href="https://robjhyndman.com/papers/mase.pdf">robjhyndman.com/papers/mase.pdf</a></li>
<li id="r12">Williams, A. R., Ashok, A., Marcotte, É., Zantedeschi, V., Subramanian, J., Riachi, R., Requeima, J., Lacoste, A., Rish, I., Chapados, N., &amp; Drouin, A. (2024). Context is Key: A benchmark for forecasting with essential textual information. arXiv:2410.18959. <a href="https://arxiv.org/abs/2410.18959">arxiv.org/abs/2410.18959</a></li>
<li id="r13">Garza, A., Rosillo, R., Mendoza-Smith, R., Salinas, D., Williams, A. R., Ashok, A., Goswami, M., &amp; Ju&aacute;rez, J. M. (2026). Impermanent: A live benchmark for temporal generalization in time series forecasting. arXiv:2603.08707. <a href="https://arxiv.org/abs/2603.08707">arxiv.org/abs/2603.08707</a></li>
</ol>
</article>
<div class="tip" id="tip"></div>
<script>
const D=__DATA__;
const LV={total:"All OpenRouter tokens",category:"By category",language:"By language",model:"By model"};
const BASE=["seasonal-naive","auto-arima"];
const tip=document.getElementById("tip");
const css=v=>getComputedStyle(document.documentElement).getPropertyValue(v).trim();
const fmtW=d=>new Date(d+"T00:00:00Z").toLocaleDateString("en-US",{month:"short",day:"numeric",timeZone:"UTC"});
function showTip(e,html){tip.innerHTML=html;tip.style.opacity=1;tip.style.left=Math.min(e.clientX+14,innerWidth-290)+"px";tip.style.top=(e.clientY+14)+"px";}
function hideTip(){tip.style.opacity=0;}
function seg(fig,name,cb){const g=fig.querySelector(`[data-ctl="${name}"]`);if(!g)return;
  g.querySelectorAll("button").forEach(b=>b.onclick=()=>{g.querySelectorAll("button").forEach(x=>x.setAttribute("aria-pressed",x===b));cb(b.dataset.v);});}
const Q=new URLSearchParams(location.hash.slice(1)),STILL=Q.get("still"),HZ0=Object.keys(D.hz)[0];
function setSeg(fig,name,v){const g=fig.querySelector(`[data-ctl="${name}"]`);if(g&&v)g.querySelectorAll("button").forEach(x=>x.setAttribute("aria-pressed",x.dataset.v===v));}
if(STILL){document.body.classList.add("still");document.getElementById(STILL).classList.add("show");document.documentElement.dataset.theme=Q.get("theme")||"light";}

/* fig 1 */
(function(){const fig=document.getElementById("fig1"),lb=document.getElementById("lb");let H=Q.get("h")||HZ0;const open=Q.has("top")?{}:{total:1,category:1,language:1,model:1};setSeg(fig,"h",H);
function draw(){lb.innerHTML="";
 if(STILL==="fig1")fig.querySelector(".sub").textContent=`${D.hz[H]} ahead. Lower is better, and seasonal naive is 1. All 18 models, ordered by MASE relative to seasonal naive. Dashed bars are the two baselines.`;
 for(const lv of (Q.get("lvs")||D.levels.join(",")).split(",")){const rows=D.stand[H][lv],all=open[lv];
  const show=all?rows:rows.filter(r=>r.p<=5).concat(rows.filter(r=>r.p>5&&BASE.includes(r.f)));
  const max=Math.max(...rows.map(r=>r.m));
  const n=Object.values(D.drill).filter(d=>d.level===lv&&d.h[H]).length;
  const p=document.createElement("div");p.className="panel";
  p.innerHTML=`<h4>${LV[lv]}</h4><div class="meta">${n} series · 12 weeks</div><div class="cols"><span>#</span><span>Model</span><span>vs naive</span></div>`;
  const ol=document.createElement("ol");
  show.forEach((r,i)=>{const li=document.createElement("li");const cut=!all&&i>0&&r.p>5&&show[i-1].p<=5;
   li.className=[r.p===1?"lead":"",cut?"cut":"",BASE.includes(r.f)?"base":""].join(" ");
   li.innerHTML=`<div class="row"><span class="rank">${r.p}</span><span class="name">${r.f}${BASE.includes(r.f)?'<span class="tag">baseline</span>':`<small>${r.org}</small>`}</span><span class="num">${r.m.toFixed(3)}</span><div class="track"><i style="width:${(100*r.m/max).toFixed(1)}%"></i></div></div>`;
   ol.appendChild(li);});
  p.appendChild(ol);const b=document.createElement("button");b.className="more";b.textContent=all?"Show top 5":"Show all 18";
  b.onclick=()=>{open[lv]=!all;draw();};p.appendChild(b);lb.appendChild(p);}}
seg(fig,"h",v=>{H=v;draw();});draw();})();

/* fig 2, fig 2b: benchmark order vs OpenRouter order */
function slopeFig(id,boxId,bench,name){const fig=document.getElementById(id),box=document.getElementById(boxId);let H=Q.get("h")||HZ0,L=Q.get("lv")||"total";setSeg(fig,"h",H);setSeg(fig,"lv",L);
const T=STILL===id&&Q.has("t")?+Q.get("t"):1,ease=x=>x<.5?4*x*x*x:1-Math.pow(-2*x+2,3)/2;   // t: 0 = benchmark order carried over, 1 = OpenRouter order (GIF frames)
const HL={};bench.slice().sort((a,b)=>a.gr-b.gr).slice(0,3).forEach((m,i)=>HL[m.f]=["--purple","--blue","--pink"][i]);   // benchmark's top 3
function draw(){const g=bench.slice().sort((a,b)=>a.g-b.g);
 const ours=D.stand[H][L];
 const rk={};ours.forEach(r=>rk[r.f]=r.p);const om={};ours.forEach(r=>om[r.f]=r.m);
 const W=560,row=27,top=44,Hh=top+row*18+8,x1=210,x2=350,rr=row*18/g.length;
 let s=`<svg viewBox="0 0 ${W} ${Hh}" role="img" aria-label="${name} order compared with OpenRouter order">`;
 s+=`<text x="${x1}" y="18" text-anchor="end" font-size="12" font-weight="700" fill="${css("--ink")}">${name}</text><text x="${x2}" y="18" font-size="12" font-weight="700" fill="${css("--ink")}">OpenRouter · ${LV[L].replace("By ","").replace("All OpenRouter tokens","all tokens")}</text>`;
 s+=`<text x="${x1}" y="32" text-anchor="end" font-size="10.5" fill="${css("--muted")}">MASE vs seasonal naive</text><text x="${x2}" y="32" font-size="10.5" fill="${css("--muted")}">MASE vs seasonal naive, ${D.hz[H]} ahead</text>`;
 const order=g.slice().sort((a,b)=>(HL[a.f]?1:0)-(HL[b.f]?1:0));
 for(const m of order){const ya=top+rr*(m.gr-1)+rr/2,yb=ya+(top+row*(rk[m.f]-1)+row/2-ya)*ease(T);const isB=BASE.includes(m.f),c=HL[m.f]?css(HL[m.f]):isB?css("--dot"):css("--stem"),bt=isB?` <tspan font-size="10" font-weight="500" fill="${css("--muted")}">baseline</tspan>`:"";
  s+=`<g class="ln" data-f="${m.f}" style="cursor:default"><path d="M${x1+8},${ya} C${(x1+x2)/2},${ya} ${(x1+x2)/2},${yb} ${x2-8},${yb}" fill="none" stroke="${c}" stroke-width="${HL[m.f]?2.6:isB?1.8:1.4}" stroke-dasharray="${isB?"5 4":""}" stroke-linecap="round"/>
  <circle cx="${x1+8}" cy="${ya}" r="3.5" fill="${c}"/><circle cx="${x2-8}" cy="${yb}" r="3.5" fill="${c}"/>
  <text x="${x1-4}" y="${ya+4}" text-anchor="end" font-size="12.5" font-weight="${HL[m.f]?700:500}" fill="${HL[m.f]?css("--ink"):css("--text")}">${m.f}${m.leak?"*":""}${m.hid?"†":""}${bt} <tspan font-family="Roboto Mono" font-size="11" fill="${css("--muted-2")}">${m.gr}</tspan></text>
  <text x="${x2+4}" y="${yb+4}" font-size="12.5" font-weight="${HL[m.f]?700:500}" fill="${HL[m.f]?css("--ink"):css("--text")}"><tspan font-family="Roboto Mono" font-size="11" fill="${css("--muted-2")}" opacity="${Math.max(0,(T-.8)/.2).toFixed(2)}">${rk[m.f]}</tspan> ${m.f}${bt}</text>
  <rect x="0" y="${Math.min(ya,yb)-6}" width="${W}" height="0" fill="transparent"/></g>`;}
 const fade=Math.max(0,(T-.8)/.2).toFixed(2);                   // models without a benchmark entry keep their OpenRouter slot
 for(const r of ours.filter(r=>!g.some(m=>m.f===r.f))){const yb=top+row*(r.p-1)+row/2;
  s+=`<g opacity="${fade}"><circle cx="${x2-8}" cy="${yb}" r="3.2" fill="none" stroke="${css("--stem")}" stroke-width="1.4"/><text x="${x2+4}" y="${yb+4}" font-size="12.5" font-weight="500" fill="${css("--muted-2")}"><tspan font-family="Roboto Mono" font-size="11">${r.p}</tspan> ${r.f}</text></g>`;}
 s+="</svg>";box.innerHTML=s;
 box.querySelectorAll(".ln").forEach(el=>{const f=el.dataset.f,m=bench.find(x=>x.f===f);
  el.addEventListener("mousemove",e=>{box.querySelectorAll(".ln").forEach(o=>o.style.opacity=o===el?1:.18);
   showTip(e,`<b>${f}</b><br>${name} <span class="m">#${m.gr}</span> · MASE vs naive <span class="m">${m.g.toFixed(3)}</span><br>OpenRouter <span class="m">#${rk[f]} of 18</span> · MASE vs naive <span class="m">${om[f].toFixed(3)}</span>`);});
  el.addEventListener("mouseleave",()=>{box.querySelectorAll(".ln").forEach(o=>o.style.opacity=1);hideTip();});});}
seg(fig,"lv",v=>{L=v;draw();});seg(fig,"h",v=>{H=v;draw();});draw();
new MutationObserver(draw).observe(document.documentElement,{attributes:true,attributeFilter:["data-theme"]});}
slopeFig("fig2","slope",D.gift,"GIFT-Eval");
slopeFig("fig2b","slopeFev",D.fev,"fev-bench");

/* fig 3 */
if(document.getElementById("fig3"))(function(){const fig=document.getElementById("fig3"),t=document.getElementById("heat");let H=Q.get("h")||HZ0,L=Q.get("lv")||"total";setSeg(fig,"h",H);setSeg(fig,"lv",L);
const ramp=document.getElementById("ramp");
const a=p=>(0.92*Math.pow((18-p)/17,1.6)+0.04).toFixed(3);
function draw(){const rgb=css("--heat");ramp.innerHTML=[1,4,7,10,13,16,18].map(p=>`<i style="background:rgba(${rgb},${a(p)})"></i>`).join("");
 const w=D.week[H][L],rows=D.stand[H][L];
 let s=`<thead><tr><th></th>${w.weeks.map(d=>`<th>${fmtW(d)}</th>`).join("")}</tr></thead><tbody>`;
 for(const r of rows){const ps=w.pos[r.f];
  s+=`<tr class="${BASE.includes(r.f)?"base":""}"><th class="f">${r.f}<small>${r.m.toFixed(2)}</small></th>${ps.map((p,i)=>`<td class="${p<=5?"hi":""}" style="background:rgba(${rgb},${a(p)})" data-t="${r.f}|${w.weeks[i]}|${p}">${p}</td>`).join("")}</tr>`;}
 t.innerHTML=s+"</tbody>";
 t.querySelectorAll("td").forEach(td=>{const [f,d,p]=td.dataset.t.split("|");
  td.addEventListener("mousemove",e=>showTip(e,`<b>${f}</b><br>Forecast made week of ${fmtW(d)}<br>Position by MASE <span class="m">${p} of 18</span>`));
  td.addEventListener("mouseleave",hideTip);});}
seg(fig,"lv",v=>{L=v;draw();});seg(fig,"h",v=>{H=v;draw();});draw();
new MutationObserver(draw).observe(document.documentElement,{attributes:true,attributeFilter:["data-theme"]});})();

/* fig 4 */
if(document.getElementById("fig4"))(function(){const fig=document.getElementById("fig4"),sel=document.getElementById("drillSel"),box=document.getElementById("drillSvg"),keys=document.getElementById("drillKeys");
let H=Q.get("h")||HZ0,S=Q.get("s")||"total:all",F=Q.has("frame")?+Q.get("frame"):null,timer=null;
const groups={total:"All tokens",category:"Category",language:"Language",model:"Model"};
for(const [lv,name] of Object.entries(groups)){const og=document.createElement("optgroup");og.label=name;
 Object.entries(D.drill).filter(([k,d])=>d.level===lv).forEach(([k,d])=>{const o=document.createElement("option");o.value=k;o.textContent=d.label;og.appendChild(o);});
 sel.appendChild(og);}
sel.value=S;sel.onchange=()=>{S=sel.value;play();};
const tok=v=>{const r=(x,u)=>(Math.round(x*10)/10).toString()+u;return v>=1000?r(v/1000,"T"):v>=1?r(v,"B"):r(v*1000,"M");};
function draw(){const d=D.drill[S];let h=H;if(!d.h[h])h=Object.keys(d.h)[0];
 fig.querySelectorAll('[data-ctl="h"] button').forEach(b=>{b.disabled=!d.h[b.dataset.v];b.style.opacity=d.h[b.dataset.v]?1:.4;b.setAttribute("aria-pressed",b.dataset.v===h);});
 document.getElementById("drillSub").textContent=`${d.label} · ${D.unit==="day"?"daily":"weekly"} tokens · ${D.hz[h]} ahead`;
 if(Q.has("big")){const [org,...rest]=d.label.split("/"),name=rest.length?rest.join("/"):org;   // loop GIF: the LLM name is the only text
  document.getElementById("drillTitle").innerHTML=`<span style="display:block;font-size:17px;font-weight:600;letter-spacing:-.01em;color:${css("--purple")};margin:0 0 8px">Forecasting model usage <span style="color:${css("--muted")};font-weight:500">· OpenRouter top 50</span></span><span style="display:block;font-size:34px;line-height:1.12;letter-spacing:-.02em;color:${css("--ink")}">${rest.length?`<span style="color:${css("--muted")};font-weight:500">${org}/</span>`:""}${name}</span>`;
  document.getElementById("drillSub").style.display="none";keys.style.display="none";
  const cap=fig.querySelector("figcaption");if(cap)cap.style.display="none";}
 const lines=d.h[h],cols=[css("--purple"),css("--blue"),css("--pink"),css("--dot"),css("--dot")],dash=["","","","5 4","1.5 3.5"];
 const sty=Q.has("big");   // loop frames only: smooth curves, area fill, dashed grid, dotted backtest marker
 const W=760,Ht=sty?640:300,ml=sty?6:52,mr=sty?6:14,mt=sty?26:12,mb=30,iw=W-ml-mr,ih=Ht-mt-mb;
 const wk=d.weeks,xi=w=>ml+iw*wk.indexOf(w)/(wk.length-1);
 let mx=Math.max(...d.y);lines.forEach(l=>Object.entries(l.pts).forEach(([w,v])=>{if(wk.includes(w))mx=Math.max(mx,v);}));
 const raw=mx/4,mag=Math.pow(10,Math.floor(Math.log10(raw))),step=[1,2,2.5,5,10].map(k=>k*mag).find(k=>k>=raw);const nt=Math.ceil(mx*1.04/step);mx=step*nt;
 const y=v=>mt+ih*(1-v/mx);
 const bt=Object.keys(lines[0].pts).filter(w=>wk.includes(w)).sort();const x0=xi(bt[0])-iw/(wk.length-1)/2;
 const per=d.per[h]||1,k=F===null?bt.length/per:Math.floor(F/2),rev=k*per,shown=new Set(F===null?bt:bt.slice(0,(k+(F%2))*per));
 const aLast=F===null||rev>=bt.length?wk.length-1:rev?wk.indexOf(bt[rev-1]):wk.indexOf(bt[0])-1;   // actuals catch up to the last revealed forecast date
 const smooth=P=>{const n=P.length;if(n<2)return "";if(n===2)return `M${P[0][0].toFixed(1)},${P[0][1].toFixed(1)}L${P[1][0].toFixed(1)},${P[1][1].toFixed(1)}`;   // monotone cubic: smooth, no invented peaks
  const dx=[],dy=[],m=[];for(let i=0;i<n-1;i++){dx[i]=P[i+1][0]-P[i][0];dy[i]=(P[i+1][1]-P[i][1])/dx[i];}
  m[0]=dy[0];m[n-1]=dy[n-2];for(let i=1;i<n-1;i++)m[i]=dy[i-1]*dy[i]<=0?0:3*(dx[i-1]+dx[i])/((2*dx[i]+dx[i-1])/dy[i-1]+(dx[i]+2*dx[i-1])/dy[i]);
  let o=`M${P[0][0].toFixed(1)},${P[0][1].toFixed(1)}`;
  for(let i=0;i<n-1;i++){const h=dx[i]/3;o+=`C${(P[i][0]+h).toFixed(1)},${(P[i][1]+m[i]*h).toFixed(1)} ${(P[i+1][0]-h).toFixed(1)},${(P[i+1][1]-m[i+1]*h).toFixed(1)} ${P[i+1][0].toFixed(1)},${P[i+1][1].toFixed(1)}`;}return o;};
 let s;
 if(sty){
  s=`<svg viewBox="0 0 ${W} ${Ht}" role="img" aria-label="Actual weekly tokens and backtest forecasts for ${d.label}"><defs><linearGradient id="fillA" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="${css("--purple")}" stop-opacity=".16"/><stop offset="1" stop-color="${css("--purple")}" stop-opacity="0"/></linearGradient></defs>`;
  for(let k=1;k<=nt;k++){const v=step*k;s+=`<line x1="${ml}" x2="${ml+iw}" y1="${y(v)}" y2="${y(v)}" stroke="${css("--line")}" stroke-dasharray="3 5"/><text x="${ml+2}" y="${y(v)-6}" style="font:600 11px 'Roboto Mono';fill:${css("--muted-2")}">${tok(v)}</text>`;}
  s+=`<line x1="${ml}" x2="${ml+iw}" y1="${mt+ih}" y2="${mt+ih}" stroke="${css("--line")}"/>`;
  const tick=D.unit==="day"?14:4;wk.forEach((w,i)=>{if((wk.length-1-i)%tick===0)s+=`<text x="${xi(w)}" y="${Ht-8}" text-anchor="${i===0?"start":i===wk.length-1?"end":"middle"}" style="font:600 11px 'Roboto Mono';fill:${css("--muted")}">${fmtW(w)}</text>`;});
  const xb=xi(bt[0])-iw/(wk.length-1)/2;
  s+=`<line x1="${xb}" x2="${xb}" y1="${mt-8}" y2="${mt+ih}" stroke="${css("--purple")}" stroke-width="1.2" stroke-dasharray="2 4"/>`;
  s+=`<text x="${ml+iw}" y="${mt-10}" text-anchor="end" style="font:600 11px 'Roboto Mono';fill:${css("--muted")}">backtest weeks</text>`;
  const wa=wk.slice(0,aLast+1),A=wa.map((w,j)=>[xi(w),y(d.y[j])]);
  if(A.length>1)s+=`<path d="${smooth(A)}L${A[A.length-1][0].toFixed(1)},${mt+ih}L${A[0][0].toFixed(1)},${mt+ih}Z" fill="url(#fillA)"/>`;
  lines.slice().reverse().forEach((l,ri)=>{const i=lines.length-1-ri;const P=Object.entries(l.pts).filter(([w])=>shown.has(w)).sort().map(([w,v])=>[xi(w),y(v)]);
   s+=`<path d="${smooth(P)}" fill="none" stroke="${cols[i]}" stroke-width="${i===0?2.6:i<3?2:1.6}" stroke-dasharray="${dash[i]}" stroke-linecap="round"/>`;
   if(P.length<3)P.forEach(([x,yy])=>s+=`<circle cx="${x}" cy="${yy}" r="3.2" fill="${i<3?cols[i]:"none"}" stroke="${cols[i]}" stroke-width="1.4"/>`);});
  s+=`<path d="${smooth(A)}" fill="none" stroke="${css("--ink")}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>`;
  if(A.length)s+=`<circle cx="${A[A.length-1][0]}" cy="${A[A.length-1][1]}" r="4" fill="${css("--ink")}"/>`;
 }else{
  s=`<svg viewBox="0 0 ${W} ${Ht}" role="img" aria-label="Actual weekly tokens and backtest forecasts for ${d.label}">`;
 s+=`<rect x="${x0}" y="${mt}" width="${ml+iw-x0+4}" height="${ih}" fill="${css("--purple-soft")}" rx="6"/>`;
 for(let k=0;k<=nt;k++){const v=step*k;s+=`<line x1="${ml}" x2="${ml+iw}" y1="${y(v)}" y2="${y(v)}" stroke="${css("--grid")}"/><text x="${ml-8}" y="${y(v)+3.5}" text-anchor="end">${k?tok(v):"0"}</text>`;}
 const tick=D.unit==="day"?14:4;wk.forEach((w,i)=>{if((wk.length-1-i)%tick===0)s+=`<text x="${xi(w)}" y="${Ht-8}" text-anchor="middle">${fmtW(w)}</text><line x1="${xi(w)}" x2="${xi(w)}" y1="${mt+ih}" y2="${mt+ih+4}" stroke="${css("--line")}"/>`;});
 s+=`<text x="${x0+8}" y="${mt+14}" style="font-family:'DM Sans';font-size:11px;fill:${css("--muted")}">backtest weeks</text>`;
 lines.slice().reverse().forEach((l,ri)=>{const i=lines.length-1-ri;const pts=Object.entries(l.pts).filter(([w])=>shown.has(w)).sort();
  s+=`<path d="${pts.map(([w,v],j)=>(j?"L":"M")+xi(w).toFixed(1)+","+y(v).toFixed(1)).join("")}" fill="none" stroke="${cols[i]}" stroke-width="${i===0?2.4:1.8}" stroke-dasharray="${dash[i]}" stroke-linecap="round" stroke-linejoin="round"/>`;
  if(i<3&&(D.unit!=="day"||per===1))pts.forEach(([w,v])=>s+=`<circle cx="${xi(w)}" cy="${y(v)}" r="2.6" fill="${cols[i]}"/>`);});
 const wa=wk.slice(0,aLast+1);
 s+=`<path d="${wa.map((w,j)=>(j?"L":"M")+xi(w).toFixed(1)+","+y(d.y[j]).toFixed(1)).join("")}" fill="none" stroke="${css("--ink")}" stroke-width="2.4" stroke-linejoin="round"/>`;
 if(D.unit!=="day")wa.forEach((w,j)=>s+=`<circle cx="${xi(w)}" cy="${y(d.y[j])}" r="2.4" fill="${css("--ink")}"/>`);
 }
 s+=`<line id="xh" x1="0" x2="0" y1="${mt}" y2="${mt+ih}" stroke="${css("--muted-2")}" stroke-dasharray="2 3" opacity="0"/><rect id="hit" x="${ml}" y="${mt}" width="${iw}" height="${ih}" fill="transparent"/></svg>`;
 box.innerHTML=s;
 if(Q.has("big")&&d.rank&&d.rank[h]){let wrap=document.getElementById("bigwrap");   // loop frame: chart left, every forecaster ranked right
  if(!wrap){wrap=document.createElement("div");wrap.id="bigwrap";wrap.style.cssText="display:grid;grid-template-columns:minmax(0,1.75fr) minmax(0,1fr);gap:22px;align-items:start";
   box.parentNode.insertBefore(wrap,box);wrap.appendChild(box);const r=document.createElement("div");r.id="rankBox";wrap.appendChild(r);}
  const rk=d.rank[h],mx=Math.max(...rk.map(x=>x[1])),top=lines.slice(0,3).map(l=>l.f);
  document.getElementById("rankBox").innerHTML=`<div style="display:flex;justify-content:space-between;font:600 10.5px 'DM Sans';letter-spacing:.06em;color:${css("--muted")};margin:0 0 6px"><span>FORECASTER</span><span>VS NAIVE</span></div>`+
   rk.map(([f,m],i)=>{const isB=BASE.includes(f),c=top.includes(f)?cols[top.indexOf(f)]:isB?css("--dot"):css("--stem");
    return `<div style="display:grid;grid-template-columns:18px 1fr auto;gap:6px;align-items:center;padding:4px 6px;border-radius:7px;${i===0?`background:${css("--purple-soft")};`:`border-top:1px solid ${css("--line")};border-radius:0;`}">
     <span style="font:500 10.5px 'Roboto Mono';color:${i===0?css("--purple"):css("--muted-2")}">${i+1}</span>
     <span style="font:${i===0||top.includes(f)?600:500} 12px 'DM Sans';color:${css("--ink")};white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${f}${isB?` <span style="font-weight:500;font-size:10px;color:${css("--muted")}">baseline</span>`:""}</span>
     <span style="font:600 11.5px 'Roboto Mono';color:${i===0?css("--purple"):css("--ink")}">${m.toFixed(3)}</span>
     <span></span><span style="grid-column:2 / 4;height:3px;border-radius:2px;background:${isB?`repeating-linear-gradient(90deg,${c} 0 4px,transparent 4px 6px)`:c};width:${(100*m/mx).toFixed(1)}%"></span></div>`;}).join("");}
 keys.innerHTML=`<span><svg viewBox="0 0 22 8"><line x1="1" x2="21" y1="4" y2="4" stroke="${css("--ink")}" stroke-width="2.4"/></svg>Actual</span>`+
  lines.map((l,i)=>`<span><svg viewBox="0 0 22 8"><line x1="1" x2="21" y1="4" y2="4" stroke="${cols[i]}" stroke-width="2.2" stroke-dasharray="${dash[i]}"/></svg>${l.f} <b>${l.m.toFixed(3)}</b></span>`).join("");
 const svg=box.querySelector("svg"),xh=svg.querySelector("#xh");
 svg.querySelector("#hit").addEventListener("mousemove",e=>{const r=svg.getBoundingClientRect();const px=(e.clientX-r.left)*W/r.width;
  const i=Math.max(0,Math.min(wk.length-1,Math.round((px-ml)/iw*(wk.length-1))));const w=wk[i];
  xh.setAttribute("x1",xi(w));xh.setAttribute("x2",xi(w));xh.setAttribute("opacity",1);
  showTip(e,`<b>${D.unit==="day"?"":"Week of "}${fmtW(w)}</b><br>Actual <span class="m">${tok(d.y[i])}</span>`+lines.filter(l=>l.pts[w]!==undefined).map(l=>`<br>${l.f} <span class="m">${tok(l.pts[w])}</span>`).join(""));});
 svg.querySelector("#hit").addEventListener("mouseleave",()=>{xh.setAttribute("opacity",0);hideTip();});}
function play(){clearInterval(timer);if(STILL){draw();return;}F=0;draw();timer=setInterval(()=>{F++;if(F>24){F=null;clearInterval(timer);}draw();},420);}
document.getElementById("replay").onclick=play;
seg(fig,"h",v=>{H=v;play();});draw();
if(!STILL&&"IntersectionObserver" in window){const io=new IntersectionObserver(es=>{if(es[0].isIntersecting){io.disconnect();play();}},{threshold:.5});io.observe(box);}
new MutationObserver(draw).observe(document.documentElement,{attributes:true,attributeFilter:["data-theme"]});})();
if(STILL)setTimeout(()=>{document.title="H"+Math.ceil(document.getElementById(STILL).getBoundingClientRect().bottom+24);},300);

document.getElementById("theme").onclick=()=>{const r=document.documentElement;
 const dark=r.dataset.theme?r.dataset.theme==="dark":matchMedia("(prefers-color-scheme: dark)").matches;r.dataset.theme=dark?"light":"dark";};
</script></body></html>
"""
out = HERE / "blog.html"
out.write_text(HTML.replace("__DATA__", json.dumps(DATA, separators=(",", ":"))))
print("wrote", out, f"{out.stat().st_size / 1e3:.0f} kB")

# Daily page: same figures on the daily study (all tokens and models only, 1 or 7 days ahead), for the daily stills.
DHTML = HTML
for a, b in (('data-v="h1" aria-pressed="true">1 week ahead<', 'data-v="d1" aria-pressed="true">1 day ahead<'),
             ('data-v="h4" aria-pressed="false">4 weeks ahead<', 'data-v="d7" aria-pressed="false">7 days ahead<'),
             ('data-v="h1" aria-pressed="true">1 week<', 'data-v="d1" aria-pressed="true">1 day<'),
             ('data-v="h4" aria-pressed="false">4 weeks<', 'data-v="d7" aria-pressed="false">7 days<'),
             ('<button data-v="category" aria-pressed="false">Category</button><button data-v="language" aria-pressed="false">Language</button>', ''),
             ("<h3>MASE vs seasonal naive by level</h3>", "<h3>MASE vs seasonal naive by level · daily data</h3>"),
             ("<h3>GIFT-Eval order vs OpenRouter order</h3>", "<h3>GIFT-Eval order vs OpenRouter order · daily data</h3>"),
             ("<h3>fev-bench order vs OpenRouter order</h3>", "<h3>fev-bench order vs OpenRouter order · daily data</h3>"),
             ("Seasonal naive repeats last week.", "Seasonal naive repeats the same day last week."),
             ("Each forecast point was made 1 week (or 4 weeks) before the week it lands on, using only the data available then.",
              "Each forecast was made from the data up to its cutoff, one cutoff per week. 1 day ahead shows each forecast's first day, a week apart, with lines joining them. 7 days ahead shows all 7 days."),
             ("For 4 weeks ahead, MASE covers all four weeks of each forecast and the chart shows the 4th.", "For 7 days ahead, MASE covers all 7 days."),
             ("backtest weeks</text>", "backtest days</text>")):
    assert a in DHTML, a
    DHTML = DHTML.replace(a, b)
lstand, ldrill = load(HERE / "loop", {"h1": 1}, "week", HIST)          # per-LLM loop animation (4-week minimum history)
lout = HERE / "loop" / "blog_loop.html"
lout.write_text(HTML.replace("__DATA__", json.dumps({**DATA, "drill": ldrill}, separators=(",", ":"))))
print("wrote", lout, f"{lout.stat().st_size / 1e3:.0f} kB")
out = HERE / "daily" / "blog_daily.html"
out.write_text(DHTML.replace("__DATA__", json.dumps(DDATA, separators=(",", ":"))))
print("wrote", out, f"{out.stat().st_size / 1e3:.0f} kB")
