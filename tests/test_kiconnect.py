import json
import httpx
import pytest
from stadtwerke import model_settings,openrouter,pdf_agent,workflow
from stadtwerke.models import PageExtraction


@pytest.fixture(autouse=True)
def isolated_account_status(tmp_path,monkeypatch):
    from stadtwerke import config
    monkeypatch.setattr(config,'RUNTIME',tmp_path)


def test_provider_switch_preserves_separate_keys_and_models(tmp_path,monkeypatch):
    monkeypatch.setattr(model_settings,'SETTINGS_PATH',tmp_path/'settings.json')
    for name in ('STADTWERKE_PROVIDER','STADTWERKE_MODEL','OPENROUTER_API_KEY','KICONNECT_API_KEY'):
        monkeypatch.delenv(name,raising=False)
    model_settings.save_settings('openrouter',model_settings.CLOUD_MODEL,'router-secret')
    model_settings.save_settings('kiconnect','Campus Model','campus-secret')
    assert model_settings.save_settings('openrouter',model_settings.CLOUD_MODEL)['api_key']=='router-secret'
    settings=model_settings.save_settings('kiconnect','Campus Model')
    assert settings['api_key']=='campus-secret'
    assert settings['providers']['openrouter']['api_key']=='router-secret'
    monkeypatch.setenv('OPENROUTER_API_KEY','wrong-provider-key')
    assert model_settings.load_settings()['api_key']=='campus-secret'


@pytest.mark.parametrize('vision',[False,True])
def test_kiconnect_request_has_shared_rules_and_no_router_parameters(monkeypatch,vision):
    settings={'provider':'kiconnect','model':'Campus Model','api_key':'campus-secret','vision':vision}
    monkeypatch.setattr(openrouter,'load_settings',lambda:settings)
    monkeypatch.setattr(openrouter,'page_images',lambda *a:['data:image/png;base64,page'] if vision else pytest.fail('Text model must not render images'))
    captured={}
    def post(url,**kw):
        captured.update(url=url,**kw)
        return httpx.Response(200,json={'choices':[{'message':{'content':'{"observations":[]}'},'finish_reason':'stop'}]})
    monkeypatch.setattr(openrouter.httpx,'post',post)
    openrouter.extract_page({'page':1,'text':'Keine Kennzahlen'},2024,'x.pdf','Campus Model')
    payload=captured['json']
    assert captured['url']==model_settings.KICONNECT_API+'/chat/completions'
    assert captured['headers']=={'Authorization':'Bearer campus-secret'}
    assert 'provider' not in payload
    assert payload['response_format']=={'type':'json_object'}
    assert pdf_agent.rules() in payload['messages'][0]['content']
    assert len(payload['messages'][1]['content'])==(2 if vision else 1)


def test_connection_checks_model_without_paid_generation(tmp_path,monkeypatch):
    from stadtwerke import config
    monkeypatch.setattr(config,'RUNTIME',tmp_path)
    settings={'provider':'kiconnect','model':'Campus Model','api_key':'campus-secret'}
    monkeypatch.setattr(openrouter,'load_settings',lambda:settings)
    def get(url,**kw):
        assert url==model_settings.KICONNECT_API+'/models'
        return httpx.Response(200,json={'data':[{'id':'Campus Model'}]})
    monkeypatch.setattr(openrouter.httpx,'get',get)
    monkeypatch.setattr(openrouter.httpx,'post',lambda *a,**kw:pytest.fail('No paid call'))
    assert openrouter.verify_connection()['models']==['Campus Model']
    assert openrouter.connection_status(settings)['valid'] is True
    assert not (tmp_path/'openrouter-connection.json').exists()
    assert 'campus-secret' not in (tmp_path/'kiconnect-connection.json').read_text()
    settings['model']='Unavailable'
    assert openrouter.connection_status(settings)=={}
    with pytest.raises(openrouter.OpenRouterConfigurationError):openrouter.verify_connection()


def test_changed_rules_invalidate_page_cache_and_are_recorded(tmp_path,monkeypatch):
    path=tmp_path/'rules.md';path.write_text('Originalbelege verwenden')
    monkeypatch.setattr(pdf_agent,'RULES_PATH',path)
    monkeypatch.setattr(workflow,'RUNTIME',tmp_path)
    monkeypatch.setattr(workflow,'load_report',lambda *a:None)
    monkeypatch.setattr(workflow,'save_report',lambda *a:None)
    monkeypatch.setattr(workflow,'read_pdf',lambda *a:('rule-test',[{'page':1,'text':'Berichtsjahr 2024'}],{}))
    monkeypatch.setattr(workflow,'source_facts',lambda *a:[])
    monkeypatch.setattr(workflow,'report_location',lambda *a:{})
    monkeypatch.setattr(model_settings,'load_settings',lambda:{'provider':'kiconnect','model':'Campus Model','api_key':'secret'})
    calls=[]
    monkeypatch.setattr(openrouter,'extract_page',lambda *a:(calls.append(1) or PageExtraction(),[]))
    state={'path':'not-existing.pdf','year':2024}
    first=workflow.ingest(state)['report']
    workflow.ingest(state)
    assert len(calls)==1
    path.write_text('Neue strengere Belegregeln')
    second=workflow.ingest(state)['report']
    assert len(calls)==2
    assert first['metadata']['pdf_agent_sha256']!=second['metadata']['pdf_agent_sha256']
    assert second['metadata']['model_resource_profile']['mode']=='cloud_text'
    assert openrouter.PROVIDER.get() is None
    assert 'secret' not in json.dumps(second)


def test_model_change_color_uses_aligned_period_and_context_stays_neutral():
    from stadtwerke.reporting import assessment,POSITIVE,NEGATIVE
    item={'observation':{'unit':'MWh'},'reference':{'kind':'flow'},'calculation':{'company_change':-50,'expected':200}}
    assert assessment(item)['color']==NEGATIVE
    assert assessment(item)['change']=='−50,00 MWh'
    item['calculation']['company_change']=50
    assert assessment(item)['color']==POSITIVE
    item['reference']['kind']='context'
    assert assessment(item) is None


def test_live_catalog_uses_api_ids_and_filters_embeddings(monkeypatch):
    from stadtwerke import kiconnect
    models=[{'id':m} for m in kiconnect.MODEL_LABELS]+[{'id':'e5-mistral-7b-instruct'},{'id':'qwen3-embedding-8b'}]
    monkeypatch.setattr(kiconnect.httpx,'get',lambda *a,**kw:httpx.Response(200,json={'data':models}))
    kiconnect.refresh_models('key')
    options=kiconnect.model_options('key')
    assert options==list(kiconnect.MODEL_LABELS)
    assert kiconnect.selected_model('OpenAI GPT-6 Sol',options)=='gpt-6-sol'
    assert kiconnect.model_options('other-key')==list(kiconnect.MODEL_LABELS)


def test_quota_details_survive_connection_check_and_never_leak_key(monkeypatch):
    from stadtwerke import kiconnect
    key='private-key'
    response=httpx.Response(429,headers={'Retry-After':'60','x-ratelimit-remaining-tokens':'0'},json={'error':{'code':'quota_exceeded','message':'Limit reached for '+key}})
    kiconnect.record_response(response,key,'gpt-6-sol')
    status=kiconnect.usage_view(key,'gpt-6-sol')
    assert status['last_limit']['kind']=='quota'
    assert status['last_limit']['retry_at']
    assert status['limit_headers']['x-ratelimit-remaining-tokens']=='0'
    assert key not in kiconnect._path().read_text()
    kiconnect.record_response(httpx.Response(200),key,'')
    assert kiconnect.usage_view(key,'gpt-6-sol')['last_limit']['kind']=='quota'
    assert not kiconnect.usage_view(key,'gpt-6-luna').get('last_limit')
    assert not kiconnect.usage_view('changed-key','gpt-6-sol').get('last_limit')
    kiconnect.record_response(httpx.Response(200),key,'gpt-6-sol',usage={'prompt_tokens':12,'completion_tokens':8})
    status=kiconnect.usage_view(key,'gpt-6-sol')
    assert not status.get('last_limit')
    assert status['requests']==1 and status['prompt_tokens']+status['completion_tokens']==20


def test_429_returns_specific_quota_and_retry_message(monkeypatch):
    response=httpx.Response(429,headers={'Retry-After':'60'},json={'error':{'code':'quota_exceeded','message':'The usage limit has been exceeded.'}})
    with pytest.raises(openrouter.OpenRouterConfigurationError,match='Nutzungskontingent ausgeschöpft.*Erneut möglich'):
        openrouter._check_status(response)


def test_ui_model_selection_saves_id_and_shows_limit_without_name_input():
    from pathlib import Path
    from streamlit.testing.v1 import AppTest
    from stadtwerke import kiconnect
    model_settings.save_settings('kiconnect','mistralai-mistral-small-4-119b','test-key')
    app=AppTest.from_file(str(Path(__file__).parents[1]/'app.py'),default_timeout=10).run()
    assert not app.exception
    select=app.selectbox(key='kiconnect-model-choice')
    assert select.value=='mistralai-mistral-small-4-119b'
    assert 'OpenAI GPT-6 Sol' in select.options
    assert not any(t.label=='KI:connect-Modellname' for t in app.text_input)
    select.set_value('gpt-6-sol')
    next(b for b in app.button if b.label=='Einstellungen speichern').click().run()
    assert not app.exception
    assert model_settings.load_settings()['model']=='gpt-6-sol'
    kiconnect.record_response(httpx.Response(429,json={'error':{'code':'quota_exceeded','message':'The usage limit has been exceeded.'}}),'test-key','gpt-6-sol')
    app.run()
    assert not app.exception
    assert any('Nutzungskontingent ausgeschöpft' in w.value for w in app.warning)
    assert any('von der API nicht gemeldet' in c.value for c in app.caption)
