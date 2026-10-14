"""Bounded, portable CPU OCR for image pages and broken PDF font encodings."""
import re
import hashlib
from functools import lru_cache
from .config import RUNTIME
import pypdfium2 as pdfium


def needs_ocr(text, page):
    broken=len(re.findall(r'\(cid:\d+\)',text))
    if broken>15:return True
    # Some wrong ToUnicode maps yield printable cipher text rather than cid
    # placeholders. Repeated symbols/digits inside words distinguish these
    # pages from normal financial tables, punctuation and decorative icons.
    words=[word for word in text.split() if len(word)>=5 and any(c.isalpha() for c in word)]
    damaged=[word for word in words if re.search(
        r'[A-Za-zÄÖÜäöüß][^\w\s.,:;()\[\]/%€+−–—\-²³][A-Za-zÄÖÜäöüß0-9]'
        r'|[A-Za-zÄÖÜäöüß][0-9][A-Za-zÄÖÜäöüß]',word)]
    if len(damaged)>=10 and len(damaged)/max(1,len(words))>.2:return True
    # Decorative/photo pages are not sent through OCR merely for being short.
    return len(text.strip())<40 and bool(page.images)


@lru_cache(maxsize=1)
def _engine():
    from rapidocr_onnxruntime import RapidOCR
    return RapidOCR(intra_op_num_threads=1,inter_op_num_threads=1,det_limit_side_len=1600,det_limit_type='max',det_box_thresh=.35,text_score=.35)


def read_ocr_page(path, number):
    import numpy as np
    from pathlib import Path
    source=Path(path);stat=source.stat()
    key=hashlib.sha256(f'{source.resolve()}:{stat.st_size}:{stat.st_mtime_ns}:{number}:ocr-v3'.encode()).hexdigest()
    cache=RUNTIME/f'{key}-ocr.txt'
    if cache.exists():return cache.read_text()
    engine=_engine()
    with pdfium.PdfDocument(str(path)) as document:
        page=document[number-1]
        bitmap=page.render(scale=2)
        try:
            rendered=bitmap.to_pil().convert('RGB')
            # A damaged font still supplies exact character coordinates. Use
            # those line boxes so the OCR detector cannot omit entire lines.
            import pdfplumber
            with pdfplumber.open(source,pages=[number]) as pdf:
                native=pdf.pages[0].within_bbox(pdf.pages[0].bbox).dedupe_chars()
                broken=len(re.findall(r'\(cid:\d+\)',native.extract_text() or ''))>15
                lines=[]
                if broken:
                    for char in sorted(native.chars,key=lambda c:(c['top'],c['x0'])):
                        line=next((line for line in reversed(lines[-3:]) if abs(line[0]['top']-char['top'])<3),None)
                        if line is None:lines.append([char])
                        else:line.append(char)
            if broken:
                result=[]
                for line in lines:
                    box=(max(0,int((min(c['x0'] for c in line)-2)*2)),max(0,int((min(c['top'] for c in line)-2)*2)),min(rendered.width,int((max(c['x1'] for c in line)+2)*2)),min(rendered.height,int((max(c['bottom'] for c in line)+2)*2)))
                    if box[2]<=box[0] or box[3]<=box[1]:continue
                    recognized,_=engine(np.asarray(rendered.crop(box)),use_det=False,use_cls=False)
                    for item in recognized or []:result.append([box,item[0],item[1]])
            else:result,_=engine(np.asarray(rendered))
        finally:bitmap.close();page.close()
    if not result:return ''
    # OCR text is retained separately; it is not silently treated as a verified
    # original PDF cell. Numeric observations from these pages require review.
    text='\n'.join(item[1] for item in result)
    cache.write_text(text)
    return text
