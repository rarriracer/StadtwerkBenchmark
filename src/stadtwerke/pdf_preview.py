"""Portable one-page proof view, no system Poppler/Office installation needed."""
from io import BytesIO
import pypdfium2 as pdfium
import threading

PDF_LOCK=threading.RLock()


def preview_page(path, page_number):
    with PDF_LOCK, pdfium.PdfDocument(str(path)) as document:
        if not 1<=page_number<=len(document):
            raise ValueError('PDF-Seite außerhalb des Dokuments')
        page=document[page_number-1]
        bitmap=page.render(scale=1.65)
        image=bitmap.to_pil()
        png=BytesIO();image.save(png,format='PNG')
        image.close();bitmap.close();page.close()
        with pdfium.PdfDocument.new() as single:
            single.import_pages(document,pages=[page_number-1])
            pdf=BytesIO();single.save(pdf)
        return png.getvalue(),pdf.getvalue()


def source_focus(png,path,page_number,raw_value,raw_unit):
    """Show a literal image crop only if one unique number/unit pair is located."""
    import pdfplumber
    from PIL import Image
    with pdfplumber.open(str(path)) as document:
        page=document.pages[page_number-1]
        words=page.within_bbox(page.bbox).extract_words(x_tolerance=2)
        matches=[]
        for i,word in enumerate(words[:-1]):
            if (word['text'].rstrip('.,;:')==raw_value and
                words[i+1]['text'].rstrip('.,;:').casefold()==raw_unit.casefold()):
                matches.append((word,words[i+1]))
        if len(matches)!=1:
            return None
        top=max(0,min(w['top'] for w in matches[0])-110)
        bottom=min(page.height,max(w['bottom'] for w in matches[0])+95)
        with Image.open(BytesIO(png)) as image:
            scale=image.height/page.height
            crop=image.crop((0,int(top*scale),image.width,int(bottom*scale)))
            out=BytesIO();crop.save(out,format='PNG');crop.close()
        return out.getvalue()
