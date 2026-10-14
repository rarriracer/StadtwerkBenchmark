"""Small, source-safe presentation components for the local analyst workspace."""
from html import escape
import math
import streamlit as st
from .config import ROOT, MODEL, METRIC_LABELS
from .reporting import number

STAGES = [('document','Bericht','Geschäftsbericht als PDF hochladen.'),
          ('extraction','Extraktion','Alle Seiten lesen, Kennzahlen erkennen und speichern.'),
          ('validation','Belegprüfung','Belege automatisch abgleichen; offene Angaben bei Bedarf bestätigen.'),
          ('selection','Themenwahl','Relevante Themen auswählen und Auswertung starten.'),
          ('reference','Referenzen','Passende historische und aktuelle API-Daten abrufen.'),
          ('outlook','Ausblick','Vergleich und eigene Diagramme berechnen; Export bereitstellen.')]
STAGE_ROLES = {'document':'Eingabe','extraction':'Automatisch',
               'validation':'Automatisch · Prüfung bei Bedarf','selection':'Auswahl',
               'reference':'Automatisch','outlook':'Automatisch'}



def e(value):
    return escape(str(value),quote=True)


def html(content, target=None):
    (target or st).markdown(content,unsafe_allow_html=True)


def stylesheet():
    html('<style>'+ (ROOT/'assets/app.css').read_text()+'</style>')


def brand(ready,model=None,provider='ollama',connection=None):
    model=model or MODEL
    if provider=='kiconnect':
        from .kiconnect import model_label
        model=model_label(model)
    mark = '<svg viewBox="0 0 32 32" aria-hidden="true"><path d="M4 27V19M12 27V13M20 27V6M28 27V2" stroke="#25232b" stroke-width="3"/><path d="M3 12L12 7L20 10L29 3" fill="none" stroke="#7c729f" stroke-width="1.5"/></svg>'
    status_class='ready' if ready else 'offline'
    if provider in ('openrouter','kiconnect'):
        connection=connection or {}
        status_text=f"{model or 'Modell fehlt'} · {'KI:connect NRW' if provider=='kiconnect' else 'OpenRouter'}"
        if connection.get('valid') is True:
            status_text+=' · Verbindung geprüft'
        elif connection.get('valid') is False:
            status_text+=' · Schlüssel abgelehnt';status_class='offline'
        elif ready:
            status_text+=' · Schlüssel gespeichert';status_class='configured'
        else:status_text+=' · Schlüssel fehlt'
    else:status_text=f'{model} · Lokal verfügbar' if ready else f'{model} · Nicht erreichbar'
    html(f'<div class="brandbar"><div class="brand">{mark}Stadtwerke Analyst<small>Research Workspace</small></div><div class="environment {status_class}" title="{e('Externe Modellauswertung' if provider in ('openrouter','kiconnect') else 'Lokales Modell: installiert und erreichbar')}"><i></i>{e(status_text)}</div></div>')



def hero(title=None,subtitle=None,eyebrow='Energieversorgung / Deutschland'):
    title_html = e(title) if title else 'Vom Bericht zum <em>belegten Ausblick.</em>'
    description = subtitle or 'Kennzahlen nachvollziehbar erfassen, öffentliche Referenzen verknüpfen und die Entwicklung unter klaren Annahmen einordnen.'
    html(f'<div class="hero{" page-hero" if title else ""}"><h1>{title_html}</h1><p>{e(description)}</p></div>')


def stepper(stage='document',target=None):
    current = next((i for i,s in enumerate(STAGES) if s[0]==stage),0)
    items = []
    for i,(key,name,kind) in enumerate(STAGES):
        state = 'active' if i==current else 'done' if i<current else ''
        items.append(f'<div class="rail-step {state}" {"aria-current=step" if i==current else ""}><span class="rail-number">{i+1:02d}</span><span class="rail-name">{e(name)}</span><span class="rail-role">{e(STAGE_ROLES[key])}</span><span class="rail-kind">{e(kind)}</span></div>')
    html('<div class="rail" aria-label="Analyseprozess">'+''.join(items)+'</div>',target)


def section(index,title,description='',accent=False):
    html(f'<div class="section-head{" accent" if accent else ""}">{('<span>'+e(index)+'</span>') if index else ''}<div><h2>{e(title)}</h2>'+ (f'<p>{e(description)}</p>' if description else '')+'</div></div>')


def notice(message,title='',error=False):
    html(f'<div class="note {"error" if error else ""}">'+(f'<b>{e(title)}</b>' if title else '')+f'<p>{e(message)}</p></div>')


def stats(entries):
    items = []
    for label,value,unit,detail in entries:
        items.append(f'<div class="stat"><span class="stat-label">{e(label)}</span><span class="stat-value">{e(value)}'+(f'<small>{e(unit)}</small>' if unit else '')+f'</span><span class="stat-detail">{e(detail)}</span></div>')
    html(f'<div class="stats" style="--count:{len(entries)}">'+''.join(items)+'</div>')


def fact(obs, show_quote=True):
    verified = obs['status'] in ('validated','manual_checked')
    source_verified = verified or obs.get('evidence_status')=='verified'
    value = ("über " if obs.get("qualifier")=="more_than" else "rund " if obs.get("approximate") else "") + f"{obs['raw_value']} {obs['raw_unit']}"
    year = f"Geschäftsjahr {obs.get('reporting_period_label',obs['year'])}" if obs['year']>=2023 else 'Jahreszuordnung offen'
    status = 'Originalbeleg nachgewiesen · Fachlich freigegeben' if verified else 'Originalbeleg nachgewiesen · Fachliche Prüfung offen' if source_verified else 'Originalbeleg nicht bestätigt · Kandidat nicht freigegeben'
    context = f"PDF-Seite {obs['page']} · {year} · {status}"
    entity = '<br>Abgrenzung: '+e(obs['entity']) if obs.get('entity') else ''
    reason = '' if verified else '<div class="reason">'+e(obs.get('validation_notes','Prüfung erforderlich'))+'</div>'
    quote = '<blockquote>„'+e(obs['evidence'])+'“</blockquote>' if show_quote else ''
    html(f'<article class="fact"><div class="fact-top"><h4>{e(METRIC_LABELS.get(obs["metric"],obs["metric"]))}</h4><strong>{e(value)}</strong></div>{quote}<div class="provenance">{e(context)}{entity}</div>{reason}</article>')


def mini_method():
    rows = [('01','Originalstellen sichern','Alle sichtbaren Seiten werden gelesen. Tabellen werden mit Jahreskolonnen und Zellpositionen gespeichert; Kennzahlen behalten Einheit, Seite und Originalbeleg.'),
            ('02','Vergleichbarkeit prüfen','Bestand und Zubau, Leistung und Ertrag sowie Konzern- und Teilbestände bleiben getrennt.'),
            ('03','Entwicklung einordnen','Historische und aktuelle Deutschlandwerte liefern den Vergleich. Die Themenauswahl bestimmt den Ausblick für das aktuelle Jahr.')]
    html('<aside class="mini-method"><div class="eyebrow">Der Analyseweg</div><h3>Die Quelle bleibt<br>Teil der Aussage.</h3>'+''.join(f'<div class="mini-row"><span>{n}</span><div><b>{e(t)}</b><p>{e(d)}</p></div></div>' for n,t,d in rows)+'</aside>')


def architecture():
    details = {
        'document':'PDF hochladen und Versorger angeben. Das Programm ermittelt das Berichtsjahr aus dem Dokument.',
        'extraction':'Alle PDF-Seiten lesen, Tabellen und Kennzahlen mit Einheit, Jahr und Originalseite erfassen und in der Datenbank speichern. Je nach Modelleinstellung unterstützt ein lokales Modell die Zuordnung oder ein API-Modell wertet den Seitentext und bei unterstützten Modellen die Originalbilder aus.',
        'validation':'Zahlen, Originalbelege, Einheiten und Jahreszuordnung prüfen. Nur offene Abgrenzungen oder unklare Angaben erfordern eine Bestätigung oder Korrektur anhand der Originalseite.',
        'selection':'Relevante Themen festlegen und den Referenzabruf starten. Das Programm bietet nur Themen mit belegten Kennzahlen und angeschlossener Referenz an; Zieljahr ist das aktuelle Jahr.',
        'reference':'Referenzen für das Berichtsjahr und die jüngste verfügbare aktuelle Periode laden, Zeiträume und Einheiten abgleichen und Quellen sowie Datenstand speichern.',
        'outlook':'Den Mengen- oder Kontextvergleich berechnen, eigene Diagramme erzeugen und PowerPoint, Vergleichstabelle und Analyse mit Quellen bereitstellen. Die Ergebnisse stehen zur fachlichen Einordnung und zum Download bereit.'}
    html('<div class="architecture" aria-label="Sechs Prozessschritte mit Eingaben und automatischer Verarbeitung">'+''.join(
        f'<article><h3>{i+1:02d} – {e(title)}</h3><span class="node">{e(STAGE_ROLES[key])}</span><p>{e(details[key])}</p></article>'
        for i,(key,title,_) in enumerate(STAGES))+'</div>')


def reference_plot(ref):
    history = ref.get('history') or [{'date':ref['baseline_date'],'value':ref['baseline']},{'date':ref['target_date'],'value':ref['target']}]
    history = sorted(history,key=lambda p:p['date'])
    if ref['baseline']<=0:
        st.caption('Indexdarstellung entfällt bei nicht positiver historischer Referenz.')
        return
    if any('baseline_value' in p for p in history):
        history=[p for p in history if p.get('baseline_value',0)>0]
        values=[p['value']/p['baseline_value']*100 for p in history]
    else:
        values = [p['value']/ref['baseline']*100 for p in history]
    if not values or not all(math.isfinite(v) for v in values):
        return
    w,h=680,255; left,right,top,bottom=50,655,25,202
    lo=math.floor(min(values)/5)*5-2;hi=math.ceil(max(values)/5)*5+3
    y=lambda v:bottom-(v-lo)/(hi-lo)*(bottom-top)
    # Date spacing, rather than equally spacing possibly missing months.
    from datetime import date
    dates=[date.fromisoformat(p['date']).toordinal() for p in history]
    x=lambda d:left+(d-dates[0])/max(1,dates[-1]-dates[0])*(right-left)
    parts=[f'<svg class="data-chart" viewBox="0 0 {w} {h}" role="img" aria-label="Öffentliche Referenzentwicklung als Index">']
    for tick in (lo+2,(lo+hi)/2,hi-3):
        parts.append(f'<line x1="{left}" y1="{y(tick):.1f}" x2="{right}" y2="{y(tick):.1f}" stroke="#eeedf1"/><text x="38" y="{y(tick)+4:.1f}" text-anchor="end" fill="#86818f" font-size="11">{number(tick,0)}</text>')
    points=' '.join(f'{x(d):.1f},{y(v):.1f}' for d,v in zip(dates,values))
    parts.append(f'<polyline points="{points}" fill="none" stroke="#645a9b" stroke-width="2.4"/>')
    for p,d,v in zip(history,dates,values):
        parts.append(f'<circle cx="{x(d):.1f}" cy="{y(v):.1f}" r="3" fill="#645a9b"><title>{e(p["date"])}: {number(p["value"],0)} {e(ref["unit"])} · Index {number(v,2)}</title></circle>')
    for d,label,anchor in ((dates[0],history[0]['date'],'start'),(dates[-1],history[-1]['date'],'end')):
        parts.append(f'<text x="{x(d):.1f}" y="230" text-anchor="{anchor}" fill="#86818f" font-size="11">{e(label)}</text>')
    parts.append(f'<text x="{right}" y="{max(15,y(values[-1])-14):.1f}" text-anchor="end" fill="#645a9b" font-size="13" font-weight="600">{number(values[-1],2)}</text></svg>')
    index_basis='historischer Vergleichsmonat = Index 100' if any('baseline_value' in p for p in history) else 'historischer Stichtag = Index 100'
    html(f'<div class="chart-title">Referenzentwicklung</div><div class="chart-sub">{e(ref.get("geography","Deutschland"))} · {index_basis} · {e(ref.get("comparison_label","Referenz"))}</div>'+''.join(parts))


def scenario_plot(calc,unit):
    w,h=360,255;left,right,top,bottom=12,345,30,202
    maximum=max(calc[k] for k in ('lower','expected','upper'))*1.2
    parts=[f'<svg class="data-chart" viewBox="0 0 {w} {h}" role="img" aria-label="Drei illustrative Bestandsszenarien">']
    for i,(label,key) in enumerate((('Niedriger','lower'),('Konstant','expected'),('Höher','upper'))):
        x=30+i*108;bh=(calc[key]/maximum*(bottom-top)) if maximum else 0
        color='#645a9b' if key=='expected' else '#d8d5e1'
        parts.append(f'<rect x="{x}" y="{bottom-bh:.1f}" width="68" height="{bh:.1f}" fill="{color}" rx="2"/><text x="{x+34}" y="{bottom-bh-10:.1f}" text-anchor="middle" fill="#48434f" font-size="14">{number(calc[key])}</text><text x="{x+34}" y="230" text-anchor="middle" fill="#86818f" font-size="11">{label}</text>')
    parts.append('</svg>')
    html(f'<div class="chart-title">Drei Szenarien</div><div class="chart-sub">{e(unit)} · frei gewählter Abstand ±{calc["spread"]*100:.0f} %</div>'+''.join(parts))


def calculation_trace(obs,ref,calc):
    kind=ref.get('kind','stock')
    if kind=='context':
        html(f'<div class="equation">{number(ref["target"])} − {number(ref["baseline"])} = {number(calc["reference_change"])} {e("Prozentpunkte" if ref["unit"]=="% p.a." else ref["unit"])}<span>Veränderung der Referenz; keine automatische Übertragung auf den Berichtswert</span></div>')
        return
    html(f'<div class="equation">{number(obs["value"],3)} × {number(ref["target"],0)} / {number(ref["baseline"],0)} = {number(calc["expected"],3)} {e(obs["unit"])}<span>Berichtswert × aktuelle Referenz / historische Referenz</span></div>')
    if kind=='flow':
        st.caption('Relation zur vollständigen historischen Jahressumme. Veränderung gegenüber denselben historischen Monaten: '+number(calc['reference_change_percent'])+' %.')
    else:
        st.caption('Konstante Ausgangsrelation: '+number(calc['ratio_percent'],6)+' %.')


def footer():
    html('<div class="footer"><span>Stadtwerke Analyst · Lokaler MVP</span></div>')


def running_detail(event,elapsed):
    minutes,seconds=divmod(int(elapsed),60)
    html(f'<div class="running-detail" role="status" aria-live="polite"><div class="running-current"><span class="activity-mark" aria-hidden="true"><i></i><i></i><i></i></span><span>{e(event["detail"])}</span></div><span class="running-time">Laufzeit <b>{minutes}:{seconds:02d}</b></span></div>')


def analysis_origin(kind):
    title='Eigener Unternehmensausblick' if kind!='context' else 'Eigene Kontextanalyse'
    html(f'<div class="analysis-origin"><span>NEUE ANALYSE · VOM PROGRAMM ERSTELLT</span><h3>{title}</h3>'
         '<p>Berichtskennzahl + historische und aktuelle API-Daten → neu berechnete Analyse. '
         'Die Diagramme werden hier erzeugt; Originalbelege und externe Datenquellen sind separat ausgewiesen.</p></div>')


def company_outlook_plot(obs,ref):
    from .calculation import company_outlook_series
    from datetime import date
    points=company_outlook_series(obs,ref)
    if not points:return
    traces=[('Bedingter Unternehmenswert','value','#645a9b','')]
    if ref.get('kind')=='flow':traces.append(('Historischer Vergleich · aus Referenz abgeleitet','historical_proxy','#92909b','5 4'))
    values=[p[key] for p in points for _,key,_,_ in traces]
    w,h=680,280;left,right,top,bottom=72,655,24,215
    high=max(values+[1])*1.12
    y=lambda v:bottom-v/high*(bottom-top)
    dates=[date.fromisoformat(p['date']).toordinal() for p in points]
    x=lambda d:left+(d-dates[0])/max(1,dates[-1]-dates[0])*(right-left)
    parts=[f'<svg class="data-chart" viewBox="0 0 {w} {h}" role="img" aria-label="Vom Programm berechneter bedingter Unternehmensausblick">']
    for tick in (0,high/2,high):
        parts.append(f'<line x1="{left}" y1="{y(tick):.1f}" x2="{right}" y2="{y(tick):.1f}" stroke="#eeedf1"/><text x="{left-9}" y="{y(tick)+4:.1f}" text-anchor="end" fill="#86818f" font-size="10">{number(tick,0)}</text>')
    for label,key,color,dash in traces:
        coords=' '.join(f'{x(d):.1f},{y(p[key]):.1f}' for p,d in zip(points,dates))
        parts.append(f'<polyline points="{coords}" fill="none" stroke="{color}" stroke-width="2.4" stroke-dasharray="{dash}"/>')
        for p,d in zip(points,dates):
            parts.append(f'<circle cx="{x(d):.1f}" cy="{y(p[key]):.1f}" r="3" fill="{color}"><title>{e(label)} · {e(p["date"])}: {number(p[key])} {e(obs["unit"])}</title></circle>')
    for d,label,anchor in ((dates[0],points[0]['date'],'start'),(dates[-1],points[-1]['date'],'end')):
        parts.append(f'<text x="{x(d):.1f}" y="242" text-anchor="{anchor}" fill="#86818f" font-size="11">{e(label)}</text>')
    parts.append('</svg>')
    html('<div class="chart-title">Unternehmensentwicklung · eigene Modellrechnung</div>'
         f'<div class="chart-sub">{e(obs.get("entity") or "Berichtskennzahl")} · {e(obs["unit"])} · '
         +('kumulierte Menge für abgeschlossene Monate' if ref.get('kind')=='flow' else 'konstanter Anteil an der Referenz')+'</div>'+''.join(parts))
    st.caption('Violett: bedingter Unternehmenswert, vom Programm berechnet. '+
        ('Grau gestrichelt: historische Monatsverteilung aus der Referenz abgeleitet; keine gemessenen Unternehmensmonatswerte.' if ref.get('kind')=='flow' else 'Ausgangspunkt ist der belegte Berichtswert; die nachfolgenden Unternehmenswerte sind modelliert.'))


def kiconnect_usage(status):
    from datetime import datetime
    from zoneinfo import ZoneInfo
    def local_time(value):
        try:return datetime.fromisoformat(value).astimezone(ZoneInfo('Europe/Berlin')).strftime('%d.%m.%Y · %H:%M')
        except (ValueError,TypeError):return value or 'Nicht gemeldet'
    st.markdown('**Nutzung & Limits**')
    limit=status.get('last_limit')
    if limit:
        title='Nutzungskontingent ausgeschöpft' if limit['kind']=='quota' else 'Anfragelimit erreicht'
        st.warning(title+' · zuletzt gemeldet am '+local_time(limit['observed_at']))
        if limit.get('message'):st.caption('Anbieterhinweis: '+limit['message'])
        if limit.get('retry_at'):st.caption('Frühester gemeldeter Wiederholungszeitpunkt: '+local_time(limit['retry_at']))
        else:st.caption('Der Anbieter hat keinen Freigabezeitpunkt gemeldet. Kontingent im Hochschul-GPT prüfen.')
    headers=status.get('limit_headers',{})
    rows=[]
    for suffix,label in [('limit-requests','Anfragelimit'),('remaining-requests','Verbleibende Anfragen'),('reset-requests','Anfragelimit zurückgesetzt'),('limit-tokens','Tokenlimit'),('remaining-tokens','Verbleibende Tokens'),('reset-tokens','Tokenlimit zurückgesetzt')]:
        value=next((headers[prefix+suffix] for prefix in ('x-ratelimit-','ratelimit-','x-rate-limit-') if prefix+suffix in headers),None)
        if value is not None:rows.append({'Angabe':label,'Vom Anbieter gemeldet':value})
    if rows:
        st.dataframe(rows,hide_index=True,width='stretch')
        st.caption('Limitangaben zuletzt empfangen: '+local_time(status.get('limits_checked_at')))
    else:st.caption('Verbleibendes Hochschulkontingent: von der API nicht gemeldet.')
    if status.get('requests'):
        left,right=st.columns(2)
        left.metric('Erfasste Modellanfragen',status['requests'])
        tokens=int(status.get('prompt_tokens',0)+status.get('completion_tokens',0))
        right.metric('Erfasste Tokens',tokens if status.get('token_usage_reports') else 'Nicht gemeldet')
        missing=status['requests']-status.get('token_usage_reports',0)
        if missing:st.caption(f'Für {missing} erfasste Anfragen hat der Anbieter keine vollständigen Tokenzahlen gemeldet.')
        st.caption('Nur Nutzung dieser Anwendung für das ausgewählte Modell seit '+local_time(status.get('since'))+'. Andere Hochschul-GPT-Chats sind nicht enthalten.')
    st.link_button('Kontingent im Hochschul-GPT ansehen','https://chat.kiconnect.nrw/app')


def signed(value,digits=2):
    return ('+' if value>0 else '−' if value<0 else '')+number(abs(value),digits)


def outlook_sources(obs,ref,calc):
    from .calculation import reference_comparison
    comparison=reference_comparison(ref)
    kind=ref.get('kind','stock')
    delta=calc.get('reference_change') if kind=='context' else calc['company_change']
    delta_unit='Prozentpunkte' if kind=='context' and ref['unit']=='% p.a.' else ref['unit'] if kind=='context' else obs['unit']
    result=(signed(delta)+' '+delta_unit) if kind=='context' else number(calc['expected'])+' '+obs['unit']
    result_label='Änderung der API-Referenz' if kind=='context' else 'Unternehmenswert unter Annahme'
    details='Aktuell − historische Referenz' if kind=='context' else ('Gleiche Monate · Δ '+signed(delta)+' '+obs['unit']) if kind=='flow' else 'Konstanter Anteil · Δ '+signed(delta)+' '+obs['unit']
    html('<div class="origin-grid">'
         f'<div><span>BERICHT</span><b>{number(obs["value"],0 if obs["unit"]=="Anzahl" else 2)} {e(obs["unit"])}</b><small>{e(obs.get("reporting_period_label",obs["year"]))} · PDF-Seite {obs["page"]}</small></div>'
         f'<div><span>API · {e(ref.get("provider","Öffentliche Referenz"))}</span><b>{number(comparison["baseline"])} → {number(comparison["target"])} {e(ref["unit"])}</b><small>{e(ref.get("comparison_label",ref.get("series","Referenz")))}</small><small>{e(comparison["baseline_period"])} → {e(comparison["target_period"])}</small></div>'
         f'<div class="derived"><span>BERECHNET · {e(result_label)}</span><b>{e(result)}</b><small>{e(details)}</small></div></div>')
    if kind=='flow':
        change=(comparison['target']/comparison['baseline']-1)*100
        st.caption('API-Vergleich für gleiche Monate: '+signed(change)+' %. Die volle Jahresreferenz '+str(obs['year'])+' von '+number(ref['baseline'])+' '+ref['unit']+' dient separat als Berechnungsbasis; sie wird hier nicht mit einem Teiljahr verglichen.')
    if kind=='context':st.caption('Der API-Vergleich beschreibt das Umfeld dieser Berichtsgröße. Eine aktuelle Unternehmenszahl wird daraus nicht abgeleitet.')


def comparison_bars(values,labels,unit,title,detail,delta_unit=None):
    low=min(0,*values);high=max(0,*values);span=high-low or 1
    top,bottom=34,172
    y=lambda v:bottom-(v-low)/span*(bottom-top)
    zero=y(0)
    delta=values[1]-values[0]
    delta_unit=delta_unit or unit
    color='#298459' if delta>0 else '#a64f4f' if delta<0 else '#777681'
    parts=['<svg class="data-chart" viewBox="0 0 760 250" role="img" aria-label="'+e(title)+'">',
           f'<line x1="62" y1="{zero:.1f}" x2="465" y2="{zero:.1f}" stroke="#d8d5e1"/>']
    for index,(value,label) in enumerate(zip(values,labels)):
        x=90+index*220;pos=y(value);fill='#a29cae' if index==0 else '#645a9b'
        parts.append(f'<rect x="{x}" y="{min(pos,zero):.1f}" width="115" height="{max(1,abs(pos-zero)):.1f}" fill="{fill}" rx="2"/>'
                     f'<text x="{x+57}" y="{max(20,min(pos,zero)-9):.1f}" text-anchor="middle" fill="#25232b" font-size="16">{number(value,0 if unit=="Anzahl" else 2)}</text>'
                     f'<text x="{x+57}" y="207" text-anchor="middle" fill="#55515f" font-size="12">{e(label)}</text>')
    delta_label=signed(delta,1)+' '+delta_unit
    delta_font=min(21,max(12,230/max(1,len(delta_label)*.58)))
    parts.append(f'<text x="505" y="75" fill="#777681" font-size="12">Veränderung</text><text x="505" y="104" fill="{color}" font-size="{delta_font:.1f}">{e(delta_label)}</text>')
    if values[0]>0:parts.append(f'<text x="505" y="154" fill="{color}" font-size="16">{signed(delta/values[0]*100)} %</text>')
    parts.append('</svg>')
    html(f'<div class="chart-title">{e(title)}</div><div class="chart-sub">{e(unit)} · {e(detail)}</div>'+''.join(parts))


def outlook_comparison(obs,ref,calc):
    from .calculation import reference_comparison
    kind=ref.get('kind','stock')
    if kind=='context':
        unit='Prozentpunkte' if ref['unit']=='% p.a.' else ref['unit']
        comparison_bars([ref['baseline'],ref['target']],['API · Berichtsperiode','API · aktuell'],ref['unit'],
                        ref.get('comparison_label','API-Referenzvergleich'),ref.get('provider','Öffentliche API')+' · '+(ref.get('baseline_start','')+'–' if ref.get('baseline_start') else '')+ref['baseline_date']+' → '+(ref.get('target_start','')+'–' if ref.get('target_start') else '')+ref['target_date'],delta_unit=unit)
    elif kind=='flow':
        comparison_bars([calc['historical_company_aligned'],calc['expected']],[reference_comparison(ref)['baseline_period'],reference_comparison(ref)['target_period']],obs['unit'],
                        'Berechneter Zeitraumvergleich',f'Beide Balken aus Bericht und API berechnet · gleiche Monate bis {ref["target_date"]}')
    else:
        comparison_bars([obs['value'],calc['expected']],[f'Bericht · {obs["year"]}','Aktuell · berechnet'],obs['unit'],
                        'Bestand bei konstantem Referenzanteil','Ausgangspunkt: Originalbericht · Vergleichswert: Modellrechnung bis '+ref['target_date'])
    if len(ref.get('history',[]))>2:
        with st.expander('API-Verlauf ansehen'):
            reference_plot(ref)
            st.caption('Alle Punkte stammen aus der API; die Kurve wird zur Vergleichbarkeit als Index dargestellt.')


def personnel_result(ref,calc):
    employees=ref['personnel'].get('employees');apprentices=ref['personnel'].get('apprentices')
    entries=[]
    for label,row in (('Bericht · Mitarbeiter',employees),('Bericht · Auszubildende',apprentices)):
        if row:entries.append((label,number(row['value'],0),'Personen',f'PDF-Seite {row["page"]} · '+ref.get('period_label',str(row['year']))))
    share=calc.get('apprentice_share_percent')
    entries.append(('Berechnet · Ausbildungsquote',number(share) if share is not None else 'Offen','%' if share is not None else '',
                    'Anteil an Mitarbeitern einschließlich Auszubildenden' if share is not None else 'Zeitbasis und Abgrenzung prüfen'))
    stats(entries)
    if employees and apprentices:
        total=employees['value']+apprentices['value']
        if share is not None:
            width=share*6.8
            html(f'<div class="chart-title">Ausbildung im Personalbestand</div><div class="chart-sub">Beide Originalzahlen aus derselben Tabelle · {number(total,0)} Personen einschließlich Auszubildender</div>'
                 f'<svg class="data-chart" viewBox="0 0 680 90" role="img" aria-label="Ausbildungsquote {number(share)} Prozent"><rect x="0" y="12" width="680" height="24" fill="#d8d5e1" rx="2"/><rect x="0" y="12" width="{width:.1f}" height="24" fill="#645a9b" rx="2"/><text x="0" y="65" fill="#645a9b" font-size="14">{number(apprentices["value"],0)} Auszubildende · {number(share)} %</text><text x="680" y="65" text-anchor="end" fill="#55515f" font-size="14">{number(employees["value"],0)} Mitarbeiter ohne Auszubildende</text></svg>')
    st.caption(ref['assumption'])


def scenario_result(item):
    obs,ref,calc=item['observation'],item['reference'],item['calculation']
    unit=calc['output_unit']
    html('<div class="origin-grid">'
         f'<div><span>BERICHT · belegte Unternehmensgröße</span><b>{number(obs["value"])} {e(obs["unit"])}</b><small>{obs["year"]} · PDF-Seite {obs["page"]}</small></div>'
         f'<div><span>API · {e(ref.get("provider","Öffentliche Referenz"))}</span><b>{number(ref["baseline"])} → {number(ref["target"])} {e(ref["unit"])}</b><small>{e(ref.get("comparison_label",ref["series"]))}</small></div>'
         f'<div class="derived"><span>BERECHNET · mit eigenen Annahmen</span><b>{number(calc["expected"])} {e(unit)}</b><small>Δ {signed(calc["company_change"])} {e(unit)}</small></div></div>')
    st.caption('EIGENE ANNAHME · Betroffene Menge: '+number(calc['assumptions']['amount'])+' '+obs['unit']+' · '+calc['period_label'])
    comparison_bars([calc['baseline_company'],calc['expected']],['Eigene Basis · berechnet','Szenario · berechnet'],unit,calc['title'],calc['period_label']+' · beide Balken aus eigener Eingabe und Referenz berechnet')
    st.caption('Bedingte Rechnung unter bestätigten Annahmen. Das Ergebnis ist keine gemessene aktuelle Unternehmenszahl.')


def method_flow():
    html('''<div class="method-flow"><svg viewBox="0 0 1100 500" role="img" aria-label="Geschäftsbericht, Berichtsgrößen erkennen und speichern, passende API-Referenz prüfen. Ohne passende Referenz für spätere Auswertung gespeichert halten. Mit passender Referenz den Referenzanteil und aktuellen bedingten Vergleichswert berechnen.">
<defs><marker id="method-arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 Z" fill="#aaa4b7"/></marker></defs>
<g fill="none" stroke="#aaa4b7" stroke-width="2" marker-end="url(#method-arrow)">
<path d="M550 60 V90"/><path d="M550 150 V180"/><path d="M445 220 H235 V290"/><path d="M655 220 H865 V290"/><path d="M865 365 V410"/>
</g>
<g fill="#faf9fc" stroke="#d8d3e4" stroke-width="1.5">
<rect x="375" y="10" width="350" height="50" rx="6"/><rect x="375" y="90" width="350" height="60" rx="6"/>
<path d="M550 180 L655 220 L550 260 L445 220 Z" fill="#f2eff8" stroke="#645a9b"/>
<rect x="70" y="290" width="330" height="75" rx="6"/><rect x="700" y="290" width="330" height="75" rx="6"/>
<rect x="700" y="410" width="330" height="75" rx="6" fill="#f2eff8" stroke="#645a9b"/>
</g>
<g text-anchor="middle" font-family="Inter,Arial,sans-serif" font-size="18" fill="#25232b">
<text x="550" y="42">Geschäftsbericht</text>
<text x="550" y="115">Berichtsgrößen erkennen</text><text x="550" y="140">und speichern</text>
<text x="550" y="215" font-size="15" fill="#645a9b">Passende</text><text x="550" y="237" font-size="15" fill="#645a9b">API-Referenz?</text>
<text x="340" y="207" fill="#777681">Nein</text><text x="755" y="207" fill="#645a9b">Ja</text>
<text x="235" y="320">Für spätere Auswertungen</text><text x="235" y="347">gespeichert halten</text>
<text x="865" y="320">Referenzanteil im</text><text x="865" y="347">Berichtsjahr berechnen</text>
<text x="865" y="440" fill="#645a9b">Aktuellen Modellwert bei</text><text x="865" y="467" fill="#645a9b">gleichem Anteil berechnen</text>
</g></svg></div>''')
