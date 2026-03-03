"""
Patient Case History — SQLite-backed storage for past diagnoses.
"""
import sqlite3
import json
import time
from pathlib import Path
from typing import List, Dict, Optional

DB_PATH = Path(__file__).parent.parent.parent / "data" / "patient_history.db"


def _get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't exist."""
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS cases (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id  TEXT NOT NULL DEFAULT 'anonymous',
                timestamp   REAL NOT NULL,
                clinical_note TEXT NOT NULL,
                urgency     TEXT,
                top_diagnosis TEXT,
                confidence  REAL,
                result_json TEXT NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_patient ON cases(patient_id)")
        conn.commit()


def save_case(
    clinical_note: str,
    result: Dict,
    patient_id: str = "anonymous",
) -> int:
    """Persist a completed diagnosis. Returns the new row id."""
    init_db()
    differential = result.get("differential_diagnosis", [])
    top = differential[0] if differential else {}

    with _get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO cases
               (patient_id, timestamp, clinical_note, urgency, top_diagnosis, confidence, result_json)
               VALUES (?,?,?,?,?,?,?)""",
            (
                patient_id or "anonymous",
                time.time(),
                clinical_note[:2000],
                result.get("urgency", "unknown"),
                top.get("disease", ""),
                top.get("confidence", 0),
                json.dumps(result, default=str),
            ),
        )
        conn.commit()
        return cur.lastrowid


def get_patient_history(patient_id: str, limit: int = 20) -> List[Dict]:
    """Return past cases for a patient, newest first."""
    init_db()
    with _get_conn() as conn:
        rows = conn.execute(
            """SELECT id, patient_id, timestamp, clinical_note, urgency,
                      top_diagnosis, confidence
               FROM cases
               WHERE patient_id = ?
               ORDER BY timestamp DESC LIMIT ?""",
            (patient_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def get_case_detail(case_id: int) -> Optional[Dict]:
    """Return full result JSON for a specific case."""
    init_db()
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM cases WHERE id = ?", (case_id,)
        ).fetchone()
    if not row:
        return None
    d = dict(row)
    try:
        d["result"] = json.loads(d.pop("result_json", "{}"))
    except Exception:
        d["result"] = {}
    return d


def get_all_patients() -> List[str]:
    """Return list of all distinct patient IDs."""
    init_db()
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT DISTINCT patient_id FROM cases ORDER BY patient_id"
        ).fetchall()
    return [r["patient_id"] for r in rows]
