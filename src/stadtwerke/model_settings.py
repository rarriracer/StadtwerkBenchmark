"""Local model configuration; credentials never enter report/workflow payloads."""
import json,os
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
SETTINGS_PATH=ROOT/'data/runtime/model-settings.json'
CLOUD_MODEL='qwen/qwen3-vl-235b-a22b-instruct'
KICONNECT_API='https://chat.kiconnect.nrw/api/v1'
PROVIDER_LABELS={'openrouter':'OpenRouter','kiconnect':'KI:connect NRW','ollama':'Ollama · lokal'}


def load_settings():
    saved=json.loads(SETTINGS_PATH.read_text()) if SETTINGS_PATH.exists() else {}
    settings={'provider':'openrouter','model':CLOUD_MODEL,'api_key':'','vision':False,**saved}
    providers=dict(saved.get('providers',{}))
    if saved.get('provider') in ('openrouter','kiconnect'):
        providers.setdefault(saved['provider'],{k:saved[k] for k in ('model','api_key','vision') if k in saved})
    provider=os.environ.get('STADTWERKE_PROVIDER',settings['provider'])
    if provider!=settings['provider']:
        settings.update(model=CLOUD_MODEL if provider=='openrouter' else '',api_key='',vision=False)
        settings.update(providers.get(provider,{}))
    settings['provider']=provider;settings['providers']=providers
    if os.environ.get('STADTWERKE_MODEL'):settings['model']=os.environ['STADTWERKE_MODEL']
    env_key={'openrouter':'OPENROUTER_API_KEY','kiconnect':'KICONNECT_API_KEY'}.get(provider)
    if env_key and os.environ.get(env_key):settings['api_key']=os.environ[env_key]
    if provider=='openrouter' and not settings.get('model','').startswith(('qwen/','google/','deepseek/','anthropic/')):
        settings['model']=CLOUD_MODEL
    return settings


def save_settings(provider,model,api_key='',vision=False):
    if provider not in PROVIDER_LABELS:raise ValueError('Unbekannter Modellanbieter')
    if not model.strip():raise ValueError('Modellname fehlt')
    previous=load_settings();providers=dict(previous.get('providers',{}))
    existing=providers.get(provider,{})
    key=api_key.strip() or existing.get('api_key','')
    if provider==previous['provider']:key=api_key.strip() or previous.get('api_key','')
    value={'provider':provider,'model':model.strip(),'api_key':key,'vision':bool(vision)}
    if provider!='ollama':providers[provider]={k:value[k] for k in ('model','api_key','vision')}
    value['providers']=providers
    SETTINGS_PATH.parent.mkdir(parents=True,exist_ok=True)
    temp=SETTINGS_PATH.with_suffix('.tmp')
    fd=os.open(temp,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
    with os.fdopen(fd,'w') as f:json.dump(value,f)
    temp.replace(SETTINGS_PATH)
    if os.name!='nt':SETTINGS_PATH.chmod(0o600)
    return value
