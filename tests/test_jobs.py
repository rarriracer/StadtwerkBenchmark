import threading
import pytest
from stadtwerke.jobs import JobRunner


def test_background_progress_duplicate_start_and_result():
    runner=JobRunner()
    entered=threading.Event(); release=threading.Event()
    def operation(callback):
        callback({'stage':'extraction','detail':'PDF-Seite 3','completed':2,'total':10})
        entered.set()
        assert release.wait(3)
        return {'report':{'id':'real-result-shape'}}
    identifier=runner.start(operation)
    assert entered.wait(3)
    assert runner.active()
    snapshot=runner.snapshot(identifier)
    assert snapshot['event']['completed']==2
    snapshot['event']['completed']=999
    assert runner.snapshot(identifier)['event']['completed']==2
    with pytest.raises(RuntimeError,match='bereits'):
        runner.start(lambda _:pytest.fail('duplicate run'))
    release.set()
    # Joining the worker via an event avoids sleep-based timing assumptions.
    with runner._lock:
        pass
    for thread in threading.enumerate():
        if thread.name=='stadtwerke-'+identifier:
            thread.join(3)
    assert not runner.active()
    done=runner.snapshot(identifier)
    assert done['status']=='done' and done['result']['report']['id']=='real-result-shape'


def test_failed_background_job_is_visible_and_next_job_can_start():
    runner=JobRunner()
    def failure(_): raise ValueError('Modell nicht erreichbar')
    identifier=runner.start(failure)
    for thread in threading.enumerate():
        if thread.name=='stadtwerke-'+identifier:
            thread.join(3)
    assert runner.snapshot(identifier)['status']=='error'
    assert runner.snapshot(identifier)['error']=='Modell nicht erreichbar'
    assert not runner.active()
    assert runner.start(lambda _: {}) != identifier


def test_ui_navigation_remains_available_during_analysis(monkeypatch,tmp_path):
    from streamlit.testing.v1 import AppTest
    from stadtwerke import database,workflow
    from pathlib import Path
    source=tmp_path/'report.pdf';source.write_bytes(b'test fixture')
    report={'id':'ui-job-fixture','metadata':{'company':'Testversorger','year':2024,'path':str(source),
        'page_count':1,'analyzed_pages':[],'source_scanned_pages':[1],
        'source_rules_version':workflow.SOURCE_RULES_VERSION},'pages':[],'observations':[],'themes':{}}
    monkeypatch.setattr(database,'DB_PATH',tmp_path/'reports.duckdb')
    database.save_report(report)
    entered=threading.Event();release=threading.Event()
    class Response:
        def json(self): return {'models':[{'name':'qwen2.5:3b'}]}
    monkeypatch.setattr('httpx.get',lambda *a,**k:Response())
    def controlled_invoke(*args,**kwargs):
        kwargs['progress']({'stage':'extraction','detail':'TEST · PDF-Seite 3','completed':2,'total':10})
        entered.set()
        if not release.wait(10): raise TimeoutError('Testworker nicht freigegeben')
        return {'report':report,'status':'Prüfung erforderlich'}
    monkeypatch.setattr(workflow,'invoke',controlled_invoke)
    monkeypatch.setattr('stadtwerke.model_settings.load_settings',lambda:{'provider':'ollama','model':'qwen2.5:3b','api_key':''})
    at=AppTest.from_file(str(Path(__file__).parents[1]/'app.py'),default_timeout=5).run()
    try:
        at.radio[0].set_value('Berichtsarchiv').run()
        next(b for b in at.button if b.label=='Gespeicherten Bericht vollständig neu analysieren').click().run()
        assert entered.wait(2)
        assert not at.exception
        assert at.radio[0].value=='Analyse'
        assert any('TEST' in m.value for m in at.markdown)
        at.radio[0].set_value('Berichtsarchiv').run()
        assert next(b for b in at.button if b.label=='Bericht öffnen · Themen auswählen').disabled
        at.radio[0].set_value('Methodik').run()
        assert not at.exception
        assert any('Methodik und Systemarchitektur' in m.value for m in at.markdown)
    finally:
        release.set()
        for thread in threading.enumerate():
            if thread.name.startswith('stadtwerke-'): thread.join(2)
    at.run()
    assert not at.exception
    assert at.radio[0].value=='Methodik'  # Completion doesn't force navigation.
    at.radio[0].set_value('Analyse').run()
    assert any('Testversorger' in m.value for m in at.markdown)
    assert not at.exception
