# Data

Every number in the write-up and the terminal, as plain CSVs. All money values are in millions of U.S. dollars.
Series ids are used everywhere as file names:

| series_id | Company | Metric |
|---|---|---|
| `coin_net` | Coinbase | Net revenue |
| `apple_iphone` | Apple | iPhone net sales |
| `palantir_total` | Palantir | Total revenue |
| `amd_dc` | AMD | Data Center revenue |
| `mcd_total` | McDonald's | Total revenues |
| `mcd_franchised` | McDonald's | Franchised revenues |
| `shopify_gmv` | Shopify | GMV (gross merchandise volume) |
| `disney_exp` | Disney | Experiences revenue |
| `hd_net_sales` | Home Depot | Net sales |
| `nvidia_dc` | Nvidia | Data Center revenue |
| `walmart_us` | Walmart | Walmart U.S. net sales |

## raw/

What the companies reported and what Wall Street expected, before any modeling.

- **`series/<series_id>.csv`**: the quarterly history each model was given.
  - Columns: `quarter`, `quarter_end_date`, `value_usd_m`, `source_url`, `notes`.
  - `quarter` uses the company's own fiscal labels, for example Apple's Q4 FY2026 is the July to September 2026 quarter.
  - `source_url` points to the SEC filing or earnings release the value came from.
  - `notes` records anything constructed or approximate.
- **`report_days.csv`**: one row per series.
  - The quarter being forecast and its calendar quarter.
  - The report date, and the date the foundation-model forecasts were locked.
  - Whether the company has reported yet.
  - The reported number, the Wall Street consensus and its source.

## processed/

Model outputs and scores. 33 models per series:
- 24 foundation models through FoundationForecast.
- Seasonal naive, also through FoundationForecast.
- 8 models run locally on the same quarters: AutoARIMA, AutoETS, AutoTheta, Naive, Prophet, LightGBM, XGBoost and N-BEATS.

### Per-series folders

Three folders, with one file per series.

- **`cross_validation/<series_id>.csv`**: the backtest. Each model forecast each of the last 12 quarters one quarter ahead, using only the data before that quarter.
  - `relative_to_naive` is the model's absolute error divided by seasonal naive's on the same quarter.
- **`leaderboards/<series_id>.csv`**: the cross-validation leaderboard.
  - `cv_relative_mase` is the geometric mean of the 12 `relative_to_naive` values. 1 means no better than seasonal naive, lower is better.
- **`locked_forecasts/<series_id>.csv`**: each model's forecast for the next four quarters, locked before report day. The first quarter column is the one scored on report day.

### Season-wide files

- **`report_day_scores.csv`**: every model and the Wall Street consensus against the reported number, for each series that has reported.
  - `rank_of_34` orders all 33 models plus Wall Street by absolute miss.
  - `relative_to_naive` divides the miss by seasonal naive's miss on the same report day.
- **`season_board.csv`**: season scores per model.
  - `report_day_score` is the geometric mean of `relative_to_naive` over the report days so far.
  - `cv_score` is the geometric mean of the cross-validation relative MASE over all 11 series.
  - `report_days_beating_wall_street` counts report days where the model missed by less than the consensus.
  - The Wall Street consensus is scored the same way and listed as its own row.
  - `gift_eval_all`, `gift_eval_quarterly` and `fev_bench` are the public benchmark scores on the same relative-MASE scale, where available. GIFT-Eval quarterly uses its M4 quarterly configuration.
- **`benchmark_correlations.csv`**: Spearman rank correlations between the rankings, over the foundation models present in both.

## How it's built

`export_data.py` writes everything here from `terminal/data.js` and `season/season.json`, using the original extraction files in
`source/` (not in the repo) for the source links. Rebuild with `python3 data/export_data.py`. The order of the full pipeline is in the
README one folder up.
