import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import analytics_db as adb


def test_init_db_creates_all_expected_tables(tmp_path):
    db_path = str(tmp_path / "test.db")
    adb.init_db(db_path)

    conn = sqlite3.connect(db_path)
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    conn.close()

    assert {"pins", "posts", "analytics", "sales"} <= tables


def test_init_db_is_idempotent(tmp_path):
    db_path = str(tmp_path / "test.db")
    adb.init_db(db_path)
    adb.init_db(db_path)  # must not raise on re-init

    conn = adb.connect(db_path)
    conn.execute("INSERT INTO pins (theme, idx) VALUES ('nature', 1)")
    conn.commit()
    row = conn.execute("SELECT theme, idx FROM pins").fetchone()
    conn.close()

    assert row["theme"] == "nature" and row["idx"] == 1


def test_pins_table_rejects_duplicate_theme_idx(tmp_path):
    db_path = str(tmp_path / "test.db")
    adb.init_db(db_path)
    conn = adb.connect(db_path)
    conn.execute("INSERT INTO pins (theme, idx) VALUES ('nature', 1)")
    conn.commit()
    try:
        conn.execute("INSERT INTO pins (theme, idx) VALUES ('nature', 1)")
        conn.commit()
        raised = False
    except sqlite3.IntegrityError:
        raised = True
    finally:
        conn.close()
    assert raised, "UNIQUE(theme, idx) constraint should reject the duplicate"
