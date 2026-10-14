import hashlib
from pathlib import Path
import pytest
import pdfplumber
from stadtwerke import documents, extraction, workflow
from stadtwerke.models import PageExtraction


def test_chunks_cover_tail_and_every_character_without_exceeding_bound():
    text=''.join(f'Zeile {i}: Photovoltaik 1.234 kWp; genaue Originalzahl.\n' for i in range(600))+'TAIL'
    chunks=list(extraction.model_chunks(text))
    assert chunks[0].startswith('Zeile 0:') and chunks[-1].endswith('TAIL')
    assert all(len(c)<=extraction.MODEL_CHUNK_CHARS for c in chunks)
    for line in text.splitlines(): assert any(line in c for c in chunks)


def test_pdf_reopens_batches_closes_each_page_and_preserves_numbers(monkeypatch,tmp_path):
    source=tmp_path/'report.pdf';source.write_bytes(b'fake pdf')
    monkeypatch.setattr(documents,'RUNTIME',tmp_path)
    monkeypatch.setattr(documents,'PDF_BATCH_SIZE',2)
    opened=[];closed=[];progress=[]
    class Count:
        def __enter__(self):return self
        def __exit__(self,*a):pass
        def __len__(self):return 5
    class Page:
        width=600;height=800
        bbox=(0,0,600,800)
        images=[]
        def __init__(self,n):self.page_number=n
        def within_bbox(self,box):return self
        def dedupe_chars(self):return self
        def extract_text(self,**kwargs):return "Originalzahl 1.234 kWp. "*10
        def extract_words(self,**kwargs):return []
        def close(self):closed.append(self.page_number)
    class PDF:
        def __init__(self,ids):self.pages=[Page(n) for n in ids]
        def __enter__(self):return self
        def __exit__(self,*a):pass
    def open_pdf(path,pages):opened.append(pages);return PDF(pages)
    monkeypatch.setattr(documents.pdfium,'PdfDocument',lambda path:Count())
    monkeypatch.setattr(documents.pdfplumber,'open',open_pdf)
    monkeypatch.setattr(documents,'visible_text',lambda page:('Originalzahl 1.234 kWp. '*10,'single_or_table'))
    token=documents.DOCUMENT_PROGRESS.set(progress.append)
    try: digest,pages,_=documents.read_pdf(source)
    finally: documents.DOCUMENT_PROGRESS.reset(token)
    assert digest==hashlib.sha256(b'fake pdf').hexdigest()
    assert opened==[[1,2],[3,4],[5]] and closed==[1,2,3,4,5]
    assert [p['page'] for p in pages]==closed
    assert progress[-1]['completed']==5 and progress[-1]['total']==5


def test_pdf_page_cache_closed_on_extraction_failure(monkeypatch,tmp_path):
    source=tmp_path/'bad.pdf';source.write_bytes(b'bad')
    closed=[]
    class PDF:
        def __enter__(self):return self
        def __exit__(self,*a):pass
        def __len__(self):return 1
        @property
        def pages(self):return [self]
        def close(self):closed.append(True)
    monkeypatch.setattr(documents.pdfium,'PdfDocument',lambda _:PDF())
    monkeypatch.setattr(documents.pdfplumber,'open',lambda *a,**k:PDF())
    monkeypatch.setattr(documents,'visible_text',lambda _:(_ for _ in ()).throw(ValueError('broken page')))
    with pytest.raises(ValueError,match='broken page'):documents.read_pdf(source)
    assert closed==[True]


def test_successful_model_pages_resume_after_interruption_but_force_is_fresh(monkeypatch,tmp_path):
    monkeypatch.setattr(workflow,'RUNTIME',tmp_path)
    monkeypatch.setattr(workflow,'load_report',lambda _:None)
    monkeypatch.setattr(workflow,'save_report',lambda _:None)
    monkeypatch.setattr(workflow,'municipality_context',lambda *a:{})
    monkeypatch.setattr(workflow,'source_facts',lambda *a:[])
    monkeypatch.setattr(workflow,'release_model',lambda *a:True)
    pages=[{'page':i,'text':'Photovoltaik 100 MWp.'} for i in (1,2)]
    monkeypatch.setattr(workflow,'read_pdf',lambda _:('test-resume',pages,{'Photovoltaik':[1,2]}))
    calls=[]
    def extract(page,*a):
        calls.append(page['page'])
        if calls==[1,2]:raise RuntimeError('interrupted')
        return PageExtraction(),[]
    monkeypatch.setattr(workflow,'extract_page',extract)
    state={'provider':'ollama','path':'does-not-exist.pdf','year':2025,'company':'Test'}
    first=workflow.ingest(state)['report']
    assert first['metadata']['extraction_errors'][0]['page']==2
    second=workflow.ingest(state)['report']
    assert calls==[1,2,2] and second['metadata']['resumed_model_pages']==[1]
    workflow.ingest(dict(state,force_reanalyze=True))
    assert calls[-2:]==[1,2]


def test_actual_large_report_visible_text_matches_after_page_cache_release():
    path=Path(__file__).parents[1]/'data/raw/STAWAG_2024.pdf'
    if not path.exists():pytest.skip('Optional 161-page report not present')
    with pdfplumber.open(path,pages=[14,54,140,148]) as pdf:
        for page in pdf.pages:
            before=documents.visible_text(page)
            page.close()
            assert documents.visible_text(page)==before
            page.close()


def test_actual_ollama_request_contains_cpu_and_batch_limits():
    from langchain_ollama import ChatOllama
    from langchain_core.messages import HumanMessage
    llm=ChatOllama(model='test-model',keep_alive='15s')
    bounded=llm.bind(format=PageExtraction.model_json_schema(),options=extraction.model_options("economy"))
    params=llm._chat_params([HumanMessage('A short original excerpt')],**bounded.kwargs)
    assert params['options']['num_gpu']==0
    assert params['options']['num_thread']==1
    assert params['options']['num_batch']==32
    assert params['options']['num_ctx']==4096
    assert params['keep_alive']=='15s'
    assert 'num_gpu' not in extraction.model_options('balanced')


def test_model_classifies_source_ids_without_copying_values_or_quotes(monkeypatch):
    import json
    from langchain_core.messages import AIMessage
    from langchain_core.runnables import RunnableLambda
    evidence='Eigene PV-Anlagen in Deutschland: insgesamt 12,5 MWp am 31.12.2025.'
    text=('Ein langer Berichtstext ohne Kennzahl.\n'*600)+evidence
    calls=[]
    def model(messages,**kwargs):
        content=messages.to_messages()[-1].content
        calls.append((content,kwargs))
        facts=json.loads(content)
        return AIMessage(content=json.dumps({'classifications':[{'id':facts[0]['id'],'metric':'pv_capacity_dc',
            'scope':'own','basis':'stock','portfolio':'total','geography':'DE'}]}))
    monkeypatch.setattr(extraction,'ChatOllama',lambda **k:RunnableLambda(model))
    result,rows=extraction.extract_page({'page':1,'text':text},2025)
    assert len(calls)==1 and calls[0][1]['options']['num_batch']==128
    assert rows[0]['raw_value']=='12,5' and rows[0]['raw_unit']=='MWp'
    assert rows[0]['status']=='validated' and evidence in rows[0]['evidence']
    assert 'raw_value' not in calls[0][1]['format']['$defs']['FactClassification']['properties']


def test_accelerated_default_keeps_small_context_and_two_cpu_threads():
    options=extraction.model_options()
    assert options['num_ctx']==4096 and options['num_batch']==128
    assert options['num_thread']==2 and 'num_gpu' not in options


def test_completed_slow_run_pages_are_reused_by_accelerated_mode(monkeypatch,tmp_path):
    import json
    monkeypatch.setattr(workflow,'RUNTIME',tmp_path)
    monkeypatch.setattr(workflow,'load_report',lambda _:None)
    monkeypatch.setattr(workflow,'save_report',lambda _:None)
    monkeypatch.setattr(workflow,'municipality_context',lambda *a:{})
    monkeypatch.setattr(workflow,'source_facts',lambda *a:[])
    monkeypatch.setattr(workflow,'release_model',lambda *a:True)
    page={'page':1,'text':'Photovoltaik 12 MWp.'}
    key=hashlib.sha256(json.dumps([workflow.MODEL_CACHE_VERSION,'ollama','qwen2.5:3b',__import__('stadtwerke.pdf_agent',fromlist=['fingerprint']).fingerprint(),False,2025,page],sort_keys=True).encode()).hexdigest()
    (tmp_path/('extraction-page-'+key+'.json')).write_text('[]')
    monkeypatch.setattr(workflow,'read_pdf',lambda _:('switch-mode',[page],{'Photovoltaik':[1]}))
    monkeypatch.setattr(workflow,'extract_page',lambda *a:pytest.fail('Completed page was reread'))
    report=workflow.ingest({'provider':'ollama','path':'not-existing.pdf','year':2025,'resource_mode':'balanced'})['report']
    assert report['metadata']['resumed_model_pages']==[1]
