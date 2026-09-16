.PHONY: signals

# Manually trigger the "Update macro signals" GitHub Action (same as the
# Actions tab "Run workflow" button), instead of waiting for the weekday cron.
# Requires `gh auth login` once.
signals:
	gh workflow run update-signals.yml
	@echo "Triggered — check status with: gh run watch"
