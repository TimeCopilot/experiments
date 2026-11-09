"""Series config for the per-company reports, read from the unpacked earnings-program bundle.

Each series: the master quarterly CSV (fiscal labels + values), the API h=1 per-fold results (12 folds), the API
leaderboard and the locked h=4 forecast. Coinbase is already done in ~/Downloads/coinbase-bundle 2 and is not here.
"""
import csv, glob, pathlib

BUNDLE = pathlib.Path(__file__).resolve().parents[2] / "source/earnings-tracker"
OUT = pathlib.Path(__file__).resolve().parent.parent / "out"

# key: (company, metric title, folder, master csv, value column, per-fold csv, leaderboard csv, locked csv glob)
SERIES = {
    "apple_iphone": ("Apple", "iPhone net sales", "apple", "apple_quarterly.csv", "iphone_net_sales_usd_m",
                     "iphone_h1_per_fold_results.csv", "iphone_cv_h1_leaderboard.csv", "forecasts/locked_*.csv"),
    "palantir_total": ("Palantir", "Total revenue", "palantir", "palantir_quarterly.csv", "total_revenue_usd_m",
                       "total_h1_per_fold_results.csv", "total_cv_h1_leaderboard.csv", "forecasts/locked_*.csv"),
    "amd_dc": ("AMD", "Data Center revenue", "amd", "amd_quarterly.csv", "data_center_revenue_usd_m",
               "forecasts/dc_h1_per_fold_results.csv", "forecasts/dc_cv_h1_leaderboard.csv", "forecasts/locked_*.csv"),
    "disney_exp": ("Disney", "Experiences revenue", "disney", "disney_quarterly.csv", "experiences_revenue_usd_m",
                   "forecasts/exp_h1_per_fold_results.csv", "forecasts/exp_cv_h1_leaderboard.csv", "forecasts/locked_*.csv"),
    "hd_net_sales": ("Home Depot", "Net sales", "home-depot", "home_depot_quarterly.csv", "net_sales_usd_m",
                     "forecasts/net_sales_h1_per_fold_results.csv", "forecasts/net_sales_cv_h1_leaderboard.csv",
                     "forecasts/locked_*.csv"),
    "mcd_total": ("McDonald's", "Total revenues", "mcdonalds", "mcdonalds_total_revenues_quarterly.csv", "total_revenues_usd_m",
                  "forecasts/total_revenues_h1_per_fold_results.csv", "forecasts/total_revenues_cv_h1_leaderboard.csv",
                  "forecasts/locked_total_revenues_*.csv"),
    "mcd_franchised": ("McDonald's", "Franchised revenues", "mcdonalds", "mcdonalds_franchised_revenues_quarterly.csv",
                       "franchised_revenues_usd_m", "forecasts/franchised_revenues_h1_per_fold_results.csv",
                       "forecasts/franchised_revenues_cv_h1_leaderboard.csv", "forecasts/locked_franchised_revenues_*.csv"),
    "nvidia_dc": ("Nvidia", "Data Center revenue", "nvidia", "nvidia_quarterly.csv", "data_center_revenue_usd_m",
                  "forecasts/dc_h1_per_fold_results.csv", "forecasts/dc_cv_h1_leaderboard.csv", "forecasts/locked_*.csv"),
    "shopify_gmv": ("Shopify", "GMV", "shopify", "shopify_quarterly.csv", "gmv_usd_m",
                    "forecasts/gmv_h1_per_fold_results_labeled.csv", "forecasts/gmv_cv_h1_leaderboard.csv", "forecasts/locked_gmv_*.csv"),
    "walmart_us": ("Walmart", "Walmart U.S. net sales", "walmart", "walmart_quarterly.csv", "walmart_us_net_sales_usd_m",
                   "forecasts/walmart_h1_per_fold_results.csv", "forecasts/wmt_us_cv_h1_leaderboard.csv", "forecasts/locked_*.csv"),
}


def norm_label(q):                                       # "2026Q2" (McDonald's) -> "Q2 2026"; fiscal labels kept
    return f"{q[4:]} {q[:4]}" if len(q) == 6 and q[4] == "Q" else q


def next_label(q):                                       # "Q4 FY2026" -> "Q1 FY2027", "Q2 2026" -> "Q3 2026"
    n, yr = q.split()
    pre, y = ("FY", int(yr[2:])) if yr.startswith("FY") else ("", int(yr))
    n = int(n[1]) + 1
    return f"Q{1 if n == 5 else n} {pre}{y + 1 if n == 5 else y}"


def load(key):
    company, metric, folder, master, col, fold_csv, board_csv, locked_glob = SERIES[key]
    d = BUNDLE / folder
    rows = list(csv.DictReader(open(d / master)))
    hist = [(norm_label(r["quarter"]), float(r[col])) for r in rows if r[col] not in ("", None)]
    folds = list(csv.DictReader(open(d / fold_csv)))
    board = list(csv.DictReader(open(d / board_csv)))
    locked = {r["model"]: r for r in csv.DictReader(open(sorted(glob.glob(str(d / locked_glob)))[-1]))}
    cols = [c for c in next(iter(locked.values())) if not c.startswith(("lo", "hi"))]
    hcols = [next(c for c in cols if c == h or c.endswith("_" + h)) for h in ("h1", "h2", "h3", "h4")]
    assert len(hcols) == 4, (key, hcols)
    fut = [hist[-1][0]]
    for _ in range(4):
        fut.append(next_label(fut[-1]))
    return {"key": key, "company": company, "metric": metric, "hist": hist, "folds": folds, "board": board,
            "locked": locked, "hcols": hcols, "fut": fut[1:]}
