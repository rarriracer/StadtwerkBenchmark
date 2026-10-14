import calendar
import hashlib
import json
from datetime import datetime, date, timezone
import httpx
from .config import RUNTIME, CAPACITY_TOPICS

URL = 'https://api.energy-charts.info/v2/installed_power?country=de&time_step=monthly'

def capacity_data():
    cache = RUNTIME / 'energy-capacity-cache.json'
    if cache.exists():
        cached = json.loads(cache.read_text())
        age = datetime.now(timezone.utc).timestamp() - cached['fetched_timestamp']
        if age < 6 * 3600:
            return cached
    response = httpx.get(URL, timeout=45,follow_redirects=True)
    response.raise_for_status()
    payload = response.json()
    if payload.get('endpoint') != 'installed_power' or 'data' not in payload:
        raise ValueError('Die Referenzantwort hat ein unerwartetes Schema.')
    fetched = datetime.now(timezone.utc)
    record = {'payload':payload,'url':URL,'fetched_at':fetched.isoformat(),
              'fetched_timestamp':fetched.timestamp(),'sha256':hashlib.sha256(response.content).hexdigest()}
    cache.write_text(json.dumps(record,ensure_ascii=False))
    return record

def end_of_month(timestamp):
    label = date.fromisoformat(timestamp[:10])
    return date(label.year,label.month,calendar.monthrange(label.year,label.month)[1])

def reference_pair(metric, baseline_year, target_year, today=None, report=None):
    today = today or date.today()
    if metric not in CAPACITY_TOPICS:
        return extended_reference(metric,baseline_year,target_year,today,report or {})
    if target_year < baseline_year:
        raise ValueError('Das Zieljahr liegt vor dem Berichtsjahr.')
    period=(report or {}).get('metadata',{}).get('reporting_period')
    if period and not period.get('end'):raise ValueError('Der belegte Stichtag des Geschäftsjahres fehlt.')
    base_month=period['end'][:7] if period else f'{baseline_year}-12'
    _,series,unit = CAPACITY_TOPICS[metric]
    record = capacity_data()
    if record['payload'].get('attributes', {}).get('timestamp_reference') != 'period_end':
        raise ValueError('Die API bestätigt den Monatsendbezug nicht.')
    series_units = {s['id']:s['unit'] for s in record['payload']['series']}
    if series_units.get(series) != ('GWh' if metric == 'battery_energy' else 'GW'):
        raise ValueError('Die API-Referenzeinheit hat sich geändert.')
    rows = record['payload']['data']
    eligible = lambda r: r['values'].get(series) is not None
    base = [r for r in rows if eligible(r) and r['timestamp'][:7] == base_month]
    targets = [r for r in rows if eligible(r) and r['timestamp'].startswith(str(target_year))
               and end_of_month(r['timestamp']) <= today]
    if not base or not targets or end_of_month(base[-1]['timestamp']) > today:
        raise ValueError('Keine vollständigen passenden Referenzstichtage vorhanden.')
    b,t = base[-1],targets[-1]
    history = [{'date':end_of_month(r['timestamp']).isoformat(), 'value':r['values'][series]*1000}
               for r in rows if eligible(r) and end_of_month(b['timestamp']) <= end_of_month(r['timestamp']) <= end_of_month(t['timestamp'])]
    return {'kind':'stock','provider':'Energy-Charts / Fraunhofer ISE','comparison_label':'Anlagenbestand Deutschland',
            **({'reporting_period':period} if period else {}),
            'assumption':'Konstanter Anteil am nationalen Anlagenbestand derselben Abgrenzung.',
            'baseline':b['values'][series]*1000,'target':t['values'][series]*1000,
            'baseline_date':end_of_month(b['timestamp']).isoformat(),
            'target_date':end_of_month(t['timestamp']).isoformat(),
            'series':series,'unit':unit,'geography':'Deutschland','history':history,'url':record['url'],
            'fetched_at':record['fetched_at'],'sha256':record['sha256'],
            'license':record['payload'].get('license','')}


def extended_reference(metric, baseline_year, target_year, today, report):
    from . import reference_sources as source
    from .config import WATER_PRICE_METRICS, ENERGY_MARKET_METRICS, FINANCIAL_RATE_METRICS
    location=report.get('metadata',{}).get('location',{})
    period=report.get('metadata',{}).get('reporting_period')
    fetch_year=int(period['start'][:4]) if period and period.get('start') else baseline_year
    kind='context';extra={};assumption='';secondary=[]
    if metric in WATER_PRICE_METRICS:
        sewerage=metric=='wastewater_volume'
        rows,meta=source.water_price_index(sewerage)
        pair=source.monthly_pair(rows,baseline_year,target_year,today,aggregate='mean',reporting_period=period)
        return dict(pair,**meta,kind='context',unit='Index (2025 = 100)',series=meta['category'],
            comparison_label='Verbraucherpreise Abwasserentsorgung' if sewerage else 'Verbraucherpreise Wasserversorgung',
            assumption='Nationaler Preisindex für private Haushalte; Vergleich identischer Monate. Berichtsvolumen und Preisindex haben unterschiedliche Einheiten. Daraus folgt keine Mengenprognose; lokale Tarife, Industriekunden und die konkrete Umsatzstruktur sind nicht abgebildet.')
    if metric in ENERGY_MARKET_METRICS:
        ref=spot_reference(baseline_year,target_year,today,period)
        ref['assumption']='Strom-Großhandelspreis als Einflussgröße für die Erzeugungs- und Ergebnisentwicklung eines Versorgers. Vergleich identischer Monate; kein direkter Unternehmensbenchmark. Für eine Mengen- oder Ergebnisprognose fehlen Erzeugungsmix, Kosten, Absatzpreise, Verträge und Absicherung.'
        return ref
    if metric in FINANCIAL_RATE_METRICS:
        ref=extended_reference('debt',baseline_year,target_year,today,report)
        ref['assumption']='Kreditzinsentwicklung als Einflussgröße für Finanzierung und Investitionen. Der ausgewiesene Unternehmenswert bleibt unverändert. Keine automatische Hochrechnung von Eigenkapital, Bilanzsumme oder Verschuldungsgrad; dafür fehlen Finanzierungsstruktur, Laufzeiten und Ergebnisplanung.'
        return ref
    if metric in ('electricity_sales_total','pv_generation'):
        filter_id='410' if metric=='electricity_sales_total' else '4068'
        rows,meta=source.smard_monthly(filter_id,fetch_year,target_year)
        pair=source.monthly_pair(rows,baseline_year,target_year,today,reporting_period=period)
        unit='MWh';series=filter_id;kind='flow'
        label='Realisierte Netzlast Deutschland' if filter_id=='410' else 'Realisierte PV-Erzeugung Deutschland'
        assumption=('Konstante Relation des Unternehmensjahresabsatzes zur nationalen Netzlast. Kundenmix, Eigenverbrauch und Beschaffungsverträge bleiben unmodelliert.'
            if filter_id=='410' else 'Konstante Relation der Unternehmenserzeugung zur nationalen PV-Erzeugungsreferenz. Anlagenbestand, Standorte und Verfügbarkeit können abweichen.')
    elif metric in ('gas_sales_total','gas_sales_slp','gas_sales_rlm'):
        segments=['slp','rlm'] if metric=='gas_sales_total' else ['slp' if metric=='gas_sales_slp' else 'rlm']
        series_rows=[];metas=[]
        for segment in segments:
            r,m=source.gas_monthly(segment);series_rows.append({v['date']:v['value'] for v in r});metas.append(m)
        dates=set(series_rows[0])
        for r in series_rows[1:]: dates &= set(r)
        rows=[{'date':d,'value':sum(r[d] for r in series_rows)} for d in sorted(dates)]
        pair=source.monthly_pair(rows,baseline_year,target_year,today,reporting_period=period)
        all_sources=[r for m in metas for r in m['sources']]
        meta=dict(metas[0],sources=all_sources,sha256=hashlib.sha256(''.join(m['sha256'] for m in metas).encode()).hexdigest())
        kind='flow';unit='MWh';series='+'.join(segments);label='Gasverbrauch Deutschland: '+series.upper()
        assumption='Konstante Relation zum nationalen Verbrauch des ausgewiesenen Segments. Monatsmengen werden aus veröffentlichten gerundeten Tagesmittelwerten angenähert. RLM enthält auch Gasverbrauch für Stromerzeugung; der lokale Kundenmix kann abweichen.'
        if metric!='gas_sales_rlm':
            secondary.append(optional_context('Gas-Bestandskundenpreis',lambda:price_reference('g-mdl_gspr-1-2',baseline_year,target_year,today,period)))
    elif metric in ('electricity_sales_households','electricity_sales_industry'):
        series='s-mdl_stpr-1-2' if metric=='electricity_sales_households' else 's-ind_stpr-1-1'
        return price_reference(series,baseline_year,target_year,today,period)
    elif metric=='heat_sales':
        rows,meta=source.weather_monthly(location,fetch_year,target_year,today)
        pair=source.monthly_pair(rows,baseline_year,target_year,today,reporting_period=period)
        unit='K·Tage';series='heating_degree_days_20_15';label='Heizgradtage / '+meta['geography']
        assumption='Örtlicher Heizgradtag-Proxy mit Heizgrenze 15 °C und Innentemperatur 20 °C. Für eine Absatzrechnung fehlen der wetterabhängige Anteil und Grund-/Prozesslast; angezeigt wird der Witterungsvergleich.'
        secondary.append(optional_context('Sieben-Tage-Wettervorhersage',lambda:source.weather_forecast(location)))
        secondary.append(optional_context('Globalstrahlung',lambda:radiation_reference(location,baseline_year,target_year,today)))
    elif metric in ('debt','interest_expense'):
        rows,meta=source.credit_rates()
        complete=source.monthly_pair(rows,baseline_year,target_year,today,aggregate='mean',reporting_period=period)
        baseline_date=period['end'] if period else f'{baseline_year}-12-31'
        pair=dict(complete,baseline=complete['baseline_annual'],baseline_date=baseline_date,
            baseline_start=period['start'] if period else f'{baseline_year}-01-01')
        extra['aligned_baseline']=complete['baseline']
        extra['baseline_label']='Jahresmittel des Berichtsjahres'
        extra['target_label']='Mittelwert der verfügbaren aktuellen Monate'
        extra['provisional']=any(r.get('provisional') for r in rows if pair['target_start']<=r['date']<=pair['target_date'])
        unit='% p.a.';series=source.CREDIT_KEY;label='Kreditzins neue Unternehmenskredite Deutschland'
        assumption='Jahresmittel des vollständigen Berichtsjahres gegenüber dem Mittelwert der verfügbaren aktuellen Monate. Marktzinsvergleich für neue Kredite über 1 Mio. EUR mit kurzer Zinsbindung. Eine Zinsaufwandsrechnung benötigt den variablen/refinanzierten Schuldenanteil und den Zeitpunkt der Zinsanpassung.'
        extra['sensitivity_eur_per_million']=(pair['target']-pair['baseline'])/100*1_000_000
    elif metric in ('charge_points','charging_energy'):
        public=optional_context('Öffentliche Ladeinfrastruktur',lambda:public_charger_reference(baseline_year,target_year,today,location))
        kba=optional_context('BEV-Fahrzeugbestand',lambda:vehicle_reference(baseline_year,target_year,today,location))
        if 'error' not in public:
            public['secondary']=[kba]
            return public
        if 'error' not in kba:
            kba['secondary']=[public]
            return kba
        raise ValueError('Ladeinfrastruktur und Fahrzeugreferenz nicht verfügbar: '+public['error']+'; '+kba['error'])
    else:
        raise ValueError('Für diese Kennzahl ist kein Referenzvergleich implementiert.')
    if kind=='flow':
        # Full-year relation produces a conditional YTD amount. Growth uses the
        # same months, not a partial current year divided by a full prior year.
        extra['aligned_baseline']=pair['baseline']
        pair['baseline']=pair['baseline_annual']
        pair['baseline_date']=period['end'] if period else f'{baseline_year}-12-31'
        extra['baseline_label']='Geschäftsjahressumme '+period['label'] if period else 'Jahressumme '+str(baseline_year)
        extra['target_label']='Januar bis '+pair['target_date']
    return dict(pair,**meta,**extra,kind=kind,unit=unit,series=series,comparison_label=label,
        assumption=assumption,secondary=secondary)


def optional_context(label,operation):
    try: return dict(operation(),label=label)
    except Exception as exc: return {'label':label,'error':str(exc)[:300]}


def price_reference(series,baseline_year,target_year,today,period=None):
    from . import reference_sources as source
    column=2 if series=='s-ind_stpr-1-1' else -1
    rows,meta=source.smard_prices(series,column)
    pair=source.monthly_pair(rows,baseline_year,target_year,today,aggregate='mean',reporting_period=period)
    return dict(pair,**meta,kind='context',unit='ct/kWh',series=series,
        comparison_label='Modellierte Endkundenpreise' if series!='s-ind_stpr-1-1' else 'Industriepreis ohne Vergünstigungen',
        assumption='Preisvergleich für identische Monate. Die Modellpreise enthalten unterschiedliche Abgabenbestandteile; eine Absatz- oder Umsatzrechnung benötigt separat belegte Mengen, zugehörige Preise und dieselbe Abgabenbasis.')


def spot_reference(baseline_year,target_year,today,period=None):
    from . import reference_sources as source
    fetch_year=int(period['start'][:4]) if period and period.get('start') else baseline_year
    rows,meta=source.spot_monthly(fetch_year,target_year,today)
    pair=source.monthly_pair(rows,baseline_year,target_year,today,aggregate='mean',reporting_period=period)
    # Monthly means must also be weighted by actual hours (including DST).
    n=pair['months']
    def mean(year):
        dates={d[:7] for d in pair.get('baseline_comparison_dates',[])} if year==baseline_year and period else None
        selected=[r for r in rows if r['date'][:7] in dates] if dates else [r for r in rows if r['date'].startswith(str(year)) and int(r['date'][5:7])<=n]
        return sum(r['value']*r['hours'] for r in selected)/sum(r['hours'] for r in selected)
    full_dates={r['date'][:7] for r in rows if (period['start'][:7]<=r['date'][:7]<=period['end'][:7])} if period else {f'{baseline_year}-{m:02}' for m in range(1,13)}
    full_rows=[r for r in rows if r['date'][:7] in full_dates]
    annual_mean=sum(r['value']*r['hours'] for r in full_rows)/sum(r['hours'] for r in full_rows)
    pair.update(baseline=mean(baseline_year),target=mean(target_year),baseline_annual=annual_mean)
    return dict(pair,**meta,kind='context',unit='EUR/MWh',series='day_ahead_price',comparison_label='Day-ahead-Marktpreis DE-LU',
        assumption='Zeitgewichteter Marktpreis für identische Monate; Unternehmensverträge und Absicherung bleiben unberücksichtigt.')


def radiation_reference(location,baseline_year,target_year,today):
    from . import reference_sources as source
    rows,meta=source.weather_monthly(location,baseline_year,target_year,today,'shortwave_radiation_sum')
    pair=source.monthly_pair(rows,baseline_year,target_year,today)
    return dict(pair,**meta,kind='context',unit='MJ/m²',series='shortwave_radiation_sum',comparison_label='Horizontale Globalstrahlung',
        assumption='Strahlungsreferenz am Wetterort; PV-Ertrag benötigt zusätzlich Anlagenstandorte, Ausrichtung und Verfügbarkeit.')


def public_charger_reference(baseline_year,target_year,today,location):
    from . import reference_sources as source
    rows,meta=source.public_chargers(location)
    b=next((r for r in rows if r['date']==f'{baseline_year+1}-01-01'),None)
    targets=[r for r in rows if r['date'].startswith(str(target_year)) and date.fromisoformat(r['date'])<=today]
    if not b or not targets: raise ValueError('Historische und aktuelle Ladepunktstichtage fehlen.')
    t=max(targets,key=lambda r:r['date'])
    if t['date']<b['date']: raise ValueError('Ladepunktvergleich liegt vor dem Berichtsjahresende.')
    return {'baseline':b['value'],'target':t['value'],'baseline_date':b['date'],'target_date':t['date'],
        'history':[r for r in rows if b['date']<=r['date']<=t['date']],**meta,
        'kind':'context','unit':'öffentliche Ladepunkte','series':'public_charge_points',
        'comparison_label':'Öffentliche Ladepunkte / '+meta['geography'],
        'assumption':'Die Referenz umfasst öffentlich zugängliche Ladepunkte; Berichtsangaben können zusätzlich private/gewerbliche Anlagen enthalten. Deshalb wird ein Marktvergleich ohne automatische Hochrechnung der Unternehmenszahl dargestellt. Der Januar-Stichtag liegt einen Tag nach dem Berichtsjahresende.'}


def vehicle_reference(baseline_year,target_year,today,location):
    from . import reference_sources as source
    state=location.get('federal_state')
    rows,meta=source.kba_rows(state if state in source.GERMAN_STATES else None)
    b=next((r for r in rows if r['date']==f'{baseline_year+1}-01-01'),None)
    current=[r for r in rows if r['date'].startswith(str(target_year)) and date.fromisoformat(r['date'])<=today]
    if not b or not current: raise ValueError('Passende historische und aktuelle KBA-Stichtage fehlen.')
    t=max(current,key=lambda r:r['date'])
    if t['date']<b['date']: raise ValueError('KBA-Zielstichtag liegt vor dem historischen Bestand.')
    return {'baseline':b['value'],'target':t['value'],'baseline_date':b['date'],'target_date':t['date'],
        'history':[r for r in rows if b['date']<=r['date']<=t['date']],**meta,
        'kind':'context','unit':'BEV-Pkw','series':'Pkw_BEV','comparison_label':'BEV-Pkw-Bestand / '+meta['geography'],
        'assumption':'Regionaler Fahrzeugmarkt als Kontext. Januar-Stichtag liegt einen Tag nach dem Berichtsjahresende; Fahrzeuge und Ladepunkte werden nicht mengenmäßig gleichgesetzt.'}
