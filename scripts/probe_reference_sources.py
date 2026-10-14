"""Reproducible GET-only API probes. Standard library, no credentials.

Coverage counts describe returned data, not forecasting accuracy.
Run: python3 scripts/probe_reference_sources.py
"""
import concurrent.futures
import csv
import datetime
import hashlib
import io
import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / 'data' / 'research'
URLS = {
 'energy_capacity':'https://api.energy-charts.info/v2/installed_power?country=de&time_step=monthly',
 'energy_schema':'https://api.energy-charts.info/openapi.json',
 'weather_archive':'https://archive-api.open-meteo.com/v1/archive?latitude=50.7374&longitude=7.0982&start_date=2024-01-01&end_date=2026-10-01&daily=temperature_2m_mean,shortwave_radiation_sum&models=era5&timezone=Europe%2FBerlin',
 'weather_forecast':'https://api.open-meteo.com/v1/forecast?latitude=50.7374&longitude=7.0982&daily=temperature_2m_mean,shortwave_radiation_sum&forecast_days=7&timezone=Europe%2FBerlin',
 'ecb_credit':'https://data-api.ecb.europa.eu/service/data/MIR/M.DE.B.A2A.D.R.1.2240.EUR.N?startPeriod=2024-01&format=csvdata',
 'bundesbank_credit':'https://api.statistiken.bundesbank.de/rest/data/BBIM1/M.DE.B.A2A.D.R.1.2240.EUR.N?startPeriod=2024-01&format=csv',
 'smard_prices':'https://www.smard.de/resource/blob/217306/-/data-csv-data.csv',
 'kba_regions':'https://services-eu1.arcgis.com/U09msXRZoxesNntH/arcgis/rest/services/FZ%20Pkw%20mit%20Elektro%20Antrieb%20Regionen/FeatureServer?f=pjson',
 'energy_price':'https://api.energy-charts.info/v2/price?bzn=DE-LU&start=2024-01-01&end=2026-10-06',
 'gas_rlm':'https://www.bundesnetzagentur.de/SiteGlobals/Functions/SVG/_functions/csv_export.html?view=renderCSV&id=870314',
 'gas_slp':'https://www.bundesnetzagentur.de/SiteGlobals/Functions/SVG/_functions/csv_export.html?view=renderCSV&id=870322',
 'kba_nrw':"https://services-eu1.arcgis.com/U09msXRZoxesNntH/arcgis/rest/services/FZ%20Pkw%20mit%20Elektro%20Antrieb%20Regionen/FeatureServer/0/query?f=json&where=Bundesland%3D%27Nordrhein-Westfalen%27%20AND%20Zulassungsbezirk%3D%27%27%20AND%20Gemeinde%3D%27%27&outFields=Berichtszeitpunkt,Pkw_BEV,ZS_Pkw_BEV,Pkw_Elektro,ZS_Pkw_Elektro&returnGeometry=false&orderByFields=Berichtszeitpunkt",
 'kba_bonn_share':"https://services-eu1.arcgis.com/U09msXRZoxesNntH/arcgis/rest/services/FZ%20Pkw%20mit%20Elektro%20Antrieb%20Regionen/FeatureServer/0/query?f=json&where=Gemeindeschluessel%3D%2705314000%27&outFields=Berichtszeitpunkt,Pkw_Elektro_Anteil,ZS_Pkw_Elektro_Anteil&returnGeometry=false&orderByFields=Berichtszeitpunkt",
}

def probe(item):
 name,url=item
 result={'source':name,'url':url,'retrieved_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 try:
  with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Stadtwerke-MVP-research/0.1'}),timeout=30) as response:
   raw=response.read(); result.update(status=response.status,content_type=response.headers.get('Content-Type'))
  result.update(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
  content=raw.decode('utf-8-sig',errors='replace')
  extension='json' if content.lstrip().startswith(('{','[')) else 'csv'
  (ROOT/(name+'.'+extension)).write_bytes(raw)
  if extension=='json':
   obj=json.loads(content)
   if obj.get('error'): raise ValueError(str(obj['error']))
   if name in ('energy_capacity','energy_price'):
    result.update(available_from=obj.get('available_from'),available_until=obj.get('available_until'),series=obj.get('series'),license=obj.get('license'),last_records=obj['data'][-3:])
    result['year_counts']={str(y):sum(str(r.get('timestamp','')).startswith(str(y)) for r in obj['data']) for y in (2024,2025,2026)}
   elif name.startswith('weather'):
    result['units']=obj.get('daily_units'); result['year_counts']={str(y):sum(t.startswith(str(y)) for t in obj['daily']['time']) for y in (2024,2025,2026)}
    result['non_null_by_year']={str(y):{k:sum(v is not None for t,v in zip(obj['daily']['time'],values) if t.startswith(str(y))) for k,values in obj['daily'].items() if k!='time'} for y in (2024,2025,2026)}
    result.update(first=obj['daily']['time'][0],last=obj['daily']['time'][-1])
   elif name.startswith('kba_') and 'features' in obj:
    rows=[r['attributes'] for r in obj['features']]
    result['year_counts']={str(y):sum(r['Berichtszeitpunkt'].startswith(str(y)) for r in rows) for y in (2024,2025,2026)}
    result['last_records']=rows[-2:]
    result['exceeded_transfer_limit']=obj.get('exceededTransferLimit',False)
   elif name=='kba_regions': result['layers']=obj.get('layers'); result['tables']=obj.get('tables')
   else: result['paths']=list(obj.get('paths',{}))
  elif name=='bundesbank_credit':
   rows=[r for r in csv.reader(io.StringIO(content),delimiter=';') if r and len(r)>1 and len(r[0])==7 and r[0][4]=='-' and r[1]]
   result['year_counts']={str(y):sum(r[0].startswith(str(y)) for r in rows) for y in (2024,2025,2026)}
   result['last_records']=rows[-2:]
  elif name=='ecb_credit':
   rows=list(csv.DictReader(io.StringIO(content))); result['columns']=list(rows[0]) if rows else []
   result['year_counts']={str(y):sum(r.get('TIME_PERIOD','').startswith(str(y)) for r in rows) for y in (2024,2025,2026)}
   result['last_records']=rows[-2:]
  elif name.startswith('gas_'):
   rows=list(csv.DictReader(io.StringIO(content),delimiter=';'))
   result['year_counts']={str(y):sum(bool(r.get(str(y),'').strip()) for r in rows) for y in (2024,2025,2026)}
   result['last_available_week']={str(y):max(int(next(iter(r.values())).strip()) for r in rows if r.get(str(y),'').strip()) for y in (2024,2025,2026)}
  elif name=='smard_prices':
   rows=list(csv.reader(io.StringIO(content),delimiter=';'))
   ids=['s-mdl_stpr-1-1','s-mdl_stpr-1-2','s-ind_stpr-1-1','g-mdl_gspr-1-1','g-mdl_gspr-1-2','s-mdl_dyn_stpr-1-1']
   result['selected_series']={s:{'year_counts':{str(y):sum(r[0]==s and r[1].startswith(str(y)) and bool(r[-1].strip()) for r in rows if len(r)>2) for y in (2024,2025,2026)},'latest':max(r[1] for r in rows if len(r)>2 and r[0]==s)} for s in ids}
  else: result['head']=content[:3500]; result['tail']=content[-1500:]
 except Exception as exc: result['error']=str(exc)
 return result

if __name__=='__main__':
 ROOT.mkdir(parents=True,exist_ok=True)
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool: results=list(pool.map(probe,URLS.items()))
 (ROOT/'api_checks.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
 for result in results:
  summary={k:v for k,v in result.items() if k not in ('last_records','paths','head','tail','series')}
  if 'last_records' in result: summary['last_sample']=result['last_records'][-1]
  if 'head' in result: summary['head']=result['head'][:2300]
  print(json.dumps(summary,ensure_ascii=False))
