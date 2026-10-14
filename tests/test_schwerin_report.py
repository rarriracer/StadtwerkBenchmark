import json
from pathlib import Path
import pdfplumber
import pytest
from stadtwerke.documents import visible_text
from stadtwerke.extraction import source_facts
from stadtwerke.kpi_cards import reconcile_cards
from stadtwerke.calculation import available_metrics
from stadtwerke.pdf_geometry import clean_page

ROOT=Path(__file__).resolve().parents[1]
PDF=ROOT/'Geschäftsberichte/Testberichte/Schwerin_2024.pdf'


def test_schwerin_original_values_company_volume_outlooks_and_personnel():
    pages=json.loads((Path(__file__).parent/'fixtures/schwerin_2024_sources.json').read_text())
    rows=reconcile_cards([r for p in pages for r in source_facts(p,2024)])
    options=available_metrics({'metadata':{'year':2024,'location':{'city':'Schwerin'}},'observations':rows})
    assert set(options)=={'electricity_sales_total','gas_sales_total','employees'}
    expected={'electricity_sales_total':347000,'gas_sales_total':552000,'heat_sales':316000,
              'water_sales':5223000,'revenue':228492398.74,'debt':52687549.95,'interest_expense':3191240.64,'net_income':-95068.72}
    for metric,value in expected.items():
        assert any(r['metric']==metric and r['value']==pytest.approx(value) and r['status']=='validated' for r in rows)
        if metric in options:assert options[metric]['observation']['value']==pytest.approx(value)
    for metric,value in [('electricity_customers',91483),('gas_customers',21767),('employees',360)]:
        assert any(r['metric']==metric and r['value']==value and r['status']=='validated' for r in rows)
    # Previous-year quantities, local subsets and a planned PV project must
    # never be promoted to current total sales / installed total capacity.
    assert not any(r['metric']=='electricity_sales_total' and r['value'] in (313000,140000,207000) for r in rows)
    heat_card=next(r for r in rows if r['metric']=='heat_sales' and r.get('evidence_kind')=='pdf_kpi_card')
    assert heat_card['value']==315000 and heat_card['status']=='needs_review'
    assert all(r['value']!=21095 for r in rows if r['metric']=='gas_customers')


@pytest.mark.skipif(not PDF.exists(),reason='Lokales Original-PDF nicht vorhanden')
def test_real_spread_keeps_customer_sentence_and_deduplication_identical():
    with pdfplumber.open(PDF,pages=[6]) as pdf:
        p=pdf.pages[0]
        assert clean_page(p).chars==p.within_bbox(p.bbox).dedupe_chars().chars
        text,layout=visible_text(p)
        assert layout=='spread'
        from stadtwerke.documents import evidence_span
        assert evidence_span(text,'Insgesamt hatte die SWS zum Jahresende 91483 Stromkunden') is not None
        assert evidence_span(text,'Zum Jahresende 2024 hatte die SWS 21767 Gaskunden') is not None


def test_location_from_explicit_company_name_with_filename_input(monkeypatch):
    from stadtwerke import workflow
    monkeypatch.setattr(workflow,'municipality_context',lambda company,city:{'city':city})
    assert workflow.report_location('Schwerin 2024','',[{'text':'Stadtwerke Schwerin GmbH'}])['city']=='Schwerin'
    assert workflow.report_location('Unbekannt','',[{'text':'Stadtwerke Schwerin GmbH; Stadtwerke Stade GmbH'}])['city']==''
