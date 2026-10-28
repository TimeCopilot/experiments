# Can we predict token usage using transformer based models?

OpenRouter's top 50 with 21 Time Series Foundation Models, measuring the latest time series foundation models against real-world patterns.

Read the interactive article at **https://timecopilot.github.io/experiments/openroutertokens/**

Data, forecasts and code behind the article on forecasting LLM usage on OpenRouter's top 50 with time series foundation models.

23 forecasting models (21 time series foundation models plus seasonal naive and AutoARIMA) were backtested on OpenRouter token usage, weekly and daily, over 12 weekly cutoffs from mid-July to early October 2026. The models at the top of GIFT-Eval and fev-bench didn't come out on top on this experiment. t0-gamma and the four Timestral sizes were added on 2026-10-20.

## Headline results

| Claim | Where it comes from |
|---|---|
| On daily data, every one of the 21 foundation models beat both baselines on individual LLMs over 7 days | `daily/standings.csv` |
| At 1 week ahead on all OpenRouter tokens, 17 of the 21 beat seasonal naive | `standings.csv` |
| At 4 weeks ahead on individual LLMs, none of them beat seasonal naive | `standings.csv` |
| Timestral 209M, now first on GIFT-Eval and fev-bench, finishes 11th, 14th, 10th and 12th of 23 on all tokens at 1 day, 7 days, 1 week and 4 weeks | both standings files |
| TimesFM 3, first on both a week earlier and now 4th, finishes 10th, 20th, 20th and 9th | both standings files |
| t0-gamma, 3rd on both, finishes 8th, 17th, 23rd and 22nd | both standings files |
| Across the 33 LLMs in the loop animation, 14 different forecasters win at least one, and neither Timestral 209M nor TimesFM 3 wins any | `loop/mase_long.csv` |

`python verify.py` checks all of these, plus a few more, straight from the files.

## Reproduce it

From the repo root, move into this folder and install the requirements (Python 3.11+):

```
cd openroutertokens
pip install -r requirements.txt
```

### 1. Check the numbers (no keys needed)

```
make score     # re-scores every saved forecast, then runs verify.py
```

This rebuilds every standings file from the saved forecasts and checks the article's claims. It should print `13 of 13 claims reproduce`.

### 2. Re-run the forecasts with FoundationForecast

Every foundation-model forecast in this repo came from the hosted API of [FoundationForecast](https://timecopilot.dev), TimeCopilot's unified API for time series foundation models. To regenerate them yourself:

```
export TIMECOPILOT_API_KEY=...   # no key yet? request one at https://cal.com/team/timecopilot/teamintro-sourceweb
make rerun
```

`make rerun` clears the cached API responses, sends every backtest window to all 22 API models again (21 foundation models plus seasonal naive), re-runs AutoARIMA locally with statsforecast, re-scores everything and runs `verify.py`. A rerun of the original requests returned identical forecasts for 12 of the original 17 API models, and the rest differed by less than 0.2%, which didn't change any ordering in the article. Models that are nearly tied could still swap places.

### 3. Rebuild the benchmark orders

```
make benchmarks   # fetches GIFT-Eval and fev-bench results at the pinned commits
```

### 4. Pull fresh OpenRouter data

```
export OPENROUTER_API_KEY=...
make data
```

This pulls current data, so results will differ from the article once new weeks come in. The exact data used is already in `data/raw/` and `daily/raw/`.

### 5. Rebuild the charts

```
make figures   # needs Google Chrome (set CHROME=/path/to/chrome if it isn't in the default macOS location)
```

## What's in here

```
data/raw/weekly/          OpenRouter weekly top 50 + "other", 2025-01-06 to 2026-10-05 (as pulled 2026-10-12)
data/raw/segments/        weekly tokens by category (12) and language type (2)
data/fetch_*.py           the scripts that pulled them
build_data.py             -> series.json, tasks.csv          weekly series and backtest windows
run_api.py, raw/          -> forecasts_api.csv               FoundationForecast requests and raw responses
run_arima.py              -> forecasts_arima.csv             local AutoARIMA baseline
score.py                  -> mase_long.csv, weekly.csv, standings.csv
gift_eval.py, fev.py      -> gift_eval.csv, fev.csv          benchmark orders from the public results
daily/                    the same pipeline on daily data (fetch, build, API, AutoARIMA, score)
loop/                     the per-LLM loop animation data (4-week minimum history)
build_blog.py, blog.html  the interactive article page
render_assets.py          chart images and GIFs -> assets/, assets_daily/
verify.py                 checks the article's claims
lib/orlib.py              FoundationForecast API helper (reads TIMECOPILOT_API_KEY)
scripts/fetch_benchmarks.sh
```

### Key files

- `forecasts_api.csv`, `forecasts_arima.csv` (weekly) and `daily/forecasts_*.csv`. One row per forecast point with `series`, `cutoff`, `forecaster`, `step`, the target `week` or `day`, `actual_tokens` and `forecast_tokens`.
- `mase_long.csv`. MASE for every series, cutoff, forecaster and horizon.
- `standings.csv`. Per level and horizon, each forecaster's `rel_mase` (MASE relative to seasonal naive, see below), its `position`, and the plain average MASE for reference.
- `tasks.csv`. Every (series, cutoff) backtest window and how many weeks of history it had.

## Method

- **Levels.** All OpenRouter tokens (the top 50 plus OpenRouter's "other" row), 12 categories, 2 language types, and individual LLMs from the latest top 50. A weekly LLM series joins once it has 8 weeks of unbroken history (4 for the loop animation). Daily data covers all tokens and individual LLMs only, since OpenRouter publishes categories and languages weekly.
- **Backtest.** Rolling origin. At each of the last 12 weekly cutoffs every model sees only the data up to that cutoff. Weekly horizons are 1 and 4 weeks, daily horizons are 1 and 7 days.
- **Models.** 21 time series foundation models through FoundationForecast, plus seasonal naive and a local AutoARIMA. Most of the 21 are transformer-based. TiRex 2 and its GIFT-Eval zero-shot version are the exceptions, built on xLSTM.
- **Settings.** FoundationForecast defaults, weekly frequency with season length 1, daily frequency with season length 7. AutoARIMA from statsforecast with the same season lengths.
- **Metric.** MASE only (Hyndman and Koehler, 2006), scaled by the in-sample naive (weekly) or seasonal naive (daily) error up to each cutoff. Results are reported the way GIFT-Eval and fev-bench do it. For each series, a model's average MASE over the cutoffs is divided by seasonal naive's, so seasonal naive is 1 and lower is better. A level's score is the geometric mean of those ratios across its series.
- **Benchmark orders.** GIFT-Eval uses each model's MASE relative to seasonal naive over all 97 configurations, combined with a geometric mean, from the public results at commit `3c7be6d` (2026-10-17). fev-bench uses the same idea over its 100 tasks, with leakage and failure handling as the fev-bench skill score does, from the public results at commit `f9e2c7d` (2026-10-16).

## Limitations

- 12 weeks of one data source. A different period or domain could produce a different order.
- Category and language numbers are OpenRouter's own estimates from sampled requests.
- OpenRouter has no daily rows for 2025-06-15 and 2025-07-15. Each is filled with the average of the day before and after, months before the first cutoff.
- Many LLMs are only a few weeks old, so their series are short.
- t0-gamma and the four Timestral sizes (5M, 28M, 123M, 209M) were added on 2026-10-20, after they reached the API. Their forecasts use the same data, cutoffs and settings as the rest.

## Licenses and attribution

- Code is MIT licensed (see `LICENSE`).
- OpenRouter data is from [openrouter.ai/rankings](https://openrouter.ai/rankings), licensed CC BY 4.0. See `DATA_LICENSE.md`.
- GIFT-Eval results come from [SalesforceAIResearch/gift-eval](https://github.com/SalesforceAIResearch/gift-eval) and fev-bench results from [autogluon/fev](https://github.com/autogluon/fev), both Apache 2.0.

## Cite

See `CITATION.cff`. MASE is from Hyndman, R. J., and Koehler, A. B. (2006), "Another look at measures of forecast accuracy," *International Journal of Forecasting* 22(4), 679-688.
