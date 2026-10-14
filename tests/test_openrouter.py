import json,os
from pathlib import Path
import httpx,pytest
from stadtwerke import openrouter,model_settings,workflow
from stadtwerke.models import PageExtraction

PAGE={'page':1,'text':'Im Jahr 2024 betrug der Stromabsatz insgesamt 347 GWh.'}
CANDIDATE={'metric':'electricity_sales_total','raw_value':'347','raw_unit':'GWh','year':2024,
           'evidence':PAGE['text'],'scope':'group','basis':'annual_sales','portfolio':'total','entity':'','geography':'unknown','notes':''}


def test_key_is_local_private_and_not_exposed_by_connection_errors(tmp_path,monkeypatch):
    monkeypatch.setattr(model_settings,'SETTINGS_PATH',tmp_path/'model-settings.json')
    monkeypatch.delenv('OPENROUTER_API_KEY',raising=False)
    settings=model_settings.save_settings('openrouter',model_settings.CLOUD_MODEL,'test-secret')
    assert settings['api_key']=='test-secret'
    assert model_settings.save_settings('openrouter',model_settings.CLOUD_MODEL)['api_key']=='test-secret'
    if os.name!='nt':assert model_settings.SETTINGS_PATH.stat().st_mode & 0o777==0o600
    response=httpx.Response(401,json={'error':{'message':'test-secret'}})
    with pytest.raises(openrouter.OpenRouterConfigurationError) as error:openrouter._check_status(response)
    assert 'test-secret' not in str(error.value)


def test_cloud_sends_original_images_and_schema_and_records_actual_usage(monkeypatch):
    monkeypatch.setattr(openrouter,'page_images',lambda *args:['data:image/png;base64,original-page'])
    captured={}
    def post(url,**kwargs):
        captured.update(url=url,**kwargs)
        return httpx.Response(200,json={'id':'generation-1','model':model_settings.CLOUD_MODEL,
            'choices':[{'finish_reason':'stop','message':{'content':json.dumps({'company':'Test','report_year':2024,'observations':[CANDIDATE]})}}],
            'usage':{'prompt_tokens':1234,'completion_tokens':456,'cost':.001}})
    monkeypatch.setattr(openrouter.httpx,'post',post)
    ledger=[];a=openrouter.KEY.set('test-secret');b=openrouter.USAGE.set(ledger)
    try:_,rows=openrouter.extract_page(PAGE,2024,'test.pdf',model_settings.CLOUD_MODEL)
    finally:openrouter.KEY.reset(a);openrouter.USAGE.reset(b)
    assert rows[0]['status']=='validated' and rows[0]['value']==347000
    assert captured['json']['messages'][1]['content'][1]['type']=='image_url'
    assert captured['json']['provider']['require_parameters'] is True
    assert captured['json']['response_format']['json_schema']['strict'] is True
    assert ledger[0]['cost_usd']==.001
    assert 'test-secret' not in json.dumps(rows+ledger)


def test_visual_model_cannot_invent_number_and_truncated_pages_are_errors(monkeypatch):
    monkeypatch.setattr(openrouter,'page_images',lambda *args:[])
    candidate=CANDIDATE|{'raw_value':'999'}
    payload={'choices':[{'finish_reason':'stop','message':{'content':json.dumps({'observations':[candidate]})}}]}
    monkeypatch.setattr(openrouter.httpx,'post',lambda *args,**kwargs:httpx.Response(200,json=payload))
    token=openrouter.KEY.set('test-secret')
    try:
        _,rows=openrouter.extract_page(PAGE,2024,'test.pdf',model_settings.CLOUD_MODEL)
        assert rows[0]['status']=='needs_review' and rows[0]['value'] is None
        payload['choices'][0]['finish_reason']='length'
        with pytest.raises(openrouter.OpenRouterError,match='abgeschnitten'):openrouter.extract_page(PAGE,2024,'test.pdf',model_settings.CLOUD_MODEL)
    finally:openrouter.KEY.reset(token)


@pytest.mark.parametrize('status',[401,402,403,429])
def test_auth_credit_and_rate_errors_stop_further_paid_requests(status):
    with pytest.raises(openrouter.OpenRouterConfigurationError):openrouter._check_status(httpx.Response(status))


def test_cloud_workflow_reads_all_pages_without_local_model_and_without_key_in_archive(tmp_path,monkeypatch):
    pages=[PAGE|{'page':i} for i in range(1,4)]
    monkeypatch.setattr(workflow,'RUNTIME',tmp_path)
    monkeypatch.setattr(workflow,'read_pdf',lambda path:('new-test',pages,{}))
    monkeypatch.setattr(workflow,'load_report',lambda report_id:None)
    monkeypatch.setattr(workflow,'report_location',lambda *a:{})
    monkeypatch.setattr(model_settings,'load_settings',lambda:{'provider':'openrouter','model':model_settings.CLOUD_MODEL,'api_key':'test-secret'})
    called=[];saved=[]
    monkeypatch.setattr(openrouter,'extract_page',lambda page,*args:(called.append(page['page']) or PageExtraction(),[]))
    monkeypatch.setattr(workflow,'release_model',lambda *a:pytest.fail('Cloud must not start/stop Ollama'))
    monkeypatch.setattr(workflow,'save_report',saved.append)
    result=workflow.ingest({'path':str(tmp_path/'new.pdf'),'company':'Test','year':2024})
    assert called==[1,2,3] and result['report']['metadata']['provider']=='openrouter'
    assert 'test-secret' not in json.dumps(saved)
    assert openrouter.KEY.get() is None


def test_launcher_cloud_skips_ollama(tmp_path,monkeypatch):
    import importlib.util
    path=Path(__file__).parents[1]/'scripts/start_app.py'
    spec=importlib.util.spec_from_file_location('cloud_launcher',path);launcher=importlib.util.module_from_spec(spec);spec.loader.exec_module(launcher)
    monkeypatch.setattr(launcher,'ROOT',tmp_path)
    config=tmp_path/'data/runtime/model-settings.json';config.parent.mkdir(parents=True);config.write_text('{"provider":"openrouter"}')
    assert launcher.model_provider()=='openrouter'
    monkeypatch.setattr(launcher,'reachable',lambda url:True)
    monkeypatch.setattr(launcher,'ensure_ollama',lambda *a:pytest.fail('Ollama not required'))
    monkeypatch.setattr(launcher.webbrowser,'open',lambda url:True)
    assert launcher.main()==0


def test_switching_to_cloud_does_not_reuse_old_local_report(tmp_path,monkeypatch):
    path=tmp_path/'report.pdf';path.write_bytes(b'local-source')
    old={'id':'old-report','metadata':{'year':2024,'model':'qwen2.5:3b','provider':'ollama','extraction_version':workflow.EXTRACTION_VERSION},'observations':[],'pages':[],'themes':{}}
    monkeypatch.setattr(workflow,'RUNTIME',tmp_path)
    monkeypatch.setattr(workflow,'load_report',lambda report_id:old)
    monkeypatch.setattr(workflow,'read_pdf',lambda path:('new-report',[PAGE],{}))
    monkeypatch.setattr(workflow,'report_location',lambda *args:{})
    monkeypatch.setattr(workflow,'save_report',lambda report:None)
    monkeypatch.setattr(model_settings,'load_settings',lambda:{'provider':'openrouter','model':model_settings.CLOUD_MODEL,'api_key':'test-secret'})
    called=[]
    monkeypatch.setattr(openrouter,'extract_page',lambda page,*args:(called.append(page['page']) or PageExtraction(),[]))
    result=workflow.ingest({'path':str(path),'year':2024,'company':'Test'})
    assert called==[1] and result['report']['metadata']['provider']=='openrouter'


def test_key_check_is_read_only_without_model_call(monkeypatch):
    token=openrouter.KEY.set('test-secret')
    monkeypatch.setattr(openrouter.httpx,'get',lambda url,**kwargs:httpx.Response(200,json={'data':{'limit_remaining':5,'usage':0}}) if url.endswith('/key') else pytest.fail('Wrong endpoint'))
    monkeypatch.setattr(openrouter.httpx,'post',lambda *args,**kwargs:pytest.fail('No paid request during key check'))
    try:assert openrouter.check_connection()['limit_remaining']==5
    finally:openrouter.KEY.reset(token)


def test_connection_status_is_bound_to_key_and_handles_rejection(tmp_path,monkeypatch):
    from stadtwerke import config
    monkeypatch.setattr(config,'RUNTIME',tmp_path)
    settings={'provider':'openrouter','model':model_settings.CLOUD_MODEL,'api_key':'test-secret'}
    monkeypatch.setattr(openrouter,'load_settings',lambda:settings)
    assert openrouter.connection_status()=={}
    def rejected():raise openrouter.OpenRouterConfigurationError('Schlüssel ungültig')
    monkeypatch.setattr(openrouter,'check_connection',rejected)
    with pytest.raises(openrouter.OpenRouterConfigurationError):openrouter.verify_connection()
    assert openrouter.connection_status()['valid'] is False
    assert 'test-secret' not in (tmp_path/'openrouter-connection.json').read_text()
    settings['api_key']='new-test-secret'
    assert openrouter.connection_status()=={}
    monkeypatch.setattr(openrouter,'check_connection',lambda:{'limit_remaining':3})
    assert openrouter.verify_connection()['limit_remaining']==3
    assert openrouter.connection_status()['valid'] is True


def test_invalid_schema_reports_field_path_without_echoing_model_input(monkeypatch):
    monkeypatch.setattr(openrouter,'page_images',lambda *a:[])
    invalid=CANDIDATE|{'metric':'unrecognized-private-model-content'}
    payload={'choices':[{'finish_reason':'stop','message':{'content':json.dumps({'observations':[invalid]})}}]}
    monkeypatch.setattr(openrouter.httpx,'post',lambda *a,**kw:httpx.Response(200,json=payload))
    key=openrouter.KEY.set('test-secret')
    try:
        with pytest.raises(openrouter.OpenRouterError) as error:
            openrouter.extract_page(PAGE,2024,'unused.pdf',model_settings.CLOUD_MODEL)
        assert 'observations.0.metric: literal_error' in str(error.value)
        assert 'unrecognized-private-model-content' not in str(error.value)
    finally:openrouter.KEY.reset(key)
