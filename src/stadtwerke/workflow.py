"""Persistenter LangGraph: PDF -> Extraktion -> Auswahlpause -> Referenz -> Export."""
import json
import hashlib
import os
import uuid
import re
from contextvars import ContextVar
from pathlib import Path
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt, Command
from langgraph.checkpoint.sqlite import SqliteSaver
from .config import RUNTIME, MODEL
from .documents import read_pdf, relevant_pages, detect_report_year, file_digest, DOCUMENT_PROGRESS
from .extraction import extract_page, source_facts, MODEL_CACHE_VERSION, MODEL_CONTEXT, MODEL_CHUNK_CHARS
from .database import load_report, save_report, save_selection, save_result
from .calculation import available_metrics, calculate_reference
from .references import reference_pair
from .models import Selection
from .model_runtime import release_model
from .reporting import export
from .reporting_period import reporting_period
from .geography import municipality_context

EXTRACTION_VERSION = 'visible-source-v2'
SOURCE_RULES_VERSION = 'source-positioned-tables-v18'
LAYOUT_VERSION = 'visible-columns-and-table-cells-v9'
PROGRESS = ContextVar('stadtwerke_progress', default=None)


def emit(stage, detail, completed=0, total=0):
    callback = PROGRESS.get()
    if callback:
        callback({'stage':stage,'detail':detail,'completed':completed,'total':total})


def report_location(company,city,pages):
    if not city and not re.search(r'\bStadtwerke\s+[A-ZÄÖÜ][\wäöüß-]+',company):
        names=set(re.findall(r'\bStadtwerke\s+([A-ZÄÖÜ][\wäöüß-]+)\s+(?:GmbH|AG)\b',
                             '\n'.join(p['text'] for p in pages[:8])))
        if len(names)==1:city=names.pop()
    return municipality_context(company,city)


def refresh_sources(report, city=''):
    if (report['metadata'].get('source_rules_version') == SOURCE_RULES_VERSION
        and report['metadata'].get('layout_version')==LAYOUT_VERSION and not city):
        return report
    archive = RUNTIME / (report['id']+'-before-generic-source-refresh.json')
    if not archive.exists():
        archive.write_text(json.dumps(report,ensure_ascii=False,indent=2))
    report['metadata']['source_update_archive']=str(archive)
    if report['metadata'].get('layout_version')!=LAYOUT_VERSION:
        emit('document','Sichtbare PDF-Seiten und Spaltenfolge aktualisieren')
        _,pages,themes = read_pdf(report['metadata']['path'])
        report.update(pages=pages,themes=themes)
        report['metadata']['layout_version']=LAYOUT_VERSION
    detected_year = detect_report_year(report['pages'])
    if detected_year:
        report['metadata'].update(year=detected_year['year'], year_detection=detected_year)
    report['metadata']['reporting_period']=reporting_period(report['pages'],detected_year)
    location = report_location(report['metadata']['company'],city,report['pages'])
    rows = [o for p in report['pages'] for o in source_facts(p,report['metadata']['year'],location)]
    originals = [o for o in report['observations'] if o.get('extraction_method')!='source_anchored_rule']
    from .extraction import validate
    from .models import Candidate
    page_lookup = {p['page']:p for p in report['pages']}
    for original in originals:
        verified = validate(Candidate.model_validate(original),page_lookup[original['page']],report['metadata']['year'])
        previous_status=original['status']
        original.update(verified)
        if previous_status=='superseded':
            original['status']='superseded'
        elif previous_status=='manual_checked' and verified.get('technical_status')=='verified':
            original['status']='manual_checked'
    # Preserve model/manual evidence. An explicit local cohort or a statement
    # including customer projects cannot be promoted to an own total by the LLM.
    for row in originals:
        if row.get('status')=='manual_checked':
            continue
        for anchor in rows:
            if (row['metric']==anchor['metric'] and row['page']==anchor['page']
                and row.get('value') is not None and row['value']==anchor.get('value')
                and (anchor['status']=='validated' or anchor['scope']=='reported_portfolio'
                     or ('privater' in anchor['evidence'] and 'gewerblicher' in anchor['evidence']))):
                row.update(status='superseded',validation_notes='Durch direkte Originalzahl mit ausdrücklicher Abgrenzung ersetzt.')
    from .kpi_cards import reconcile_cards
    report['observations'] = reconcile_cards(originals+rows)
    report['metadata'].update(source_rules_version=SOURCE_RULES_VERSION,location=location)
    save_report(report)
    return report


class State(TypedDict, total=False):
    path: str
    year: int
    company: str
    max_pages: int
    model: str
    force_reanalyze: bool
    city: str
    resource_mode: str
    resume_extraction: bool
    reuse_saved_analysis: bool
    provider: str
    report: dict
    options: dict
    selection: dict
    result: dict
    files: dict
    session_id: str
    status: str


def ingest(state):
    emit('document','Dokument und gespeicherte Analyse prüfen')
    # A verified current-version analysis can be loaded without re-reading and
    # re-laying out every PDF page. Still hash the file so a replaced PDF cannot
    # reuse a different document's analysis.
    from .model_settings import load_settings
    from .openrouter import KEY,USAGE,PROVIDER,VISION,OpenRouterConfigurationError
    from .pdf_agent import fingerprint
    policy_hash=fingerprint()
    settings=load_settings()
    provider=state.get('provider',settings['provider'])
    if provider!=settings['provider']:
        settings={'provider':provider,**settings.get('providers',{}).get(provider,{})}
    model=state.get('model') or (settings.get('model',MODEL))
    cloud=provider in ('openrouter','kiconnect')
    if provider not in ('ollama','openrouter','kiconnect'):raise ValueError('Unbekannter Modellanbieter')
    state=dict(state,provider=provider,model=model)
    def same_backend(saved):
        return state.get('reuse_saved_analysis') or (saved['metadata'].get('provider','ollama')==provider and saved['metadata'].get('model')==model and saved['metadata'].get('pdf_agent_sha256')==policy_hash and saved['metadata'].get('page_images',provider=='openrouter')==(cloud and (provider=='openrouter' or settings.get('vision',False))))
    source = Path(state['path'])
    if source.is_file() and not state.get('force_reanalyze') and not state.get('resume_extraction'):
        cached_id = file_digest(source)
        cached = load_report(cached_id)
        if cached and same_backend(cached) and (not state.get('year') or cached['metadata']['year'] == state['year']) and cached['metadata'].get('extraction_version') == EXTRACTION_VERSION and (not cached['metadata'].get('extraction_errors') or state.get('reuse_saved_analysis')):
            emit('validation','Gespeicherte Belege und allgemeine Standortregeln prüfen')
            return {'report': refresh_sources(cached,state.get('city','')), 'status': 'Gespeicherte Analyse geladen'}
    report_id, pages, themes = read_pdf(state['path'])
    detected_year = detect_report_year(pages)
    year = detected_year['year'] if detected_year else state.get('year')
    if not year:
        raise ValueError('Das Berichtsjahr ist im PDF nicht eindeutig erkennbar. Bitte einen Text-Geschäftsbericht mit eindeutiger Jahresangabe verwenden.')
    state = dict(state, year=year)
    saved = load_report(report_id)
    if saved and same_backend(saved) and saved['metadata']['year'] == state['year'] and saved['metadata'].get('extraction_version') == EXTRACTION_VERSION and not state.get('force_reanalyze') and (not saved['metadata'].get('extraction_errors') or state.get('reuse_saved_analysis')) and not state.get('resume_extraction'):
        return {'report': refresh_sources(saved,state.get('city','')), 'status': 'Gespeicherte Analyse geladen'}
    company = state.get('company') or Path(state['path']).stem
    location = report_location(company,state.get('city',''),pages)
    observations = []
    for index,page in enumerate(pages,1):
        observations.extend(source_facts(page,state['year'],location))
        emit('extraction',f"Originalzahlen prüfen · PDF-Seite {page['page']} von {len(pages)}",index,len(pages))
    errors = []
    resumed_pages=[]
    computed_since_release=0
    selected = pages[:state['max_pages']] if cloud and state.get('max_pages') else pages if cloud else relevant_pages(pages, themes, state.get('max_pages'))
    api_usage=[]
    key_token=KEY.set(settings.get('api_key',''))
    provider_token=PROVIDER.set(provider)
    vision_token=VISION.set(settings.get('vision',False))
    usage_token=USAGE.set(api_usage)
    if cloud and not settings.get('api_key'):
        KEY.reset(key_token);USAGE.reset(usage_token);PROVIDER.reset(provider_token);VISION.reset(vision_token)
        raise OpenRouterConfigurationError('OpenRouter-API-Schlüssel fehlt. Modelleinstellungen öffnen.')
    try:
        for index,page in enumerate(selected,1):
            emit('extraction',f"{('KI:connect liest Originalseite' if provider=='kiconnect' else 'OpenRouter prüft Originalseite') if cloud else 'Lokales Modell liest PDF-Seite'} {page['page']} · {index} von {len(selected)} {'PDF-Seiten' if cloud else 'vorausgewählten Seiten'}",index-1,len(selected))
            print(f"Extraktion: PDF-Seite {page['page']}", flush=True)
            try:
                model=state.get('model',MODEL)
                from .openrouter import CACHE_VERSION
                version=CACHE_VERSION if cloud else MODEL_CACHE_VERSION
                key=hashlib.sha256(json.dumps([version,provider,model,policy_hash,cloud and (provider=='openrouter' or settings.get('vision',False)),state['year'],page],sort_keys=True).encode()).hexdigest()
                checkpoint=RUNTIME/('extraction-page-'+key+'.json')
                # Resource scheduling does not change this instruction-bound cache.
                existing=checkpoint if checkpoint.exists() else None
                if existing and not state.get('force_reanalyze'):
                    rows=json.loads(existing.read_text())
                    resumed_pages.append(page['page'])
                    emit('extraction',f"PDF-Seite {page['page']} · gespeicherte Modellauswertung übernommen",index,len(selected))
                else:
                    if cloud:
                        from .openrouter import extract_page as extract_visual
                        extracted,rows=extract_visual(page,state['year'],state['path'],model)
                    else:
                        extracted, rows = extract_page(page,state['year'],model,state.get('resource_mode','balanced'))
                    temporary=checkpoint.with_name(checkpoint.name+'.'+uuid.uuid4().hex+'.tmp')
                    temporary.write_text(json.dumps(rows,ensure_ascii=False))
                    os.replace(temporary,checkpoint)
                    computed_since_release+=1
                # Periodically clear accumulated prompt caches, not after every
                # page. Both modes keep a fixed small request context.
                if not cloud and computed_since_release>=5:
                    emit('extraction',f"PDF-Seite {page['page']} beendet · Modellspeicher bereinigen",index,len(selected))
                    release_model(model)
                    computed_since_release=0
                for row in rows:
                    anchors = [a for a in observations if a.get('extraction_method')=='source_anchored_rule'
                               and a['page']==row['page'] and a['metric']==row['metric']
                               and a.get('value') is not None and a['value']==row.get('value')]
                    if any(a['status']=='validated' or a.get('scope')=='reported_portfolio'
                           or ('privater' in a['evidence'] and 'gewerblicher' in a['evidence']) for a in anchors):
                        row.update(status='superseded',validation_notes='Durch Originalzahl mit direktem Textbeleg ersetzt.')
                    observations.append(row)
            except OpenRouterConfigurationError:
                raise
            except Exception as exc:
                errors.append({'page': page['page'], 'error': str(exc)[:500]})
    finally:
        KEY.reset(key_token);USAGE.reset(usage_token);PROVIDER.reset(provider_token);VISION.reset(vision_token)
        if selected and not cloud:
            emit('validation','Modellauswertung beendet · lokalen Modellspeicher freigeben')
            release_model(state.get('model', MODEL))
    emit('validation','Originalbelege, Einheiten, Geschäftsjahr und Abgrenzung prüfen')
    report = {'id': report_id, 'metadata': {'company': company, 'year': state['year'],
              'path': str(Path(state['path']).resolve()), 'model': model,'provider':provider,
              'api_usage':api_usage,'api_cost_usd':sum(u['cost_usd'] for u in api_usage if isinstance(u.get('cost_usd'),(int,float))) if api_usage and all(isinstance(u.get('cost_usd'),(int,float)) for u in api_usage) else None,
              'year_detection': detected_year,
              'reporting_period': reporting_period(pages,detected_year),
              'page_count': len(pages), 'analyzed_pages': [p['page'] for p in selected],
              'source_scanned_pages': [p['page'] for p in pages],
              'extraction_version': EXTRACTION_VERSION,'pdf_agent_sha256':policy_hash,'pdf_agent_rules':'docs/PDF_AGENT.md','page_images':cloud and (provider=='openrouter' or settings.get('vision',False)),
              'source_rules_version': SOURCE_RULES_VERSION, 'location':location, 'layout_version':LAYOUT_VERSION,
              'extraction_errors': errors, 'resumed_model_pages':resumed_pages,
              'model_resource_profile':{'mode':'cloud_vision' if cloud else state.get('resource_mode','balanced'),'context_tokens':MODEL_CONTEXT,'threads':1 if state.get('resource_mode','balanced')=='economy' else 2,
              'batch_tokens':32 if state.get('resource_mode','balanced')=='economy' else 128,
              'classification_batch_size':4,'source_excerpt_max_chars':500,'strategy':MODEL_CACHE_VERSION}}, 'pages': pages, 'themes': themes,
              'observations': observations}
    if cloud:
        report['metadata']['model_resource_profile']={'mode':'cloud_vision' if report['metadata']['page_images'] else 'cloud_text','strategy':'original-page-v2','page_images':report['metadata']['page_images'],'page_text':True,'all_pages':len(selected)==len(pages)}
    if saved:
        archive = RUNTIME / f"{report_id}-previous-analysis.json"
        archive.write_text(json.dumps(saved,ensure_ascii=False,indent=2))
        report['metadata']['previous_analysis'] = str(archive)
        report['observations'].extend(r for r in saved['observations'] if r.get('status')=='manual_checked')
    from .kpi_cards import reconcile_cards
    report['observations']=reconcile_cards(report['observations'])
    save_report(report)
    emit('selection','Bericht und belegte Kennzahlen gespeichert')
    return {'report': report, 'status': 'Bericht in DuckDB gespeichert'}


def choose(state):
    # Reload permits reviewed corrections without re-extracting the complete PDF.
    report = load_report(state['report']['id']) or state['report']
    options = available_metrics(report)
    if not options:
        emit('validation','Prüfung erforderlich: noch kein passender belegter Referenzwert')
        return {'report': report, 'options': {}, 'status': 'Prüfung erforderlich'}
    emit('selection',f'{len(options)} Thema/Themen mit passender Referenz zur Auswahl')
    selection = Selection.model_validate(interrupt({
        'question': 'Relevante Themen auswählen', 'options': options,
        'report_id': report['id'], 'company': report['metadata']['company']}))
    if any(metric not in options for metric in selection.metrics):
        raise ValueError('Ein gewähltes Thema hat keinen passenden belegten Berichtswert.')
    if selection.target_year < report['metadata']['year']:
        raise ValueError('Das Zieljahr liegt vor dem Berichtsjahr.')
    save_selection(state['session_id'], report['id'], selection.model_dump())
    return {'report': report, 'options': options, 'selection': selection.model_dump(),
            'status': 'Themen ausgewählt'}


def calculate(state):
    result = {'company': state['report']['metadata']['company'],
              'report_id': state['report']['id'], 'topics': [], 'reviews': [],
              'analysis_origin':{'generator':'Stadtwerke Analyst','created_by':'program',
                  'description':'Neue Analyse und eigene Diagramme aus belegten Berichtswerten und öffentlichen Referenzdaten.'},
              'method': 'Unternehmensbestände: konstante Relation. Absatz/Erzeugung: bedingter Unternehmensvergleich für gleiche Monate. Personal: berechnete Berichtskennzahlen. Alle Eingabewerte stammen aus automatisch gelesenen Berichtsdaten und öffentlichen Referenzen. Reine Umfeldvergleiche sind ausgeschlossen.'}
    for index,metric in enumerate(state['selection']['metrics'],1):
        item = state['options'][metric]
        if item.get('reference_kind') in ('context','scenario') or item.get('scenario'):continue
        emit('reference','Historische und aktuelle Referenz abrufen · '+item['label'],index-1,len(state['selection']['metrics']))
        obs = item['observation']
        try:
            from .config import CAPACITY_TOPICS
            if item.get('reference_kind')=='report':
                from .personnel import personnel_analysis
                ref,calc=personnel_analysis(item,state['report'])
                result['topics'].append({'metric':metric,**item,'reference':ref,'calculation':calc})
                continue
            if metric in CAPACITY_TOPICS:
                ref = reference_pair(metric,obs['year'],state['selection']['target_year'],
                    **({'report':state['report']} if state['report']['metadata'].get('reporting_period') else {}))
            else:
                ref = reference_pair(metric,obs['year'],state['selection']['target_year'],report=state['report'])
            calc = calculate_reference(obs,ref,state['selection']['spread'])
            result['topics'].append({'metric': metric, **item, 'reference': ref, 'calculation': calc})
        except Exception as exc:
            result['reviews'].append({'metric': metric, 'reason': str(exc)})
    save_result(state['session_id'], result)
    return {'result': result, 'status': 'Referenzen und Vergleichswerte berechnet'}


def write_output(state):
    emit('outlook','Vergleichswerte, Quellen und PowerPoint erstellen')
    return {'files': export(state['result'], state['session_id']), 'status': 'Fertig'}


def build_graph(checkpointer):
    graph = StateGraph(State)
    for name, node in [('ingest', ingest), ('choose', choose), ('calculate', calculate), ('export', write_output)]:
        graph.add_node(name, node)
    graph.add_edge(START, 'ingest')
    graph.add_edge('ingest', 'choose')
    graph.add_conditional_edges('choose', lambda s: 'calculate' if s.get('selection') else END)
    graph.add_edge('calculate', 'export')
    graph.add_edge('export', END)
    return graph.compile(checkpointer=checkpointer)


def invoke(session_id, initial=None, selection=None, progress=None):
    token = PROGRESS.set(progress)
    document_token=DOCUMENT_PROGRESS.set(progress)
    try:
        return _invoke(session_id,initial,selection)
    finally:
        DOCUMENT_PROGRESS.reset(document_token)
        PROGRESS.reset(token)


def _invoke(session_id, initial=None, selection=None):
    with SqliteSaver.from_conn_string(str(RUNTIME / 'checkpoints.sqlite')) as saver:
        graph = build_graph(saver)
        config = {'configurable': {'thread_id': session_id}}
        if selection is not None:
            return graph.invoke(Command(resume=selection), config)
        if initial is not None:
            return graph.invoke({**initial, 'session_id': session_id}, config)
        return graph.get_state(config).values


def open_saved_report(session_id, report):
    """Create a selection checkpoint directly; never ingest or refresh an archive."""
    with SqliteSaver.from_conn_string(str(RUNTIME / 'checkpoints.sqlite')) as saver:
        graph=build_graph(saver)
        config={'configurable':{'thread_id':session_id}}
        graph.update_state(config,{'report':report,'session_id':session_id,'status':'Gespeicherter Bericht geöffnet'},as_node='ingest')
        return graph.invoke(None,config)
