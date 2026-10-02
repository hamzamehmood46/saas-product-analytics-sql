-- Signup -> workspace -> upgrade funnel. A user counts at a step only if they
-- reached the previous step first, so the numbers can only go down.
WITH step AS (
    SELECT user_id, event_name, MIN(event_ts) AS ts
    FROM events
    WHERE event_name IN ('signed_up', 'created_workspace', 'upgraded')
    GROUP BY user_id, event_name
),
journey AS (
    SELECT s1.ts AS t1, s2.ts AS t2, s3.ts AS t3
    FROM step s1
    LEFT JOIN step s2 ON s2.user_id = s1.user_id
                     AND s2.event_name = 'created_workspace' AND s2.ts >= s1.ts
    LEFT JOIN step s3 ON s3.user_id = s1.user_id
                     AND s3.event_name = 'upgraded' AND s2.ts IS NOT NULL AND s3.ts >= s2.ts
    WHERE s1.event_name = 'signed_up'
),
counts AS (
    SELECT 1 AS step_no, 'Signed up' AS step, COUNT(t1) AS users FROM journey
    UNION ALL SELECT 2, 'Created a workspace', COUNT(t2) FROM journey
    UNION ALL SELECT 3, 'Upgraded to paid', COUNT(t3) FROM journey
)
SELECT step_no,
       step,
       users,
       ROUND(100.0 * users / FIRST_VALUE(users) OVER (ORDER BY step_no), 1) AS pct_of_signups,
       ROUND(100.0 * users / LAG(users) OVER (ORDER BY step_no), 1)         AS pct_of_previous_step
FROM counts
ORDER BY step_no;
