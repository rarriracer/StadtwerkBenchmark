import pytest
import pypdfium2 as pdfium
from stadtwerke.documents import evidence_span,visible_text
from stadtwerke.pdf_preview import preview_page
from stadtwerke.extraction import validate
from stadtwerke.models import Candidate


@pytest.mark.parametrize('source,excerpt',[
    ('  Eigene PV-Anlagen in Deutschland: insgesamt 12,5 MWp Ende 2024.','Eigene PV-Anlagen in Deutschland: insgesamt 12,5 MWp Ende 2024.'),
    ('Die installierte Leis-\ntung beträgt 12,5 MWp.','Die installierte Leistung beträgt 12,5 MWp.'),
    ('Leistung 12,5\n MWp.','Leistung 12,5 MWp.')])
def test_layout_match_returns_original_span(source,excerpt):
    span=evidence_span(source,excerpt)
    assert span is not None and span in source


@pytest.mark.parametrize('excerpt',['Leistung 125 MWp.','Leistung 12,5 MWh.','Leistung beträgt 12,5 MWp.'])
def test_layout_match_does_not_repair_numbers_units_or_words(excerpt):
    assert evidence_span('Leistung 12,5 MWp.',excerpt) is None


def test_validated_layout_quote_keeps_original_source():
    original='Eigene PV-Anlagen in Deutschland: insgesamt 12,5 MWp installierte Leis-\ntung Ende 2024.'
    c=Candidate(metric='pv_capacity_dc',raw_value='12,5',raw_unit='MWp',year=2024,
        evidence=original.replace('Leis-\ntung','Leistung'),scope='group',basis='stock',portfolio='total',geography='DE')
    result=validate(c,{'page':3,'text':original},2024)
    assert result['status']=='validated'
    assert result['evidence']==original
    assert 'evidence_adjustment' in result


def test_one_page_preview_preserves_page_content_and_bounds(tmp_path):
    # Actual PDF rendering and page import, without external executables.
    with pdfium.PdfDocument.new() as source:
        page=source.new_page(595,842);page.close()
        page=source.new_page(400,300);page.close()
        path=tmp_path/'two-pages.pdf';source.save(path)
    png,pdf=preview_page(path,2)
    assert png.startswith(b'\x89PNG')
    with pdfium.PdfDocument(pdf) as single:
        assert len(single)==1
        assert single[0].get_size()==(400,300)
    with pytest.raises(ValueError):preview_page(path,3)


def test_asymmetric_gutter_with_small_baseline_variations():
    class FakePage:
        width=600;height=800;bbox=(0,0,600,800)
        def within_bbox(self,box):
            if box!=self.bbox:
                return type('Crop',(),{'extract_text':lambda s,**k:'LEFT' if box[0]==0 else 'RIGHT'})()
            return self
        def dedupe_chars(self):return self
        def extract_words(self,**kwargs):
            words=[]
            for line in range(14):
                for index in range(5):
                    words.append({'text':'leftproseword','x0':60+index*44,'x1':100+index*44,'top':40+line*14.2,'bottom':49+line*14.2})
                    words.append({'text':'rightproseword','x0':325+index*44,'x1':365+index*44,'top':39.9+line*14.2,'bottom':48.9+line*14.2})
            return words
        def extract_text(self,**kwargs):return 'MERGED'
    text,layout=visible_text(FakePage())
    assert layout=='two_columns'
    assert text.count('leftproseword')==70 and text.count('rightproseword')==70
    assert text.rfind('leftproseword')<text.find('rightproseword')


def test_source_crop_requires_one_unique_number_unit_pair(monkeypatch):
    from io import BytesIO
    from PIL import Image
    from stadtwerke.pdf_preview import source_focus
    class Page:
        bbox=(0,0,600,800);height=800
        words=[{'text':'90','top':600,'bottom':612},{'text':'MWp.','top':600,'bottom':612}]
        def within_bbox(self,_):return self
        def extract_words(self,**kwargs):return self.words
    class Document:
        pages=[Page()]
        def __enter__(self):return self
        def __exit__(self,*a):pass
    monkeypatch.setattr('pdfplumber.open',lambda _:Document())
    png=BytesIO();Image.new('RGB',(600,800),'white').save(png,format='PNG')
    crop=source_focus(png.getvalue(),'test.pdf',1,'90','MWp')
    with Image.open(BytesIO(crop)) as image:assert image.height<800
    Document.pages[0].words*=2
    assert source_focus(png.getvalue(),'test.pdf',1,'90','MWp') is None
    assert source_focus(png.getvalue(),'test.pdf',1,'99','MWp') is None
