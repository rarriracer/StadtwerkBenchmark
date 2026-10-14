import httpx
from stadtwerke.review import review_groups
from stadtwerke import model_runtime, workflow


def row(**changes):
    return dict(status='needs_review',evidence_status='verified',year=2024,metric='pv_capacity_dc',
        value=90,unit='MWp',basis='stock',portfolio='total',scope='group',geography='unknown') | changes


def test_review_queue_contains_only_actionable_source_backed_candidates():
    report={'metadata':{'year':2024},'observations':[
        row(),row(evidence_status='not_verified'),row(year=2025),row(unit='MWh'),
        row(value=None),row(portfolio='project'),row(metric='revenue'),row(status='validated'),
        row(status='superseded')]}
    groups=review_groups(report)
    assert len(groups['targeted'])==1
    assert len(groups['rejected'])==4
    assert len(groups['other'])==2
    assert len(groups['accepted'])==1


def test_release_model_unloads_without_deleting_files(monkeypatch):
    calls=[]
    class Response:
        def raise_for_status(self): pass
    monkeypatch.setattr(model_runtime.httpx,'post',lambda url,**kwargs:calls.append((url,kwargs)) or Response())
    assert model_runtime.release_model('test-model')
    assert calls[0][1]['json']=={'model':'test-model','keep_alive':0}
    def offline(*a,**k): raise httpx.ConnectError('offline')
    monkeypatch.setattr(model_runtime.httpx,'post',offline)
    assert not model_runtime.release_model('test-model')


def test_ingest_releases_model_even_if_every_model_page_fails(monkeypatch):
    released=[]
    report_page={'page':1,'text':'A test page'}
    monkeypatch.setattr(workflow,'read_pdf',lambda _:('new-test-report',[report_page],{}))
    monkeypatch.setattr(workflow,'load_report',lambda _:None)
    monkeypatch.setattr(workflow,'source_facts',lambda *a:[])
    monkeypatch.setattr(workflow,'municipality_context',lambda *a:{'country':'unknown'})
    monkeypatch.setattr(workflow,'relevant_pages',lambda *a:[report_page])
    def failing_page(*a): raise RuntimeError('model failed')
    monkeypatch.setattr(workflow,'extract_page',failing_page)
    monkeypatch.setattr(workflow,'release_model',lambda model:released.append(model))
    monkeypatch.setattr(workflow,'save_report',lambda _:None)
    result=workflow.ingest({'provider':'ollama','path':'nonexistent-test.pdf','year':2024,'model':'test-model'})
    assert released==['test-model']
    assert result['report']['metadata']['extraction_errors'][0]['error']=='model failed'
