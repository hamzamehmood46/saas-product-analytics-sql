-- Which acquisition channel brings users who actually convert?
-- Ranked by upgrade rate (upgraded users / all signups from that channel).
WITH per_user AS (
    SELECT u.user_id,
           u.channel,
           MAX(e.event_name = 'created_workspace') AS activated,
           MAX(e.event_name = 'upgraded')          AS upgraded
    FROM users u
    LEFT JOIN events e ON e.user_id = u.user_id
    GROUP BY u.user_id, u.channel
),
by_channel AS (
    SELECT channel,
           COUNT(*)       AS users,
           SUM(activated) AS activated,
           SUM(upgraded)  AS upgraded
    FROM per_user
    GROUP BY channel
)
SELECT channel,
       users,
       activated,
       upgraded,
       ROUND(100.0 * activated / users, 1) AS activation_rate,
       ROUND(100.0 * upgraded / users, 1)  AS upgrade_rate,
       RANK() OVER (ORDER BY 1.0 * upgraded / users DESC) AS rank_by_upgrade
FROM by_channel
ORDER BY rank_by_upgrade, channel;
