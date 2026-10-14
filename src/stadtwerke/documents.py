from .pdf_geometry import clean_page
from collections import Counter
import hashlib
import json
import re
from contextvars import ContextVar
import pypdfium2 as pdfium
import pdfplumber
from pathlib import Path
from .config import RUNTIME

DOCUMENT_PROGRESS = ContextVar('document_progress',default=None)
PDF_BATCH_SIZE = 12

def file_digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()

THEMES = {
    'Photovoltaik': r'photovoltaik|\bsolar\w*|\bPV[- ]',
    'Windenergie': r'windenergie|windpark|windkraft|windanlagen',
    'Batteriespeicher': r'batteriespeicher|großspeicher|stromspeicher',
    'Stromvertrieb': r'stromabsatz|stromvertrieb|stromverkauf|Absatzmenge in der Sparte Strom|Betriebsmengen[^\n]*Strom|Kunden[^\n]*Strom',
    'Gas': r'gasabsatz|gasvertrieb|gasverkauf',
    'Wärme': r'wärmeabsatz|wärmeverkauf|fernwärme',
    'Elektromobilität': r'ladepunkt|ladesäule|elektromobilität|ladestrom',
    'Finanzierung': r'finanzschulden|zinsaufwand|verbindlichkeiten gegenüber kreditinstituten',
}

def spread_boxes(page):
    """Separate a wide PDF spread only when its centre is a persistent gutter."""
    x0,y0,x1,y1=page.bbox
    if x1-x0 < (y1-y0)*1.38:return []
    words=clean_page(page).extract_words(x_tolerance=2)
    mid=(x0+x1)/2
    left=[w for w in words if w['x1']<mid-5]
    right=[w for w in words if w['x0']>mid+5]
    crossing=[w for w in words if w['x0']<mid+5 and w['x1']>mid-5]
    if min(len(left),len(right))<20 or len(crossing)>max(2,len(words)*.008):return []
    # A single wide table has year columns across the gutter. A spread has
    # independent repeated year pairs, or substantial prose on both pages.
    years=lambda ws:[w['text'] for w in ws if re.fullmatch(r'20\d\d',w['text'])]
    ly,ry=years(left),years(right)
    prose=lambda ws:sum(len(w['text']) for w in ws if w['text'].isalpha())
    if not (len(set(ly)&set(ry))>=2 or min(prose(left),prose(right))>=500):return []
    if crossing:return []  # Never crop a word or a full-width footnote.
    return [(x0,y0,mid,y1),(mid,y0,x1,y1)]


def visible_text(page):
    """Read paragraph columns in order without splitting numeric tables.

    A persistent centre gutter with substantial prose on BOTH sides is
    required. Dense number tables and full-width paragraphs keep their layout.
    """
    boxes=spread_boxes(page)
    if boxes:
        return '\n'.join(visible_text(page.within_bbox(box))[0] for box in boxes), 'spread'
    x0,top,x1,bottom=page.bbox
    width=x1-x0
    visible = clean_page(page)
    words = visible.extract_words(x_tolerance=2)
    mid = x0+width/2
    lines = {}
    for word in sorted(words,key=lambda w:w['top']):
        if page.height*.035 < word['top'] < page.height*.94:
            # Nearby font baselines must not fall into separate rounding bins.
            key=next((y for y in reversed(lines) if abs(y-word['top'])<3),word['top'])
            lines.setdefault(key,[]).append(word)
    # Reports often have asymmetric margins: their gutter is not necessarily
    # at page.width/2. Find a persistent prose gutter in the central band.
    rich_lines=[]
    for line in lines.values():
        text=' '.join(w['text'] for w in line)
        letters=sum(c.isalpha() for c in text)
        if letters>=40 and letters/max(1,len(text.replace(' ','')))>=.7:
            rich_lines.append(line)
    candidates=[]
    for split in range(int(x0+width*.38),int(x0+width*.62),2):
        supporters=[]
        support_lines=0
        comparable_lines=0
        for line in rich_lines:
            left=[w for w in line if w['x1']<split-3]
            right=[w for w in line if w['x0']>split+3]
            crossing=[w for w in line if w['x0']<split+3 and w['x1']>split-3]
            substantial=(len(left)>=3 and len(right)>=3
                and sum(len(w['text']) for w in left)>=20 and sum(len(w['text']) for w in right)>=20)
            if substantial:
                comparable_lines+=1
                if not crossing:
                    supporters.extend(line)
                    support_lines+=1
        if support_lines>=8 and support_lines/max(1,comparable_lines)>=.6:
            candidates.append((support_lines,-abs(split-mid),split,supporters))
    if not candidates:
        # Independent paragraph baselines can be staggered across columns.
        # Require substantial prose on each side and a persistent empty gutter;
        # numeric table columns cannot meet the right-hand prose requirement.
        for split in range(int(x0+width*.38),int(x0+width*.62),2):
            left_lines=right_lines=crossing_lines=0;supporters=[]
            for line in rich_lines:
                left=[w for w in line if w['x1']<split-3]
                right=[w for w in line if w['x0']>split+3]
                crossing=[w for w in line if w['x0']<split+3 and w['x1']>split-3]
                left_rich=sum(sum(c.isalpha() for c in w['text']) for w in left)>=20
                right_rich=sum(sum(c.isalpha() for c in w['text']) for w in right)>=20
                left_lines+=left_rich;right_lines+=right_rich
                crossing_lines+=bool(crossing)
                if (left_rich or right_rich) and not crossing:supporters.extend(line)
            if min(left_lines,right_lines)>=12 and crossing_lines/max(1,len(rich_lines))<=.12:
                candidates.append((left_lines+right_lines,-abs(split-mid),split,supporters))
    if not candidates:
        return visible.extract_text(x_tolerance=2) or '', 'single_or_table'
    _,_,mid,supporters=max(candidates,key=lambda item:item[:2])
    y0=max(0,min(w['top'] for w in supporters)-2)
    y1=min(page.height,max(w['bottom'] for w in supporters)+2)
    boxes=[(x0,top,x1,y0),(x0,y0,mid,y1),(mid,y0,x1,y1),(x0,y1,x1,bottom)]
    # Assign each full word exactly once. Cropping character boxes can cut
    # letters at a gutter or at the top/bottom of a paragraph.
    groups=[[],[],[],[]]
    for word in words:
        y=(word['top']+word['bottom'])/2
        group=0 if y<y0 else 3 if y>=y1 else 1 if (word['x0']+word['x1'])/2<mid else 2
        groups[group].append(word)
    parts=[]
    for group in groups:
        ordered=[]
        for word in sorted(group,key=lambda w:(w['top'],w['x0'])):
            line=next((line for line in reversed(ordered[-3:]) if abs(line[0]['top']-word['top'])<3),None)
            if line is None:ordered.append([word])
            else:line.append(word)
        parts.append('\n'.join(' '.join(w['text'] for w in sorted(line,key=lambda w:w['x0'])) for line in ordered))
    return '\n'.join(p for p in parts if p), 'two_columns'

def read_pdf(path: str):
    path = Path(path)
    digest = file_digest(path)
    pages = []
    with pdfium.PdfDocument(str(path)) as document:
        count=len(document)
    callback=DOCUMENT_PROGRESS.get()
    # Reopen small batches so pdfminer document/resource caches cannot grow
    # with every page of the report. Only extracted strings are retained.
    for start in range(1,count+1,PDF_BATCH_SIZE):
        ids=list(range(start,min(count+1,start+PDF_BATCH_SIZE)))
        with pdfplumber.open(path,pages=ids) as pdf:
            for page in pdf.pages:
                try:
                    text,layout = visible_text(page)
                    from .table_layout import table_layout
                    tables=table_layout(page) if len(re.findall(r'20\d\d',text))>=2 or re.search(r'Marktanteile zum 31\. Dezember 20\d\d',text) else []
                    native=clean_page(page).extract_text(x_tolerance=2) or ''
                    expected=Counter(c for c in native if c.isalnum())
                    actual=Counter(c for c in text if c.isalnum())
                    if expected-actual:
                        text,layout=native,'full_layout_fallback'
                    from .ocr import needs_ocr, read_ocr_page
                    if needs_ocr(text,page):
                        if callback:callback({'stage':'document','detail':f'PDF-Seite {page.page_number} von {count} · lokale Texterkennung','completed':page.page_number-1,'total':count})
                        text=read_ocr_page(path,page.page_number)
                        layout='ocr';tables=[]
                    regions=[]
                    if page.width>page.height and layout!='ocr':
                        for x0,x1 in [(0,page.width/2),(page.width/2,page.width)]:
                            regions.append(visible_text(page.within_bbox((x0,0,x1,page.height)))[0])
                    from .kpi_cards import card_layout
                    cards=card_layout(page) if layout!='ocr' else []
                    pages.append({'page':page.page_number,'text':text,'layout':layout,'tables':tables,'narrative_regions':regions,'cards':cards})
                    if callback:
                        callback({'stage':'document','detail':f"PDF-Seite {page.page_number} von {count} lesen · Seitenspeicher freigeben",
                            'completed':page.page_number,'total':count})
                finally:
                    page.close()
    if sum(len(p['text']) for p in pages) < 200:
        raise ValueError('Das PDF enthält zu wenig lesbaren Text. Auch die lokale Texterkennung konnte keine ausreichenden Inhalte lesen.')
    themes = {name:[p['page'] for p in pages if re.search(pattern,p['text'],re.I)] for name,pattern in THEMES.items()}
    target = RUNTIME / f'{digest}-pages.json'
    target.write_text(json.dumps(pages,ensure_ascii=False))
    return digest,pages,themes

def relevant_pages(pages, themes, limit=None):
    candidates = []
    for page in pages:
        hits = sum(page['page'] in ids for ids in themes.values())
        numeric = len(re.findall(r'\d[\d.,]*\s*(?:[kMG]Wp?|[kMGT]Wh|T€|TEUR|Mio\.|Ladepunkt)',page['text'],re.I))
        if hits and numeric:
            candidates.append((hits + min(numeric,8),page))
    ordered = sorted(candidates,key=lambda x:x[1]['page'])
    return [p for _,p in (ordered if limit is None else ordered[:limit])]


def evidence_span(source, excerpt):
    """Match only layout changes, and return the actual original source span.

    Numbers, units, punctuation and word order are never repaired or guessed.
    Only whitespace, soft hyphens and lowercase word continuation after a
    printed line-break hyphen may differ.
    """
    def canonical(text):
        removed=set()
        for match in re.finditer(r'(?<=[A-Za-zÄÖÜäöüß])[-\u00ad][ \t]*\r?\n[ \t]*(?=[a-zäöüß])',text):
            removed.update(range(match.start(),match.end()))
        output=[]; offsets=[]
        for index,char in enumerate(text):
            if index in removed or char=='\u00ad':
                continue
            if char.isspace():
                if output and output[-1]!=' ':
                    output.append(' ');offsets.append(index)
            else:
                output.append(char);offsets.append(index)
        return ''.join(output).strip(),offsets
    haystack,offsets=canonical(source)
    needle,_=canonical(excerpt)
    if not needle:
        return None
    start=haystack.find(needle)
    if start<0:
        return None
    return source[offsets[start]:offsets[start+len(needle)-1]+1]


def detect_report_year(pages):
    """Prefer a labelled cover year, then repeated labelled report headers.

    A facts excerpt may instead supply repeated current/prior-year columns.
    Publication dates, forecasts and isolated unlabelled years are not votes.
    Ambiguous titles require clarification rather than a guessed year.
    """
    hits = []
    fiscal_hits=[]
    for page in pages:
        for match in re.finditer(r'(?:Geschäftsbericht|Jahresbericht|Jahresabschluss|Geschäftsjahr)[\s:–—-]*(20\d{2})\s*/\s*(20\d{2}|\d{2})(?!\d)',page['text'],re.I):
            start=int(match[1]);end=int(match[2]) if len(match[2])==4 else start//100*100+int(match[2])
            if end==start+1:
                fiscal_hits.append({'year':end,'period_label':f'{start}/{end}','start_year':start,
                    'period_kind':'fiscal_year','page':page['page'],'evidence':match[0]})
    fiscal_cover=[h for h in fiscal_hits if h['page']<=2]
    if fiscal_cover:
        return fiscal_cover[0] if len({h['year'] for h in fiscal_cover})==1 else None
    pattern = r'(?:Geschäftsbericht|Jahresbericht|Jahresabschluss|Geschäftsjahr)[\s:–—-]*(20\d{2})(?!\s*[/–-]\s*\d{2,4})'
    for page in pages:
        for match in re.finditer(pattern, page['text'], re.I):
            hits.append({'year': int(match[1]), 'page': page['page'], 'evidence': match[0]})
    cover = [h for h in hits if h['page'] <= 2]
    if not cover and fiscal_hits:
        counts={y:len({h['page'] for h in fiscal_hits if h['year']==y}) for y in {h['year'] for h in fiscal_hits}}
        winners=[y for y,n in counts.items() if n==max(counts.values())]
        if len(winners)!=1:return None
        return next(h for h in fiscal_hits if h['year']==winners[0])
    pool = cover or hits
    if not pool:
        return _comparison_report_year(pages)
    counts = {year: len({h['page'] for h in pool if h['year'] == year}) for year in {h['year'] for h in pool}}
    winners = [year for year, count in counts.items() if count == max(counts.values())]
    if len(winners) != 1:
        return None
    return next(h for h in pool if h['year'] == winners[0])


def _comparison_report_year(pages):
    """Recognize a facts overview's repeated descending annual comparisons.

    Require both an overview heading and financial results, two matching
    current/prior column pairs, and no competing pairs or planning language.
    This also works with line-separated OCR text of infographic excerpts.
    """
    hits=[]
    for page in pages:
        text=page['text']
        if not re.search(r'auf einen Blick|Kennzahlen|Zahlen,?\s+Daten,?\s+Fakten',text,re.I):
            continue
        if not re.search(r'Konzernergebnis|Jahres[üu]berschuss|Gewinn.*Verlust',text,re.I):
            continue
        if re.search(r'\b(?:Plan\w*|Prognos\w*|Budget\w*|Zieljahr|Ausblick)\b',text,re.I):
            continue
        pairs=list(re.finditer(r'(?m)^[ \t]*(20\d{2})[ \t]*\r?\n[ \t]*(20\d{2})[ \t]*$',text))
        if len(pairs)<2:
            continue
        years={(int(match[1]),int(match[2])) for match in pairs}
        if len(years)!=1:
            continue
        current,previous=next(iter(years))
        if current!=previous+1:
            continue
        hits.append({'year':current,'page':page['page'],
                     'evidence':pairs[0][0].strip(),'method':'repeated_comparison_columns'})
    if len({hit['year'] for hit in hits})!=1:
        return None
    return hits[0]
