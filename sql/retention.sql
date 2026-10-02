-- Weekly cohort retention. A cohort is everyone who signed up in the same
-- Monday-to-Sunday week; "retained in week N" means at least one session
-- N weeks after the cohort week started. Weeks that have not happened yet
-- (relative to the last event in the data) are left out, not shown as zero.
WITH cohort AS (
    SELECT user_id, date(event_ts, 'weekday 0', '-6 days') AS cohort_week
    FROM events
    WHERE event_name = 'signed_up'
),
data_end AS (
    SELECT MAX(date(event_ts)) AS last_day FROM events
),
sizes AS (
    SELECT cohort_week, COUNT(*) AS cohort_size
    FROM cohort
    GROUP BY cohort_week
),
weeks(n) AS (
    SELECT 0
    UNION ALL
    SELECT n + 1 FROM weeks WHERE n < 30
),
grid AS (
    SELECT s.cohort_week, s.cohort_size, w.n AS week_no
    FROM sizes s
    CROSS JOIN weeks w
    CROSS JOIN data_end d
    WHERE date(s.cohort_week, '+' || (w.n * 7) || ' days') <= d.last_day
),
active AS (
    SELECT c.cohort_week,
           CAST((julianday(date(e.event_ts)) - julianday(c.cohort_week)) / 7 AS INTEGER) AS week_no,
           COUNT(DISTINCT e.user_id) AS retained
    FROM events e
    JOIN cohort c ON c.user_id = e.user_id
    WHERE e.event_name = 'session'
    GROUP BY c.cohort_week, week_no
)
SELECT g.cohort_week,
       g.cohort_size,
       g.week_no,
       COALESCE(a.retained, 0) AS retained,
       ROUND(100.0 * COALESCE(a.retained, 0) / g.cohort_size, 1) AS retention_pct
FROM grid g
LEFT JOIN active a ON a.cohort_week = g.cohort_week AND a.week_no = g.week_no
ORDER BY g.cohort_week, g.week_no;
