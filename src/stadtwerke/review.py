"""Separate unusable model candidates from meaningful human review tasks."""
from .config import CAPACITY_TOPICS, REFERENCE_TOPICS


def review_groups(report):
    groups={'accepted':[],'targeted':[],'rejected':[],'other':[]}
    for row in report['observations']:
        if row['status']=='superseded':
            continue
        if row['year'] != report['metadata']['year'] or row.get('year_status') in ('unconfirmed','different_year'):
            groups['rejected'].append(row)
        elif row['status'] in ('validated','manual_checked'):
            groups['accepted'].append(row)
        elif row.get('evidence_status')!='verified' or row.get('value') is None:
            groups['rejected'].append(row)
        elif row['metric'] not in CAPACITY_TOPICS:
            groups['other'].append(row)
        elif row.get('value') is None or row.get('unit') != CAPACITY_TOPICS[row['metric']][2]:
            groups['rejected'].append(row)
        elif row.get('basis') in ('planned','additions') or row.get('portfolio')=='project':
            groups['other'].append(row)
        else:
            groups['targeted'].append(row)
    return groups


def confirm_observation(report, observation):
    """A human confirms scope; source, date and dimensions remain mandatory."""
    from copy import deepcopy
    from datetime import datetime, timezone
    from .models import Candidate
    from .extraction import validate

    metric = observation['metric']
    if metric not in CAPACITY_TOPICS:
        raise ValueError('Für diese Kennzahl ist kein Referenzvergleich angebunden.')
    subset = observation.get('portfolio') == 'defined_subset'
    if subset and not observation.get('entity','').strip():
        raise ValueError('Für einen Teilbestand ist eine ausdrückliche Abgrenzung erforderlich.')
    candidate = Candidate.model_validate(observation).model_copy(update={
        'scope': 'reported_portfolio' if subset else 'group',
        'portfolio': 'defined_subset' if subset else 'total',
        'basis': 'stock', 'geography': 'DE', 'year': report['metadata']['year']})
    page = next((p for p in report['pages'] if p['page'] == observation['page']), None)
    if page is None:
        raise ValueError('Originalseite ist nicht verfügbar.')
    verified = validate(candidate, page, report['metadata']['year'])
    if verified.get('technical_status') != 'verified':
        raise ValueError(verified['validation_notes'])
    row = dict(observation, **verified)
    row.update(status='manual_checked', extraction_method='user_review',
        reviewed_at=datetime.now(timezone.utc).isoformat(),
        validation_notes='Originalzahl, Einheit und Jahr automatisch nachgewiesen; Standorte, Betriebsbestand und Abgrenzung fachlich bestätigt.')
    updated = deepcopy(report)
    # Do not erase a different, already reviewed cohort of the same metric.
    for old in updated['observations']:
        if (old['metric'], old['page'], old['raw_value'], old['raw_unit'], old.get('entity','')) == (
            metric, observation['page'], observation['raw_value'], observation['raw_unit'], observation.get('entity','')):
            old['status'] = 'superseded'
    updated['observations'].append(row)
    return updated


def topic_coverage(report):
    """Explain absent options without promoting unsupported candidates."""
    from .calculation import available_metrics
    from .config import METRIC_LABELS
    available = available_metrics(report)
    groups = review_groups(report)
    rows = []
    for metric, (label, _, unit) in CAPACITY_TOPICS.items():
        if metric in available:
            obs = available[metric]['observation']
            reason = f"Belegter Bestand in {unit} · PDF-Seite {obs['page']}"
            status = 'Automatisch vergleichbar'
        elif any(o['metric'] == metric for o in groups['targeted']):
            status, reason = 'Fachliche Bestätigung offen', 'Originalzahl belegt; Bestandsabgrenzung oder Standorte noch offen.'
        elif any(o['metric'] == metric for o in groups['accepted']):
            status, reason = 'Vergleichsbasis unklar', 'Mehrere Bestände oder widersprüchliche Werte; keine eindeutige Vergleichsbasis.'
        else:
            status, reason = 'Keine Vergleichsbasis', f'Kein freigegebener Anlagenbestand in {unit} zum Berichtsjahresende.'
        rows.append({'Thema': label, 'Status': status, 'Auswahlgrundlage': reason})
    for metric in dict.fromkeys(o['metric'] for o in groups['accepted'] + groups['other']):
        if metric not in CAPACITY_TOPICS:
            if metric in ('employees','apprentices') and any(v.get('reference_kind')=='report' for v in available.values()):
                rows.append({'Thema':METRIC_LABELS[metric],'Status':'Automatisch vergleichbar','Auswahlgrundlage':'Originalzahlen und bei gemeinsamer Abgrenzung eine berechnete Ausbildungsquote.'})
                continue
            if metric in available:
                rows.append({'Thema':available[metric]['label'],'Status':'Automatisch vergleichbar','Auswahlgrundlage':'Belegte Berichtsgröße; Mengen- oder Kontextreferenz verfügbar.'})
                continue
            if metric in REFERENCE_TOPICS and REFERENCE_TOPICS[metric][3]=='context':
                rows.append({'Thema':METRIC_LABELS[metric],'Status':'Gespeichert ohne passenden Referenzvergleich','Auswahlgrundlage':'Die Umfeldreferenz liefert keine belastbare aktuelle Unternehmenszahl.'})
                continue
            if metric in REFERENCE_TOPICS:
                reason='Jahr, Einheit, Mengenbasis oder Abgrenzung bilden noch keine eindeutige Vergleichsbasis.'
                if metric=='heat_sales' and not report['metadata'].get('location',{}).get('city'):
                    reason='Für die örtliche Wetterreferenz fehlt ein eindeutig zugeordneter Ort.'
                rows.append({'Thema':REFERENCE_TOPICS[metric][0],'Status':'Vergleichsbasis unklar','Auswahlgrundlage':reason})
                continue
            rows.append({'Thema': METRIC_LABELS.get(metric,metric), 'Status': 'Gespeichert ohne passenden Referenzvergleich',
                'Auswahlgrundlage': 'Berichtsangabe vorhanden; passender historischer und aktueller Referenzvergleich im MVP noch nicht umgesetzt.'})
    return rows


def report_findings(report):
    """Display extracted report information independently of adapter readiness."""
    from .calculation import available_metrics
    from .config import METRIC_LABELS
    available=available_metrics(report)
    seen=set()
    findings=[]
    for row in review_groups(report)['accepted']:
        identity=(row['metric'],row.get('value'),row.get('unit'),row.get('entity',''))
        if identity in seen:
            continue
        seen.add(identity)
        prefix='über ' if row.get('qualifier')=='more_than' else 'fast ' if row.get('qualifier')=='less_than' else 'rund ' if row.get('approximate') else ''
        findings.append({'Berichtsgröße':METRIC_LABELS.get(row['metric'],row['metric']),
            'Originalwert':prefix+row['raw_value']+' '+row['raw_unit'],
            'Abgrenzung':row.get('entity') or ('Gebietsbestand' if row.get('scope')=='network_area' else 'Berichtsangabe'),
            'PDF-Seite':row['page'],
            'Referenzvergleich':'Automatisch vergleichbar' if row['metric'] in available or (row['metric'] in ('employees','apprentices') and any(v.get('reference_kind')=='report' for v in available.values())) else 'Gespeichert ohne passenden Referenzvergleich' if row['metric'] not in CAPACITY_TOPICS and (row['metric'] not in REFERENCE_TOPICS or REFERENCE_TOPICS[row['metric']][3]=='context') else 'Vergleichsbasis unklar'})
    return findings


def comparison_summary(report):
    """Count selectable report metrics and their distinct subject areas."""
    from .calculation import available_metrics
    metrics=available_metrics(report)
    def area(metric):
        for prefix,label in (('pv_','Photovoltaik'),('wind_','Windenergie'),('battery_','Speicher'),
                             ('electricity_','Strom'),('gas_','Gas'),('heat_','Wärme'),
                             ('water_','Wasser'),('wastewater_','Wasser'),
                             ('charge_','Elektromobilität'),('charging_','Elektromobilität')):
            if metric.startswith(prefix):return label
        if metric in ('employees','apprentices'):return 'Personal'
        return 'Finanzen'
    recognized={row['metric'] for row in report.get('observations',[])
                if row.get('status') in ('validated','manual_checked')
                and row.get('year')==report['metadata'].get('year')
                and row.get('year_status') not in ('unconfirmed','different_year')
                and row.get('value') is not None}
    counted=set(metrics)
    areas=list(dict.fromkeys(area(metric) for metric in metrics))
    return {'scanned_pages':len(report['metadata'].get('source_scanned_pages',[])),
            'recognized_metrics':len(recognized),'comparable_metrics':len(counted),'areas':areas}


def model_error_summary(report):
    """Explain persisted failures without claiming to know unavailable raw output."""
    errors=report['metadata'].get('extraction_errors',[])
    rows=[]
    for error in errors:
        message=error.get('error','')
        if 'Kennzahlenschema' in message:
            cause='Antwortformat passt nicht zum Kennzahlenschema'
        elif 'abgeschnitten' in message:
            cause='KI-Antwort wurde abgeschnitten'
        elif 'Zeitlimit' in message or 'unterbrochen' in message:
            cause='Verbindung unterbrochen oder Zeitlimit überschritten'
        else:cause='Technischer Fehler bei der Modellauswertung'
        rows.append({'PDF-Seite':error['page'],'Ursache':cause})
    return rows


def selection_topics(options):
    """Show available comparisons beside a compact list of unavailable areas."""
    from .config import METRIC_LABELS
    areas=[('Photovoltaik',('pv_capacity_dc','pv_capacity_ac','pv_generation')),
           ('Windenergie',('wind_onshore','wind_offshore')),
           ('Batteriespeicher',('battery_power','battery_energy')),
           ('Stromabsatz',('electricity_sales_total',)),
           ('Gasabsatz',('gas_sales_total','gas_sales_slp','gas_sales_rlm')),
           ('Wärme',('heat_sales',)),('Wasser & Abwasser',('water_sales','wastewater_volume')),
           ('Elektromobilität',('charge_points','charging_energy')),
           ('Finanzen',('debt','equity','operating_cashflow')),
           ('Beschäftigte & Ausbildung',('employees','apprentices'))]
    rows=[];seen=set()
    for label,metrics in areas:
        available=[metric for metric in metrics if metric in options]
        if available:
            for metric in available:
                rows.append({'id':metric,'label':options[metric]['label'] if options[metric].get('reference_kind')=='report' else METRIC_LABELS.get(metric,options[metric]['label']).split(' / ')[0],'available':True})
                seen.add(metric)
        else:rows.append({'id':'unavailable-'+metrics[0],'label':label,'available':False})
    for metric,item in options.items():
        if metric not in seen:rows.append({'id':metric,'label':item['label'].split(' / ')[0],'available':True})
    return rows
