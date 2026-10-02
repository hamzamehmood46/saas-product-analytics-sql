"""Seeded, synthetic SaaS event data.

Nothing here is real customer data. The generator is deterministic (same seed, same rows)
and has one planted incident, a bad release in the week of 2025-05-12 that cuts activity,
so the analysis has a real signal to find.
"""
from __future__ import annotations

import random
import sqlite3
from datetime import date, datetime, timedelta

FIRST_SIGNUP = date(2025, 1, 6)
LAST_SIGNUP = date(2025, 6, 29)
DATA_END = datetime(2025, 7, 6, 23, 59, 59)
INCIDENT_WEEK = date(2025, 5, 12)  # a Monday: the week a bad release shipped

# channel -> (share of signups, activation rate, invite rate, weekly-activity multiplier)
CHANNELS = {
    "organic":     (0.40, 0.62, 0.42, 1.00),
    "paid_search": (0.25, 0.55, 0.38, 0.95),
    "paid_social": (0.20, 0.35, 0.28, 0.75),
    "referral":    (0.15, 0.70, 0.60, 1.15),
}
COUNTRIES = ["US", "US", "US", "CA", "GB", "DE", "IN"]


def _monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def populate(conn: sqlite3.Connection, n_users: int = 5000, seed: int = 42) -> None:
    rng = random.Random(seed)
    names, weights = zip(*[(c, v[0]) for c, v in CHANNELS.items()])
    span_days = (LAST_SIGNUP - FIRST_SIGNUP).days
    users, events = [], []

    for uid in range(1, n_users + 1):
        channel = rng.choices(names, weights)[0]
        _, p_activate, p_invite, activity = CHANNELS[channel]
        signup = datetime.combine(FIRST_SIGNUP + timedelta(days=rng.randint(0, span_days)), datetime.min.time())
        signup += timedelta(seconds=rng.randint(8 * 3600, 22 * 3600))
        users.append((uid, signup.date().isoformat(), channel, rng.choice(COUNTRIES)))
        events.append((uid, signup, "signed_up"))
        events.append((uid, signup + timedelta(minutes=rng.randint(1, 20)), "session"))

        activated = rng.random() < p_activate
        activated_at = signup + timedelta(hours=rng.randint(1, 72)) if activated else None
        if activated_at:
            events.append((uid, activated_at, "created_workspace"))
            invited = rng.random() < p_invite
            if invited:
                events.append((uid, activated_at + timedelta(hours=rng.randint(2, 96)), "invited_teammate"))
            p_upgrade = 0.07 + (0.28 if invited else 0.0)
            if rng.random() < min(p_upgrade * activity, 0.9):
                events.append((uid, activated_at + timedelta(days=rng.randint(1, 30), hours=rng.randint(0, 20)), "upgraded"))

        # one coin flip per later calendar week: engaged users keep coming back, others fade
        p_week = (0.55 if activated else 0.18) * activity
        week = _monday(signup.date())
        for k in range(1, 40):
            start = datetime.combine(week + timedelta(weeks=k), datetime.min.time())
            if start > DATA_END:
                break
            p = p_week * (0.93 ** k)
            if (week + timedelta(weeks=k)) == INCIDENT_WEEK:
                p *= 0.55
            if rng.random() < p:
                for _ in range(rng.randint(1, 3)):
                    when = start + timedelta(days=rng.randint(0, 6), seconds=rng.randint(7 * 3600, 21 * 3600))
                    if when <= DATA_END:
                        events.append((uid, when, "session"))

    events = [e for e in events if e[1] <= DATA_END]  # the dataset ends on DATA_END, like a real export
    events.sort(key=lambda e: (e[1], e[0], e[2]))
    conn.executemany("INSERT INTO users VALUES (?,?,?,?)", users)
    conn.executemany(
        "INSERT INTO events (user_id, event_ts, event_name) VALUES (?,?,?)",
        [(u, _iso(t), n) for u, t, n in events],
    )
    conn.commit()
