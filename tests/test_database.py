import subprocess
import sys
import threading

import duckdb
import pytest

from stadtwerke import database


@pytest.fixture
def locked_database(monkeypatch, tmp_path):
    path = tmp_path / 'archive.duckdb'
    monkeypatch.setattr(database, 'DB_PATH', path)
    report = dict(id='dresden', metadata={'company': 'Dresden', 'year': 2024},
                  pages=[], observations=[], themes={})
    database.save_report(report)
    process = subprocess.Popen(
        [sys.executable, '-u', '-c',
         'import duckdb, sys; db = duckdb.connect(sys.argv[1]); '
         'print("locked", flush=True); sys.stdin.readline(); db.close()', str(path)],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        assert process.stdout.readline().strip() == 'locked'
        yield process, report
    finally:
        if process.poll() is None:
            process.communicate('\n', timeout=5)


def test_archive_retries_until_other_process_releases_database(locked_database, monkeypatch):
    process, report = locked_database
    original = duckdb.connect
    conflicts = []

    def tracked_connect(*args, **kwargs):
        try:
            return original(*args, **kwargs)
        except duckdb.IOException:
            conflicts.append(True)
            raise

    monkeypatch.setattr(database.duckdb, 'connect', tracked_connect)
    release = threading.Timer(.3, lambda: process.communicate('\n', timeout=5))
    release.start()
    try:
        assert database.load_report('dresden') == report
        assert conflicts
    finally:
        release.join(5)


def test_persistent_lock_has_actionable_error_and_recovers(locked_database, monkeypatch):
    process, report = locked_database
    monkeypatch.setattr(database, 'LOCK_TIMEOUT', .1)
    with pytest.raises(database.DatabaseBusyError, match='anderen Programmprozess'):
        database.list_reports()
    process.communicate('\n', timeout=5)
    assert database.list_reports() == [('dresden', report['metadata'])]


def test_other_io_errors_are_not_retried(monkeypatch):
    def broken_connect(*args, **kwargs):
        raise duckdb.IOException('Cannot open file: Permission denied')
    monkeypatch.setattr(database.duckdb, 'connect', broken_connect)
    with pytest.raises(duckdb.IOException, match='Permission denied'):
        database.list_reports()


@pytest.mark.parametrize('blocked_operation', ['list_reports', 'load_report'])
def test_archive_displays_busy_notice_instead_of_exception(monkeypatch, blocked_operation):
    from pathlib import Path
    from streamlit.testing.v1 import AppTest

    def blocked(*args):
        raise database.DatabaseBusyError('Archiv vorübergehend gesperrt')

    monkeypatch.setattr(database, 'list_reports', lambda: [('dresden', {'company': 'Dresden', 'year': 2024})])
    monkeypatch.setattr(database, blocked_operation, blocked)
    at = AppTest.from_file(str(Path(__file__).parents[1] / 'app.py')).run()
    at.radio[0].set_value('Berichtsarchiv').run()
    assert not at.exception
    assert at.warning[0].value == 'Archiv vorübergehend gesperrt'
    assert any(button.label == 'Archiv erneut laden' for button in at.button)
