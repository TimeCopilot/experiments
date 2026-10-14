# Data licenses

## OpenRouter rankings

The files in `data/raw/` and `daily/raw/day_*.json`, and every series derived from them (`series.json`, `daily/series.json`, `loop/series.json`, the `actual_tokens` columns), come from OpenRouter's public rankings datasets at https://openrouter.ai/rankings, licensed under Creative Commons Attribution 4.0 (CC BY 4.0), https://creativecommons.org/licenses/by/4.0/.

Source: OpenRouter (openrouter.ai/rankings), CC BY 4.0. Weekly data pulled 2026-10-12, daily data pulled 2026-10-14. Each raw file records its pull time in `meta.as_of`.

Category and language-type numbers are OpenRouter's estimates from sampled requests.

## Benchmark results

`gift_eval.csv` is derived from the public results in SalesforceAIResearch/gift-eval (commit 577a65c), Apache License 2.0, Copyright (c) 2024 Salesforce, Inc.

`fev.csv` is derived from the public results in autogluon/fev (commit 83d347d), Apache License 2.0.

## Forecasts

The forecasts in `forecasts_api.csv`, `daily/forecasts_api.csv`, `loop/forecasts_api.csv` and the raw API responses were produced with FoundationForecast (https://timecopilot.dev) and are released with this repository under CC BY 4.0.
