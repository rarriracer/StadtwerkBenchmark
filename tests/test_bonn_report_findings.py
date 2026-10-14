from pathlib import Path
import pdfplumber
import pytest
from stadtwerke.documents import visible_text
from stadtwerke.extraction import source_facts
from stadtwerke.review import report_findings


def test_actual_bonn_pdf_has_five_verified_operating_areas():
    path=Path(__file__).parents[1]/'Geschaeftsbericht Stadtwerke bonn.pdf'
    if not path.exists(): pytest.skip('Original Bonn fixture not available')
    pages=[]
    with pdfplumber.open(path) as document:
        for n in (12,13,20):
            text,_=visible_text(document.pages[n-1])
            pages.append({'page':n,'text':text})
    rows=[r for p in pages for r in source_facts(p,2025,{'country':'DE','city':'Bonn'})]
    released={r['metric']:r for r in rows if r['status']=='validated'}
    expected={'electricity_sales_total':896000,'gas_sales_total':1215000,'heat_sales':432000,
        'pv_capacity_dc':2.4,'charge_points':1800}
    assert set(released)==set(expected)
    for metric,value in expected.items():
        assert released[metric]['value']==pytest.approx(value)
        assert released[metric]['evidence_status']=='verified'
        assert released[metric]['year_status']=='verified'
    assert 'Preisanpassungen Anfang 2025' in released['electricity_sales_total']['evidence']
    assert released['charge_points']['qualifier']=='more_than'
    assert released['charge_points']['scope']=='network_area'
    assert released['charge_points']['entity']=='Bonner Stadtgebiet'
    findings=report_findings({'metadata':{'year':2025,'location':{'city':'Bonn'}},'observations':rows})
    assert len(findings)==5
    assert next(r for r in findings if r['Berichtsgröße']=='Ladepunkte')['Originalwert']=='über 1.800 Ladepunkte'
    assert sum(r['Referenzvergleich']=='Automatisch vergleichbar' for r in findings)==5


def test_annual_following_context_must_be_a_contiguous_nonforecast_quote():
    page={'page':1,'text':('Der Stromabsatz lag bei 100 GWh. Der Anstieg beruht auf zusätzlichen Kunden im Jahr 2025.')}
    row=next(r for r in source_facts(page,2025) if r['metric']=='electricity_sales_total')
    assert row['status']=='validated'
    assert row['evidence']==page['text']
    future={'page':1,'text':'Der Stromabsatz lag bei 100 GWh. Für 2025 sind zusätzliche Kunden geplant.'}
    row=next(r for r in source_facts(future,2025) if r['metric']=='electricity_sales_total')
    assert row['status']=='needs_review' and row.get('year_status')=='unconfirmed'


def test_charger_count_does_not_assign_summer_or_unknown_dates_to_year_end():
    page={'page':1,'text':'Im Sommer 2025 wurden 500 Ladepunkte erreicht. Heute gibt es 640 öffentliche Lademöglichkeiten.'}
    assert not any(r['metric']=='charge_points' for r in source_facts(page,2025))
