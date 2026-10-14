"""Local, source-first analyst workspace. Start via Stadtwerke starten.command."""
import hashlib
import json
import uuid
from datetime import date
from pathlib import Path
import httpx
import streamlit as st
from stadtwerke.config import ROOT, MODEL, OLLAMA_URL, CAPACITY_TOPICS, REFERENCE_TOPICS, METRIC_LABELS
from stadtwerke.database import DatabaseBusyError, list_reports, load_report, save_report
from stadtwerke.workflow import invoke, open_saved_report, SOURCE_RULES_VERSION
from stadtwerke.jobs import JobRunner
from stadtwerke.review import review_groups, confirm_observation, topic_coverage, report_findings, comparison_summary, model_error_summary
from stadtwerke.pdf_preview import preview_page, source_focus
from stadtwerke.calculation import available_metrics

from stadtwerke.models import Candidate
from stadtwerke.reporting import number
from stadtwerke import ui
from stadtwerke.model_settings import load_settings,save_settings,CLOUD_MODEL,PROVIDER_LABELS,KICONNECT_API
from stadtwerke.openrouter import verify_connection,connection_status,OpenRouterError
from stadtwerke import kiconnect

st.set_page_config(page_title='Stadtwerke Analyst', page_icon='◩', layout='wide', initial_sidebar_state='collapsed')
ui.stylesheet()

@st.cache_data(ttl=15)
def model_ready(provider='ollama',model=MODEL,configured=False):
    if provider in ('openrouter','kiconnect'):return configured
    try:
        models = httpx.get(OLLAMA_URL+'/api/tags',timeout=3).json().get('models',[])
        return any(m['name']==model for m in models)
    except (httpx.HTTPError,ValueError):
        return False

@st.cache_resource
def job_runner():
    return JobRunner()

jobs = job_runner()
settings=load_settings()
connection=connection_status(settings) if settings['provider'] in ('openrouter','kiconnect') else {}
ready = model_ready(settings['provider'],settings['model'],bool(settings.get('api_key')) and connection.get('valid') is not False)
with st.container(key='workspace-header'):
    brand_column, settings_column, new_column = st.columns([5, 1.7, 1.7], vertical_alignment='center')
    with brand_column:
        ui.brand(ready,settings['model'],settings['provider'],connection)
    settings_popover = settings_column.popover('Modelleinstellungen',width='stretch')
with settings_popover:
    provider_ids=list(PROVIDER_LABELS)
    selected_provider=st.selectbox('Modellanbieter',provider_ids,index=provider_ids.index(settings['provider']),format_func=PROVIDER_LABELS.get,key='settings-provider')
    local=selected_provider=='ollama'
    selected_config=settings if selected_provider==settings['provider'] else settings.get('providers',{}).get(selected_provider,{})
    selected_name=PROVIDER_LABELS[selected_provider]
    st.caption('Ollama verarbeitet den Bericht auf diesem Rechner.' if local else f'{selected_name} verarbeitet die bereitgestellten PDF-Seiten extern. Dokumente, Belege und Referenzen bleiben lokal gespeichert.')
    with st.form('model-settings',clear_on_submit=False):
        vision=False
        if local:
            chosen_model=st.text_input('Lokales Ollama-Modell',value=settings['model'] if settings['provider']=='ollama' else MODEL)
            st.caption('Beim Speichern wird der lokale Modellserver bei Bedarf gestartet. Modelle werden nicht automatisch heruntergeladen.')
            api_key=''
        elif selected_provider=='kiconnect':
            st.caption('API-Endpunkt: '+KICONNECT_API)
            campus_models=kiconnect.model_options(selected_config.get('api_key',''))
            if campus_models:
                chosen_model=st.selectbox('KI:connect-Modell',campus_models,index=campus_models.index(kiconnect.selected_model(selected_config.get('model',''),campus_models)),format_func=kiconnect.model_label,key='kiconnect-model-choice')
            else:
                chosen_model=''
                st.warning('Der Zugang meldet derzeit keine Chatmodelle. Modellliste aktualisieren.')
            api_key=st.text_input('KI:connect-API-Schlüssel',type='password',placeholder='Gespeicherten Schlüssel beibehalten' if selected_config.get('api_key') else 'Schlüssel aus der API-Schlüsselverwaltung',key='kiconnect-key')
            vision=st.checkbox('Originalseiten zusätzlich als Bilder senden',value=selected_config.get('vision',False),help='Nur aktivieren, wenn das gewählte Modell Bildeingaben unterstützt. Sonst erhält es den vollständigen extrahierten Seitentext.',key='kiconnect-vision')
            st.caption('Modell auswählen; die passende API-Kennung wird automatisch verwendet. Schlüssel und Modell werden für KI:connect getrennt gespeichert.')
            st.link_button('KI:connect öffnen','https://chat.kiconnect.nrw/app')
            st.link_button('API-Dokumentation','https://chat.kiconnect.nrw/app/api-docs/')
        else:
            chosen_model=st.selectbox('OpenRouter-Modell',[CLOUD_MODEL,'google/gemini-3-flash-preview'],index=1 if selected_config.get('model')=='google/gemini-3-flash-preview' else 0)
            api_key=st.text_input('OpenRouter-API-Schlüssel',type='password',placeholder='Gespeicherten Schlüssel beibehalten' if selected_config.get('api_key') else 'sk-or-v1-…',key='openrouter-key')
        if not local:st.caption('Der Schlüssel wird lokal gespeichert und nicht exportiert. Beim Anbieterwechsel bleibt er erhalten.')
        save=st.form_submit_button('Einstellungen speichern',disabled=jobs.active())
    if save:
        try:
            save_settings(selected_provider,chosen_model,api_key,vision=vision)
            st.session_state.pop('kiconnect-key',None);st.session_state.pop('openrouter-key',None)
            if local:
                from scripts.start_app import ensure_ollama,ensure_model
                with st.spinner('Lokales Modell vorbereiten …'):
                    ensure_model(ensure_ollama(ROOT/'data/runtime'))
            model_ready.clear();st.rerun()
        except (OSError,RuntimeError,ValueError) as exc:
            model_ready.clear();st.error(str(exc))
    if selected_provider=='kiconnect':
        campus_key=selected_config.get('api_key','')
        if st.button('KI:connect-Modellliste aktualisieren',disabled=jobs.active() or not campus_key):
            try:
                kiconnect.refresh_models(campus_key)
                st.session_state.pop('kiconnect-model-choice',None)
                st.rerun()
            except OpenRouterError as exc:st.error(str(exc))
        st.caption('Die Auswahl enthält verfügbare Chatmodelle. Embedding-Modelle werden ausgeblendet.')
        ui.kiconnect_usage(kiconnect.usage_view(campus_key,chosen_model))
    connection_notice=st.session_state.pop('connection_notice',None)
    if connection_notice:
        (st.success if connection_notice['valid'] else st.error)(connection_notice['message'])
    if not local and st.button(selected_name+'-Verbindung prüfen',disabled=jobs.active() or selected_provider!=settings['provider'] or not settings.get('api_key')):
        try:
            result=verify_connection()
            st.session_state['connection_notice']={'valid':True,'message':selected_name+'-Zugriff geprüft. Die Prüfung startet keine Modellauswertung.'}
        except OpenRouterError as exc:
            st.session_state['connection_notice']={'valid':False,'message':str(exc)}
        model_ready.clear();st.rerun()

def new_report():
    """Return to upload without changing archived reports or active jobs."""
    for key in ('state','workflow_session','job_session','job_completed','job_error','confirmation_notice'):
        st.session_state.pop(key,None)
    st.session_state['upload_generation']=st.session_state.get('upload_generation',0)+1
    st.session_state['pending_view']='Analyse'

if 'pending_view' in st.session_state:
    st.session_state['navigation'] = st.session_state.pop('pending_view')
with st.container(key='main-nav'):
    with st.container():
        view = st.radio('Arbeitsbereich',['Analyse','Berichtsarchiv','Quellen & Themen','Methodik'],horizontal=True,
                    label_visibility='collapsed',key='navigation')
with new_column:
    st.button('Neuer Bericht',key='new-report',on_click=new_report,disabled=jobs.active(),width='stretch')

state = st.session_state.get('state')
report = load_report(state['report']['id']) if view=='Analyse' and state and state.get('report') else None
options = available_metrics(report) if report else {}
stage = ('outlook' if state and state.get('result',{}).get('topics') else
         'reference' if state and state.get('result') else
         'selection' if options else 'validation' if report else 'document')
progress_rail = None
progress_detail = None
def mount_progress(stage=None):
    global progress_rail, progress_detail
    progress_rail = st.empty()
    progress_detail = st.empty()
    if stage:
        ui.stepper(stage,progress_rail)


def start_job(session, *, initial=None, selection=None):
    try:
        if initial:
            current=load_settings()
            initial=dict(initial,provider=current['provider'],model=current['model'])
        identifier = jobs.start(lambda callback: invoke(session,initial=initial,selection=selection,progress=callback))
        st.session_state.update(job_id=identifier,job_session=session,pending_view='Analyse')
        st.session_state.pop('job_error',None)
        st.rerun()
    except RuntimeError as exc:
        ui.notice(str(exc),'Auftrag nicht gestartet',error=True)


# A managed restart can leave a single resumable analysis request. Consume it
# once across windows, preserving the original request for audit/recovery.
resume_request=ROOT/'data/runtime/pending-analysis-resume.json'
if resume_request.exists() and not jobs.active():
    try:
        request=json.loads(resume_request.read_text())
        source=Path(request['initial']['path']).resolve()
        if not source.is_relative_to(ROOT.resolve()) or not source.is_file():
            raise ValueError('Fortsetzungsauftrag verweist nicht auf einen gespeicherten Projektbericht.')
        resume_request.rename(resume_request.with_name('analysis-resume-applied-'+uuid.uuid4().hex+'.json'))
        start_job(request['session'],initial=request['initial'])
    except (OSError,ValueError,KeyError) as exc:
        st.caption('Fortsetzung konnte nicht gestartet werden: '+str(exc))


@st.fragment(run_every='1s')
def job_status():
    identifier = st.session_state.get('job_id')
    job = jobs.snapshot(identifier) if identifier else None
    if not job:
        return
    if job['status']=='running':
        ui.section('','Analyse läuft','Archiv und Methodik bleiben während der Analyse zugänglich. Der Auftrag läuft im Hintergrund weiter.')
        event = job['event']
        ui.stepper(event['stage'])
        ui.running_detail(event,job['elapsed'])
        if event.get('total'):
            st.progress(min(1.0,event.get('completed',0)/event['total']),
                text=f"{event.get('completed',0)} von {event['total']} Seiten in diesem Schritt abgeschlossen")
        else:
            st.caption('Vorbereitung / Verarbeitung · Seitenfortschritt erscheint, sobald die Seitenzahl feststeht.')
        if event['stage']=='extraction':
            st.caption('Die KI-Seiten werden vorab anhand von Themenbegriffen und Zahlen mit passenden Einheiten ausgewählt. Alle PDF-Seiten werden zuvor gelesen und nach Originalzahlen durchsucht.')
    else:
        st.session_state.pop('job_id',None)
        if job['status']=='done':
            st.session_state.update(state=job['result'],workflow_session=st.session_state['job_session'])
            st.session_state['job_completed']=True
        else:
            st.session_state['job_error']=job['error']
        st.rerun()


def open_report(saved,force=False):
    session = str(uuid.uuid4())
    if force:
        start_job(session,initial={'path':saved['metadata']['path'],
            'year':saved['metadata']['year'],'company':saved['metadata']['company'],
            'force_reanalyze':True})
        return
    loaded=open_saved_report(session,saved)
    for key in ('job_id','job_session','job_completed','job_error'):
        st.session_state.pop(key,None)
    st.session_state.update(state=loaded,workflow_session=session,pending_view='Analyse')
    st.rerun()

job_status()
busy = jobs.active()
if busy and not st.session_state.get('job_id'):
    st.caption('Eine Analyse läuft in einem anderen geöffneten Fenster. Neue Aufträge sind bis zum Abschluss gesperrt.')
if st.session_state.get('confirmation_notice') and not busy:
    st.success(st.session_state.pop('confirmation_notice'))
if st.session_state.get('job_error'):
    ui.notice(st.session_state['job_error'],'Analyse konnte nicht abgeschlossen werden',error=True)
if settings['provider']=='kiconnect' and not busy:
    last_limit=kiconnect.usage_view(settings.get('api_key',''),settings['model']).get('last_limit')
    if last_limit:
        ui.notice('Details und einen gegebenenfalls gemeldeten Wiederholungszeitpunkt findest du unter Modelleinstellungen → Nutzung & Limits.','KI:connect · Zuletzt gemeldetes Nutzungslimit',error=True)
if st.session_state.get('job_completed') and view!='Analyse':
    st.caption('Analyse abgeschlossen. Das Ergebnis ist unter „Analyse“ verfügbar.')

def upload_form():
    left,right = st.columns([1.55,1],gap='large')
    with left:
        ui.section('01','Bericht hinzufügen','Ausgangspunkt ist ein öffentlicher Geschäftsbericht.')
        with st.form('upload'):
            generation=st.session_state.get('upload_generation',0)
            uploaded = st.file_uploader('Geschäftsbericht als PDF',type=['pdf'],key=f'upload-pdf-{generation}')
            company = st.text_input('Name des Versorgers',placeholder='z. B. Stadtwerke Marburg',key=f'upload-company-{generation}')
            economy=False
            if settings['provider']=='ollama':
                economy=st.checkbox('Maximale Rechnerentlastung · langsam',value=False)
                st.caption('Standard: automatische Beschleunigung mit begrenztem Speicher. Maximale Entlastung nutzt nur einen CPU-Kern ohne Grafikkarte und ist deutlich langsamer. Alle Seiten bleiben berücksichtigt.')
            else:
                st.caption('Alle PDF-Seiten werden über '+PROVIDER_LABELS[settings['provider']]+(' mit Bild und Text' if settings['provider']=='openrouter' or settings.get('vision') else ' als Seitentext')+' geprüft. Bereits ausgewertete Seiten können bei einer Wiederaufnahme übernommen werden.')
            st.caption('Das Berichtsjahr wird aus dem Dokument erkannt.')
            if settings['provider']=='ollama':
                st.caption('Die erste Auswertung kann mehrere Minuten dauern und beansprucht Prozessor/Grafik sowie Arbeitsspeicher. Das Modell wird nach der Modellauswertung entladen. Berichtstext und Kennzahlen bleiben auf diesem Rechner.')
            else:
                st.caption('PDF-Inhalte werden an '+PROVIDER_LABELS[settings['provider']]+ ' übertragen. Die Nutzung zählt gegen das Kontingent des Anbieters. Quellen und berechnete Vergleichswerte bleiben nachvollziehbar.')
            submitted = st.form_submit_button('Bericht analysieren',disabled=not ready or busy,type='primary')
        if not ready:
            ui.notice('Unter „Modelleinstellungen“ Modell und API-Schlüssel hinterlegen und die Verbindung prüfen.' if settings['provider'] in ('openrouter','kiconnect') else 'Der Stadtwerke-Starter stellt die Verbindung zum lokalen Modell her. Gespeicherte Analysen bleiben im Archiv verfügbar.','Modell noch nicht eingerichtet')
        if submitted:
            if uploaded is None:
                ui.notice('Für die Analyse ist ein Geschäftsbericht als PDF erforderlich.','Dokument fehlt',error=True)
            else:
                content = uploaded.getvalue()
                path = ROOT/'data/raw'/(hashlib.sha256(content).hexdigest()+'.pdf')
                path.write_bytes(content)
                session = str(uuid.uuid4())
                start_job(session,initial={'path':str(path),
                    'company':company.strip() or Path(uploaded.name).stem,
                    'resource_mode':'economy' if economy else 'balanced'})
    with right:
        ui.mini_method()


def archive_diagnostics(saved):
    rows=saved['observations']
    groups=review_groups(saved)
    st.caption(f"{len(groups['targeted'])} Angaben gezielt prüfbar · {len(groups['rejected'])} Kandidaten nicht übernommen")
    supported=[o for o in rows if o['metric'] in (CAPACITY_TOPICS | REFERENCE_TOPICS)]
    missing=sum(o.get('evidence_status')!='verified' for o in rows)
    ui.notice(f"{len(rows)} Kennzahlenkandidaten gespeichert, davon {sum(o.get('evidence_status')=='verified' for o in rows)} mit geprüftem Originalbeleg. "
        f"{len(supported)} Kandidaten betreffen angeschlossene Mengen- oder Kontextgrößen. "
        'Ein Originalbeleg allein reicht nicht für den Vergleich: Stichtag, Einheit, Standort und Abgrenzung müssen ebenfalls passen.',
        'Was die Archivzahlen bedeuten')
    if not available_metrics(saved):
        reasons=sorted({o.get('validation_notes','Fachliche Zuordnung prüfen') for o in groups['targeted']})
        if not supported:
            st.caption('Keine Berichtskennzahl für die angeschlossenen Mengen- oder Kontextreferenzen gespeichert.')
        for reason in reasons[:5]:
            st.caption('Prüfgrund: '+reason)
        if missing:
            st.caption(f'{missing} Kandidaten haben noch keinen bestätigten Originalbeleg. Das kleine Modell kann Zahlen oder Textstellen falsch übernehmen; diese Kandidaten werden nicht übernommen und müssen nicht einzeln abgearbeitet werden.')
    if saved['metadata'].get('source_rules_version')!=SOURCE_RULES_VERSION:
        st.caption('Diese gespeicherte Analyse stammt aus einem älteren Regelstand. Das Öffnen verwendet sie unverändert. Eine Neuauswertung wird nur über „Analyse erneut ausführen“ gestartet.')


def archive_view():
    ui.hero('Berichtsarchiv','Gespeicherte Belege wiederverwenden und neue Themen vergleichen.',eyebrow='Arbeitsbereich / Dokumente')
    mount_progress()
    try:
        reports = list_reports()
        st.caption('Fünf vorbereitete Beispielberichte stehen direkt zur Themenwahl bereit. Eigene Uploads werden im Archiv ergänzt.')
    except DatabaseBusyError as exc:
        st.warning(str(exc))
        if st.button('Archiv erneut laden'):
            st.rerun()
        return
    if not reports:
        ui.notice('Geschäftsberichte können im Bereich „Analyse“ hochgeladen werden.','Noch kein Bericht gespeichert')
        return
    choices = {rid:f"{meta['company']} · {(meta.get('reporting_period') or {}).get('label',meta['year'])}" for rid,meta in reports}
    rid = st.selectbox('Bereits gespeicherte Analyse',choices,format_func=choices.get)
    try:
        saved = load_report(rid)
    except DatabaseBusyError as exc:
        st.warning(str(exc))
        if st.button('Archiv erneut laden'):
            st.rerun()
        return
    meta = saved['metadata']
    ui.stats([('Geschäftsjahr',(meta.get('reporting_period') or {}).get('label',meta['year']),'','Berichtsperiode'),
              ('Dokumentumfang',meta.get('page_count',len(saved['pages'])),'Seiten','Original-PDF gespeichert'),
              ('Originalbeleg',sum(o.get('evidence_status')=='verified' for o in saved['observations']),'Werte','Zahl, Einheit und Text nachgewiesen'),
              ('Vergleichbar',len(available_metrics(saved)),'Themen','Passender Referenzadapter')])
    if st.button('Bericht öffnen · Themen auswählen',type='primary',disabled=busy):
        open_report(saved)
    archive_diagnostics(saved)
    with st.expander('Analyse erneut ausführen'):
        st.caption('Eine vollständige Neuauswertung verwendet die automatische Beschleunigung mit begrenztem Speicher. Bereits vollständige Analysen öffnen benötigt keine erneute Modellauswertung.')
        if st.button('Gespeicherten Bericht vollständig neu analysieren',disabled=not ready or busy):
            open_report(saved,force=True)


def sources_view():
    ui.hero('Quellen & Themen','Historische und aktuelle Referenzen werden nach der Themenwahl automatisch über die angebundenen Schnittstellen abgerufen.',eyebrow='Referenzdaten / Automatischer Abruf')
    st.caption('Die Übersicht zeigt alle angeschlossenen Quellen. Auswählbar sind die zum Bericht passenden Kennzahlen; Mengenvergleiche und ergänzende Einflussgrößen bleiben fachlich getrennt.')
    ui.section('','Angeschlossene Datenquellen · alle acht bleiben erhalten')
    rows = [
        {'Quelle':'Energy-Charts · Fraunhofer ISE','Themen':'PV, Wind, Batteriespeicher; Strommarktpreise','Schnittstelle':'API · JSON','Zeitbasis':'Bestand: Berichtsstichtag; Preise: Mittelwerte','Gebiet':'Deutschland / DE-LU'},
        {'Quelle':'SMARD · Bundesnetzagentur','Themen':'Stromabsatz, PV-Ertrag, Haushalts- und Industriepreise','Schnittstelle':'JSON / CSV','Zeitbasis':'Mengen: Jahressumme; Preise: Mittelwerte','Gebiet':'Deutschland'},
        {'Quelle':'Bundesnetzagentur · Gas','Themen':'Gasabsatz gesamt, SLP und RLM','Schnittstelle':'Öffentlicher CSV-Endpunkt','Zeitbasis':'Monatsmengen und Jahressumme','Gebiet':'Deutschland'},
        {'Quelle':'Open-Meteo','Themen':'Wärmeabsatz, Heizgradtage, Strahlung, Wettervorhersage','Schnittstelle':'API · JSON','Zeitbasis':'Tagesdaten → Monats-/Jahreswerte; 7-Tage-Vorhersage','Gebiet':'Unternehmensort, sofern eindeutig'},
        {'Quelle':'Bundesnetzagentur · Ladeinfrastruktur','Themen':'Öffentliche Ladepunkte · Referenzdaten','Schnittstelle':'Öffentliche XLSX-Datei','Zeitbasis':'Veröffentlichte Bestandsstichtage','Gebiet':'Ort / Bundesland / Deutschland'},
        {'Quelle':'Kraftfahrt-Bundesamt','Themen':'BEV-Bestand · Referenzdaten','Schnittstelle':'ArcGIS-API · JSON','Zeitbasis':'Veröffentlichte Bestandsstichtage','Gebiet':'Bundesland / Deutschland'},
        {'Quelle':'Bundesbank · EZB als Ersatzquelle','Themen':'Unternehmenskreditzinsen · Referenzdaten','Schnittstelle':'Statistik-API · CSV','Zeitbasis':'Berichtsjahr: Jahresmittel; aktuell: Monatsmittel','Gebiet':'Deutschland'},
        {'Quelle':'Eurostat','Themen':'Wasser-/Abwasserpreisindizes · Referenzdaten','Schnittstelle':'API · JSON','Zeitbasis':'Monatsindizes, Jahresmittel und gleiche Vergleichsmonate','Gebiet':'Deutschland'},
    ]
    st.dataframe(rows,hide_index=True,width='stretch')
    with st.expander('Unternehmensvergleich für alle acht Quellen'):
        from stadtwerke.source_catalog import company_comparisons
        st.caption('Alle Quellen bleiben erhalten. Gerechnet wird nur, wenn die benötigten Unternehmensangaben im automatisch gelesenen Bericht vorhanden sind. Fehlende Angaben werden nicht durch manuelle Annahmen ersetzt.')
        for comparison in company_comparisons():
            st.markdown('**'+comparison['source']+'**')
            st.write(comparison['comparison'])
            st.caption('Benötigt: '+comparison['inputs'])
            st.caption('Umsetzungsstand: '+comparison['state'])
    ui.notice('Der Abruf erfolgt beim Start des Referenzvergleichs. Die Anwendung lädt das Berichtsjahr und die jüngsten veröffentlichten Daten, berechnet daraus die Vergleichswerte und speichert Abrufzeit, Quelle und Prüfsumme. Aktuell bedeutet den neuesten verfügbaren Datenstand; die Veröffentlichungsfrequenz unterscheidet sich je Quelle. Antworten werden in der Regel sechs Stunden zwischengespeichert, Wettervorhersagen eine Stunde.','So funktioniert der API-Abruf')
    with st.expander('Zeitbasis und fachliche Verwendung'):
        st.write('Absatz und Erzeugung: Summe des vollständigen Geschäfts- oder Berichtsjahres. Die Entwicklung im laufenden Jahr wird zusätzlich mit denselben Monaten des Berichtsjahres verglichen. Ein Teiljahr wird nicht als vollständiges Jahresergebnis ausgegeben.')
        st.write('Preise und Indizes: Jahresmittel als zusätzliche historische Basis sowie Mittelwerte identischer Vergleichsmonate. Kreditzinsen: Jahresmittel des Berichtsjahres und Mittelwert der verfügbaren aktuellen Monate. Strommarktpreise werden nach Stunden gewichtet.')
        st.write('Anlagen, Ladepunkte und Fahrzeuge: belegter Bestandsstichtag statt Jahressumme oder Jahresmittel. Ein Anlagenbestand zum Jahresende wird mit dem damaligen Referenzbestand verglichen. Bei abweichenden Geschäftsjahren gilt deren belegtes Ende.')
        st.write('Wetter, Preise, Fahrzeuge und Kreditzinsen werden bei passenden Themen im Ausblick als Einflussgrößen berücksichtigt. Sie ersetzen keine Absatz- oder Ergebnisprognose. Das Marktstammdatenregister ist bisher nicht angeschlossen.')
        st.caption('Die aktuelle Kennzahlenauswahl verwendet Jahreswerte und Bestände. Einzelne Monatswerte aus dem PDF sind noch keine separat auswählbaren Vergleichsthemen.')
    with st.expander('Beispiel einer Originalantwort'):
        st.caption('Dieser Link öffnet die JSON-Rohdaten der Energy-Charts-API im Browser. Die Anwendung liest diese Daten automatisch; ein manueller Download ist für den Vergleich nicht erforderlich.')
        st.link_button('Energy-Charts: API-Antwort öffnen (JSON)','https://api.energy-charts.info/v2/installed_power?country=de&time_step=monthly')


def method_view():
    ui.hero('Methodik und Systemarchitektur','Eingaben und Entscheidungen im Prozess: Bericht bereitstellen, offene Angaben bei Bedarf prüfen und relevante Themen auswählen. Das Programm übernimmt die Verarbeitung und Berechnung.',eyebrow='Methodik / Nachvollziehbarkeit')
    ui.section('','Analyseprozess und Themenauswahl')
    ui.method_flow()
    with st.expander('Systemarchitektur'):
        ui.architecture()
        st.caption('LangGraph speichert den Ablauf, SQLite sichert die Wiederaufnahme und DuckDB hält Berichtsdaten und Originalbelege.')
    ui.section('','Vom Anteil im Berichtsjahr zum heutigen Vergleichswert')
    ui.html('<div class="equation">Berichtswert × aktuelle Referenz / historische Referenz<span>Konstantes Verhältnis als ausdrücklich gewählte Modellannahme</span></div>')
    ui.notice('Der Vergleichswert beantwortet: Wie groß wäre derselbe Bestand, wenn sein Anteil am deutschen Gesamtbestand konstant geblieben wäre? Er ist kein tatsächlich gemessener aktueller Unternehmenswert.','Was die Rechnung aussagt')
    ui.section('','Was vor einem Vergleich geprüft wird')
    for title,text in [('Originalbeleg','Zahl, Einheit und zusammenhängender Beleg müssen auf derselben PDF-Seite vorhanden sein.'),
                       ('Fachliche Abgrenzung','Bestand, Zubau, Planung, Energieertrag und Umsatz werden unterschieden. Ein Teilbestand bleibt als Teilbestand bezeichnet.'),
                       ('Standorte und Stichtag','Der Anlagenbestand muss zum Ende des Berichtsjahres in Deutschland liegen. Unklare oder ausländische Portfolios werden nicht automatisch freigegeben.'),
                       ('Mengen und Einflussgrößen','Strom-, Gas- und PV-Erzeugungsmengen werden für identische Zeiträume verglichen. Preise, Wetter, Ladepunkte, Fahrzeuge und Kreditzinsen dürfen nur dann Unternehmenswerte verändern, wenn die erforderliche Verknüpfung im Bericht belegt ist. Fehlende Expositionen werden nicht geschätzt oder manuell abgefragt.')]:
        ui.notice(text,title)


def evidence_view(report):
    groups=review_groups(report)
    with st.expander('Kennzahlen und Originalbelege',expanded=not available_metrics(report)):
        t1,t2 = st.tabs(['Fachlich zugeordnet','Gezielte Prüfung'])
        for container,rows in ((t1,groups['accepted']),(t2,groups['targeted'])):
            with container:
                if not rows:
                    st.caption('Keine Einträge in diesem Prüfstatus.')
                for index,obs in enumerate(rows):
                    fact_with_source(report,obs,f'evidence-{container is t2}-{index}')
                    if container is t2:
                        st.caption(confirmation_text(report,obs))
                        if st.button('Kennzahl bestätigen',key=f"confirm-{report['id']}-{index}",type='primary',disabled=busy):
                            confirm_and_save(report,obs)
                        with st.expander('Originaltext und Korrekturen'):
                            page=next(p for p in report['pages'] if p['page']==obs['page'])
                            st.caption(f"Vollständiger Seitentext · PDF-Seite {obs['page']}")
                            st.text(page['text'])
                            if st.button('Angaben korrigieren',key=f"correct-{report['id']}-{index}",disabled=busy):
                                review_dialog(report,index)
        if report['metadata'].get('extraction_errors'):
            failures=model_error_summary(report)
            scanned=len(report['metadata'].get('source_scanned_pages',[]))
            ui.notice(f"Alle {scanned} Seiten wurden nach Originalzahlen durchsucht. Bei {len(failures)} Seiten konnte die ergänzende KI-Antwort nicht übernommen werden; weitere Kennzahlen können dadurch fehlen.",'Ergänzende KI-Auswertung unvollständig')
            with st.expander(f'Fehlerursachen ansehen · {len(failures)} Seiten'):
                st.dataframe(failures,hide_index=True,width='stretch')
                st.caption('Bei einem Schemafehler passt die Antwortstruktur oder ein Feldwert nicht zu den vorgegebenen Kennzahlen. Die ursprünglichen Modellantworten wurden in diesem Lauf nicht gespeichert; der genaue fehlerhafte Feldwert lässt sich daraus nicht rekonstruieren.')
                with st.expander('Technische Fehlerdetails'):
                    st.json(report['metadata']['extraction_errors'])
        retained=[]
        for page in report['pages']:
            for table in page.get('tables',[]):
                for cell in table['rows']:
                    entry={'PDF-Seite':page['page'],'Originalbeschriftung':cell['label']}
                    for i,year in enumerate(table['years']):
                        entry[f"{table['roles'][i]} {year}"]=cell['values'][i]
                    retained.append(entry)
        if retained:
            with st.expander('Erfasste Tabellenzeilen'):
                st.caption('Originalzellen einschließlich weiterer Tabellenangaben. Eine gespeicherte Tabellenzeile ist noch keine fachlich zugeordnete Kennzahl oder freigegebene Referenzbasis.')
                st.dataframe(retained,hide_index=True,width='stretch')
                selected=st.selectbox('Originaltabelle anzeigen',sorted({r['PDF-Seite'] for r in retained}),key='table-page-'+report['id'])
                if st.button('PDF-Seite öffnen',key='table-preview-'+report['id']):source_dialog(report,{'page':selected,'evidence':'Erfasste Originaltabelle'})
        c1,c2 = st.columns(2)
        with c1:
            st.download_button('Originalbericht herunterladen',Path(report['metadata']['path']).read_bytes(),'Originalbericht.pdf','application/pdf')
        with c2:
            st.download_button('Berichtsdaten mit Belegen herunterladen',json.dumps(report,ensure_ascii=False,indent=2),'bericht.json','application/json')


@st.cache_data(show_spinner=False,max_entries=12)
def cached_preview(path,page_number,modified,raw_value='',raw_unit=''):
    png,pdf=preview_page(path,page_number)
    focus=source_focus(png,path,page_number,raw_value,raw_unit) if raw_value and raw_unit else None
    return png,pdf,focus


def proof_view(report,page_number,context='review',observation=None):
    path=Path(report['metadata']['path'])
    try:
        with st.spinner('Originalseite wird geöffnet …'):
            png,pdf,focus=cached_preview(str(path),int(page_number),path.stat().st_mtime_ns,(observation or {}).get('raw_value',''),(observation or {}).get('raw_unit',''))
        if focus:
            st.image(focus,caption=f'Originalausschnitt · PDF-Seite {page_number}',width='stretch')
        with st.expander('Ganze Originalseite und Seitentext',expanded=not bool(focus)):
            image_tab,text_tab=st.tabs(['Vollständige Originalseite','Seitentext'])
            with image_tab:
                st.image(png,caption=f'Original-PDF · Seite {page_number}',width='stretch')
                st.caption('Über die Bildvergrößerung lässt sich die Seite genauer lesen.')
            with text_tab:
                page=next(p for p in report['pages'] if p['page']==page_number)
                st.text(page['text'])
        st.download_button(f'Nur PDF-Seite {page_number} öffnen / herunterladen',pdf,
            f"Originalseite-{page_number}.pdf",'application/pdf',key=f"pdf-page-{context}-{report['id']}-{page_number}")
    except (OSError,ValueError,RuntimeError) as exc:
        ui.notice(str(exc),'Originalseite konnte nicht geöffnet werden',error=True)


@st.dialog('Originalstelle im Geschäftsbericht',width='large')
def source_dialog(report,observation):
    st.markdown('„'+observation['evidence']+'“')
    proof_view(report,observation['page'],context='quote',observation=observation)


def fact_with_source(report,observation,context):
    ui.fact(observation,show_quote=False)
    if observation.get('section_reference'):
        st.caption('Datierter Originalabschnitt: '+observation['section_reference']['header'])
    with st.container(key='quote-'+context+'-'+report['id']):
        if st.button(f"PDF-Seite {observation['page']} öffnen ↗\n\n"+'„'+observation['evidence']+'“',key='open-quote-'+context+'-'+report['id'],width='stretch',help='Originalseite im Geschäftsbericht öffnen'):
            source_dialog(report,observation)


def confirmation_text(report,observation):
    boundary = ('Teilbestand: '+observation.get('entity','')) if observation.get('portfolio')=='defined_subset' else 'Gesamtbestand eigener Anlagen / Beteiligungen'
    return f"Bestätigung: {boundary}; in Deutschland zum Ende {report['metadata']['year']} in Betrieb. Zahl, Einheit und Originalbeleg sind automatisch geprüft."


def confirm_and_save(report,observation):
    try:
        updated=confirm_observation(report,observation)
        save_report(updated)
        st.session_state['confirmation_notice']='Kennzahl bestätigt und für den Referenzvergleich übernommen.'
        open_report(updated)
    except ValueError as exc:
        ui.notice(str(exc),'Wert noch nicht freigegeben',error=True)


@st.dialog('Kennzahl anhand der Originalseite prüfen',width='large')
def review_dialog(report,index):
    review_form(report,dialog_index=index)


def review_form(report,dialog_index=None):
    is_dialog=dialog_index is not None
    wrapper=st.container() if is_dialog else st.expander('Kennzahl ergänzen oder korrigieren')
    with wrapper:
        st.caption('Die Bestätigung betrifft den installierten Anlagenbestand in Deutschland zum Ende des Berichtsjahres sowie dessen Eigentumsbezug und Abgrenzung.')
        candidates=review_groups(report)['targeted']
        if is_dialog:
            selected=dialog_index
        else:
            selected=st.selectbox('Belegte Angabe zur gezielten Prüfung',[None]+list(range(len(candidates))),
                format_func=lambda i:'Neue Originalstelle ergänzen' if i is None else f"{METRIC_LABELS[candidates[i]['metric']]} · {candidates[i]['raw_value']} {candidates[i]['raw_unit']} · Seite {candidates[i]['page']}",key='review_candidate_'+report['id'])
        preset=candidates[selected] if selected is not None else {}
        form_target=st.container()
        if preset:
            if is_dialog:
                page_column,form_target=st.columns([1.3,1],gap='large')
                with page_column:
                    proof_view(report,preset['page'],context='dialog',observation=preset)
            else:
                proof_view(report,preset['page'],observation=preset)
        with form_target:
            if preset:
                ui.fact(preset)
                st.caption(confirmation_text(report,preset))
            with st.form(('dialog_' if is_dialog else '')+'review_'+str(selected)):

                with st.expander('Angaben korrigieren oder neue Kennzahl ergänzen',expanded=not bool(preset)):
                    metric = st.selectbox('Bestandsgröße',list(CAPACITY_TOPICS),index=list(CAPACITY_TOPICS).index(preset.get('metric','pv_capacity_dc')),format_func=lambda m:CAPACITY_TOPICS[m][0])
                    kind = st.radio('Abgrenzung',['Gesamtbestand eigener Anlagen / Beteiligungen','Ausdrücklich abgegrenzter Teilbestand'],index=1 if preset.get('portfolio')=='defined_subset' else 0,horizontal=True)
                    left,right = st.columns(2)
                    with left:
                        raw_value = st.text_input('Originalzahl',value=preset.get('raw_value',''),placeholder='z. B. 1.142 oder 12,5')
                        page_number = st.number_input('PDF-Seite',1,report['metadata']['page_count'],value=preset.get('page',1))
                    with right:
                        raw_unit = st.text_input('Originaleinheit',value=preset.get('raw_unit',''),placeholder='z. B. MWp oder kWp')
                        entity = st.text_input('Unternehmen / genaue Abgrenzung',value=preset.get('entity') or report['metadata']['company'])
                    evidence = st.text_area('Originalbeleg mit Zahl, Einheit und Kontext',value=preset.get('evidence',''))
                st.caption('Mit der Bestätigung werden Betriebsbestand, Deutschlandbezug und Bestandsabgrenzung fachlich freigegeben.')
                add = st.form_submit_button('Kennzahl bestätigen und übernehmen',type='primary',disabled=busy)
        if add:
            try:
                subset = kind=='Ausdrücklich abgegrenzter Teilbestand'
                candidate = Candidate(metric=metric,raw_value=raw_value,raw_unit=raw_unit,
                    year=report['metadata']['year'],evidence=evidence,
                    scope='reported_portfolio' if subset else 'group',basis='stock',
                    portfolio='defined_subset' if subset else 'total',entity=entity,geography='DE')
                confirm_and_save(report,candidate.model_dump() | {'page':int(page_number)})
            except Exception as exc:
                ui.notice(str(exc),'Wert noch nicht freigegeben',error=True)


def toggle_topic(selection_key,metric):
    selected=list(st.session_state[selection_key])
    if metric in selected:selected.remove(metric)
    else:selected.append(metric)
    st.session_state[selection_key]=selected


def choice_form(report,options):
    from stadtwerke.review import selection_topics
    ui.section('','Relevante Themen auswählen','Themen anklicken · Lila ist ausgewählt, ausgegraute Themen sind derzeit nicht automatisch vergleichbar.',accent=True)
    selection_key='automatic-topic-selection-'+report['id']
    if selection_key not in st.session_state:st.session_state[selection_key]=[next(iter(options))]
    selected=[metric for metric in st.session_state[selection_key] if metric in options]
    st.session_state[selection_key]=selected
    rows=selection_topics(options)
    with st.container(key='topic-choices'):
        columns=st.columns(3,gap='small')
        for index,row in enumerate(rows):
            active=row['id'] in selected
            appearance='selected' if active else 'available' if row['available'] else 'unavailable'
            with columns[index%3]:
                with st.container(key='topic-'+appearance+'-'+row['id']):
                    st.button(row['label'],key='choose-topic-'+report['id']+'-'+row['id'],
                        disabled=busy or not row['available'],width='stretch',
                        help='Auswahl aufheben' if active else 'Thema auswählen' if row['available'] else 'Die erforderlichen Berichtsdaten oder eine passende automatische Unternehmensrechnung fehlen.',
                        on_click=toggle_topic,args=(selection_key,row['id']))
    target = date.today().year
    st.caption(f'Ausblick {target} · Keine zusätzlichen Zahlen erforderlich. Berichtswerte, API-Referenzen und berechnete Veränderungen werden getrennt ausgewiesen. Personalvergleiche verwenden ausschließlich die belegten Berichtszahlen.')
    if st.button('Themenauswahl bestätigen und Ausblick erstellen',type='primary',disabled=busy):
        if not selected:
            ui.notice('Mindestens ein Thema ist erforderlich.','Auswahl fehlt',error=True)
        else:
            start_job(st.session_state['workflow_session'],selection={'metrics':selected,
                'target_year':target,'spread':0})


def result_view(result,files):
    from stadtwerke.outlook import company_result
    original=result
    result=company_result(result)
    if result!=original and files.get('json'):
        from stadtwerke.reporting import export
        from stadtwerke.config import OUTPUTS
        output_path=Path(files['json']).resolve()
        if output_path.is_relative_to(OUTPUTS.resolve()):files=export(original,output_path.parent.name)
    current=st.session_state.get('state')
    if current and current.get('result') is original and result!=original:
        st.session_state['state']=dict(current,result=result,files=files)
    if not result['topics']:
        ui.notice('Die bisherige Auswahl enthält keine belastbare Unternehmensrechnung. Wähle Strom-/Gasabsatz, einen belegten Anlagenbestand oder den Personalvergleich.','Unternehmensthemen auswählen')
    ui.section('','Ausblick · neue Analyse','Berichtszahlen werden mit passenden Referenzen verknüpft. Gleiche Zeiträume und berechnete Veränderungen machen den Vergleich nachvollziehbar.',accent=True)
    for item in result['topics']:
        calc,obs,ref = item['calculation'],item['observation'],item['reference']
        st.subheader('Beschäftigte & Ausbildung' if ref.get('kind')=='report' else METRIC_LABELS.get(item['metric'],item['label'].split(' · ')[0]))
        kind=ref.get('kind','stock')
        if kind=='report':
            ui.html(f'<div class="scope-line">{ui.e(result["company"])} · {ui.e(ref.get("period_label",ref["target_date"]))} · Originalzahlen aus dem Geschäftsbericht</div>')
        else:
            ui.html(f'<div class="scope-line">{ui.e(result["company"])} · {ui.e(obs.get("entity") or "Berichtsgröße")} · Vergleich zum {ui.e(ref["target_date"])} · {ui.e(ref.get("geography","Deutschland"))}</div>')
        if kind=='report':
            ui.personnel_result(ref,calc)
            with st.expander('Originalbelege und Berechnung'):
                for key,staff_row in ref['personnel'].items():
                    if staff_row:fact_with_source(report,staff_row,'result-personnel-'+key)
                st.caption(ref['assumption'])
            continue
        if kind=='scenario':
            ui.scenario_result(item)
        else:
            ui.outlook_sources(obs,ref,calc)
            ui.outlook_comparison(obs,ref,calc)
        with st.expander('Berechnung und Annahmen'):
            if kind=='scenario':
                st.code(calc['formula'],language=None)
                for name,label,_ in item['fields']:
                    st.write(label+': '+number(calc['assumptions'][name]))
                if calc['assumptions'].get('direction'):st.write('Preisexposition: '+calc['assumptions']['direction'])
                st.caption('Eigene Eingaben, keine aus dem PDF extrahierten Tatsachen. '+calc['confirmation_text'])
            else:
                ui.calculation_trace(obs,ref,calc)
            if ref.get('baseline_annual') is not None:
                st.caption('Jahresbasis '+str(obs['year'])+': '+number(ref['baseline_annual'])+' '+ref['unit'])
            if ref.get('reporting_period'):
                period=ref['reporting_period']
                st.caption(f"Berichtsperiode: {period['start']} bis {period['end']}.")
            st.caption(ref.get('assumption','Konstante Relation zur öffentlichen Referenz.'))
            if kind=='flow':st.caption('Die Unternehmenswerte für den Teilzeitraum sind aus der Referenzverteilung berechnet. Eine Jahresendprognose erfordert zusätzliche Annahmen.')
            if 'sensitivity_eur_per_million' in ref:
                st.caption('Zinssensitivität: '+number(ref['sensitivity_eur_per_million'])+' EUR pro Jahr je 1 Mio. EUR neu verzinster Kreditsumme.')
        for context_index,context in enumerate(ref.get('secondary',[])):
            with st.expander(context.get('label','Ergänzende Referenz')):
                if 'error' in context:
                    st.caption('Referenz nicht verfügbar: '+context['error'])
                elif 'baseline' in context:
                    st.write(context.get('comparison_label','Referenz'))
                    st.write(f"{context['baseline_date']}: {number(context['baseline'])} / {context['target_date']}: {number(context['target'])} {context['unit']}")
                    st.caption(context.get('assumption',''))
                    st.link_button('Ergänzende Quelle öffnen',context['url'],key='secondary-'+item['metric']+'-'+str(context_index))
                else:
                    st.caption('Vorhersagedaten; getrennt vom historischen Vergleich.')
                    st.json(context.get('daily',context))
        with st.expander('Quellen, Originalbeleg und Datenstand'):
            fact_with_source(report,obs,'result-'+item['metric'])
            st.caption(f"{ref.get('provider','Energy-Charts')} · Reihe {ref['series']} · Abruf {ref['fetched_at'][:10]} · historische Basis {ref['baseline_date']} · aktueller Bezug {ref['target_date']}")
            if ref.get('baseline_annual') is not None:
                st.caption('Vollständiges Berichtsjahr: '+number(ref['baseline_annual'])+' '+ref['unit']+' · '+('Summe' if ref.get('aggregation')=='sum' else 'Mittelwert')+'. Der laufende Vergleich verwendet die jeweils angegebenen Zeiträume.')
            st.caption('Öffentliche Referenz: '+ref.get('license',''))
            for index,source in enumerate(ref.get('sources') or [{'url':ref['url']}]):
                st.link_button('Referenzquelle '+str(index+1)+' öffnen',source['url'],key='reference-'+item['metric']+'-'+str(index))
            st.caption('Prüfsumme der Referenzantwort: '+ref['sha256'])
    for review in result['reviews']:
        ui.notice(review['reason'],METRIC_LABELS.get(review['metric'],review['metric']),error=True)
    if files:
        ui.html('<div class="download-intro"><b>Analyse exportieren</b><span>Editierbare Folie, Daten und Quellen</span></div>')
        columns = st.columns(3)
        for col,kind in zip(columns,('pptx','csv','json')):
            if kind in files:
                with col:
                    path = Path(files[kind])
                    mime = {'pptx':'application/vnd.openxmlformats-officedocument.presentationml.presentation','json':'application/json','csv':'text/csv'}[kind]
                    label = {'pptx':'PowerPoint herunterladen','json':'Analyse mit Quellen herunterladen','csv':'Vergleichswerte als Tabelle herunterladen'}[kind]
                    st.download_button(label,path.read_bytes(),path.name,mime,type='primary' if kind=='pptx' else 'secondary',width='stretch')
    if st.button('Andere Themen wählen',disabled=busy):
        open_report(report)


if view=='Berichtsarchiv':
    archive_view()
elif view=='Quellen & Themen':
    sources_view()
elif view=='Methodik':
    method_view()
else:
    if st.session_state.get('job_id'):
        pass
    elif report is None:
        ui.hero()
        mount_progress('document')
        upload_form()
    else:
        st.session_state.pop('job_completed',None)
        meta = report['metadata']
        ui.hero(meta['company'],f"Geschäftsjahr {(meta.get('reporting_period') or {}).get('label',meta['year'])} · Belegte Kennzahlen und öffentliche Referenzen",eyebrow='Analyse / Geschäftsbericht')
        mount_progress(stage)
        if not state.get('result'):
            summary=comparison_summary(report)
            ui.stats([('Seiten durchsucht',summary['scanned_pages'],'','Originalzahlensuche'),
                      ('Berichtsgrößen erkannt',summary['recognized_metrics'],'','Eindeutige, belegte Kennzahlen'),
                      ('Auswertbare Vergleiche',summary['comparable_metrics'],'','Bericht und Live-API-Referenzen'),
                      ('Themenbereiche',len(summary['areas']),'',' · '.join(summary['areas']) or 'Keine vergleichbaren Themenbereiche')])
        findings=report_findings(report)
        if findings:
            ui.section('','Belegte Berichtskennzahlen','Erfasste Angaben aus dem Bericht. Die Verfügbarkeit des Referenzvergleichs wird separat ausgewiesen.')
            st.dataframe(findings,hide_index=True,width='stretch')
        if state.get('result'):
            result_view(state['result'],state.get('files',{}))
        elif options:
            choice_form(report,options)
        else:
            ui.section('03','Noch keine belastbare Themenauswahl','Die erfassten Kandidaten ergeben bisher keinen eindeutig belegten Referenzvergleich.')
            ui.notice('Angeschlossen sind Anlagenbestände, Strom-/Gasabsatz sowie Preis-, Wetter-, Ladeinfrastruktur- und Finanzierungsreferenzen. Die Auswahl benötigt einen nachgewiesenen Berichtswert mit passendem Jahr, Einheit und Abgrenzung. Themenbegriffe allein reichen nicht.','Warum noch keine Themen ausgewählt werden können')
        with st.expander('Themenabdeckung und Auswahlgrundlage'):
            st.caption('Die Themenauswahl erfordert sowohl einen passenden Berichtswert als auch einen angebundenen historischen und aktuellen Referenzvergleich.')
            st.dataframe(topic_coverage(report),hide_index=True,width='stretch')
        evidence_view(report)
        review_form(report)
        with st.expander('Wie dieser Ablauf arbeitet'):
            ui.method_flow()
            st.caption('„Quellen & Themen“ zeigt die Referenzübersicht; „Methodik“ erläutert Vergleichsformel und Auswertungsgrenzen. Das „Berichtsarchiv“ ermöglicht den Dokumentwechsel und die erneute Analyse.')
ui.footer()
