import json
import time
from contextlib import contextmanager
import duckdb
from .config import RUNTIME, ROOT

DB_PATH = RUNTIME / 'analyst.duckdb'
LOCK_TIMEOUT = 5.0
LOCK_RETRY_INTERVAL = 0.1


class DatabaseBusyError(RuntimeError):
    """Another process still owns the archive database."""


@contextmanager
def connect():
    deadline = time.monotonic() + LOCK_TIMEOUT
    while True:
        try:
            db = duckdb.connect(str(DB_PATH))
            break
        except duckdb.IOException as exc:
            # Retry only ownership conflicts, never missing/corrupt files.
            if 'Could not set lock on file' not in str(exc):
                raise
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise DatabaseBusyError(
                    'Das Berichtsarchiv wird gerade von einem anderen Programmprozess verwendet. '
                    'Bitte warten Sie, bis dessen Datenbankzugriff abgeschlossen ist, '
                    'und versuchen Sie es erneut.'
                ) from exc
            time.sleep(min(LOCK_RETRY_INTERVAL, remaining))
    try:
        db.execute('CREATE TABLE IF NOT EXISTS reports (id VARCHAR PRIMARY KEY, metadata JSON, pages JSON, observations JSON, themes JSON)')
        db.execute('CREATE TABLE IF NOT EXISTS selections (session_id VARCHAR PRIMARY KEY, report_id VARCHAR, payload JSON)')
        db.execute('CREATE TABLE IF NOT EXISTS results (session_id VARCHAR PRIMARY KEY, payload JSON)')
        if DB_PATH == RUNTIME / 'analyst.duckdb':
            from .example_archive import seed_examples
            seed_examples(db,ROOT)
        yield db
    finally:
        db.close()

def save_report(report):
    with connect() as db:
        db.execute('INSERT OR REPLACE INTO reports VALUES (?, ?, ?, ?, ?)',
                   [report['id'],json.dumps(report['metadata']),json.dumps(report['pages']),
                    json.dumps(report['observations']),json.dumps(report['themes'])])

def load_report(report_id):
    with connect() as db:
        row = db.execute('SELECT * FROM reports WHERE id=?',[report_id]).fetchone()
    if row is None:
        return None
    return dict(id=row[0],metadata=json.loads(row[1]),pages=json.loads(row[2]),
                observations=json.loads(row[3]),themes=json.loads(row[4]))

def list_reports():
    with connect() as db:
        return [(r[0],json.loads(r[1])) for r in db.execute('SELECT id,metadata FROM reports').fetchall()]

def save_selection(session_id, report_id, payload):
    with connect() as db:
        db.execute('INSERT OR REPLACE INTO selections VALUES (?, ?, ?)',
                   [session_id, report_id,json.dumps(payload)])

def save_result(session_id, result):
    with connect() as db:
        db.execute('INSERT OR REPLACE INTO results VALUES (?, ?)',[session_id,json.dumps(result)])
