# SaaS Product Analytics in SQL

[![Test and deploy](https://github.com/hamzamehmood46/saas-product-analytics-sql/actions/workflows/pages.yml/badge.svg)](https://github.com/hamzamehmood46/saas-product-analytics-sql/actions/workflows/pages.yml)

**Live report: [hamzamehmood46.github.io/saas-product-analytics-sql](https://hamzamehmood46.github.io/saas-product-analytics-sql/)**

Where do new users drop off? Which acquisition channels bring users who actually pay? How well do signup cohorts stick? What happened the week activity fell? This project answers those questions in plain SQL (CTEs and window functions) and presents the results as a readable report, with the query behind every number.

## The data

Synthetic, and labelled as such. A seeded generator (`analytics/generate.py`) creates 5,000 users and about 42,000 events (`signed_up`, `created_workspace`, `invited_teammate`, `session`, `upgraded`) across four channels. The same seed always produces the same rows. One bad release is planted in the week of 2025-05-12 so there is a real signal to find.

## The analyses

| Question | File | SQL techniques |
|---|---|---|
| Where do users drop out of signup, workspace, upgrade? | [`sql/funnel.sql`](sql/funnel.sql) | ordered funnel with self-joins, `FIRST_VALUE`, `LAG` |
| How well do signup-week cohorts retain? | [`sql/retention.sql`](sql/retention.sql) | recursive CTE for the week grid, cohort assignment, `COUNT(DISTINCT)` |
| Which channels bring users who pay? | [`sql/channel_quality.sql`](sql/channel_quality.sql) | conditional aggregation, `RANK()` |
| Do users who invite a teammate upgrade more? | [`sql/invite_lift.sql`](sql/invite_lift.sql) | `EXISTS` flags, segment comparison |
| Weekly active users and week-over-week change | [`sql/weekly_active.sql`](sql/weekly_active.sql) | `LAG` over weekly buckets |

What it finds on this dataset: about 56% of signups create a workspace and 17% of those upgrade; referral signups upgrade at roughly five times the rate of paid social; users who invite a teammate upgrade about five times as often (an association, not proof of cause, and the report says so); and weekly active users fall 34% in the bad-release week and rebound 52% after.

## Correctness

Each query is tested against a six-user dataset whose answers were worked out by hand (`tests/test_queries.py`), including edge cases: an upgrade that happens before the workspace must not count in the funnel, and cohort weeks that have not happened yet must not be shown as zero retention. Tests also check that the generator is deterministic, never creates orphan events, never produces events after the data cutoff and never upgrades a user before signup. (One of those tests caught a real generator bug while this was being built.)

## Run it

Python 3.10+ and nothing else (standard library only: `sqlite3`, `unittest`).

```bash
python -m unittest discover -s tests -t .
python build_site.py          # writes site/index.html and analytics.db
```

Open `analytics.db` in any SQLite tool to run your own queries.

## Layout

```
sql/        the analyses, one question per file
analytics/  schema, seeded data generator, HTML report builder
tests/      hand-verified query tests and generator checks
```

## Scope and honesty

This is a SQLite project on synthetic data. The same SQL patterns carry over to Snowflake, BigQuery or Databricks, but this repository does not use them, and the report does not use a BI platform; it is static HTML so it can be hosted for free.

## License

MIT
