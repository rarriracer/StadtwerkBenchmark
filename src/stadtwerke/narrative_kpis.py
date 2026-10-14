"""Literal annual volume statements governed by an explicit report/section year."""
import re
from .models import Candidate
from .documents import evidence_span


def annual_narrative_facts(page, report_year):
    rows=[]
    for region in page.get('narrative_regions',[]) or [page['text']]:
        rows.extend(_region_facts(page,report_year,region))
    return rows


def _region_facts(page, report_year, region):
    from .extraction import normalize_number, normalize_unit, validate
    joined=re.sub(r'(?<=[A-Za-zÄÖÜäöüß])[-\u00ad][ \t]*\r?\n[ \t]*(?=[a-zäöüß])','',region)
    text=re.sub(r'\s+',' ',joined)
    heading=re.search(r'Geschäftsbericht\s+'+str(report_year)+r'\s*[–-]\s*Lagebericht',text,re.I)
    patterns=[
        ('electricity_sales_total',r'Stromgesamtabsatz im Endkundengeschäft von',r'GWh|MWh|kWh'),
        ('gas_sales_total',r'In der Sparte Erdgas\b.{0,400}?Gesamtabsatz von',r'GWh|MWh|kWh'),
        ('heat_sales',r'Fernwärmeabsatz lag mit',r'GWh|MWh|kWh'),
        ('water_sales',r'Wasserabsatz\b.{0,120}?Absatzvolumen von',r'Mio\.?\s*m³|Mio\.?\s*m3'),
        ('heat_sales',r'Die Absatzmenge Wärme betrug',r'Megawattstunden|MWh'),
    ]
    # Explicit current-period statements retain their previous-year comparison
    # in the quote; only the first labelled current value is extracted.
    patterns += [
        ('electricity_sales_total',r'Im Medium Strom lag der Absatz mit',r'GWh|MWh|kWh'),
        ('gas_sales_total',r'Im Medium Gas erhöhte sich der Absatz[^.!?]{0,160}?auf',r'GWh|MWh|kWh'),
        ('heat_sales',r'(?:Der )?Fernwärmeabsatz[^.!?]{0,80}?im Geschäftsjahr '+str(report_year)+r' bei',r'GWh|MWh|kWh'),
    ]
    local_year=re.search(r'Die Gesellschaft erzielte in\s+'+str(report_year)+r'\s+Umsatzerlöse',text,re.I)
    rows=[]
    for metric,label,unit in patterns:
        pattern=r'(?P<label>'+label+r')\s+(?P<approx>rund\s+)?(?P<value>\d[\d.,]*)\s*(?P<unit>'+unit+r')\b'
        for m in re.finditer(pattern,text,re.I):
            section=list(re.finditer(r'Höhepunkte\s+(20\d\d)\s*:',text[:m.start()],re.I))
            anchor=section[-1] if section else heading or (local_year if local_year and 0<=m.start()-local_year.end()<2000 else None)
            if anchor is None:continue
            if section:
                if int(anchor[1])!=report_year:continue
                if re.search(r'Unser Blick in die Zukunft',text[anchor.end():m.start()],re.I):continue
            entity=re.search(r'([A-ZÄÖÜ][A-ZÄÖÜa-zäöüß -]{4,70}GMBH)',region,re.I)
            quote=evidence_span(page['text'],m[0])
            if quote is None or len(quote)>500:continue
            candidate=Candidate(metric=metric,raw_value=m['value'],raw_unit=m['unit'],year=report_year,
                evidence=quote,scope='group' if heading or local_year else 'reported_portfolio',basis='annual_sales',
                portfolio='total' if heading or local_year else 'defined_subset',entity='' if heading or local_year else entity[1].strip() if entity else 'Im datierten Abschnitt berichtetes Unternehmen',
                notes='Jahreszuordnung aus ausdrücklich datiertem Lagebericht bzw. Jahresrückblick; Originalmenge unverändert.')
            row=validate(candidate,page,report_year)
            # The section header is additional source evidence, just as the
            # header of a table is separate from the literal numeric row.
            if row.get('evidence_status')!='verified':continue
            unit_name,factor=normalize_unit(m['unit'])
            row.update(value=normalize_number(m['value'])*factor,unit=unit_name,status='validated',
                year_status='verified',source_year=report_year,technical_status='verified',
                extraction_method='source_anchored_rule',approximate=bool(m['approx']),
                evidence_kind='dated_narrative',section_reference={'header':anchor[0],'year':report_year},
                validation_notes='Originalzahl und Einheit geprüft; ausdrücklich datierter Abschnitt liefert die Berichtsperiode.')
            if page.get('layout')=='ocr':row.update(status='needs_review',validation_notes='OCR-Zahl am gerenderten Original prüfen.')
            rows.append(row)
    count_pattern=r'(?P<quote>(?:Zum Jahresende(?:\s+(?P<year>20\d\d))?\s+hatte|Insgesamt hatte)[^.]{0,100}?\b(?P<value>\d[\d.,]*)\s+(?P<label>Stromkunden|Gaskunden))'
    for m in re.finditer(count_pattern,text,re.I):
        explicit=int(m['year']) if m['year'] else None
        anchor=local_year if local_year and 0<=m.start()-local_year.end()<2000 else None
        if explicit!=report_year and not (explicit is None and anchor):continue
        quote=evidence_span(page['text'],m['quote'])
        if quote is None:continue
        value=normalize_number(m['value'])
        if value<0 or value!=int(value):continue
        row=Candidate(metric='electricity_customers' if m['label'].lower()=='stromkunden' else 'gas_customers',
            raw_value=m['value'],raw_unit=m['label'],year=report_year,evidence=quote,
            scope='group',basis='stock',portfolio='total',entity='').model_dump()
        row.update(page=page['page'],value=value,unit='Anzahl',status='validated',evidence_status='verified',
            source_year=report_year,year_status='verified',technical_status='verified',
            extraction_method='source_anchored_rule',evidence_kind='dated_narrative',
            section_reference={'header':m['quote'] if explicit else anchor[0],'year':report_year},
            validation_notes='Originale Kundenzahl und Kundenart; ausdrücklich datierte Jahresschlussangabe bzw. Unternehmensabschnitt.')
        rows.append(row)
    return rows
