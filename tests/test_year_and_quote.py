from datetime import date
from pathlib import Path
import pytest
from stadtwerke.documents import detect_report_year
from stadtwerke.extraction import validate, source_facts
from stadtwerke.models import Candidate
from stadtwerke.review import review_groups
import json


def guetersloh_excerpt():
    return json.loads((Path(__file__).parent/'fixtures/guetersloh_year_excerpt.json').read_text())


def test_printable_broken_font_uses_ocr_but_clean_excerpt_does_not():
    from stadtwerke.ocr import needs_ocr
    fixture=guetersloh_excerpt()
    page=type('Page',(),{'images':[]})()
    assert needs_ocr(fixture['native_text'],page)
    assert not needs_ocr(fixture['pages'][0]['text'],page)
    assert not needs_ocr('PV-Anlagen CO2-Emissionen 10,5 Mio. EUR\n'*30,page)


def test_actual_guetersloh_excerpt_year_from_repeated_comparison_columns():
    result=detect_report_year(guetersloh_excerpt()['pages'])
    assert result=={'year':2024,'page':1,'evidence':'2024\n2023',
                   'method':'repeated_comparison_columns'}


@pytest.mark.parametrize('text',[
    'Kennzahlen\nKonzernergebnis\n2024\n2023',
    'Kennzahlen\nKonzernergebnis\n2024\n2023\nPlan\n2024\n2023',
    'Kennzahlen\nKonzernergebnis\n2024\n2023\n2025\n2024',
    'Kennzahlen\nKonzernergebnis\n2023\n2024\n2023\n2024',
    'Kennzahlen\nKonzernergebnis\n2024\n2022\n2024\n2022',
    'Publikation\n2024\n2023\n2024\n2023',
])
def test_comparison_year_requires_consistent_reported_annual_columns(text):
    assert detect_report_year([{'page':1,'text':text}]) is None


def test_labelled_cover_precedes_excerpt_year():
    pages=[{'page':1,'text':'Geschäftsbericht 2025'},
           {**guetersloh_excerpt()['pages'][0],'page':5}]
    assert detect_report_year(pages)['year']==2025


def test_guetersloh_excerpt_ingestion_passes_year_detection(monkeypatch,tmp_path):
    from stadtwerke import database,workflow
    monkeypatch.setattr(database,'DB_PATH',tmp_path/'archive.duckdb')
    pages=guetersloh_excerpt()['pages']
    monkeypatch.setattr(workflow,'read_pdf',lambda _:('guetersloh-excerpt',pages,{}))
    monkeypatch.setattr(workflow,'municipality_context',lambda *args:{'country':'DE'})
    result=workflow.ingest({'provider':'ollama','path':str(tmp_path/'excerpt.pdf'),
                            'company':'Stadtwerke Gütersloh','max_pages':0})
    assert result['report']['metadata']['year']==2024
    assert result['report']['pages'][0]['layout']=='ocr'
    assert database.load_report('guetersloh-excerpt')['metadata']['year']==2024


def observation(text, year=2024):
    return Candidate(metric='pv_capacity_dc',raw_value='12,5',raw_unit='MWp',year=year,
        evidence=text,scope='own',basis='stock',portfolio='total',geography='DE')


def test_report_year_uses_title_instead_of_forecast_or_publication_date():
    pages=[{'page':1,'text':'Geschäftsbericht\n2024\nVeröffentlicht 2025. Ausblick 2026.'},
           {'page':4,'text':'Geschäftsjahr 2025 der Beteiligung.'}]
    assert detect_report_year(pages)['year']==2024
    assert detect_report_year([{'page':1,'text':'Publikation 2025. Prognose 2026.'}]) is None
    assert detect_report_year([{'page':1,'text':'Geschäftsbericht 2024 und Geschäftsbericht 2025'}]) is None
    fiscal=detect_report_year([{'page':1,'text':'Geschäftsjahr 2024/25'}])
    assert fiscal['year']==2025 and fiscal['period_label']=='2024/2025'


@pytest.mark.parametrize('text,source_year',[
    ('Eigene PV-Anlagen in Deutschland: insgesamt 12,5 MWp am 31.12.2023.',2023),
    ('Eigene PV-Anlagen in Deutschland: insgesamt 12,5 MWp.',None),
])
def test_model_cannot_assign_reporting_year_without_original_evidence(text,source_year):
    row=validate(observation(text),{'page':2,'text':text},2024)
    assert row['status']=='needs_review'
    assert row['source_year']==source_year
    groups=review_groups({'metadata':{'year':2024},'observations':[row]})
    assert groups['rejected']==[row]
    assert not groups['accepted'] and not groups['targeted']


def test_direct_rule_retains_actual_wrong_year_for_audit():
    text='Ende 2023 waren eigene PV-Anlagen in Deutschland mit insgesamt 12,5 MWp installiert.'
    rows=source_facts({'page':2,'text':text},2024)
    assert rows[0]['year']==2023
    assert not review_groups({'metadata':{'year':2024},'observations':rows})['targeted']


def test_ui_quote_opens_page_and_topic_selection_has_no_year_or_scenario(monkeypatch,tmp_path):
    from streamlit.testing.v1 import AppTest
    from stadtwerke import database, pdf_preview
    text='Eigene PV-Anlagen in Deutschland: insgesamt 12,5 MWp am 31.12.2024.'
    row=validate(observation(text),{'page':1,'text':text},2024)
    source=tmp_path/'report.pdf';source.write_bytes(b'fixture')
    report={'id':'quote-fixture','metadata':{'company':'Testversorger','year':2024,
        'path':str(source),'page_count':1,'analyzed_pages':[1]},
        'pages':[{'page':1,'text':text}],'observations':[row],'themes':{}}
    monkeypatch.setattr(database,'DB_PATH',tmp_path/'reports.duckdb')
    database.save_report(report)
    class Response:
        def json(self): return {'models':[]}
    monkeypatch.setattr('httpx.get',lambda *a,**k:Response())
    # Valid PNG so Streamlit's media manager exercises the real popup path.
    from PIL import Image
    import io
    png=io.BytesIO();Image.new('RGB',(20,20),'white').save(png,format='PNG')
    monkeypatch.setattr(pdf_preview,'preview_page',lambda *a:(png.getvalue(),b'one-page-pdf'))
    monkeypatch.setattr(pdf_preview,'source_focus',lambda *a:None)
    at=AppTest.from_file(str(Path(__file__).parents[1]/'app.py'),default_timeout=5)
    at.session_state['state']={'report':report}
    at.session_state['workflow_session']='fixture'
    at.run()
    assert not at.exception
    assert not at.slider
    assert not any(n.label in ('Berichtsjahr','Zieljahr','Originalseite auswählen') for n in at.number_input)
    assert any(f'Ausblick {date.today().year}' in c.value for c in at.caption)
    assert not any('Im Originalbericht nachsehen' in e.label for e in at.expander)
    quote=next(b for b in at.button if b.label=='PDF-Seite 1 öffnen ↗\n\n„'+text+'“')
    quote.click().run()
    assert not at.exception
    assert any('Ganze Originalseite' in e.label for e in at.expander)
    assert any('PDF-Seite 1' in b.label for b in at.get('download_button'))


def test_quantity_equal_to_year_does_not_prove_a_date():
    text='Eigene PV-Anlagen in Deutschland: insgesamt 2024 MWp.'
    c=observation(text).model_copy(update={'raw_value':'2024'})
    row=validate(c,{'page':1,'text':text},2024)
    assert row['year_status']=='unconfirmed'
    assert row['status']=='needs_review'
