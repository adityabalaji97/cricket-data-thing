# Automation for Delivery Details Sync

This project’s delivery details refresh is driven by the entrypoint script `run_full_dd_sync.py`. It expects a `DATABASE_URL` environment variable that points at the target PostgreSQL database. Store the value in a local `.env` (for on-host jobs) or a secret manager (for scheduled workflows) instead of hard-coding it in command lines.

## Cron (weekly)

Example cron entry to run every Sunday at 03:00. Adjust paths to your checkout and Python environment:

```cron
0 3 * * 0 cd /path/to/cricket-data-thing \
  && source /path/to/venv/bin/activate \
  && set -a && source /path/to/.env && set +a \
  && python run_full_dd_sync.py --confirm
```

## systemd timer (optional)

For long-running jobs, a systemd timer avoids cron timeouts and provides journal logs. Example:

**`/etc/systemd/system/cricket-dd-sync.service`**
```ini
[Unit]
Description=Weekly delivery_details sync

[Service]
Type=oneshot
WorkingDirectory=/path/to/cricket-data-thing
EnvironmentFile=/path/to/.env
ExecStart=/path/to/venv/bin/python run_full_dd_sync.py --confirm
```

**`/etc/systemd/system/cricket-dd-sync.timer`**
```ini
[Unit]
Description=Weekly delivery_details sync timer

[Timer]
OnCalendar=Sun *-*-* 03:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

Enable the timer:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now cricket-dd-sync.timer
```

## GitHub Actions (CI preferred)

If you want a hosted weekly run, use the workflow in `.github/workflows/refresh-delivery-details.yml`. It runs `run_full_dd_sync.py` and pulls the database connection string from `DATABASE_URL` in repository secrets.

Expected environment variables:
- `DATABASE_URL`: PostgreSQL connection string used by `run_full_dd_sync.py`.
