"""Stills and the animated GIF for the Google Doc version of the post, rendered from blog.html in headless Chrome.

Each still opens blog.html#still=<figure>&... (only that figure, light theme, controls hidden), reads the
figure's height from the page title, then screenshots at 2x. The GIF steps fig4 through its 25 animation
frames (each backtest week: forecasts appear, then the actual) and holds the last frame. The fig2 and fig2b GIFs (one per level and horizon) slide each model
from its GIFT-Eval or fev-bench position to its OpenRouter position. They open on the finished chart, so a PDF or print shows the
real order, then rewind to straight lines and play forward.

Writes assets/*.png and *.gif (fig2/fig2b slope GIFs, fig4 GIFs per horizon). With --daily, renders the daily
study from daily/blog_daily.html into assets_daily/ (all tokens and models, 1 and 7 days ahead). Pass figure ids
to render only those.

    python render_assets.py [--daily] [fig1 fig2 fig2b fig4 loop]
"""
import os, pathlib, re, subprocess, sys, tempfile
from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
DAILY = "--daily" in sys.argv                               # daily study: daily/blog_daily.html -> assets_daily/
ONLY = [a for a in sys.argv[1:] if a != "--daily"]          # figure ids, e.g. "fig1 fig2b": render only those
OUT = HERE / ("assets_daily" if DAILY else "assets")
OUT.mkdir(exist_ok=True)
CHROME = os.environ.get("CHROME", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
URL = (HERE / ("daily/blog_daily.html" if DAILY else "blog.html")).as_uri()
W = 1048
HZ = {"d1": "1day", "d7": "7days"} if DAILY else {"h1": "1week", "h4": "4weeks"}
LVS = {"total": "alltokens", "model": "models"} if DAILY else \
      {"total": "alltokens", "category": "category", "language": "language", "model": "models"}
if DAILY:                                                   # two levels fit one board per horizon
    STILLS = {f"fig1_avg_mase_{hn}_all": f"still=fig1&h={h}" for h, hn in HZ.items()}
else:
    STILLS = {
        "fig1_avg_mase_1week": "still=fig1&h=h1&top=1",
        "fig1_avg_mase_4weeks": "still=fig1&h=h4&top=1",
        "fig1_avg_mase_1week_all_a": "still=fig1&h=h1&lvs=total,category",
        "fig1_avg_mase_1week_all_b": "still=fig1&h=h1&lvs=language,model",
        "fig1_avg_mase_4weeks_all_a": "still=fig1&h=h4&lvs=total,category",
        "fig1_avg_mase_4weeks_all_b": "still=fig1&h=h4&lvs=language,model",
    }
STILLS.update({f"fig4_actual_vs_forecast_alltokens_{hn}": f"still=fig4&s=total:all&h={h}" for h, hn in HZ.items()})
FIG2 = {f"{prefix}_{n}_{hn}": f"still={fig}&lv={lv}&h={h}"
        for fig, prefix in (("fig2", "fig2_gift_eval_vs_openrouter"), ("fig2b", "fig2b_fev_vs_openrouter"))
        for h, hn in HZ.items() for lv, n in LVS.items()}
if ONLY:
    keep = lambda d: {k: q for k, q in d.items() if any(f"still={f}&" in q for f in ONLY)}
    STILLS, FIG2 = keep(STILLS), keep(FIG2)


def height(q):
    dom = subprocess.run([CHROME, "--headless=new", "--disable-gpu", f"--window-size={W},4000",
                          "--virtual-time-budget=4000", "--dump-dom", f"{URL}#{q}"],
                         capture_output=True, text=True).stdout
    return int(re.search(r"<title>H(\d+)</title>", dom).group(1))


def shot(q, path, scale, h=None):
    h = h or height(q)
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--window-size={W},{h}",
                    f"--force-device-scale-factor={scale}", "--virtual-time-budget=4000",
                    f"--screenshot={path}", f"{URL}#{q}"], capture_output=True)
    return path


def save_gif(frames, durations, path):
    frames = [im.convert("P", palette=Image.Palette.ADAPTIVE, colors=256) for im in frames]
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=durations, loop=0, optimize=True)
    print("wrote", path, f"{path.stat().st_size / 1e6:.2f} MB")


for name, q in {**STILLS, **FIG2}.items():
    print("wrote", shot(q, OUT / f"{name}.png", 2))

N = 24                                                      # motion steps between straight lines and the real order
for name, q in FIG2.items():
    h = height(q)
    with tempfile.TemporaryDirectory() as tmp:
        im = {k: Image.open(shot(f"{q}&t={k / N:.4f}", pathlib.Path(tmp) / f"{k:02d}.png", 1, h)).convert("RGB")
              for k in range(N + 1)}
    seq = [N] + list(range(N - 1, 0, -2)) + [0] + list(range(1, N))
    durations = [3500] + [30] * len(range(N - 1, 0, -2)) + [1100] + [70] * (N - 1)
    save_gif([im[k] for k in seq], durations, OUT / f"{name}.gif")

if "loop" in ONLY:                                          # one frame per OpenRouter model, big model name, then loop
    import json
    URL = (HERE / "loop" / "blog_loop.html").as_uri()      # loop data: 4-week minimum history, more windows and LLMs
    D = json.loads(re.search(r"const D=(\{.*?\});\n", (HERE / "loop" / "blog_loop.html").read_text(), re.S).group(1))
    h0 = list(HZ)[0]
    models = sorted((k for k, d in D["drill"].items() if d["level"] == "model" and h0 in d["h"]),
                    key=lambda k: -D["drill"][k]["y"][-1])     # largest token volume first
    q = lambda i, k: f"still=fig4&s={k}&h={h0}&big=1&n={i + 1}&of={len(models)}"
    hh = max(height(q(i, k)) for i, k in enumerate(models))
    with tempfile.TemporaryDirectory() as tmp:
        frames = [Image.open(shot(q(i, k), pathlib.Path(tmp) / f"{i:02d}.png", 1, hh)).convert("RGB") for i, k in enumerate(models)]
    save_gif(frames, [2600] * len(frames), OUT / f"fig4_loop_models_{HZ[h0]}.gif")

if ONLY and "fig4" not in ONLY:
    sys.exit()

for h, hn in HZ.items():                                    # fig4: forecasts appear week by week, then the actuals
    frames = []
    with tempfile.TemporaryDirectory() as tmp:
        for f in range(25):
            p = shot(f"still=fig4&s=total:all&h={h}&frame={f}", pathlib.Path(tmp) / f"{f:02d}.png", 1)
            frames.append(Image.open(p).convert("RGB"))
    save_gif(frames, [900] + [450] * 23 + [3500], OUT / f"fig4_actual_vs_forecast_alltokens_{hn}.gif")
