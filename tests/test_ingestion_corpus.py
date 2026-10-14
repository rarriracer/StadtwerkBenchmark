"""Regression corpus: literal PDF cells versus independently read control values."""
import json
import math
from pathlib import Path
import pytest
from stadtwerke.extraction import source_facts, validate
from stadtwerke.models import Candidate
from stadtwerke.ocr import needs_ocr

FIXTURES=Path(__file__).parent/'fixtures'
EXPECTED=json.loads((FIXTURES/'ingestion_expected.json').read_text())


@pytest.mark.parametrize('case',EXPECTED,ids=lambda c:f"{c['report']}-p{c['page']}-{c['metric']}-{c['value']}")
def test_control_value_from_original_report(case):
    corpus=json.loads((FIXTURES/'ingestion_pages.json').read_text())
    report=corpus[case['report']]
    page=next(p for p in report['pages'] if p['page']==case['page'])
    rows=source_facts(page,report['year'])
    assert any(r['metric']==case['metric'] and r.get('status')=='validated' and r.get('unit')==case['unit'] and r.get('value') is not None and math.isclose(r['value'],case['value'],rel_tol=1e-9,abs_tol=1e-7) and (not case.get('reporting_scope') or case['reporting_scope']==r.get('reporting_scope')) and (not case.get('entity') or case['entity']==r.get('entity')) for r in rows),case


@pytest.mark.parametrize('year',[2024,2025])
def test_bremen_keeps_both_cohorts_and_uses_consolidated_sales(year):
    from stadtwerke.calculation import available_metrics
    corpus=json.loads((FIXTURES/'ingestion_pages.json').read_text())[f'Bremen_{year}']
    page=next(p for p in corpus['pages'] if p['page']==3)
    rows=source_facts(page,year)
    assert len(rows)==25
    report={'metadata':{'year':year,'location':{'city':'Bremen'}},'observations':rows}
    available=available_metrics(report)
    for metric in ('electricity_sales_total','gas_sales_total','heat_sales'):
        cohorts=[r for r in rows if r['metric']==metric]
        assert {r['reporting_scope'] for r in cohorts}=={'consolidated','extended_group'}
        if metric=='heat_sales':
            assert metric not in available
        else:
            assert available[metric]['observation']['reporting_scope']=='consolidated'
            assert available[metric]['observation']['value']!=next(r['value'] for r in cohorts if r['reporting_scope']=='extended_group')


def test_bremen_cashflow_with_full_date_range_is_read():
    corpus=json.loads((FIXTURES/'ingestion_pages.json').read_text())['Bremen_2024']
    page=next(p for p in corpus['pages'] if p['page']==37)
    assert any(r['metric']=='operating_cashflow' and r['value']==38230000 for r in source_facts(page,2024))


def test_actual_muenster_plan_is_not_a_reported_baseline():
    report=json.loads((FIXTURES/'ingestion_pages.json').read_text())['Muenster_2023']
    p=next(p for p in report['pages'] if p['page']==31)
    assert not source_facts(p,2024)


def test_customer_segment_is_not_total_sales():
    report=json.loads((FIXTURES/'ingestion_pages.json').read_text())['Karlsruhe_2024']
    p=next(p for p in report['pages'] if p['page']==39)
    rows=source_facts(p,2024)
    assert not any(r['metric']=='electricity_sales_total' and r.get('value')==378000 for r in rows)


def test_broken_font_encoding_triggers_ocr():
    assert needs_ocr('(cid:123)'*16,type('Page',(),{'images':[]})())
    assert not needs_ocr('Titelseite',type('Page',(),{'images':[]})())


def test_ocr_number_is_never_silently_released():
    candidate=Candidate(metric='electricity_sales_total',raw_value='100',raw_unit='GWh',year=2024,evidence='Stromabsatz 2024: 100 GWh',scope='group',basis='annual_sales',portfolio='total')
    row=validate(candidate,{'page':1,'text':candidate.evidence,'layout':'ocr'},2024)
    assert row['status']=='needs_review' and row['evidence_kind']=='ocr'


def test_actual_broken_font_page_keeps_all_paragraph_lines():
    report=json.loads((FIXTURES/'ingestion_pages.json').read_text())['Leipzig_2024']
    page=next(p for p in report['pages'] if p['page']==24)
    assert page['layout']=='ocr'
    assert '(cid:' not in page['text']
    assert '31.12.2029' in page['text']
    assert 'Geschäftsfuhrerpositionen Frauen' in page['text']
    assert '30,0 %' in page['text'] and '35,0 %' in page['text']
