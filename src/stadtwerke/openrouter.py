"""Visual PDF extraction through OpenRouter with literal source validation."""
import base64,io,json
from contextvars import ContextVar
from datetime import datetime,timezone
import httpx,pypdfium2 as pdfium
from .models import PageExtraction
from .model_settings import load_settings,KICONNECT_API
from .pdf_agent import rules

API='https://openrouter.ai/api/v1'
USAGE=ContextVar('openrouter_usage',default=None)
KEY=ContextVar('openrouter_key',default=None)
PROVIDER=ContextVar('cloud_provider',default=None)
VISION=ContextVar('cloud_vision',default=None)

def backend():
    provider=PROVIDER.get() or load_settings().get('provider','openrouter')
    return 'kiconnect' if provider=='kiconnect' else 'openrouter'

def api_base():
    return KICONNECT_API if backend()=='kiconnect' else API

def label():
    return 'KI:connect NRW' if backend()=='kiconnect' else 'OpenRouter'
CACHE_VERSION='openrouter-original-page-v1'


class OpenRouterError(RuntimeError):pass
class OpenRouterConfigurationError(OpenRouterError):pass


def _headers():
    key=KEY.get() or load_settings().get('api_key','')
    if not key:raise OpenRouterConfigurationError('Modellanbieter-API-Schlüssel fehlt. Modelleinstellungen öffnen.')
    return {'Authorization':'Bearer '+key,**({'X-OpenRouter-Title':'Stadtwerke Analyst'} if backend()=='openrouter' else {})}


def check_connection():
    try:
        r=httpx.get(api_base()+('/models' if backend()=='kiconnect' else '/key'),headers=_headers(),timeout=15)
        if backend()=='kiconnect':
            from .kiconnect import record_response
            record_response(r,KEY.get() or load_settings().get('api_key',''),'')
        _check_status(r)
        try:data=r.json().get('data',{})
        except (ValueError,AttributeError) as exc:raise OpenRouterError('Der Modellanbieter hat keine gültige Schlüsselprüfung zurückgegeben.') from exc
        if backend()=='kiconnect':
            if not isinstance(data,list):raise OpenRouterError('Modellliste hat ein ungültiges Format.')
            models=[m['id'] for m in data if isinstance(m,dict) and isinstance(m.get('id'),str)]
            from .kiconnect import save_catalog
            save_catalog(models,KEY.get() or load_settings().get('api_key',''))
            return {'models':models}
        return {'limit_remaining':data.get('limit_remaining'),'usage':data.get('usage')}
    except httpx.HTTPError as exc:raise OpenRouterError('Der Modellanbieter ist nicht erreichbar. Internetverbindung prüfen.') from exc


def _check_status(response):
    status=response.status_code
    if status in (401,403):raise OpenRouterConfigurationError('Modellanbieter-Schlüssel ist ungültig, abgelaufen oder für diesen Zugriff gesperrt.')
    if status in (402,429):
        from .kiconnect import limit_details
        details=limit_details(response,KEY.get() or load_settings().get('api_key',''))
        message='Nutzungskontingent ausgeschöpft.' if details['kind']=='quota' else 'Anfragelimit erreicht.'
        if details['message']:message+=' Anbieterhinweis: '+details['message']
        if details['retry_at']:
            from zoneinfo import ZoneInfo
            local=datetime.fromisoformat(details['retry_at']).astimezone(ZoneInfo('Europe/Berlin'))
            message+=' Erneut möglich ab '+local.strftime('%d.%m.%Y um %H:%M')+'.'
        raise OpenRouterConfigurationError(message)
    if status>=400:raise OpenRouterError(f'Modellanbieter-Anfrage fehlgeschlagen (HTTP {status}). Modell und Anbieter prüfen.')


def page_images(path,number):
    """Transmit readable bounded page images; release each native bitmap."""
    with pdfium.PdfDocument(str(path)) as document:
        page=document[number-1]
        bitmap=page.render(scale=2)
        try:
            im=bitmap.to_pil().convert('RGB')
            # Two images preserve small printed type on double-page spreads.
            regions=[im.crop((0,0,im.width//2,im.height)),im.crop((im.width//2,0,im.width,im.height))] if im.width>im.height*1.38 else [im]
            urls=[]
            for region in regions:
                region.thumbnail((1800,1800))
                data=io.BytesIO();region.save(data,format='PNG')
                urls.append('data:image/png;base64,'+base64.b64encode(data.getvalue()).decode())
            return urls
        finally:bitmap.close();page.close()


def strict_schema(schema):
    if isinstance(schema,dict):
        result={k:strict_schema(v) for k,v in schema.items() if k!='default'}
        if result.get('type')=='object':
            result['additionalProperties']=False
            result['required']=list(result.get('properties',{}))
        return result
    if isinstance(schema,list):return [strict_schema(v) for v in schema]
    return schema


PROMPT='Extrahiere belegte Unternehmenskennzahlen in das vorgegebene JSON-Schema. Berichtsjahr: {year}.'


def extract_page(page,year,path,model):
    from .extraction import validate,source_facts,normalize_number,normalize_unit
    content=[{'type':'text','text':f"PDF-Seite {page['page']}; erkanntes Berichtsjahr {year}.\nOriginalseitentext:\n"+page['text']}]
    vision=backend()=='openrouter' or (VISION.get() if VISION.get() is not None else load_settings().get('vision',False))
    if vision:content += [{'type':'image_url','image_url':{'url':url}} for url in page_images(path,page['page'])]
    payload={'model':model,'temperature':0,'max_tokens':8000,
             'provider':{'require_parameters':True},
             'messages':[{'role':'system','content':PROMPT.format(year=year)+'\n'+rules()},{'role':'user','content':content}],
             'response_format':{'type':'json_schema','json_schema':{'name':'PageExtraction','strict':True,'schema':strict_schema(PageExtraction.model_json_schema())}}}
    try:
        if backend()=='kiconnect':
            payload.pop('provider',None)
            payload['response_format']={'type':'json_object'}
            payload['messages'][0]['content']+='\nAntwortschema: '+json.dumps(PageExtraction.model_json_schema(),ensure_ascii=False)
        response=httpx.post(api_base()+'/chat/completions',headers=_headers(),json=payload,timeout=180)
        if backend()=='kiconnect':
            from .kiconnect import record_response
            record_response(response,KEY.get() or load_settings().get('api_key',''),model)
        _check_status(response);data=response.json()
    except httpx.HTTPError as exc:raise OpenRouterError('Modellanbieter-Anfrage unterbrochen oder Zeitlimit überschritten. Seite bleibt für erneute Auswertung gespeichert.') from exc
    usage=data.get('usage',{});ledger=USAGE.get()
    if backend()=='kiconnect':
        record_response(response,KEY.get() or load_settings().get('api_key',''),model,usage=usage)
    if ledger is not None:
        ledger.append({'page':page['page'],'model':data.get('model',model),'prompt_tokens':usage.get('prompt_tokens'),
                       'completion_tokens':usage.get('completion_tokens'),'cost_usd':usage.get('cost'),
                       'request_id':data.get('id'),'time':datetime.now(timezone.utc).isoformat()})
    if data.get('error'):raise OpenRouterError('Der Modellanbieter hat die Anfrage mit einem Anbieterfehler beendet.')
    choices=data.get('choices',[])
    if not choices:raise OpenRouterError('Der Modellanbieter hat keine Modellausgabe zurückgegeben.')
    if choices[0].get('finish_reason')=='length':raise OpenRouterError('Modellausgabe abgeschnitten; diese Seite gilt nicht als vollständig ausgewertet.')
    message=choices[0].get('message',{})
    if message.get('refusal'):raise OpenRouterError('Das Modell hat die Auswertung dieser Seite abgelehnt.')
    try:extracted=PageExtraction.model_validate_json(message.get('content') or '')
    except (ValueError,TypeError) as exc:
        details=''
        if hasattr(exc,'errors'):
            issues=exc.errors(include_url=False,include_context=False,include_input=False)
            details=' ('+'; '.join('.'.join(map(str,e['loc']))+': '+e['type'] for e in issues[:4])+')'
        raise OpenRouterError('Modellanbieter-Antwort entspricht nicht dem Kennzahlenschema'+details+'; Seite muss erneut ausgewertet werden.') from exc
    anchors=source_facts(page,year);rows=[]
    for candidate in extracted.observations:
        if candidate.year!=year:continue
        row=validate(candidate,page,year)
        # Independent PDF cells can corroborate a visually read value when a
        # printed unit is separated from its numeric cell in linear text.
        try:
            unit,factor=normalize_unit(candidate.raw_unit);value=normalize_number(candidate.raw_value)*factor
            matches=[a for a in anchors if a['metric']==candidate.metric and a.get('value')==value
                     and a.get('unit')==unit and a['status']=='validated']
        except ValueError:matches=[]
        if matches:row=dict(matches[0])
        elif page.get('layout')=='ocr':row.update(status='needs_review',validation_notes='Visuell erkannte Zahl aus einer OCR-Seite am Original prüfen.')
        row['extraction_method']='openrouter_visual_extraction';rows.append(row)
    return extracted,rows


def connection_status(settings=None):
    """Only a recent check for the current key can report a verified connection."""
    import hashlib
    from .config import RUNTIME
    settings=settings or load_settings()
    path=RUNTIME/(settings.get('provider','openrouter')+'-connection.json')
    if not settings.get('api_key') or not path.exists():return {}
    try:
        status=json.loads(path.read_text())
        same=status.get('key_hash')==hashlib.sha256(settings['api_key'].encode()).hexdigest() and status.get('model',settings['model'])==settings['model']
        age=datetime.now(timezone.utc).timestamp()-status['checked_timestamp']
        return status if same and 0<=age<3600 else {}
    except (ValueError,KeyError,TypeError,OSError):return {}


def verify_connection():
    """Free key check; persist status without the credential or account details."""
    import hashlib
    from .config import RUNTIME
    settings=load_settings()
    status={'key_hash':hashlib.sha256(settings.get('api_key','').encode()).hexdigest(),
        'checked_timestamp':datetime.now(timezone.utc).timestamp(),'model':settings['model']}
    error=None
    try:
        result=check_connection()
        if backend()=='kiconnect' and settings['model'] not in result.get('models',[]):
            raise OpenRouterConfigurationError('Der Modellname ist für diesen Schlüssel nicht verfügbar. Exakten Namen aus der Modellübersicht eintragen.')
        status.update(valid=True,message='Schlüssel und Modellzugriff geprüft' if backend()=='kiconnect' else 'Schlüssel erfolgreich geprüft')
    except OpenRouterError as exc:
        result={};error=exc
        status.update(valid=False if isinstance(exc,OpenRouterConfigurationError) else None,message=str(exc))
    path=RUNTIME/(backend()+'-connection.json')
    temp=path.with_suffix('.tmp');temp.write_text(json.dumps(status));temp.replace(path)
    if error:raise error
    return result
