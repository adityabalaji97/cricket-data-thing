# cricket-data-thing (Hindsight)

Cricket stats app: FastAPI + Postgres (Heroku) backend, React/MUI frontend on Vercel
(hindsight2020.vercel.app). Hero features are the **query builder**, **match preview** and
**scorecard**.

## Active project: multi-format expansion

The app is being extended from men's-T20-only to ODIs, women's T20s and Tests.

* **Plan and chunk briefs:** [MULTI_FORMAT_PLAN.md](MULTI_FORMAT_PLAN.md)
* **Dev log / handoff state:** [MULTI_FORMAT_DEV_LOG.md](MULTI_FORMAT_DEV_LOG.md)

**Read the dev log's CURRENT STATE block before starting work, and update it before you finish.**
Sessions alternate between Claude Code and Codex, so an undescribed change is a lost change.

## Local development

All work is developed and verified locally before anything reaches git or Heroku.

```bash
scripts/dev/setup_local_db.sh        # build hindsight_local from a subset of production
scripts/dev/run_local_api.sh         # API on :8000 against the local DB
npm start                            # frontend on :3000
python scripts/regression_snapshot.py check   # diff hero endpoints against frozen goldens
```

Run the golden `check` after every backend change: the point of the current phase is that men's T20
behaviour stays bit-identical while new formats are added.

## Landmines

* **Never run `cleanup_non_t20.py`.** It deletes any match with more than 260 deliveries — that is
  every ODI and every Test.
* **`.env` holds the production database URL.** Never repoint it at localhost. Local runs export
  `DATABASE_URL` instead, which wins because `database.py` calls `load_dotenv(override=False)`.
* **`models.py:308-396` (`DeliveryDetails`) is stale** and does not match the live table.
  `scripts/recreate_delivery_details.sql` is authoritative.
* **`delivery_details.date` is entirely NULL.** The populated column is `match_date`
  (varchar, ISO `YYYY-MM-DD`).
* **`matches.match_type` means `'league'`/`'international'`,** not the cricket format. Format lives
  in the new `format` column.
* The `/cricket-data-thing/` subdirectory is a stale vendored copy of the app — ignore it.
* There is **no migration framework**. Schema changes are hand-written SQL in `scripts/migrations/`,
  applied to the local DB first and to production as an explicit promotion step.
