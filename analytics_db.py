#!/usr/bin/env python3
"""Local SQLite cache over post_log.jsonl and the out/ manifests, so posting
history and the product catalog are actually queryable instead of grepped by
hand. Read-only against Pinterest/Gumroad -- never posts or uploads anything.
"""
import argparse, glob, json, os, sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(HERE, "pinforge.db")
POST_LOG = os.path.join(HERE, "post_log.jsonl")
OUT_DIR = os.path.join(HERE, "out")

SCHEMA = """
CREATE TABLE IF NOT EXISTS pins (
    id              INTEGER PRIMARY KEY,
    theme           TEXT NOT NULL,
    idx             INTEGER NOT NULL,
    image           TEXT,
    headline        TEXT,
    title           TEXT,
    description     TEXT,
    posted          INTEGER DEFAULT 0,
    UNIQUE(theme, idx)
);

CREATE TABLE IF NOT EXISTS posts (
    id              INTEGER PRIMARY KEY,
    ts              TEXT NOT NULL,
    theme           TEXT NOT NULL,
    idx             INTEGER NOT NULL,
    title           TEXT,
    link            TEXT,
    board           TEXT,
    publish         TEXT,
    verified        TEXT,
    pinterest_pin_id TEXT,
    pin_url         TEXT,
    UNIQUE(ts, theme, idx)
);

CREATE TABLE IF NOT EXISTS analytics (
    id              INTEGER PRIMARY KEY,
    pinterest_pin_id TEXT NOT NULL,
    captured_at     TEXT NOT NULL,
    impressions     INTEGER,
    saves           INTEGER,
    pin_clicks      INTEGER,
    outbound_clicks INTEGER,
    UNIQUE(pinterest_pin_id, captured_at)
);

CREATE TABLE IF NOT EXISTS sales (
    id              INTEGER PRIMARY KEY,
    product         TEXT,
    gumroad_sale_id TEXT,
    amount_usd      REAL,
    currency        TEXT,
    sold_at         TEXT,
    referrer        TEXT,
    UNIQUE(gumroad_sale_id)
);

CREATE INDEX IF NOT EXISTS idx_posts_theme ON posts(theme);
CREATE INDEX IF NOT EXISTS idx_analytics_pin ON analytics(pinterest_pin_id);
"""


def connect(db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path=DB_PATH):
    conn = connect(db_path)
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()
    return db_path


def import_post_log(db_path=DB_PATH, jsonl_path=POST_LOG):
    """Read post_log.jsonl (read-only) into the posts table. Idempotent."""
    if not os.path.exists(jsonl_path):
        return 0
    conn = connect(db_path)
    n = 0
    with open(jsonl_path) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            if "theme" not in rec or "idx" not in rec:
                continue  # skip _correction / annotation rows
            cur = conn.execute(
                """INSERT OR IGNORE INTO posts
                   (ts, theme, idx, title, link, board, publish, verified,
                    pinterest_pin_id, pin_url)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (rec.get("ts"), rec["theme"], rec["idx"], rec.get("title"),
                 rec.get("link"), rec.get("board"), rec.get("publish"),
                 rec.get("verified"), rec.get("pin_id"), rec.get("pin_url")),
            )
            n += cur.rowcount
    conn.commit()
    conn.close()
    return n


def import_pins(db_path=DB_PATH, out_dir=OUT_DIR):
    """Read out/*/manifest.json (read-only) into the pins catalog. Idempotent."""
    conn = connect(db_path)
    n = 0
    for mpath in sorted(glob.glob(os.path.join(out_dir, "*", "manifest.json"))):
        manifest = json.load(open(mpath))
        theme = manifest.get("theme", os.path.basename(os.path.dirname(mpath)))
        for idx, pin in enumerate(manifest.get("pins", [])):
            cur = conn.execute(
                """INSERT OR IGNORE INTO pins
                   (theme, idx, image, headline, title, description, posted)
                   VALUES (?,?,?,?,?,?,?)""",
                (theme, idx, pin.get("image"), pin.get("headline_on_image"),
                 pin.get("title"), pin.get("description"),
                 1 if pin.get("posted") else 0),
            )
            n += cur.rowcount
    conn.commit()
    conn.close()
    return n


def summary(db_path=DB_PATH):
    conn = connect(db_path)
    rows = {}
    for table in ("pins", "posts", "analytics", "sales"):
        rows[table] = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    conn.close()
    return rows


def main():
    ap = argparse.ArgumentParser(description="PinForge analytics store (internal)")
    ap.add_argument("cmd", choices=["init", "import-log", "import-pins", "summary"])
    ap.add_argument("--db", default=DB_PATH)
    a = ap.parse_args()

    if a.cmd == "init":
        print(f"schema ready -> {init_db(a.db)}")
    elif a.cmd == "import-log":
        init_db(a.db)
        print(f"imported {import_post_log(a.db)} new post rows")
    elif a.cmd == "import-pins":
        init_db(a.db)
        print(f"imported {import_pins(a.db)} new pin rows")
    elif a.cmd == "summary":
        for table, count in summary(a.db).items():
            print(f"{table:10} {count}")


if __name__ == "__main__":
    main()
