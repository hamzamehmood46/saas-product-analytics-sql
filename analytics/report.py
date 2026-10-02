"""Builds a single static HTML report from the SQL in sql/. No JavaScript, no external assets."""
from __future__ import annotations

import html
import sqlite3

from . import db

INCIDENT_WEEK = "2025-05-12"

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SaaS Product Analytics in SQL</title>
<meta name="description" content="Funnel, cohort retention, channel quality and an engagement drop, all in plain SQL (CTEs and window functions) on a seeded synthetic SaaS dataset.">
<style>
:root{--bg:#f7f5f0;--card:#fff;--ink:#1d2433;--muted:#5b6579;--line:#e3dfd5;--accent:#0f6b5e;--bad:#b4412f;--soft:#e8f3f0}
@media (prefers-color-scheme:dark){:root{--bg:#12161d;--card:#1a202b;--ink:#e8ecf3;--muted:#9aa5b8;--line:#2a3242;--accent:#4fc4af;--bad:#ee8470;--soft:#17302c}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
.wrap{max-width:980px;margin:0 auto;padding:24px 16px 64px}
h1{font-size:clamp(1.8rem,4vw,2.5rem);line-height:1.15;margin:.2em 0}
h2{font-size:1.35rem;margin:2.2em 0 .4em}
p{margin:.5em 0}.muted{color:var(--muted)}
.banner{background:var(--soft);border:1px solid var(--line);border-radius:10px;padding:10px 14px;margin:16px 0;font-size:.95rem}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:12px;margin:18px 0}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px}
.card b{display:block;font-size:1.7rem;color:var(--accent)}
.card.bad b{color:var(--bad)}
.panel{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px;margin:12px 0;overflow-x:auto}
table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums;font-size:.95rem}
th,td{padding:6px 10px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}
th:first-child,td:first-child{text-align:left}
.bar{display:grid;grid-template-columns:150px 1fr 120px;gap:10px;align-items:center;margin:8px 0;font-size:.95rem}
.bar i{display:block;height:22px;border-radius:5px;background:var(--accent)}
.bar span:last-child{text-align:right;font-variant-numeric:tabular-nums}
.heat td{padding:4px 6px;text-align:center;font-size:.8rem;min-width:40px}
.heat th{font-size:.8rem}
details{margin-top:10px}summary{cursor:pointer;color:var(--accent);font-weight:600}
pre{overflow:auto;background:var(--bg);border:1px solid var(--line);border-radius:8px;padding:12px;font-size:.82rem;line-height:1.45}
svg text{fill:var(--muted);font-size:11px}
footer{margin-top:48px;color:var(--muted);font-size:.9rem}
a{color:var(--accent)}
@media (max-width:560px){.bar{grid-template-columns:1fr;gap:2px}.bar span:last-child{text-align:left}}
</style>
</head>
<body>
<div class="wrap">
<p class="muted">A portfolio project by <a href="https://hamzamehmood46.github.io">Hamza Mehmood</a></p>
<h1>SaaS product analytics, in plain SQL</h1>
<p class="muted">Where do new users drop off, which channels bring users who pay, how well do cohorts stick, and what happened the week activity fell? Every number below comes from a query you can read.</p>
<div class="banner"><b>About the data:</b> it is synthetic, generated from a fixed seed (no real customers). A bad release is planted in the week of __INCIDENT__ so the analysis has something to find. __USERS__ users, __EVENTS__ events.</div>

<h2>What the data says</h2>
<div class="cards">__CARDS__</div>

<h2>1. Signup funnel</h2>
<p class="muted">A user counts at a step only after reaching the one before it.</p>
<div class="panel">__FUNNEL__</div>
__SQL_FUNNEL__

<h2>2. Which channels bring users who pay?</h2>
<div class="panel">__CHANNELS__</div>
__SQL_CHANNEL__

<h2>3. Do users who invite a teammate upgrade more?</h2>
<div class="panel">__INVITE__</div>
<p class="muted">This is an association. People who invite teammates may already be the more committed ones, so the right next step is an experiment (nudge inviting, then compare), not a conclusion.</p>
__SQL_INVITE__

<h2>4. Weekly active users</h2>
<div class="panel">__WAU__</div>
<p class="muted">The activity drop and rebound lines up with the planted bad release. Signups end on 29 June, so the last week falls for that reason and should not be read as churn.</p>
__SQL_WAU__

<h2>5. Cohort retention</h2>
<p class="muted">Share of each signup-week cohort with at least one session N weeks later. Look for the diagonal dip in the incident week.</p>
<div class="panel">__HEAT__</div>
__SQL_RET__

<footer>
Built with Python and SQLite (CTEs, window functions: FIRST_VALUE, LAG, RANK). <a href="https://github.com/hamzamehmood46/saas-product-analytics-sql">Source and tests on GitHub</a>.
</footer>
</div>
</body>
</html>
"""


def _sql_block(name: str) -> str:
    return f"<details><summary>Show the SQL</summary><pre>{html.escape(db.sql_text(name).strip())}</pre></details>"


def _funnel(rows) -> str:
    top = rows[0][2]
    out = []
    for _, step, users, pct_total, pct_prev in rows:
        width = max(2.0, 100.0 * users / top)
        note = f"{users:,} ({pct_total:.1f}%)"
        out.append(f'<div class="bar"><span>{html.escape(step)}</span><span><i style="width:{width:.1f}%"></i></span><span>{note}</span></div>')
    return "".join(out)


def _table(columns, rows, fmt=None) -> str:
    fmt = fmt or {}
    head = "".join(f"<th>{html.escape(c.replace('_', ' '))}</th>" for c in columns)
    body = ""
    for r in rows:
        cells = "".join(f"<td>{html.escape(fmt.get(c, str)(v))}</td>" for c, v in zip(columns, r))
        body += f"<tr>{cells}</tr>"
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def _bars(rows) -> str:
    peak = max(r[3] for r in rows) or 1
    return "".join(
        f'<div class="bar"><span>{html.escape(seg)}</span><span><i style="width:{max(2.0, 100*rate/peak):.1f}%"></i></span>'
        f"<span>{rate:.1f}% ({up:,} of {n:,})</span></div>"
        for seg, n, up, rate in rows
    )


def _wau_chart(rows) -> str:
    w, h, pad_l, pad_b, pad_t = 900, 260, 46, 40, 16
    peak = max(r[1] for r in rows)
    ceil = (peak // 200 + 1) * 200
    step = (w - pad_l - 10) / (len(rows) - 1)
    y = lambda v: pad_t + (h - pad_b - pad_t) * (1 - v / ceil)
    pts = [(pad_l + i * step, y(r[1])) for i, r in enumerate(rows)]
    line = " ".join(f"{x:.1f},{yy:.1f}" for x, yy in pts)
    grid = "".join(
        f'<line x1="{pad_l}" x2="{w-10}" y1="{y(v):.1f}" y2="{y(v):.1f}" stroke="currentColor" opacity=".12"/>'
        f'<text x="{pad_l-6}" y="{y(v)+4:.1f}" text-anchor="end">{v}</text>'
        for v in range(0, ceil + 1, 200)
    )
    labels = "".join(
        f'<text x="{pts[i][0]:.1f}" y="{h-18}" text-anchor="middle">{rows[i][0][5:]}</text>'
        for i in range(0, len(rows), 4)
    )
    mark = ""
    for i, r in enumerate(rows):
        if r[0] == INCIDENT_WEEK:
            x, yy = pts[i]
            mark = (
                f'<circle cx="{x:.1f}" cy="{yy:.1f}" r="6" fill="var(--bad)"/>'
                f'<text x="{x+10:.1f}" y="{yy-8:.1f}" style="fill:var(--bad);font-weight:600">bad release week ({r[2]:+.1f}%)</text>'
            )
    return (
        f'<svg viewBox="0 0 {w} {h}" width="100%" role="img" aria-label="Weekly active users over time, with a dip in the week of {INCIDENT_WEEK}" style="color:var(--ink)">'
        f'{grid}<polyline points="{line}" fill="none" stroke="var(--accent)" stroke-width="2.5" stroke-linejoin="round"/>{mark}{labels}</svg>'
    )


def _heat(rows) -> str:
    cohorts: dict[str, dict[int, float]] = {}
    sizes: dict[str, int] = {}
    for cohort, size, wk, _, pct in rows:
        cohorts.setdefault(cohort, {})[wk] = pct
        sizes[cohort] = size
    max_wk = max(wk for c in cohorts.values() for wk in c)
    head = "<th>Cohort</th><th>Users</th>" + "".join(f"<th>W{n}</th>" for n in range(0, max_wk + 1, 1) if n <= 12)
    body = ""
    for cohort, cells in cohorts.items():
        tds = ""
        for n in range(0, max_wk + 1):
            if n > 12:
                break
            if n in cells:
                p = cells[n]
                alpha = min(1.0, p / 100)
                tds += f'<td style="background:rgba(15,107,94,{alpha:.2f});color:{"#fff" if alpha > .5 else "inherit"}">{p:.0f}</td>'
            else:
                tds += "<td></td>"
        body += f"<tr><td>{cohort}</td><td>{sizes[cohort]:,}</td>{tds}</tr>"
    return f'<table class="heat"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>'


def _cards(conn: sqlite3.Connection) -> str:
    _, funnel = db.run(conn, "funnel")
    _, channels = db.run(conn, "channel_quality")
    _, invite = db.run(conn, "invite_lift")
    _, wau = db.run(conn, "weekly_active")
    best, worst = channels[0], channels[-1]
    invited, not_invited = invite[0], invite[1]
    incident = next(r for r in wau if r[0] == INCIDENT_WEEK)
    rebound = wau[[r[0] for r in wau].index(INCIDENT_WEEK) + 1]
    items = [
        ("", f"{funnel[1][4]:.0f}%", f"of signups create a workspace; of those, {funnel[2][4]:.0f}% upgrade"),
        ("", f"{best[5]:.1f}%", f"upgrade rate for <b style='display:inline;font-size:inherit;color:inherit'>{best[0]}</b> signups, vs {worst[5]:.1f}% for {worst[0]} ({best[5]/worst[5]:.1f}x)"),
        ("", f"{invited[3] / max(not_invited[3], 0.1):.1f}x", f"upgrade rate for users who invite a teammate ({invited[3]:.0f}% vs {not_invited[3]:.0f}%)"),
        ("bad", f"{incident[2]:+.0f}%", f"weekly active users in the bad-release week, then {rebound[2]:+.0f}% the week after"),
    ]
    return "".join(f'<div class="card {c}"><b>{big}</b><span>{text}</span></div>' for c, big, text in items)


def build(conn: sqlite3.Connection) -> str:
    n_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    n_events = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    _, funnel = db.run(conn, "funnel")
    ch_cols, channels = db.run(conn, "channel_quality")
    _, invite = db.run(conn, "invite_lift")
    _, wau = db.run(conn, "weekly_active")
    _, ret = db.run(conn, "retention")

    pct = lambda v: f"{v:.1f}%"
    channel_table = _table(
        ch_cols[:-1] + [ch_cols[-1]],
        channels,
        {"activation_rate": pct, "upgrade_rate": pct, "users": lambda v: f"{v:,}", "activated": lambda v: f"{v:,}", "upgraded": lambda v: f"{v:,}"},
    )
    page = PAGE
    for key, value in {
        "__INCIDENT__": INCIDENT_WEEK,
        "__USERS__": f"{n_users:,}",
        "__EVENTS__": f"{n_events:,}",
        "__CARDS__": _cards(conn),
        "__FUNNEL__": _funnel(funnel),
        "__CHANNELS__": channel_table,
        "__INVITE__": _bars(invite),
        "__WAU__": _wau_chart(wau),
        "__HEAT__": _heat(ret),
        "__SQL_FUNNEL__": _sql_block("funnel"),
        "__SQL_CHANNEL__": _sql_block("channel_quality"),
        "__SQL_INVITE__": _sql_block("invite_lift"),
        "__SQL_WAU__": _sql_block("weekly_active"),
        "__SQL_RET__": _sql_block("retention"),
    }.items():
        page = page.replace(key, value)
    return page
