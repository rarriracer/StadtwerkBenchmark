"""Read labelled KPI rows using explicit year columns, without model copying."""
import re
from .models import Candidate

UNIT = r'(?:Millionen|Million|Mio\.?|Tausend|Tsd\.?)\s*(?:Kilowattstunden|Megawattstunden|Gigawattstunden|kWh|MWh|GWh|Kubikmeter|m³|m3|Euro|EUR|€)|Kilowattstunden|Megawattstunden|Gigawattstunden|[kMG]Wh|[kMG]W|Tm³|Tm3|km|Kubikmeter|m³|m3|TEuro|TEUR|T€|Euro|EUR|€|FTE(?:\d)?|VZK|MAK|Mg|Faktor|Anzahl|Kunden|Stück|%'
UNIT_RE = re.compile(r'(?<!\w)('+UNIT+r')(?!\w)', re.I)
NUMBER = r'-?\d[\d.,]*'


def classify_label(label, section, dimension):
    context = (section+' '+label).lower()
    sector_patterns = (
        ('electricity',r'strom'),('gas',r'gas'),('water',r'wasser'),('heat',r'wärme'))
    sector = next((name for name,pattern in sector_patterns if re.search(pattern,label.lower())),None)
    if sector is None:
        sector = next((name for name,pattern in sector_patterns if re.search(pattern,section.lower())),None)
    if dimension == 'Anzahl' and sector and re.search(r'kunden|kundenzahl|kundenanzahl',context):
        return sector+'_customers', 'stock'
    revenue_row = re.search(r'\b(?:Umsatz|Umsatzerlöse?|Erlöse)\b',label,re.I)
    revenue_segment = re.search(r'umsatz|umsatzerlös',section,re.I) and re.fullmatch(
        r'(?:Strom|Gas|Erdgas|Wasser|Fernwärme|Verkehr|Bäder|Telekommunikation|Sonstige|Stromversorgung|Gasversorgung|Wasserversorgung|Fernwärmeversorgung|Stromerzeugung und -vermarktung|Stadtentwässerung|Sonstige Geschäfte)',label,re.I)
    if dimension == 'EUR' and (revenue_row or revenue_segment):
        return 'revenue', 'annual_revenue'
    if dimension in ('MWh','m³') and sector:
        if re.search(r'erzeugung',label,re.I) and sector in ('electricity','heat'):return sector+'_generation','annual_generation'
        if re.search(r'netz|durchleitung',context):
            return None
        if re.search(r'betriebsmengen?',context):
            return sector+'_operating_volume', 'annual_volume'
        if re.search(r'absatz|verkauf|vertrieb|abgabe',context):
            if re.search(r'haushalt|privat|industrie|gewerbe|geschäft|tarifkunden|sondervertrags',label,re.I):
                return None  # Segment totals require their own unambiguous mapping.
            return {'electricity':'electricity_sales_total','gas':'gas_sales_total',
                    'water':'water_sales','heat':'heat_sales'}[sector], 'annual_sales'
    return None


def kpi_table_facts(page, report_year):
    from .extraction import normalize_number, normalize_unit
    source=page['text']
    if not re.search(r'kennzahlen|zahlen\s*[–-]\s*daten|betriebsmengen|kundenanzahl|anzahl\s+kunden',source,re.I):
        return []
    lines=source.splitlines(); header=None; years=[]; period_labels=[]; section=''; section_line=''; results=[]
    for line in lines:
        # Only a dedicated all-year heading defines the column order. Report
        # titles, dates in prose and projection headings never become headers.
        if re.fullmatch(r'\s*(?:20\d\d(?:/(?:20\d\d|\d{2}))?\s+){1,5}20\d\d(?:/(?:20\d\d|\d{2}))?\s*',line):
            from .table_layout import column_year
            period_labels=line.split();years=[column_year(y) for y in period_labels]
            if None in years:header=None;continue
            header=line; section=''; section_line=''
            continue
        if header is None or years.count(report_year)!=1 or len(set(years))!=len(years):
            continue
        values=re.search(r'(?<![\d.,])('+NUMBER+r'(?:\s+'+NUMBER+r'){'+str(len(years)-1)+r'})\s*$',line)
        if not values:
            if re.search(r'umsatz|umsatzerlös|betriebsmengen|absatz|verkauf|abgabe|anzahl\s+kunden|kundenanzahl|kundenzahl|versorgung',line,re.I):
                section=line;section_line=line
            continue
        prefix=line[:values.start()].strip()
        if not prefix or re.search(r'prognose|geplant|planung|ziel',prefix+' '+section,re.I):
            continue
        unit_match=UNIT_RE.search(prefix)
        inherited=False
        if unit_match is None:
            if re.search(r'\d[\d.,]*\s+\d',section_line):continue
            unit_match=UNIT_RE.search(section_line);inherited=True
        if unit_match is None:continue
        raw_unit=unit_match[1]
        try:dimension,factor=normalize_unit(raw_unit)
        except ValueError:continue
        label=(prefix[:unit_match.start()]+prefix[unit_match.end():]).strip() if not inherited else prefix
        # Remove a printed footnote marker, never a numerical data column.
        label=re.sub(r'\s+\d+\)','',label).strip()
        label=re.sub(r'\(\s*(?:in\s*)?\)', '',label).strip()
        if dimension=='EUR' and re.fullmatch(r'Strom|Gas|Wasser|Fernwärme',label,re.I):
            section=label;section_line=line
        classified=classify_label(label,section,dimension)
        if not classified and dimension=='EUR' and re.fullmatch(r'Strom|Gas|Wasser|Fernwärme|Verkehr',label,re.I):
            classified=('revenue','annual_revenue')
        if not classified:continue
        metric,basis=classified
        tokens=values[1].split();column=years.index(report_year)
        raw_value=tokens[column]
        try:value=normalize_number(raw_value)*factor
        except ValueError:continue
        if value<0 or (dimension=='Anzahl' and value!=int(value)):continue
        if len(line.strip())>500:continue
        candidate=Candidate(metric=metric,raw_value=raw_value,raw_unit=raw_unit,year=report_year,
            evidence=line.strip(),scope='group' if re.search(r'Quelle:.*Konzern',source,re.I) else 'own',
            basis=basis,portfolio='total',entity=label,
            notes='Kennzahlentabelle mit ausdrücklich beschrifteten Jahres-, Mengen- und Einheitenspalten.')
        proof=header+ ('\n'+section_line if inherited else '')
        row=candidate.model_dump()
        row.update(page=page['page'],value=value,unit=dimension,status='validated',
            evidence_status='verified',year_status='verified',source_year=report_year,technical_status='verified',
            extraction_method='source_anchored_rule',validation_notes='Originalzeile, Einheit und ausdrücklich beschriftete Jahresspalte geprüft.',
            table_reference={'header':proof,'row':line.strip(),'column':column+1,'year':report_year,'unit':raw_unit})
        if '/' in period_labels[column]:
            row['reporting_period_label']=period_labels[column]
            row['table_reference']['period_label']=period_labels[column]
        if metric=='revenue' and re.fullmatch(r'Strom|Gas|Wasser|Fernwärme|Verkehr',label,re.I):row['portfolio']='defined_subset'
        if re.fullmatch('Verkaufsmenge',label,re.I):row['entity']=section+'vertrieb'
        if label=='Verkehr':section='';section_line=''
        results.append(row)
        if re.search(r'^Umsatzerlöse?$|^Umsatz$',label,re.I):section=label;section_line=line
    return results


def layout_table_facts(page, report_year):
    """Read PDF-positioned cells. Plan columns cannot become reported values."""
    from .extraction import normalize_number, normalize_unit
    rows=[]
    for table in page.get('tables',[]):
        if table['years'].count(report_year)!=1:continue
        col=table['years'].index(report_year)
        if table['roles'][col] in ('plan','prognose'):continue
        section=(('Absatz ' if table.get('kind')=='absatz' else '')+table['heading']).strip()
        revenue_section=''
        sales_sector='';sales_sector_evidence=''
        for cell in table['rows']:
            row_section=(' '.join([section,cell.get('section','')])).strip()
            label=cell['label'];context=row_section+' '+label
            raw=cell['values'][col]
            if raw.startswith('+'):raw=raw[1:]
            raw=raw.replace('–','-')
            if raw in ('–','—','-'):continue
            footnote=re.search(r'(\d)\)$',raw)
            raw_value=raw[:footnote.start()] if footnote else raw
            match=UNIT_RE.search(label)
            inherited_unit=(cell.get('section_unit') or table['column_units'][col])
            if match and match[1].lower()=='kunden' and re.search(r'EUR|Euro|€',inherited_unit,re.I):match=None
            raw_unit=match[1] if match else (cell.get('units',['']*len(table['years']))[col] or cell.get('section_unit') or table['column_units'][col])
            if table.get('kind')=='umsatz':raw_unit=table['column_units'][col]
            if match:
                label=(label[:match.start()]+label[match.end():]).strip()
                label=re.sub(r'\(\s*(?:in\s*)?\)\*?', '', label).strip()
            label=re.sub(r'\s+\d{1,2}\)','',label).strip()
            label=re.sub(r'(?<=[A-Za-zÄÖÜäöüß])\d+(?:,\d+)*$', '', label)
            label=re.sub(r'^\d+(?:\)|\.)\s*','',label)
            label=re.sub(r'^[IVX]+\.\s*','',label)
            if re.search(r'\bAnhang\b',table['header']):label=re.sub(r'\s+\d{1,2}$','',label)
            label=re.sub(r'\b([A-ZÄÖÜ]) (?=[a-zäöüß])',r'\1',label)
            label=re.sub(r'\s+in$','',label)
            context=section+' '+label
            sectors=[('electricity','strom'),('gas','gas'),('water','wasser'),('heat','wärme')]
            sector=next((k for k,p in sectors if re.search(p,label,re.I)),None)
            if sector is None:sector=next((k for k,p in sectors if re.search(p,section,re.I)),None)
            if sector and re.fullmatch(r'Strom|Gas|Wasser|Fernwärme',label,re.I) and re.search(r'EUR|Euro|€',raw_unit,re.I):
                sales_sector=sector;sales_sector_evidence=cell['evidence']
            elif re.fullmatch(r'Verkehr',label,re.I):sales_sector='';sales_sector_evidence=''
            if re.fullmatch('Summe',label,re.I):continue
            metric=basis=None
            count_suffix='network_connections' if re.fullmatch(r'Anschlüsse',label,re.I) else 'network_meters' if re.fullmatch(r'Zähler im Netz',label,re.I) else None
            if table.get('kind')=='market_share' and sector in ('electricity','gas'):metric=sector+'_market_share';basis='stock';raw_unit='%'
            elif sales_sector and re.fullmatch(r'Verkaufsmenge',label,re.I):
                sector=sales_sector
                metric={'electricity':'electricity_sales_total','gas':'gas_sales_total','water':'water_sales','heat':'heat_sales'}[sector];basis='annual_sales'
            elif table.get('kind')=='umsatz':metric='revenue';basis='annual_revenue'
            elif sector and re.search(r'Netzlänge',section,re.I):metric=sector+'_network_length';basis='stock'
            elif sector and re.search(r'Anzahl.*Hausanschlüsse',section,re.I):metric=sector+'_network_connections';basis='stock';raw_unit='Anzahl'
            elif sector and re.search(r'Vertriebsabsatz',section,re.I) and re.fullmatch('Gesamt',label,re.I):
                metric={'electricity':'electricity_sales_total','gas':'gas_sales_total','water':'water_sales','heat':'heat_sales'}[sector];basis='annual_sales'
            elif sector and count_suffix and re.search(r'NETZ',section,re.I):
                metric=sector+'_'+count_suffix;basis='stock';raw_unit='Anzahl'
            elif sector and re.match(r'Netzlänge',label,re.I) and raw_unit=='km':
                metric=sector+'_network_length';basis='stock';raw_unit='km'
            elif sector and re.fullmatch(r'Gesamte (?:Rohrnetzlänge|Netzlänge)',label,re.I) and raw_unit=='km':
                metric=sector+'_network_length';basis='stock'
            elif sector and re.fullmatch(r'Gesamte Hausanschlüsse',label,re.I):
                metric=sector+'_network_connections';basis='stock';raw_unit='Stück'
            elif sector and re.fullmatch(r'Eingebaute Zähler',label,re.I):
                metric=sector+'_network_meters';basis='stock';raw_unit='Stück'
            elif sector and re.search(r'Netzeinspeisung',label,re.I) and not re.search(r'max|leistung|höchst',label,re.I):
                metric=sector+'_network_input';basis='annual_volume'
                if 'regenerativ' in label.lower() and sector=='electricity':metric='electricity_network_renewable_input'
            elif sector in ('electricity','gas') and re.search(r'NETZAUSSPEISUNG',section,re.I):
                metric=sector+'_network_output';basis='annual_volume'
            elif sector in ('electricity','heat') and re.match(r'Höchstlast',label,re.I):
                metric=sector+'_peak_load';basis='stock';raw_unit='MW'
            elif sector=='gas' and re.search(r'Max.*Leistung.*Netzeinspeisung',label,re.I):
                metric='gas_network_max_power';basis='stock';raw_unit='kW'
            elif re.search(r'Wärme-/Kälteabsatz',label,re.I):metric='heat_cold_sales';basis='annual_sales'
            elif re.search(r'Wärmecontracting',label,re.I) and re.search(r'VERTRIEB',section,re.I):metric='heat_contracting_sales';basis='annual_sales'
            else:
                if raw_unit:
                    try:dimension,_=normalize_unit(raw_unit)
                    except ValueError:continue
                    classified=classify_label(label,revenue_section or row_section,dimension)
                    if classified:metric,basis=classified
                if metric is None:
                    financial={r'^Jahresüberschuss|^Konzernjahresergebnis':'net_income',r'^EBITDA\b':'ebitda',r'^EBIT\b|^Operatives EBIT\b|Operatives Ergebnis \(EBIT\)|^Ergebnis vor Zinsen und Steuern \(EBIT\)':'ebit',r'^EBT\b|^Ergebnis vor Steuern':'ebt',
                        r'^FFO\b':'funds_from_operations',r'^Gesamter Personalaufwand':'personnel_expense',r'^Bilanzsumme':'balance_total',r'^Eigenkapital(?:\s+\d\))?$':'equity',
                        r'^Cash[ -]?Flow.*(?:laufender|operativ)':'operating_cashflow',r'^Summe Finanzschulden$':'debt',r'^Investitionen(?:\b|\*)':'investments',r'Verbindlichkeiten.*(?:gegenüber|ggü\.).*Kreditinstituten':'debt',r'^Zinsen und ähnliche Aufwendungen':'interest_expense'}
                    metric=next((m for p,m in financial.items() if re.search(p,label,re.I)),None)
                    if metric:basis='stock' if metric in ('equity','balance_total','debt') else 'annual_expense' if metric in ('interest_expense','personnel_expense') else 'annual_revenue'
                    elif re.search(r'Anzahl Mitarbeiter|^Mitarbeiter|^Mitarbeitende$',label,re.I):metric='employees';basis='stock';raw_unit=raw_unit if raw_unit in ('FTE7','FTE','VZK','MAK') else 'Anzahl'
            special={r'^Auszubildende$':('apprentices','Anzahl','stock'),r'^Abwasser(?: in)?$':('wastewater_volume',raw_unit,'annual_volume'),r'^Klärschlamm(?: in)?$':('sewage_sludge_volume',raw_unit,'annual_volume'),r'^Dynamischer Verschuldungsgrad(?: in)?$':('dynamic_debt_ratio','%','stock'),r'^Nettoverschuldungsgrad$':('net_debt_multiple','Faktor','stock'),r'^Gearing Ratio(?: in)?$':('gearing_ratio','%','stock')}
            if metric is None:
                for pattern,(m,u,b) in special.items():
                    if re.fullmatch(pattern,label,re.I):metric,raw_unit,basis=m,u,b;break
            if not metric and re.search(r'Personalentwicklung|Mitarbeiter',label,re.I) and raw_unit in ('FTE7','FTE','VZK','MAK'):
                metric='employees_fte';basis='stock'
            if metric=='employees' and raw_unit in ('FTE7','FTE','VZK','MAK'):metric='employees_fte'
            if not metric or not raw_unit:continue
            if re.search(r'\bUmsatzerlöse?\b',label,re.I):revenue_section='Umsatzerlöse'
            try:unit,factor=normalize_unit(raw_unit);value=normalize_number(raw_value)*factor
            except ValueError:continue
            if metric.endswith(('_network_connections','_network_meters','_customers')) or metric in ('employees','apprentices'):
                if unit!='Anzahl' or value<0 or value!=int(value):continue
            if metric.endswith(('_network_input','_network_output')):
                if unit!=('m³' if sector=='water' else 'MWh'):continue
            if metric in ('revenue','ebit','ebitda','ebt','equity','balance_total','operating_cashflow','investments','debt','interest_expense','net_income','funds_from_operations','personnel_expense') and unit!='EUR':continue
            if value<0 and metric not in ('ebit','ebitda','ebt','operating_cashflow','net_income'):continue
            evidence=cell['evidence']
            if len(evidence)>500:continue
            candidate=Candidate(metric=metric,raw_value=raw_value,raw_unit=raw_unit,year=report_year,
                evidence=evidence,scope='network_area' if '_network_' in metric or 'peak_load' in metric else 'group',
                basis=basis,portfolio='total',entity=label if metric in ('revenue','ebit','ebitda','ebt','employees','investments') else section.strip() if section.strip() else label,
                notes='Originale Tabellenzellen anhand PDF-Spaltenpositionen gelesen; ausschließlich Ist-/Berichtsspalten.')
            row=candidate.model_dump()
            row.update(page=page['page'],value=value,unit=unit,status='validated',evidence_status='verified',
                year_status='verified',source_year=report_year,technical_status='verified',
                extraction_method='source_anchored_rule',evidence_kind='pdf_table_cells',
                validation_notes='Jahreskolonne, Spaltenart und Originalzellen anhand ihrer PDF-Position geprüft.',
                table_reference={'header':table['header'],'row':evidence,'column':col+1,'year':report_year,
                    'unit':raw_unit,'role':table['roles'][col],'bbox':cell['bbox'],'values':cell['values'],
                    'heading':section,'footnote':footnote[1] if footnote else None})
            if metric=='net_income' and re.search(r'\bPASSIVA\b',table['header']):
                row.update(portfolio='defined_subset',entity='Eigenkapitalausweis · '+label)
            if table.get('kind')=='market_share':
                if not 0<=value<=100:continue
                row.update(scope='customers',portfolio='defined_subset',entity=table['market_entity'])
            if metric=='debt' and re.search(r'kurzfristig|langfristig',label,re.I):
                row.update(portfolio='defined_subset',entity=label)
            column_entity=table.get('column_entities',['']*len(table['years']))[col]
            if column_entity:
                row.update(reporting_scope='consolidated' if column_entity.lower()=='konzern' else 'extended_group',entity=column_entity+' · '+label)
                row['table_reference']['column_entity']=column_entity
            period_label=table.get('period_labels',['']*len(table['years']))[col]
            if '/' in period_label:
                row['reporting_period_label']=period_label
                row['table_reference']['period_label']=period_label
            if re.fullmatch('Verkaufsmenge',label,re.I) and sales_sector:
                row['entity']={'electricity':'Stromvertrieb','gas':'Gasvertrieb','water':'Wasservertrieb','heat':'Wärmevertrieb'}[sales_sector]
                row['table_reference']['sector_row']=sales_sector_evidence
            if metric=='revenue' and re.fullmatch(r'Strom|Gas|Wasser|Fernwärme|Verkehr',label,re.I):
                row['portfolio']='defined_subset'
            if not column_entity and re.search(r'^Geschäftsentwicklung der [^\n/]+ AG\s*$',page['text'],re.M):
                row.update(scope='own',reporting_scope='standalone',entity='Einzelabschluss · '+label)
            # Extreme dimensional jumps remain visible for diagnosis, but do
            # not silently repair what may already be a typo in the original.
            others=[]
            for v in cell['values']:
                try:others.append(abs(normalize_number(v)))
                except ValueError:pass
            positive=[v for v in others if v>0]
            if unit in ('MWh','m³') and positive and max(positive)/min(positive)>100:
                row.update(status='needs_review',validation_notes='Originaltabelle zeigt einen Mengenunterschied um mehr als Faktor 100. Einheit oder Druckfehler prüfen; keine automatische Korrektur.')
            rows.append(row)
    return rows
