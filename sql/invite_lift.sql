-- Among users who created a workspace: do those who invited a teammate
-- upgrade more often? (An association, not proof that inviting causes upgrades.)
WITH activated AS (
    SELECT DISTINCT user_id FROM events WHERE event_name = 'created_workspace'
),
flags AS (
    SELECT a.user_id,
           EXISTS (SELECT 1 FROM events e
                   WHERE e.user_id = a.user_id AND e.event_name = 'invited_teammate') AS invited,
           EXISTS (SELECT 1 FROM events e
                   WHERE e.user_id = a.user_id AND e.event_name = 'upgraded')         AS upgraded
    FROM activated a
)
SELECT CASE invited WHEN 1 THEN 'Invited a teammate' ELSE 'Did not invite' END AS segment,
       COUNT(*)      AS users,
       SUM(upgraded) AS upgraded,
       ROUND(100.0 * SUM(upgraded) / COUNT(*), 1) AS upgrade_rate
FROM flags
GROUP BY invited
ORDER BY invited DESC;
