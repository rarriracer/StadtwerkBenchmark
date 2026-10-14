"""Keep fiscal-year labels and source-backed calendar boundaries separate."""
import calendar
import json
import re
from pathlib import Path
from .config import ROOT


def reporting_period(pages, detection):
    if not detection or detection.get('period_kind')!='fiscal_year':return None
    period={'label':detection['period_label'],'year':detection['year'],'kind':'fiscal_year'}
    text='\n'.join(p['text'] for p in pages)
    # Exact dates in the source take precedence over a registered calendar.
    dates=re.search(r'(?:Geschäftsjahr|Berichtszeitraum)[^\n]{0,50}(\d{1,2})\.(\d{1,2})\.(20\d\d)\s*(?:bis|[–−-])\s*(\d{1,2})\.(\d{1,2})\.(20\d\d)',text,re.I)
    if dates and int(dates[3])==detection['start_year'] and int(dates[6])==detection['year']:
        from datetime import date
        start=date(int(dates[3]),int(dates[2]),int(dates[1]));end=date(int(dates[6]),int(dates[5]),int(dates[4]))
        period.update(start=start.isoformat(),end=end.isoformat(),evidence=dates[0],source='Originalbericht')
        return period
    catalog=ROOT/'data/reporting-calendars.json'
    for entry in json.loads(catalog.read_text()) if catalog.exists() else []:
        domain=entry['domain']
        imprint='\n'.join(p['text'] for p in pages if re.search(r'\bImpressum\b',p['text'],re.I))
        if not re.search(r'(?<![\w.-])(?:www\.)?'+re.escape(domain)+r'(?![\w.-])',imprint,re.I):continue
        year=detection['year'];month=entry['start_month'];end_month=12 if month==1 else month-1
        period.update(start=f'{year if month==1 else year-1}-{month:02d}-01',end=f'{year}-{end_month:02d}-{calendar.monthrange(year,end_month)[1]}',
            source=entry['source'],evidence=entry['evidence'],verified_at=entry['verified_at'])
        return period
    return period
