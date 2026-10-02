"""The queries are checked against a six-user dataset whose answers were worked out by hand."""
import unittest

from analytics import db, generate

# user_id, signup_date, channel
USERS = [
    (1, "2025-01-06", "organic"),
    (2, "2025-01-07", "organic"),
    (3, "2025-01-08", "paid_social"),
    (4, "2025-01-13", "paid_social"),
    (5, "2025-01-14", "referral"),
    (6, "2025-01-14", "organic"),
]
# user_id, timestamp, event
EVENTS = [
    (1, "2025-01-06 09:00:00", "signed_up"), (1, "2025-01-06 09:05:00", "session"),
    (1, "2025-01-06 10:00:00", "created_workspace"), (1, "2025-01-07 10:00:00", "invited_teammate"),
    (1, "2025-01-10 10:00:00", "upgraded"), (1, "2025-01-14 09:00:00", "session"),
    (2, "2025-01-07 09:00:00", "signed_up"), (2, "2025-01-07 09:05:00", "session"),
    (2, "2025-01-08 10:00:00", "created_workspace"),
    (3, "2025-01-08 09:00:00", "signed_up"), (3, "2025-01-08 09:05:00", "session"),
    (4, "2025-01-13 09:00:00", "signed_up"), (4, "2025-01-13 09:05:00", "session"),
    (4, "2025-01-13 10:00:00", "created_workspace"), (4, "2025-01-21 09:00:00", "session"),
    (4, "2025-01-28 09:00:00", "session"),
    (5, "2025-01-14 09:00:00", "signed_up"), (5, "2025-01-14 09:05:00", "session"),
    (5, "2025-01-14 10:00:00", "created_workspace"), (5, "2025-01-15 10:00:00", "invited_teammate"),
    (5, "2025-01-16 10:00:00", "upgraded"),
    (6, "2025-01-14 09:00:00", "signed_up"), (6, "2025-01-14 09:05:00", "session"),
]


def fixture():
    conn = db.connect()
    conn.executemany("INSERT INTO users VALUES (?,?,?,'US')", USERS)
    conn.executemany("INSERT INTO events (user_id, event_ts, event_name) VALUES (?,?,?)", EVENTS)
    return conn


class QueryTests(unittest.TestCase):
    def setUp(self):
        self.conn = fixture()

    def test_funnel_only_counts_users_who_reached_the_previous_step(self):
        _, rows = db.run(self.conn, "funnel")
        self.assertEqual(
            rows,
            [
                (1, "Signed up", 6, 100.0, None),
                (2, "Created a workspace", 4, 66.7, 66.7),
                (3, "Upgraded to paid", 2, 33.3, 50.0),
            ],
        )

    def test_funnel_ignores_an_upgrade_that_happened_before_the_workspace(self):
        self.conn.execute(
            "INSERT INTO events (user_id, event_ts, event_name) VALUES (2, '2025-01-07 09:30:00', 'upgraded')"
        )
        _, rows = db.run(self.conn, "funnel")
        self.assertEqual(rows[2][2], 2)  # user 2 upgraded before creating a workspace, so not counted

    def test_retention_by_weekly_cohort(self):
        _, rows = db.run(self.conn, "retention")
        self.assertEqual(
            rows,
            [
                ("2025-01-06", 3, 0, 3, 100.0),
                ("2025-01-06", 3, 1, 1, 33.3),
                ("2025-01-06", 3, 2, 0, 0.0),
                ("2025-01-06", 3, 3, 0, 0.0),
                ("2025-01-13", 3, 0, 3, 100.0),
                ("2025-01-13", 3, 1, 1, 33.3),
                ("2025-01-13", 3, 2, 1, 33.3),
            ],
        )

    def test_retention_does_not_report_weeks_that_have_not_happened(self):
        _, rows = db.run(self.conn, "retention")
        latest = [r for r in rows if r[0] == "2025-01-13"]
        self.assertEqual(max(r[2] for r in latest), 2)

    def test_channels_are_ranked_by_upgrade_rate(self):
        _, rows = db.run(self.conn, "channel_quality")
        self.assertEqual(
            rows,
            [
                ("referral", 1, 1, 1, 100.0, 100.0, 1),
                ("organic", 3, 2, 1, 66.7, 33.3, 2),
                ("paid_social", 2, 1, 0, 50.0, 0.0, 3),
            ],
        )

    def test_invite_lift(self):
        _, rows = db.run(self.conn, "invite_lift")
        self.assertEqual(rows, [("Invited a teammate", 2, 2, 100.0), ("Did not invite", 2, 0, 0.0)])

    def test_weekly_active_users_and_week_over_week_change(self):
        _, rows = db.run(self.conn, "weekly_active")
        self.assertEqual(
            rows,
            [
                ("2025-01-06", 3, None),
                ("2025-01-13", 4, 33.3),
                ("2025-01-20", 1, -75.0),
                ("2025-01-27", 1, 0.0),
            ],
        )


class GeneratorTests(unittest.TestCase):
    def test_same_seed_gives_identical_data(self):
        a, b = db.connect(), db.connect()
        generate.populate(a, n_users=300, seed=5)
        generate.populate(b, n_users=300, seed=5)
        q = "SELECT user_id, event_ts, event_name FROM events ORDER BY event_id"
        self.assertEqual(a.execute(q).fetchall(), b.execute(q).fetchall())

    def test_every_event_belongs_to_a_known_user_and_nothing_is_in_the_future(self):
        conn = db.connect()
        generate.populate(conn, n_users=400, seed=9)
        orphans = conn.execute(
            "SELECT COUNT(*) FROM events e LEFT JOIN users u USING (user_id) WHERE u.user_id IS NULL"
        ).fetchone()[0]
        latest = conn.execute("SELECT MAX(event_ts) FROM events").fetchone()[0]
        self.assertEqual(orphans, 0)
        self.assertLessEqual(latest, "2025-07-06 23:59:59")

    def test_a_user_never_upgrades_before_signing_up(self):
        conn = db.connect()
        generate.populate(conn, n_users=800, seed=3)
        bad = conn.execute(
            """SELECT COUNT(*) FROM events up JOIN events su
                 ON su.user_id = up.user_id AND su.event_name = 'signed_up'
               WHERE up.event_name = 'upgraded' AND up.event_ts < su.event_ts"""
        ).fetchone()[0]
        self.assertEqual(bad, 0)


if __name__ == "__main__":
    unittest.main()
