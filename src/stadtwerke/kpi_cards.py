"""Read labelled numeric infographic cards from literal PDF word positions."""
import re
from .pdf_geometry import clean_page
from .models import Candidate

LABELS={'Strom':('electricity_sales_total','annual_sales'),'Gas':('gas_sales_total','annual_sales'),
        'Wärme':('heat_sales','annual_sales'),'Wasser':('water_sales','annual_sales'),
        'Umsatz':('revenue','annual_revenue'),'Mitarbeitende':('employees','stock'),
        'Stromverkauf':('electricity_sales_total','annual_sales'),'Erdgasverkauf':('gas_sales_total','annual_sales'),
        'Mitarbeiter':('employees','stock')}


def card_layout(page):
    words=clean_page(page).extract_words(x_tolerance=2)
    text=' '.join(w['text'] for w in words)
    years=sorted(set(int(w['text']) for w in words if re.fullmatch(r'20\d\d',w['text'])))
    if not re.search(r'in Zahlen|Kennzahlen|Auf einen Blick',text,re.I):return []
    if len(years)!=1:return year_chart_layout(words)
    cards=[]
    for label in words:
        if label['text'] not in LABELS:continue
        center=(label['x0']+label['x1'])/2
        near=[w for w in words if abs((w['x0']+w['x1'])/2-center)<65
              and label['bottom']-2<=w['top']<=label['bottom']+55]
        numbers=[w for w in near if re.fullmatch(r'\d[\d.,]*',w['text']) and not re.fullmatch(r'\d{1,2}\.\d{1,2}\.20\d\d',w['text']) and w['top']<label['bottom']+23]
        if len(numbers)!=1:continue
        number=numbers[0]
        if abs((number['x0']+number['x1'])/2-center)>15:continue
        units=[w for w in near if w['top']>=number['bottom']-1]
        units=sorted(units,key=lambda w:(round(w['top']/3),w['x0']))
        unit_text=' '.join(w['text'] for w in units)
        unit_text=re.sub(r'Tm\s+3\b','Tm3',unit_text)
        if label['text']=='Mitarbeitende':
            if not re.fullmatch(r'Stand\s+31\.12\.'+str(years[0]),unit_text):continue
            unit='Anzahl'
        else:
            m=re.fullmatch(r'(?:Absatz in|in)\s+(GWh|MWh|kWh|Tm3|Tm³|Mio\.?\s*€)',unit_text)
            if not m:continue
            unit=m[1]
        all_words=[label,number]+units
        cards.append({'label':label['text'],'value':number['text'],'unit':unit,'year':years[0],
                      'year_evidence':str(years[0]),'evidence':label['text']+'\n'+number['text']+'\n'+unit_text,
                      'bbox':[min(w['x0'] for w in all_words),min(w['top'] for w in all_words),max(w['x1'] for w in all_words),max(w['bottom'] for w in all_words)]})
    return cards


def card_facts(page,report_year):
    from .extraction import normalize_number,normalize_unit
    rows=[]
    for c in page.get('cards',[]):
        if c['year']!=report_year:continue
        metric,basis=LABELS[c['label']];unit,factor=normalize_unit(c['unit']);value=normalize_number(c['value'])*factor
        row=Candidate(metric=metric,raw_value=c['value'],raw_unit=c['unit'],year=report_year,
                      evidence=c['evidence'],scope='group',basis=basis,portfolio='total',entity='',
                      notes='Beschriftung, Originalzahl und Einheit aus derselben grafischen Kennzahlenkachel.').model_dump()
        row.update(page=page['page'],value=value,unit=unit,status='validated',evidence_status='verified',
                   source_year=report_year,year_status='verified',technical_status='verified',extraction_method='source_anchored_rule',
                   evidence_kind=c.get('kind','pdf_kpi_card'),table_reference={'header':c['year_evidence'],'row':c['evidence'],'year':report_year,'unit':c['unit'],'bbox':c['bbox']},
                   validation_notes='Jahr und zusammengehörige Kachel anhand Originalpositionen geprüft.')
        if c.get('kind')=='pdf_year_chart':row.update(validation_notes='Jahresbalken, Beschriftung und Einheit anhand ihrer Originalpositionen geprüft.')
        if metric=='revenue':row.update(status='needs_review',validation_notes='Umsatz der Kennzahlenübersicht: Abgrenzung gegenüber Einzel-/Konzernabschluss prüfen.')
        rows.append(row)
    return rows


def reconcile_cards(rows):
    """Keep conflicting overview figures visible, prefer explicit detailed evidence."""
    for card in rows:
        if card.get('evidence_kind') not in ('pdf_kpi_card','pdf_year_chart') or card['status']!='validated':continue
        detailed=[r for r in rows if r['metric']==card['metric'] and r['year']==card['year']
                  and r.get('evidence_kind') in ('dated_narrative','pdf_table_cells') and r['status']=='validated']
        if detailed:
            if any(r['value']!=card['value'] for r in detailed):
                card.update(status='needs_review',validation_notes='Die Kennzahlenübersicht weicht vom detaillierten Berichtsbeleg ab. Beide Originalwerte bleiben erhalten.')
            else:card.update(status='superseded',validation_notes='Gleiche Originalkennzahl auch im detaillierten Bericht belegt.')
    return rows


def year_chart_layout(words):
    """Read labelled annual bar charts; require one literal value per year column."""
    anchors=[w for w in words if re.fullmatch(r'20\d\d',w['text'])]
    lines=[]
    for word in sorted(anchors,key=lambda w:(w['bottom'],w['x0'])):
        line=next((r for r in lines if abs(r[0]['bottom']-word['bottom'])<3),None)
        if line is None:lines.append([word])
        else:line.append(word)
    output=[]
    for line in lines:
        groups=[]
        for w in sorted(line,key=lambda w:w['x0']):
            if not groups or int(w['text'])!=int(groups[-1][-1]['text'])+1:groups.append([w])
            else:groups[-1].append(w)
        for group in groups:
            if len(group)<3:continue
            centers=[(w['x0']+w['x1'])/2 for w in group]
            gaps=[b-a for a,b in zip(centers,centers[1:])]
            gap=min(gaps)
            if gap<15 or max(gaps)>gap*1.35:continue
            top=group[0]['top'];left=centers[0]-gap/2;right=centers[-1]+gap/2
            labels=[w for w in words if w['text'] in ('Stromverkauf','Erdgasverkauf','Mitarbeiter')
                    and left<=(w['x0']+w['x1'])/2<=right+(gap*2.5 if w['text']=='Mitarbeiter' else 0)
                    and top-180<w['top']<top-35]
            if len(labels)!=1:continue
            label=labels[0]
            if label['text']=='Mitarbeiter':
                units=[w for w in words if label['x0']-2<=w['x0']<=label['x1']+110
                       and label['bottom']-1<=w['top']<=label['bottom']+35]
                unit_text=' '.join(w['text'] for w in sorted(units,key=lambda w:(round(w['top']/3),w['x0'])))
                if not re.search(r'Durchschnittliche Anzahl',unit_text):continue
                unit='Anzahl'
            else:
                units=[w for w in words if label['x0']-2<=w['x0']<label['x1']+20
                       and label['bottom']-1<=w['top']<=label['bottom']+20]
                unit_text=' '.join(w['text'] for w in sorted(units,key=lambda w:w['x0']))
                match=re.fullmatch(r'in (GWh|MWh|kWh)',unit_text)
                if not match:continue
                unit=match[1]
            values=[]
            for center in centers:
                nearby=[w for w in words if re.fullmatch(r'\d[\d.,]*',w['text'])
                        and abs((w['x0']+w['x1'])/2-center)<gap*.35
                        and label['bottom']+20<w['top']<top-5]
                if len(nearby)!=1:break
                values.append(nearby[0])
            if len(values)!=len(group):continue
            # Each number keeps its own year and bbox; the value is never chosen
            # by the order of flattened page text or a language-model guess.
            for year,value in zip(group,values):
                source=[label,value,year]+units
                output.append({'label':label['text'],'value':value['text'],'unit':unit,'year':int(year['text']),
                    'year_evidence':unit_text+' · '+year['text'],'kind':'pdf_year_chart',
                    'evidence':label['text']+'\n'+unit_text+'\n'+value['text']+'\n'+year['text'],
                    'bbox':[min(w['x0'] for w in source),min(w['top'] for w in source),max(w['x1'] for w in source),max(w['bottom'] for w in source)]})
    return output
