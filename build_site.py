"""python build_site.py  ->  site/index.html (and analytics.db for poking at with any SQLite tool)."""
from pathlib import Path

from analytics import db, generate, report

OUT = Path(__file__).parent / "site"


def main() -> None:
    OUT.mkdir(exist_ok=True)
    db_path = OUT.parent / "analytics.db"
    db_path.unlink(missing_ok=True)
    conn = db.connect(str(db_path))
    generate.populate(conn)
    (OUT / "index.html").write_text(report.build(conn), encoding="utf-8")
    conn.close()
    print(f"wrote {OUT / 'index.html'}")


if __name__ == "__main__":
    main()
