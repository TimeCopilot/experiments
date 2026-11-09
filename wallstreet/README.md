# Can we beat Wall Street using ✨FoundationForecast?

Q3 2026 earnings from 10 public companies, forecast by 24 time series foundation models through FoundationForecast plus
9 classical and machine learning models, and scored against the Wall Street consensus on report day.

This is not investment advice.

## What's here

| Folder | What it is |
|---|---|
| `web/` | The write-up. Open `web/index.html`. |
| `terminal/` | The interactive analyst terminal. Open `terminal/index.html`. |
| `data/raw/` | The reported quarterly numbers with their sources, plus actuals and Wall Street consensus per report day. |
| `data/processed/` | Model outputs and scores: cross-validation, leaderboards, locked forecasts, report-day scores, season board. |
| `season/` | `analysis.py` computes the season-wide numbers into `season.json`. |
| `pipeline/` | `code/` loads each series (`config.py`, `plot_company.py`) and runs the local models (`run_local.py`). `out/` holds those local runs. |

`data/README.md` describes every file and column.

To view the pages locally with working links between them, serve this folder and open `/web/` and `/terminal/`:

    python3 -m http.server 8000

## Rebuilding

The original extraction bundle (SEC filings and API job files, one folder per company) lives in
`source/earnings-tracker/`, which isn't committed. With `source/` in place, rebuild in this order:

    python3 pipeline/code/run_local.py      # local models: 12 backtest quarters plus the locked forecast, per series
    python3 terminal/build_data.py          # terminal/data.js
    python3 season/analysis.py              # season/season.json
    python3 data/export_data.py             # data/raw and data/processed
    python3 web/build_web.py                # web/index.html
    python3 web/build_loop.py               # web/assets/loop_report_days.gif

Without `source/`, the CSVs in `data/` already contain every number shown on the pages.
