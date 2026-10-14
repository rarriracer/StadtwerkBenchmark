"""KI:connect catalogue and observed usage; never invent a remaining quota."""
import hashlib
import json
import re
import threading
from datetime import datetime,timezone,timedelta
from email.utils import parsedate_to_datetime
import httpx
from .model_settings import KICONNECT_API

MODEL_LABELS={
    'mistralai-mistral-small-4-119b':'Mistral Small 4 · 119B',
    'Qwen 3.8 27B':'Qwen 3.8 · 27B',
    'gpt-oss-120b':'OpenAI GPT OSS · 120B',
    'gpt-6-luna':'OpenAI GPT-6 Luna',
    'gpt-6-sol':'OpenAI GPT-6 Sol',
    'gpt-6-astra':'OpenAI GPT-6 Astra',
}
LOCK=threading.RLock()


def _now():return datetime.now(timezone.utc)


def _path():
    from .config import RUNTIME
    return RUNTIME/'kiconnect-account-status.json'


def _read(key):
    try:
        data=json.loads(_path().read_text())
        if data.get('key_hash')==hashlib.sha256(key.encode()).hexdigest():return data
    except (OSError,ValueError,TypeError):pass
    return {'key_hash':hashlib.sha256(key.encode()).hexdigest(),'models':[],'usage':{}}


def _write(data):
    import os
    path=_path();path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix('.tmp')
    fd=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
    with os.fdopen(fd,'w') as f:json.dump(data,f,ensure_ascii=False)
    temporary.replace(path)


def account_status(key,model=''):
    if not key:return {}
    with LOCK:
        data=_read(key)
    return {'models':data.get('models',[]),'models_checked_at':data.get('models_checked_at'),
            **data.get('usage',{}).get(model,{})}


def model_options(key=''):
    models=account_status(key).get('models') or list(MODEL_LABELS)
    return [m for m in models if 'embedding' not in m.lower() and not m.lower().startswith('e5-')]


def model_label(model):return MODEL_LABELS.get(model,model)


def selected_model(model,options):
    if model in options:return model
    clean=lambda s:re.sub(r'[^a-z0-9]','',s.lower().replace('openai',''))
    aliases={'mistralsmall4':'mistralai-mistral-small-4-119b'}
    if aliases.get(clean(model)) in options:return aliases[clean(model)]
    for option in options:
        if clean(model) in (clean(option),clean(model_label(option))):return option
    return options[0] if options else None


def save_catalog(models,key):
    with LOCK:
        state=_read(key);state.update(models=models,models_checked_at=_now().isoformat());_write(state)


def refresh_models(key):
    from .openrouter import _check_status,OpenRouterError
    if not key:raise OpenRouterError('Zuerst den KI:connect-Schlüssel speichern.')
    try:
        response=httpx.get(KICONNECT_API+'/models',headers={'Authorization':'Bearer '+key},timeout=15)
        if response.status_code>=400:record_response(response,key,'')
        _check_status(response)
        data=response.json().get('data')
        if not isinstance(data,list):raise ValueError('Ungültige Modellliste')
        models=[m['id'] for m in data if isinstance(m,dict) and isinstance(m.get('id'),str)]
        if not models:raise ValueError('Leere Modellliste')
    except (httpx.HTTPError,ValueError,AttributeError) as exc:
        raise OpenRouterError('Die KI:connect-Modellliste konnte nicht geladen werden. Gespeicherte Auswahl bleibt verfügbar.') from exc
    save_catalog(models,key)
    return models


def limit_details(response,key=''):
    """Whitelist useful error fields, redact credentials and ignore arbitrary body text."""
    try:error=response.json().get('error',{})
    except (ValueError,AttributeError):error={}
    code=str(error.get('code','')) if isinstance(error,dict) else ''
    kind='quota' if code in ('quota_exceeded','insufficient_quota','usage_limit_exceeded') or response.status_code==402 else 'rate'
    raw=error.get('message','') if isinstance(error,dict) else ''
    message=raw if isinstance(raw,str) else ''
    if key:message=message.replace(key,'[Schlüssel entfernt]')
    message=re.sub(r'Bearer\s+\S+','Bearer [entfernt]',message,flags=re.I)
    message=re.sub(r'\bsk-[A-Za-z0-9_-]+','[Schlüssel entfernt]',message)
    message=' '.join(message.split())[:500]
    retry_at=None
    retry=response.headers.get('retry-after')
    if retry:
        try:
            retry_at=(_now()+timedelta(seconds=max(0,float(retry)))).isoformat()
        except ValueError:
            try:retry_at=parsedate_to_datetime(retry).astimezone(timezone.utc).isoformat()
            except (ValueError,TypeError,OverflowError):pass
    return {'kind':kind,'message':message,'retry_at':retry_at,'observed_at':_now().isoformat(),'http_status':response.status_code}


def record_response(response,key,model,usage=None):
    if not key:return
    headers={k.lower():v for k,v in response.headers.items() if k.lower().startswith(('x-ratelimit-','ratelimit-','x-rate-limit-')) or k.lower()=='retry-after'}
    with LOCK:
        state=_read(key);entry=state.setdefault('usage',{}).setdefault(model,{'requests':0,'prompt_tokens':0,'completion_tokens':0,'since':_now().isoformat()})
        if headers:entry['limit_headers']=headers;entry['limits_checked_at']=_now().isoformat()
        if response.status_code in (402,429):entry['last_limit']=limit_details(response,key)
        elif response.status_code<400 and usage is not None:
            entry.pop('last_limit',None)
            entry['requests']+=1
            if all(isinstance(usage.get(name),(int,float)) for name in ('prompt_tokens','completion_tokens')):
                entry['token_usage_reports']=entry.get('token_usage_reports',0)+1
            for name in ('prompt_tokens','completion_tokens'):
                value=usage.get(name)
                if isinstance(value,(int,float)) and value>=0:entry[name]+=value
            entry['last_success_at']=_now().isoformat()
        _write(state)


def usage_view(key,model):
    selected=account_status(key,model);general=account_status(key,'')
    if general.get('last_limit') and not selected.get('last_limit'):selected['last_limit']=general['last_limit']
    return selected
