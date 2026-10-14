"""Public read-only clients. Cache raw replies and preserve attribution/provenance."""
import calendar
import base64
import zipfile
import xml.etree.ElementTree as ET
import html
from urllib.parse import urljoin
import csv
import hashlib
import io
import json
import math
import os
import re
import time
import uuid
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import httpx
from .config import RUNTIME

BERLIN = ZoneInfo('Europe/Berlin')
GAS_URL = 'https://www.bundesnetzagentur.de/SiteGlobals/Functions/SVG/_functions/csv_export.html'
SMARD_URL = 'https://www.smard.de/app/chart_data'
SMARD_PRICES_URL = 'https://www.smard.de/resource/blob/217306/-/data-csv-data.csv'
CREDIT_KEY = 'M.DE.B.A2A.D.R.1.2240.EUR.N'
KBA_URL = 'https://services-eu1.arcgis.com/U09msXRZoxesNntH/arcgis/rest/services/FZ%20Pkw%20mit%20Elektro%20Antrieb%20Regionen/FeatureServer/0/query'
GERMAN_STATES = {'Baden-Württemberg','Bayern','Berlin','Brandenburg','Bremen','Hamburg','Hessen',
    'Mecklenburg-Vorpommern','Niedersachsen','Nordrhein-Westfalen','Rheinland-Pfalz','Saarland',
    'Sachsen','Sachsen-Anhalt','Schleswig-Holstein','Thüringen'}


def get_record(url, params=None, ttl=21600, binary=False):
    """Never label an old cached reply as freshly fetched or hide a failure."""
    key = hashlib.sha256((url+json.dumps(params or {},sort_keys=True)+str(binary)).encode()).hexdigest()
    cache = RUNTIME / ('reference-'+key+'.json')
    old = json.loads(cache.read_text()) if cache.exists() else None
    now = datetime.now(timezone.utc)
    if old and now.timestamp()-old['fetched_timestamp'] < ttl:
        return old
    for attempt in range(2):
        try:
            response=httpx.get(url,params=params,timeout=25,follow_redirects=True,
                headers={'User-Agent':'Stadtwerke-Analyst/0.1 (public reference data)'})
            if response.status_code in (429,503) and not attempt:
                try: delay=min(2,max(0,float(response.headers.get('Retry-After','1'))))
                except ValueError: delay=1
                time.sleep(delay)
                continue
            response.raise_for_status()
            record={'url':str(response.url),'text':base64.b64encode(response.content).decode('ascii') if binary else response.content.decode('utf-8-sig'),
                'fetched_at':now.isoformat(),'fetched_timestamp':now.timestamp(),
                'sha256':hashlib.sha256(response.content).hexdigest()}
            temp=cache.with_suffix('.'+uuid.uuid4().hex+'.tmp')
            temp.write_text(json.dumps(record,ensure_ascii=False));os.replace(temp,cache)
            return record
        except httpx.HTTPError:
            if attempt: raise
    raise ValueError('Referenzquelle konnte nicht abgerufen werden.')


def provenance(records, provider, license, **extra):
    return {'provider':provider,'license':license,'url':records[0]['url'],
        'fetched_at':max(r['fetched_at'] for r in records),
        'sha256':hashlib.sha256(''.join(r['sha256'] for r in records).encode()).hexdigest(),
        'sources':[{k:r[k] for k in ('url','fetched_at','sha256')} for r in records],**extra}


def number(value, decimal_comma=False):
    if value is None or isinstance(value,bool): raise ValueError('Fehlender numerischer Referenzwert.')
    if decimal_comma: value=str(value).replace('.','').replace(',','.')
    result=float(value)
    if not math.isfinite(result): raise ValueError('Nicht endlicher Referenzwert.')
    return result


def month_end(year, month):
    return date(year,month,calendar.monthrange(year,month)[1])


def monthly_pair(rows, baseline_year, target_year, today, aggregate='sum', require_full_base=True, reporting_period=None):
    """Use a contiguous January-to-month period on both sides; never fill gaps."""
    by_date={}
    for row in rows:
        key=(int(row['date'][:4]),int(row['date'][5:7]))
        val=number(row['value'])
        if key in by_date and by_date[key]!=val: raise ValueError('Widersprüchliche Monatswerte.')
        by_date[key]=val
    if reporting_period:
        start=reporting_period.get('start');end=reporting_period.get('end')
        if not start or not end:raise ValueError('Für den Geschäftsjahresvergleich fehlen belegte Beginn- und Enddaten.')
        begin=date.fromisoformat(start);finish=date.fromisoformat(end)
        sequence=[(begin.year+(begin.month-1+i)//12,(begin.month-1+i)%12+1) for i in range(12)]
        if begin.day!=1 or sequence[-1]!=(finish.year,finish.month) or finish.day!=month_end(finish.year,finish.month).day:
            raise ValueError('Die Berichtsperiode ist kein vollständiges Geschäftsjahr aus zwölf Monaten.')
        full=[by_date.get(k) for k in sequence]
        if any(v is None for v in full):raise ValueError('Das Geschäftsjahr ist in der Referenz nicht vollständig vorhanden.')
        if target_year<=finish.year:raise ValueError('Der aktuelle Vergleich muss nach dem abgeschlossenen Geschäftsjahr liegen.')
        historic=[];current=[];history=[];historic_dates=[]
        for m in range(1,13):
            if month_end(target_year,m)>today or (target_year,m) not in by_date:break
            historical_key=next(k for k in sequence if k[1]==m)
            h=by_date[historical_key];v=by_date[target_year,m]
            historic.append(h);current.append(v)
            historic_dates.append(month_end(*historical_key).isoformat())
            history.append({'date':month_end(target_year,m).isoformat(),'value':v,'baseline_value':h,
                'baseline_date':historic_dates[-1]})
        if not history:raise ValueError('Keine abgeschlossenen aktuellen Referenzmonate vorhanden.')
        reducer=(lambda v:sum(v)/len(v)) if aggregate=='mean' else (lambda v:v[-1]) if aggregate=='last' else sum
        return {'baseline':reducer(historic),'target':reducer(current),'baseline_annual':reducer(full),
            'baseline_date':historic_dates[-1],'target_date':history[-1]['date'],
            'baseline_start':historic_dates[0][:7]+'-01','target_start':f'{target_year}-01-01',
            'months':len(history),'history':history,'aggregation':aggregate,
            'reporting_period':reporting_period,'baseline_comparison_dates':historic_dates}
    if target_year<baseline_year: raise ValueError('Das Zieljahr liegt vor dem Berichtsjahr.')
    full=[by_date.get((baseline_year,m)) for m in range(1,13)]
    if require_full_base and any(v is None for v in full):
        raise ValueError('Das Berichtsjahr ist in der Referenz nicht vollständig vorhanden.')
    final=0
    for m in range(1,13):
        if month_end(target_year,m)>today or (target_year,m) not in by_date: break
        if (baseline_year,m) not in by_date: raise ValueError('Historischer Vergleichsmonat fehlt.')
        final=m
    if not final: raise ValueError('Keine abgeschlossenen aktuellen Referenzmonate vorhanden.')
    reducer=(lambda v:sum(v)/len(v)) if aggregate=='mean' else (lambda v:v[-1]) if aggregate=='last' else sum
    historic=[by_date[baseline_year,m] for m in range(1,final+1)]
    current=[by_date[target_year,m] for m in range(1,final+1)]
    return {'baseline':reducer(historic),'target':reducer(current),
        'baseline_annual':reducer(full) if all(v is not None for v in full) else None,
        'baseline_date':month_end(baseline_year,final).isoformat(),
        'target_date':month_end(target_year,final).isoformat(),
        'baseline_start':f'{baseline_year}-01-01','target_start':f'{target_year}-01-01',
        'months':final,'history':[{'date':month_end(target_year,m).isoformat(),
            'value':by_date[target_year,m],'baseline_value':by_date[baseline_year,m]} for m in range(1,final+1)],
        'aggregation':aggregate}


def smard_monthly(filter_id, baseline_year, target_year):
    index=get_record(f'{SMARD_URL}/{filter_id}/DE/index_month.json')
    stamps=json.loads(index['text']).get('timestamps',[])
    records=[index];rows=[]
    for year in range(baseline_year,target_year+1):
        chunks=[s for s in stamps if datetime.fromtimestamp(s/1000,BERLIN).year==year]
        if not chunks: raise ValueError(f'SMARD enthält kein Monatsfenster für {year}.')
        for stamp in chunks:
            record=get_record(f'{SMARD_URL}/{filter_id}/DE/{filter_id}_DE_month_{stamp}.json')
            payload=json.loads(record['text'])
            if not isinstance(payload.get('series'),list): raise ValueError('Unerwartetes SMARD-Schema.')
            records.append(record)
            for ts,value in payload['series']:
                day=datetime.fromtimestamp(ts/1000,BERLIN).date()
                if value is not None and day.year==year:
                    rows.append({'date':day.isoformat(),'value':number(value)})
    return rows,provenance(records,'SMARD / Bundesnetzagentur / ENTSO-E',
        'SMARD-Daten unter Namensnennung; Quellenhinweise der Bundesnetzagentur beachten.',geography='Deutschland')


def gas_monthly(segment):
    identifier={'slp':'870320','rlm':'870312'}[segment]
    record=get_record(GAS_URL,{'view':'renderCSV','id':identifier})
    parsed=list(csv.reader(io.StringIO(record['text']),delimiter=';'))
    if not parsed: raise ValueError('Leere Gasreferenz.')
    years={i:int(s) for i,s in enumerate(parsed[0]) if re.fullmatch(r'20\d\d',s.strip())}
    if not years: raise ValueError('Gasreferenz enthält keine Jahresüberschriften.')
    rows=[]
    for row in parsed[1:]:
        if not row or not row[0].strip(): continue
        month=int(row[0]);
        if not 1<=month<=12: raise ValueError('Unerwartete Monatsnummer in Gasreferenz.')
        for col,year in years.items():
            if col<len(row) and row[col].strip():
                daily_gwh=number(row[col],decimal_comma=True)
                if daily_gwh<0: raise ValueError('Negativer Gasverbrauch.')
                rows.append({'date':f'{year}-{month:02}-01','value':daily_gwh*calendar.monthrange(year,month)[1]*1000})
    return rows,provenance([record],'Bundesnetzagentur / Trading Hub Europe',
        'Quelle: Trading Hub Europe (THE), Bundesnetzagentur.',geography='Deutschland',
        conversion='Veröffentlichter gerundeter Tagesmittelwert GWh/Tag × Kalendertage × 1.000 ≈ MWh.')


def smard_prices(series, column=-1):
    record=get_record(SMARD_PRICES_URL)
    rows=[]
    for row in csv.reader(io.StringIO(record['text']),delimiter=';'):
        if len(row)<3 or row[0]!=series: continue
        if not re.fullmatch(r'20\d\d-\d\d-\d\d',row[1]): raise ValueError('Unerwartetes Preisdatum.')
        raw=row[column]
        if raw.strip(): rows.append({'date':row[1],'value':number(raw)})
    if not rows: raise ValueError('SMARD-Preisreihe nicht mehr im Datenexport vorhanden.')
    return rows,provenance([record],'SMARD / Bundesnetzagentur',
        'SMARD unter Namensnennung; modellierte Endkundenpreise.',geography='Deutschland')


def credit_rates():
    errors=[]
    for provider,url,params in [
        ('Deutsche Bundesbank',f'https://api.statistiken.bundesbank.de/rest/data/BBIM1/{CREDIT_KEY}',{'startPeriod':'2023-01','format':'csv'}),
        ('Europäische Zentralbank',f'https://data-api.ecb.europa.eu/service/data/MIR/{CREDIT_KEY}',{'startPeriod':'2023-01','format':'csvdata'})]:
        try:
            record=get_record(url,params);rows=[]
            if provider=='Deutsche Bundesbank':
                for row in csv.reader(io.StringIO(record['text']),delimiter=';'):
                    if len(row)>1 and re.fullmatch(r'20\d\d-\d\d',row[0]) and row[1].strip():
                        rows.append({'date':row[0]+'-01','value':number(row[1],True),'provisional':len(row)>2 and bool(row[2].strip())})
            else:
                for row in csv.DictReader(io.StringIO(record['text'])):
                    if row.get('OBS_VALUE','').strip():
                        if row.get('UNIT')!='PCPA': raise ValueError('Unpassende Zinsreferenzeinheit.')
                        rows.append({'date':row['TIME_PERIOD']+'-01','value':number(row['OBS_VALUE']),
                            'provisional':row.get('OBS_STATUS') not in ('A','')})
            if not rows: raise ValueError('Keine Kreditzinsen im erwarteten Schema.')
            return rows,provenance([record],provider,'Quelle: Deutsche Bundesbank / EZB, MIR-Zinsstatistik.',
                geography='Deutschland',fallback_notes=errors,
                series_description='Neue Unternehmenskredite über 1 Mio. EUR, variabel oder Zinsbindung bis drei Monate.')
        except (httpx.HTTPError,ValueError,KeyError) as exc:
            errors.append(provider+': '+str(exc)[:180])
    raise ValueError('Kreditzinsreferenz nicht erreichbar: '+'; '.join(errors))


def geocode(location):
    city=location.get('city','')
    if not city: raise ValueError('Für die örtliche Wetterreferenz fehlt eine eindeutig zugeordnete Stadt.')
    record=get_record('https://geocoding-api.open-meteo.com/v1/search',
        {'name':city,'countryCode':'DE','language':'de','count':100},ttl=30*86400)
    matches=[r for r in json.loads(record['text']).get('results',[]) if r.get('country_code')=='DE' and r.get('name','').casefold()==city.casefold()]
    state=location.get('federal_state')
    if state: matches=[r for r in matches if r.get('admin1')==state]
    if len(matches)!=1: raise ValueError('Wetterort nicht eindeutig; keine automatische Ortsannahme.')
    return matches[0],record


def weather_monthly(location, baseline_year, target_year, today, variable='temperature_2m_mean'):
    place,geo=geocode(location)
    end=min(today-timedelta(days=1),date(target_year,12,31))
    record=get_record('https://archive-api.open-meteo.com/v1/archive',{
        'latitude':place['latitude'],'longitude':place['longitude'],
        'start_date':f'{min(baseline_year,target_year)}-01-01','end_date':end.isoformat(),
        'daily':variable,'models':'era5','timezone':'Europe/Berlin'})
    payload=json.loads(record['text']);unit=payload.get('daily_units',{}).get(variable)
    if unit!=('°C' if variable=='temperature_2m_mean' else 'MJ/m²'):
        raise ValueError('Unpassende Wetterreferenzeinheit.')
    daily=payload.get('daily',{});dates=daily.get('time',[]);values=daily.get(variable,[])
    if len(dates)!=len(values): raise ValueError('Wetterdaten enthalten widersprüchliche Tageslängen.')
    months=defaultdict(dict)
    for label,val in zip(dates,values):
        day=date.fromisoformat(label)
        if val is not None:
            v=number(val)
            months[day.year,day.month][day.day]=max(20-v,0) if variable=='temperature_2m_mean' and v<15 else 0 if variable=='temperature_2m_mean' else v
    rows=[]
    for (year,month),days in months.items():
        if set(days)==set(range(1,calendar.monthrange(year,month)[1]+1)):
            rows.append({'date':f'{year}-{month:02}-01','value':sum(days.values())})
    return rows,provenance([record,geo],'Open-Meteo / ECMWF ERA5 / GeoNames',
        'Wetterdaten CC BY 4.0; kostenlose API für nicht kommerzielle Nutzung.',
        geography=place['name'],coordinates={'latitude':place['latitude'],'longitude':place['longitude']},
        model='ERA5',conversion='Heizgradtag-Proxy: 20 − Tagesmitteltemperatur für Tage unter 15 °C.' if variable=='temperature_2m_mean' else 'Summe horizontaler Globalstrahlung MJ/m².')


def weather_forecast(location):
    place,geo=geocode(location)
    record=get_record('https://api.open-meteo.com/v1/forecast',{'latitude':place['latitude'],'longitude':place['longitude'],
        'daily':'temperature_2m_mean,shortwave_radiation_sum','forecast_days':7,'timezone':'Europe/Berlin'},ttl=3600)
    payload=json.loads(record['text'])
    if not isinstance(payload.get('daily',{}).get('time'),list): raise ValueError('Unerwartetes Wettervorhersageschema.')
    return {'daily':payload['daily'],'units':payload['daily_units'],'kind':'forecast',
        **provenance([record,geo],'Open-Meteo','Wetterdaten CC BY 4.0; kostenlose API für nicht kommerzielle Nutzung.',geography=place['name'])}


def kba_rows(state=None):
    clauses="Zulassungsbezirk='' AND Gemeinde=''"
    if state: clauses+=" AND Bundesland='"+state.replace("'","''")+"'"
    records=[];features=[];offset=0
    while True:
        record=get_record(KBA_URL,{'f':'json','where':clauses,'outFields':'Berichtszeitpunkt,Bundesland,Pkw_BEV,ZS_Pkw_BEV,Pkw_Plug_In_Hybrid,ZS_Pkw_Plug_In_Hybrid',
            'returnGeometry':'false','orderByFields':'Berichtszeitpunkt,Bundesland','resultOffset':offset,'resultRecordCount':1000})
        payload=json.loads(record['text'])
        if payload.get('error'): raise ValueError('KBA-Abfrage wurde abgewiesen.')
        batch=payload.get('features')
        if not isinstance(batch,list): raise ValueError('Unerwartetes KBA-Schema.')
        records.append(record);features.extend(f['attributes'] for f in batch)
        if not payload.get('exceededTransferLimit'): break
        if not batch: raise ValueError('KBA-Paginierung bleibt ohne Fortschritt.')
        offset+=len(batch)
        if offset>10000: raise ValueError('KBA-Abfrage überschreitet erwartete Bundeslanddaten.')
    grouped=defaultdict(dict)
    for attr in features:
        label=attr['Berichtszeitpunkt'];region=attr['Bundesland']
        if region not in GERMAN_STATES: continue
        if attr.get('ZS_Pkw_BEV') not in ('',None): continue
        val=number(attr['Pkw_BEV'])
        if val<0: raise ValueError('Negativer Fahrzeugbestand.')
        if region in grouped[label]: raise ValueError('Doppelte aggregierte KBA-Gebietszeile.')
        grouped[label][region]=val
    rows=[]
    required={state} if state else GERMAN_STATES
    for label,regions in grouped.items():
        if set(regions)!=required: continue
        year,month=map(int,label.split('.'))
        rows.append({'date':date(year,month,1).isoformat(),'value':sum(regions.values())})
    if not rows: raise ValueError('Kein freigegebener regional passender KBA-Bestand verfügbar.')
    return rows,provenance(records,'Kraftfahrt-Bundesamt','Datenlizenz Deutschland – Namensnennung 2.0; KBA.',
        geography=state or 'Deutschland',series_description='BEV-Pkw-Bestand; keine Ladepunktzahl. Vertraulichkeitskennzeichen werden ausgewertet.')


def spot_monthly(baseline_year,target_year,today):
    cutoff=min(date(target_year,12,31),today.replace(day=1)-timedelta(days=1))
    record=get_record('https://api.energy-charts.info/v2/price',{'bzn':'DE-LU','start':f'{min(baseline_year,target_year)}-01-01','end':cutoff.isoformat()})
    payload=json.loads(record['text'])
    if payload.get('endpoint')!='price' or payload.get('unit','').replace(' ','')!='EUR/MWh': raise ValueError('Unpassendes Day-ahead-Schema.')
    rows=payload.get('data',[]);months=defaultdict(lambda:[0,0])
    for i,row in enumerate(rows):
        instant=datetime.fromisoformat(row['timestamp']);price=row['values'].get('day_ahead_price')
        if price is None: raise ValueError('Fehlender Day-ahead-Wert; kein stilles Auffüllen.')
        end=datetime.fromisoformat(rows[i+1]['timestamp']) if i+1<len(rows) else instant+(instant.astimezone(timezone.utc)-datetime.fromisoformat(rows[i-1]['timestamp']).astimezone(timezone.utc)) if i else instant+timedelta(hours=1)
        hours=(end.astimezone(timezone.utc)-instant.astimezone(timezone.utc)).total_seconds()/3600
        if hours not in (.25,1): raise ValueError('Lücke oder unbekannte Auflösung in Day-ahead-Preisen.')
        local=instant.astimezone(BERLIN);key=(local.year,local.month)
        months[key][0]+=number(price)*hours;months[key][1]+=hours
    result=[]
    for (year,month),(area,hours) in months.items():
        start=datetime(year,month,1,tzinfo=BERLIN)
        end=datetime(year+1,1,1,tzinfo=BERLIN) if month==12 else datetime(year,month+1,1,tzinfo=BERLIN)
        expected=(end.astimezone(timezone.utc)-start.astimezone(timezone.utc)).total_seconds()/3600
        if abs(hours-expected)<.01: result.append({'date':start.date().isoformat(),'value':area/hours,'hours':hours})
    return result,provenance([record],'Energy-Charts / Bundesnetzagentur / SMARD',payload.get('license',''),geography='DE-LU',
        conversion='Day-ahead-Mittel nach Intervalldauer gewichtet; Stunden- und Viertelstundenwerte bleiben zeitlich gleich gewichtet.')


CHARGER_PAGE='https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/E-Mobilitaet/Ladesaeulenkarte/start.html'
CHARGER_STATS='https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/E-Mobilitaet/_DL/Ladesaeuleninfrastruktur.xlsx'


def xlsx_tables(raw):
    """Read cached OOXML cell values, including hidden historical columns."""
    ns={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        if sum(i.file_size for i in archive.infolist())>40_000_000:
            raise ValueError('Ladeinfrastrukturdatei überschreitet erwartete Größe.')
        strings=[]
        if 'xl/sharedStrings.xml' in archive.namelist():
            strings=[''.join(si.itertext()) for si in ET.fromstring(archive.read('xl/sharedStrings.xml'))]
        props=ET.fromstring(archive.read('xl/workbook.xml')).find('m:workbookPr',ns)
        epoch=date(1904,1,1) if props is not None and props.get('date1904') in ('1','true') else date(1899,12,30)
        tables=[]
        for name in archive.namelist():
            if not re.fullmatch(r'xl/worksheets/sheet\d+.xml',name): continue
            table=[]
            for row in ET.fromstring(archive.read(name)).findall('.//m:row',ns):
                cells={}
                for cell in row.findall('m:c',ns):
                    value=cell.findtext('m:v',default='',namespaces=ns)
                    if cell.get('t')=='s': value=strings[int(value)] if value else ''
                    elif cell.get('t')=='inlineStr': value=''.join(cell.find('m:is',ns).itertext())
                    cells[re.sub(r'\d','',cell.get('r',''))]=value
                table.append(cells)
            tables.append(table)
        return tables,epoch


def column_number(label):
    result=0
    for char in label: result=result*26+ord(char)-64
    return result


def column_label(n):
    result=''
    while n:
        n,remainder=divmod(n-1,26);result=chr(65+remainder)+result
    return result


def parse_public_chargers(raw, location):
    tables,epoch=xlsx_tables(raw)
    city=location.get('city','');state=location.get('federal_state','')
    # Exact city matches only; a Landkreis is not automatically a city.
    for level in ('city','state','country'):
        for table in tables:
            title=' '.join(table[1].values()) if len(table)>1 else ''
            wanted=('Ladepunkte je Kreis' in title if level=='city' else 'Ladepunkte je Bundesland' in title if level=='state' else 'Ladepunkte in Deutschland' in title)
            if not wanted: continue
            row=None
            if level=='city' and city:
                candidates=[r for r in table if r.get('E') in ('Kreisfreie Stadt '+city,'Stadt '+city)
                    and (not state or r.get('F')==state)]
                if len(candidates)==1: row=candidates[0]
            elif level=='state' and state:
                candidates=[r for r in table if r.get('E')==state]
                if len(candidates)==1: row=candidates[0]
            elif level=='country':
                row=next((r for r in table if r.get('E')=='Ladepunkte insgesamt'),None)
            if row is None: continue
            header=next((r for r in table if sum(bool(re.fullmatch(r'\d{5}(?:\.0)?',v)) for v in r.values())>=8),None)
            if not header: raise ValueError('Ladepunktstatistik enthält keine historische Datumskopfzeile.')
            rows=[]
            for col,value in header.items():
                if not re.fullmatch(r'\d{5}(?:\.0)?',value): continue
                day=epoch+timedelta(days=int(float(value)))
                if not 2016<=day.year<=2100: continue
                data_col=col if level=='country' else column_label(column_number(col)+2)
                raw_value=row.get(data_col,'')
                if raw_value:
                    val=number(raw_value)
                    if val<0: raise ValueError('Negativer Ladepunktbestand.')
                    rows.append({'date':day.isoformat(),'value':val})
            if rows: return rows,city if level=='city' else state if level=='state' else 'Deutschland',level
    raise ValueError('Historische Ladepunktstatistik hat ein unbekanntes Schema.')


def public_chargers(location):
    page=get_record(CHARGER_PAGE)
    links=re.findall(r'href=["\']([^"\']*Ladesaeuleninfrastruktur\.xlsx[^"\']*)["\']',page['text'],re.I)
    url=urljoin(CHARGER_PAGE,html.unescape(links[0])) if links else CHARGER_STATS+'?__blob=publicationFile'
    record=get_record(url,binary=True)
    rows,region,level=parse_public_chargers(base64.b64decode(record['text']),location)
    return rows,provenance([record,page],'Bundesnetzagentur / Ladesäulenregister',
        'Quelle: Bundesnetzagentur, Ladeinfrastruktur in Zahlen.',geography=region,geography_level=level,
        series_description='Historische öffentlich zugängliche Ladepunkte, veröffentlicht in derselben Statistikversion; private Ladepunkte sind nicht enthalten.')


def water_price_index(sewerage=False):
    """Current ECOICOP v2 series, including comparable historical back series."""
    code='CP0443' if sewerage else 'CP0441'
    record=get_record('https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/prc_hicp_minr',
        {'geo':'DE','coicop18':code,'unit':'I25','freq':'M','sinceTimePeriod':'2023-01','lang':'EN'})
    payload=json.loads(record['text']);ids=payload.get('id',[]);sizes=payload.get('size',[])
    if ids!=['freq','unit','coicop18','geo','time'] or len(sizes)!=5 or sizes[:4]!=[1,1,1,1]:
        raise ValueError('Unpassende oder mehrdeutige Eurostat-Preisreihe.')
    dimensions=payload.get('dimension',{})
    for dimension,code_expected in [('freq','M'),('unit','I25'),('coicop18',code),('geo','DE')]:
        if dimensions.get(dimension,{}).get('category',{}).get('index')!={code_expected:0}:
            raise ValueError('Klassifikation oder Indexbasis der Preisreferenz verändert.')
    timeline=dimensions['time']['category']['index'];values=payload.get('value',{})
    if isinstance(values,list):values={str(i):v for i,v in enumerate(values) if v is not None}
    rows=[]
    for period,index in sorted(timeline.items()):
        if not re.fullmatch(r'20\d\d-\d\d',period):raise ValueError('Unpassendes Eurostat-Monatsdatum.')
        raw=values.get(str(index))
        if raw is not None:
            value=number(raw)
            if value<=0:raise ValueError('Nicht positiver Preisindex.')
            rows.append({'date':period+'-01','value':value})
    if not rows:raise ValueError('Keine historischen und aktuellen Wasserpreiswerte vorhanden.')
    return rows,provenance([record],'Eurostat / HVPI',
        'Quelle: Eurostat, harmonisierter Verbraucherpreisindex; Wiederverwendung mit Quellenangabe.',
        geography='Deutschland',index_base='2025 = 100',classification='ECOICOP Version 2',
        series_description='Abwasserentsorgung' if sewerage else 'Wasserversorgung',dataset='prc_hicp_minr',category=code,
        published_at=payload.get('updated',''))
