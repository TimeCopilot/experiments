PY ?= python

.PHONY: help verify score rerun forecasts benchmarks data figures

help:
	@echo "make verify      check the article's headline numbers against the saved results (no keys needed)"
	@echo "make score       re-score every saved forecast, then verify (no keys needed)"
	@echo "make rerun       re-run every forecast through FoundationForecast, re-score, verify (needs TIMECOPILOT_API_KEY)"
	@echo "make benchmarks  fetch GIFT-Eval and fev-bench results at the pinned commits and rebuild their orders"
	@echo "make data        pull fresh OpenRouter data and rebuild the series (needs OPENROUTER_API_KEY)"
	@echo "make figures     rebuild the article page and every chart image (needs Google Chrome)"

verify:
	$(PY) verify.py

score:
	$(PY) score.py
	$(PY) daily/score_daily.py
	$(PY) verify.py

# Clears the cached API responses so every forecast is requested again.
rerun:
	rm -rf raw loop/raw
	rm -f daily/raw/api_*.json
	$(MAKE) forecasts
	$(MAKE) score

forecasts:
	$(PY) run_api.py
	$(PY) run_arima.py
	$(PY) daily/run_api_daily.py
	$(PY) daily/run_arima_daily.py
	$(PY) loop/run_loop.py

benchmarks:
	sh scripts/fetch_benchmarks.sh
	$(PY) gift_eval.py
	$(PY) fev.py

data:
	$(PY) data/fetch_weekly.py
	$(PY) data/fetch_segments.py
	$(PY) build_data.py
	$(PY) daily/fetch_daily.py
	$(PY) daily/build_data_daily.py

figures:
	$(PY) build_blog.py
	$(PY) render_assets.py
	$(PY) render_assets.py --daily
	$(PY) render_assets.py loop
