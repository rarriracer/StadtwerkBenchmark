"""Read explicitly dated market-share tables with named places and segments."""
import re
from .pdf_geometry import clean_page


def market_share_layout(page):
    source=clean_page(page).extract_text(x_tolerance=2) or ''
    date=re.search(r'Marktanteile zum 31\. Dezember (20\d\d)',source)
    if not date or 'Vorjahr' not in source:return []
    year=int(date[1]);words=clean_page(page).extract_words(x_tolerance=2)
    cities=[w for w in words if w['text'] in ('HB','BHV')]
    segments=[w for w in words if re.fullmatch(r'(?:SLP|RLM)-Geschäftskunden',w['text'])]
    results=[]
    for city in cities:
        nearby=[s for s in segments if 0<city['top']-s['top']<25]
        if not nearby:continue
        segment=min(nearby,key=lambda s:abs((city['x0']+city['x1']-s['x0']-s['x1'])/2))
        row_cities=[w for w in cities if abs(w['top']-city['top'])<3]
        centers=sorted((w['x0']+w['x1'])/2 for w in row_cities)
        center=(city['x0']+city['x1'])/2;index=centers.index(center)
        gap=min(b-a for a,b in zip(centers,centers[1:])) if len(centers)>1 else 40
        left=(centers[index-1]+center)/2 if index else center-gap/2
        right=(centers[index+1]+center)/2 if index+1<len(centers) else center+gap/2
        table={'years':[year,year-1],'roles':['reported','reported'],'header':date[0]+'\n'+segment['text']+' '+city['text']+' · Vorjahr',
               'heading':'Marktanteil','kind':'market_share','column_units':['%','%'],'column_entities':['',''],
               'market_entity':segment['text']+' · '+('Bremen' if city['text']=='HB' else 'Bremerhaven'),'rows':[]}
        labels=[w for w in words if w['text'] in ('Strom','Gas') and city['top']<w['top']<city['top']+70 and w['x1']<centers[0]-gap/2]
        for label in labels:
            cell=[w for w in words if left<=(w['x0']+w['x1'])/2<right and abs(w['top']-label['top'])<4]
            first=re.search(r'(\d+(?:,\d+)?)\s*%', ' '.join(w['text'] for w in cell))
            below=[w for w in words if left<=(w['x0']+w['x1'])/2<right and label['top']+4<w['top']<label['top']+14]
            tail=' '.join(w['text'] for w in cell)[first.end():] if first else ''
            previous=re.search(r'\(\s*(\d+(?:,\d+)?)\s*%\s*\)',tail)
            if previous:below=[]
            else:previous=re.search(r'\(\s*(\d+(?:,\d+)?)\s*%\s*\)',' '.join(w['text'] for w in below))
            if not first or not previous:continue
            included=[label]+cell+below
            table['rows'].append({'label':label['text'],'values':[first[1],previous[1]],'units':['%','%'],
                'evidence':label['text']+' '+first[0]+' ('+previous[1]+' %)',
                'bbox':[min(w['x0'] for w in included),min(w['top'] for w in included),max(w['x1'] for w in included),max(w['bottom'] for w in included)]})
        if table['rows']:results.append(table)
    return results
