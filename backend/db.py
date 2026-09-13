import sqlite3
from pathlib import Path
from datetime import datetime, timezone

DB = Path(__file__).resolve().parent.parent / "data" / "events.db"

def init_db():
    DB.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB) as con:
        con.execute("""
        CREATE TABLE IF NOT EXISTS analysis_events (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          timestamp TEXT NOT NULL,
          voice_risk REAL NOT NULL,
          contextual_risk REAL NOT NULL,
          risk_level TEXT NOT NULL,
          prediction TEXT NOT NULL,
          recommendation TEXT NOT NULL
        )
        """)

def log_event(result):
    init_db()
    with sqlite3.connect(DB) as con:
        con.execute("""
        INSERT INTO analysis_events
        (timestamp, voice_risk, contextual_risk, risk_level, prediction, recommendation)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (
            datetime.now(timezone.utc).isoformat(),
            result["voice_risk"], result["contextual_risk"],
            result["risk_level"], result["prediction"],
            result["recommendation"]
        ))

def recent_events(limit=10):
    init_db()
    with sqlite3.connect(DB) as con:
        con.row_factory = sqlite3.Row
        rows = con.execute(
            "SELECT * FROM analysis_events ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
