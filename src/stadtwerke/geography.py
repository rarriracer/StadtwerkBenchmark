"""Public municipality lookup, independent of utility-specific names.

A headquarters lookup NEVER releases the geography of a national/group asset
portfolio. It may only support an explicitly local municipal site cohort.
"""
import hashlib
import json
import re
from datetime import datetime, timezone
import httpx
from .config import RUNTIME

URL = 'https://openplzapi.org/de/Localities'


def municipality_context(company, city=''):
    if not city:
        match = re.search(r'\bStadtwerke\s+(?:der Stadt\s+)?([A-ZÄÖÜ][\wäöüß-]+)', company)
        city = match[1] if match else ''
    if not city:
        return {'country': 'unknown', 'reason': 'Kein Ort angegeben oder eindeutig im Unternehmensnamen enthalten.'}
    key = hashlib.sha256(city.casefold().encode()).hexdigest()[:20]
    cache = RUNTIME / f'municipality-{key}.json'
    if cache.exists():
        return json.loads(cache.read_text())
    try:
        response = httpx.get(URL, params={'name': '^'+re.escape(city)+'$', 'pageSize':50}, timeout=12)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload,list) or any(not isinstance(r,dict) for r in payload):
            raise ValueError('Unerwartetes Ortsverzeichnis-Schema')
        matches = [r for r in payload if r.get('name','').casefold()==city.casefold()]
        states = {r.get('federalState',{}).get('name') for r in matches}
        if not matches or len(states)!=1:
            return {'country':'unknown','city':city,'reason':'Ort nicht eindeutig im deutschen Ortsverzeichnis gefunden.'}
        result = {'country':'DE','city':city,'federal_state':next(iter(states)),
                  'source':str(response.url),'fetched_at':datetime.now(timezone.utc).isoformat(),
                  'sha256':hashlib.sha256(response.content).hexdigest(),
                  'usage':'Nur örtliche kommunale Teilbestände; kein Nachweis für den gesamten Anlagenbestand.'}
        cache.write_text(json.dumps(result,ensure_ascii=False,indent=2))
        return result
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        return {'country':'unknown','city':city,'reason':'Ortszuordnung nicht verfügbar: '+str(exc)[:160]}


def portfolio_geography(evidence, subset='', location=None):
    # A foreign/mixed asset location in the very same statement takes priority.
    if re.search(r'Ausland|weltweit|international|Niederlanden|Frankreich|Österreich|Schweiz|Belgien|Spanien|Polen|Italien|Luxemburg', evidence,re.I):
        return 'unknown', 'Auslands-/Mischbestand im Beleg; geografische Abgrenzung prüfen.'
    if re.search(r'\bin Deutschland\b|\bdeutschlandweit\b|\bdeutschen (?:Anlagen|Standorten|Liegenschaften)\b',evidence,re.I):
        return 'DE', 'Deutschlandbezug im Originalbeleg.'
    other_locations = re.findall(r'\b(?:in|im)\s+(?:den\s+|der\s+)?([A-ZÄÖÜ][\wäöüß-]+)',evidence)
    safe_context = {'Betrieb','Deutschland','Jahr','Berichtsjahr','Bestand'}
    if any(place not in safe_context and (not location or place!=location.get('city')) for place in other_locations):
        return 'unknown', 'Zusätzliche Ortsangabe im Beleg; Standorte gezielt prüfen.'
    local = bool(subset and re.search(r'städtisch|kommunal|Gemeinde|Stadtgebiet',subset,re.I))
    if local and location and location.get('country')=='DE':
        return 'DE', f"Örtlicher kommunaler Teilbestand; {location['city']} über öffentliches Ortsverzeichnis zugeordnet."
    return 'unknown', 'Standorte dieses Bestands nicht eindeutig in Deutschland belegt.'
