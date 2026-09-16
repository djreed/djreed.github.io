.PHONY: signals analyze

# Manually trigger the "Update macro signals" GitHub Action (same as the
# Actions tab "Run workflow" button), instead of waiting for the weekday cron.
# Requires `gh auth login` once.
signals:
	gh workflow run update-signals.yml
	@echo "Triggered — check status with: gh run watch"

# Re-run just the classification step against the last-fetched raw data —
# no FRED API call, no network. Use this to tune analyze_signals.py locally.
analyze:
	python3 scripts/analyze_signals.py
