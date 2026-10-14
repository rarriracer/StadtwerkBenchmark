"""Retain literal dated PDF cells, including parallel quantity/revenue tables."""
import re
from .pdf_geometry import clean_page

YEAR=re.compile(r'^(?:(?:1\.1\.[–−-])?31\.12\.)?(20\d\d)(?:/(20\d\d|\d{2}))?(?:\d{1,2}\))?$')

def column_year(token):
    match=YEAR.fullmatch(token)
    start=int(match[1])
    if not match[2]:return start
    end=int(match[2]) if len(match[2])==4 else start//100*100+int(match[2])
    return end if end==start+1 else None
NUMERIC=re.compile(r'^[+−–-]?\s*\d[\d.,]*(?:\s+\d{3})*(?:\d{1,2}\))?(?:\s*%)?$|^[–—-]$')


def table_layout(page):
    """Use printed horizontal rules to keep adjacent tables independent."""
    from .documents import spread_boxes
    boxes=spread_boxes(page)
    if boxes:
        return [table for box in boxes for table in table_layout(page.within_bbox(box))]
    # Parallel narrow tables and opposite-column prose must not share labels.
    middle=(page.bbox[0]+page.bbox[2])/2
    width=page.bbox[2]-page.bbox[0]
    narrow_right=[e for e in page.edges if e.get('orientation')=='h'
                  and middle<e['x0']<middle+width*.15 and width*.2<e['x1']-e['x0']<width*.55]
    words_for_split=clean_page(page).extract_words(x_tolerance=2)
    right_years=[w for w in words_for_split if YEAR.fullmatch(w['text']) and w['x0']>middle]
    if len(narrow_right)>=3 and len(right_years)>=2:
        boxes=[(page.bbox[0],page.bbox[1],middle,page.bbox[3]),
               (middle,page.bbox[1],page.bbox[2],page.bbox[3])]
        return [table for box in boxes for table in table_layout(page.within_bbox(box))]
    from .market_share_tables import market_share_layout
    market_tables=market_share_layout(page)
    words=clean_page(page).extract_words(x_tolerance=2)
    anchors=[w for w in words if YEAR.fullmatch(w['text'])]
    regions=set()
    for anchor in anchors:
        edges=sorted((e['x0'],e['x1']) for e in page.edges
                     if e['orientation']=='h' and abs(e['top']-anchor['bottom'])<4)
        spans=[]
        for left,right in edges:
            if spans and left-spans[-1][1]<=8:spans[-1][1]=max(spans[-1][1],right)
            else:spans.append([left,right])
        for left,right in spans:
            matching=[w for w in anchors if abs(w['bottom']-anchor['bottom'])<3
                      and left<=(w['x0']+w['x1'])/2<=right]
            if len(matching)>=2:regions.add((round(left,2),round(right,2)))
    if not regions:return _table_layout(page)+market_tables
    result=[];seen=set()
    for left,right in sorted(regions):
        cropped=page.within_bbox((max(page.bbox[0],left-1),page.bbox[1],min(page.bbox[2],right+1),page.bbox[3]))
        for table in _table_layout(cropped):
            identity=(table['header'],tuple(table['years']),tuple(tuple(r['values']) for r in table['rows']))
            if identity not in seen:result.append(table);seen.add(identity)
    return result+market_tables


def _table_layout(page):
    from .kpi_tables import UNIT_RE
    words=clean_page(page).extract_words(x_tolerance=2)
    lines=[]
    for word in sorted(words,key=lambda w:(w['bottom'],w['x0'])):
        line=next((line for line in reversed(lines[-3:]) if abs(line[0]['bottom']-word['bottom'])<3),None)
        if line is None:lines.append([word])
        else:line.append(word)
    lines=[sorted(line,key=lambda w:w['x0']) for line in lines]
    result=[]
    for index,line in enumerate(lines):
        anchors=[w for w in line if YEAR.fullmatch(w['text'])]
        if not 2<=len(anchors)<=8:continue
        years=[column_year(w['text']) for w in anchors]
        if None in years:continue
        middle=[w['text'] for w in line if anchors[0]['x0']<=w['x0']<=anchors[-1]['x1'] and w not in anchors]
        allowed=r'ist|plan|prognose|absatz|umsatz|in|teur|t€|eur|euro|tsd\.|mio\.|Δ|\(in|%\)|veränderung|absolut|anhang|1\.1\.[–−-]|\d{1,2}\)'
        if any(not re.fullmatch(allowed,w,re.I) for w in middle):continue
        edges=[(w['x0']+w['x1'])/2 for w in anchors];gap=min(b-a for a,b in zip(edges,edges[1:]))
        if gap<20:continue
        bounds=[anchors[0]['x0']-gap*.2]+[(a+b)/2 for a,b in zip(edges,edges[1:])]+[edges[-1]+gap*.65]
        note_anchor=next((w for w in line if w['text'].lower()=='anhang'),None)
        roles=[];kinds=[]
        for i,a in enumerate(anchors):
            preceding=[w for w in line if (anchors[i-1]['x1'] if i else 0)<=w['x0']<a['x0']]
            text=' '.join(w['text'] for w in preceding)
            role=re.search(r'\b(ist|plan|prognose)\s*$',text,re.I)
            roles.append(role[1].lower() if role else 'reported')
            kind=re.search(r'\b(Absatz|Umsatz)\b',text,re.I)
            kinds.append(kind[1].lower() if kind else '')
        groups=[]
        if any(kinds):
            for kind in dict.fromkeys(kinds):
                cols=[i for i,k in enumerate(kinds) if k==kind]
                if kind and len({years[i] for i in cols})==len(cols):groups.append((cols,kind))
        else:
            current=[];seen=set()
            for i,y in enumerate(years):
                # Same-year Ist/Plan stays together, and is separated by roles.
                if y in seen and roles[i]==roles[current[0]]:
                    groups.append((current,''));current=[];seen=set()
                current.append(i);seen.add(y)
            if current:groups.append((current,''))
        for cols,kind in groups:
            if len(cols)<2 and not any(r in ('ist','plan','prognose') for r in roles):continue
            selected_years=[years[i] for i in cols]
            if len(set(selected_years))!=len(selected_years):
                # One reported column per year, retain Plan independently below.
                cols=[i for i in cols if roles[i] not in ('plan','prognose')]
                selected_years=[years[i] for i in cols]
                if not cols or len(set(selected_years))!=len(selected_years):continue
            previous=lines[max(0,index-3):index]
            near=[ln for ln in previous if line[0]['top']-ln[0]['top']<50]
            header_words=sorted([w for w in words if abs(w['top']-anchors[0]['top'])<4],key=lambda w:w['x0'])
            if not any(w['text'].lower()=='gmbh' and w['x1']<bounds[0] for w in header_words):header_words=line
            prefix=' '.join(w['text'] for w in header_words if w['x1']<bounds[0])
            nearby=' '.join(' '.join(w['text'] for w in ln) for ln in near)
            # For two adjacent tables use the literal heading above this group.
            lo=0 if cols[0]==0 else (edges[cols[0]-1]+edges[cols[0]])/2
            hi=page.bbox[2] if cols[-1]==len(years)-1 else (edges[cols[-1]]+edges[cols[-1]+1])/2
            local_lines=[' '.join(w['text'] for w in ln if lo<=w['x0']<hi) for ln in near]
            heading_lines=[t for t in local_lines if len(t)<120 and re.search(r'^(?:Spartendarstellung|Vertriebsabsatz|Verkaufserlöse|Kennzahlen|Umsatzerlöse|NETZ\b|VERTRIEB|MENGENENTWICKLUNG|FINANZIELLE KENNZAHLEN|NETZAUSSPEISUNG)',t,re.I)]
            local=' '.join(heading_lines)
            heading=prefix if re.search(r'Netzlänge|Hausanschlüsse',prefix,re.I) else prefix+' '+local
            if not re.search(r'NETZ|VERTRIEB|KENNZAHLEN|UMSATZ|Betriebsmengen|Kunden|Absatz|Versorgung|Netzlänge|Hausanschlüsse|GmbH',heading,re.I):heading=''
            # A page-level currency heading governs all financial rows. Never
            # inherit a unit from a paragraph containing a numerical amount.
            unit_match=UNIT_RE.search(prefix) or (UNIT_RE.search(local) if re.search(r'\bin\s+(?:Mio|Tsd|T€|TEUR|EUR|Euro|GWh|MWh|Tm3|Tm³|m\b)',local,re.I) else None)
            default_unit=unit_match[1] if unit_match else ''
            if re.search(r'Netzlänge\s+in\s+m\b',prefix,re.I):default_unit='m'
            if re.search(r'Anzahl.*Hausanschlüsse',prefix,re.I):default_unit='Anzahl'
            if kind=='umsatz':
                m=re.search(r'in\s+((?:Tsd|Mio)\.?\s*(?:EUR|Euro|€))', ' '.join(w['text'] for w in line),re.I)
                if m:default_unit=m[1]
            if not default_unit and re.search(r'\bin\s+(?:Mio|Tsd)\.?\s*(?:EUR|€)',nearby,re.I) and len(groups)==1:
                default_unit=UNIT_RE.search(nearby)[1]
            header='\n'.join([' '.join(w['text'] for ln in near for w in ln), ' '.join(w['text'] for w in header_words)])
            table={'years':selected_years,'roles':[roles[i] for i in cols], 'header':header.strip(),
                   'heading':heading.strip(),'kind':kind or ('umsatz' if 'verkaufserlöse' in local.lower() else ''),
                   'rows':[],'column_units':[default_unit]*len(cols)}
            table['period_labels']=[anchors[i]['text'] for i in cols]
            # Entity labels may sit underneath the years rather than above them.
            column_entities=['']*len(cols)
            for following in lines[index+1:index+3]:
                for n,c in enumerate(cols):
                    labels=[w['text'] for w in following if bounds[c]<=(w['x0']+w['x1'])/2<bounds[c+1]]
                    text=' '.join(labels)
                    if re.fullmatch(r'Konzern|Gruppe',text,re.I):column_entities[n]=text
            table['column_entities']=column_entities
            subsection=''
            section_unit=default_unit
            pending=[]
            for j in range(index+1,min(len(lines),index+85)):
                current=lines[j]
                if current[0]['top']-line[0]['top']>600:break
                if len([w for w in current if YEAR.fullmatch(w['text'])])>=2:break
                cells=[[] for _ in years];label=[]
                for w in current:
                    center=(w['x0']+w['x1'])/2
                    if note_anchor and NUMERIC.fullmatch(w['text']) and note_anchor['x0']-3<=center<=note_anchor['x1']+3:
                        continue
                    if NUMERIC.fullmatch(w['text']) and re.search(r'Δ|Veränderung',table['header']) and min(abs(center-e) for e in edges)>gap*.42:
                        continue
                    if center<bounds[0] and NUMERIC.fullmatch(w['text']) and w['x1']>bounds[0]-gap*.55 and not re.fullmatch(r'\d{1,2}\)',w['text']):cells[0].append(w)
                    elif center<bounds[0]:label.append(w)
                    else:
                        for c in range(len(years)):
                            if bounds[c]<=center<bounds[c+1]:cells[c].append(w);break
                texts=[' '.join(w['text'] for w in cells[c]) for c in cols]
                # Values can include a printed unit per cell (Ist vs Plan).
                values=[];cell_units=[]
                for text in texts:
                    m=UNIT_RE.search(text)
                    cell_units.append(m[1] if m else '')
                    values.append(text[:m.start()].strip() if m else text)
                if all(re.fullmatch(r'(?:in\s+)?(?:T€|TEUR|Euro|EUR)',t,re.I) for t in texts):
                    table['column_units']=[re.sub(r'^in\s+','',t,flags=re.I) for t in texts]
                    table['header']+='\n'+' '.join(w['text'] for w in current)
                    continue
                label_text=' '.join(w['text'] for w in label)
                if not all(NUMERIC.fullmatch(t) for t in values):
                    if not any(texts) and label:
                        if re.fullmatch(r'Absatz|Verwertete Mengen|Personal|Finanzkennzahlen(?: in .+)?',label_text,re.I):
                            subsection=label_text
                            section_match=UNIT_RE.search(label_text)
                            section_unit=section_match[1] if section_match else ''
                        if table['rows']:
                            last=table['rows'][-1]
                            if (label_text.startswith('(') or last['label'].endswith('incl.')) and current[0]['top']-last['bbox'][3]<12:
                                last['label']+='\n'+label_text;last['evidence']+='\n'+label_text;last['bbox'][3]=max(w['bottom'] for w in current);continue
                        if re.search(r'(?:ggü\.|gegenüber|laufender|vor|-)$',label_text):pending.append((label_text,current[0]['top']))
                    if table['rows'] and current[0]['top']-table['rows'][-1]['bbox'][3]>70:break
                    continue
                if not label:continue
                # Only immediately adjacent label-only lines are continuations;
                # section headings in bold are excluded from pending prefixes.
                if pending:
                    tail=[t for t,y in pending if current[0]['top']-y<15]
                    if tail:label_text=' '.join(tail)+' '+label_text
                pending=[]
                included=label+[w for c in cols for w in cells[c]]
                table['rows'].append({'label':label_text,'values':values,'units':cell_units,
                    'section':subsection,'section_unit':section_unit,
                    'evidence':label_text+' '+' '.join(texts),
                    'bbox':[min(w['x0'] for w in included),min(w['top'] for w in included),max(w['x1'] for w in included),max(w['bottom'] for w in included)]})
            if table['rows']:result.append(table)
    return result
