"""TimeCopilot FoundationForecast API helper used by run_api.py, daily/run_api_daily.py and loop/run_loop.py.

Set TIMECOPILOT_API_KEY in the environment (request a key at https://cal.com/team/timecopilot/teamintro-sourceweb).
"""
import json, os, sys, urllib.request

BASE = os.environ.get("TIMECOPILOT_API_BASE", "https://api.timecopilot.dev")
UA = "openrouter-tsfm-benchmark/1.0"
SCALE = 1e9                                   # series are sent in billions of tokens


def token():
    key = os.environ.get("TIMECOPILOT_API_KEY")
    if not key:
        sys.exit("Set TIMECOPILOT_API_KEY first. Request a FoundationForecast API key at https://cal.com/team/timecopilot/teamintro-sourceweb")
    return key


def post(path, body, timeout=900):
    req = urllib.request.Request(
        BASE + path, data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {token()}", "Content-Type": "application/json", "User-Agent": UA},
        method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)
