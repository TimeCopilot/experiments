"""Looping GIF for the top of the write-up, in the style of the OpenRouter article's model loop. Each frame is Figure 1
of the write-up for one report day (history, backtest and locked forecasts of the 3 closest models next to the top 6
and Wall Street), captured from index.html's still mode (#still=<report day index>) so the GIF matches the page.

Run after build_web.py. Writes assets/loop_report_days.gif.

    python3 build_web.py && python3 build_loop.py
"""
import json, pathlib, re, subprocess, tempfile
from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
PAGE = (HERE / "index.html").as_uri()
W = 1100
N = len(json.load(open(HERE.parent / "season/season.json"))["prints"])


def height(i):
    dom = subprocess.run([CHROME, "--headless=new", "--disable-gpu", f"--window-size={W},3000", "--virtual-time-budget=5000",
                          "--dump-dom", f"{PAGE}#still={i}"], capture_output=True, text=True).stdout
    return int(re.search(r"<title>H(\d+)</title>", dom).group(1))


def shot(i, path, h):
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--window-size={W},{h}",
                    "--force-device-scale-factor=1", "--virtual-time-budget=5000", f"--screenshot={path}",
                    f"{PAGE}#still={i}"], capture_output=True)
    return path


h = max(height(i) for i in range(N))
with tempfile.TemporaryDirectory() as tmp:
    ims = [Image.open(shot(i, pathlib.Path(tmp) / f"{i:02d}.png", h)).convert("RGB") for i in range(N)]
(HERE / "assets").mkdir(exist_ok=True)
out = HERE / "assets" / "loop_report_days.gif"
ims = [im.convert("P", palette=Image.Palette.ADAPTIVE, colors=256) for im in ims]
ims[0].save(out, save_all=True, append_images=ims[1:], duration=[3200] * len(ims), loop=0, optimize=True)
print("wrote", out, f"{out.stat().st_size / 1e6:.2f} MB, {len(ims)} frames, {ims[0].size}")
