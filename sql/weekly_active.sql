-- Weekly active users (anyone with a session) and week-over-week change.
WITH weekly AS (
    SELECT date(event_ts, 'weekday 0', '-6 days') AS week_start,
           COUNT(DISTINCT user_id)                AS wau
    FROM events
    WHERE event_name = 'session'
    GROUP BY week_start
)
SELECT week_start,
       wau,
       ROUND(100.0 * (wau - LAG(wau) OVER (ORDER BY week_start))
                   / LAG(wau) OVER (ORDER BY week_start), 1) AS wow_pct
FROM weekly
ORDER BY week_start;
