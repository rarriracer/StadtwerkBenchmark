from pathlib import Path
import pytest
import pdfplumber
from stadtwerke.documents import visible_text
from stadtwerke.table_layout import table_layout
from stadtwerke.extraction import source_facts
from stadtwerke.kpi_tables import layout_table_facts
from stadtwerke.calculation import available_metrics

ROOT=Path(__file__).parents[1]


def pages(path, numbers):
    if not path.exists():pytest.skip('Optional original report')
    with pdfplumber.open(path,pages=numbers) as pdf:
        return [{'page':p.page_number,'text':visible_text(p)[0],'tables':table_layout(p)} for p in pdf.pages]


def test_actual_stawag_ist_columns_are_sales_not_forecasts_or_grid_quantities():
    p=pages(ROOT/'STAWAG_GB2024_Web_251107.pdf',[61])[0]
    rows=source_facts(p,2024)
    m={r['metric']:r for r in rows}
    assert m['electricity_sales_total']['value']==646000
    assert m['gas_sales_total']['value']==1222000
    assert m['water_sales']['value']==30000000
    assert m['heat_contracting_sales']['value']==16000
    assert m['revenue']['value']==729562000
    assert all(r['table_reference']['role']=='ist' for r in rows)
    assert layout_table_facts(p,2025)==[]
    assert {'electricity_sales_total','gas_sales_total'}<=available_metrics({'metadata':{'year':2024},'observations':rows}).keys()


def test_actual_network_tables_preserve_footnotes_and_do_not_invent_customers():
    ps=pages(ROOT/'STAWAG_GB2024_Web_251107.pdf',[24,25])
    rows=[r for p in ps for r in layout_table_facts(p,2024)]
    m={r['metric']:r for r in rows}
    assert m['electricity_network_input']['value']==1864000
    assert m['gas_network_input']['value']==5231000
    assert m['water_network_input']['value']==55910000
    assert m['electricity_network_connections']['value']==172785
    assert m['gas_network_meters']['value']==168663
    assert m['gas_network_length']['value']==4047
    assert m['water_network_length']['value']==3465
    assert not any(r['metric'].endswith('_customers') for r in rows)
    assert '20244)' in m['gas_network_input']['table_reference']['header']
    assert m['heat_network_input']['raw_value']=='334325'
    assert m['heat_network_input']['status']=='needs_review'
    options=available_metrics({'metadata':{'year':2024},'observations':rows})
    assert set(options)=={'water_network_input'}
    assert options['water_network_input']['reference_kind']=='context'


def test_actual_dresden_tables_include_spaced_thousands_and_multiline_unit():
    path=ROOT/'data/raw/885fdbe78539f2e2bd59812c4fb434cedf0eec71bb1e809b98a0685ef1a931a3.pdf'
    rows=[r for p in pages(path,[30,32,33]) for r in layout_table_facts(p,2025)]
    m={r['metric']:r for r in rows}
    assert m['electricity_sales_total']['raw_value']=='18 057'
    assert m['electricity_sales_total']['value']==18057000
    assert m['gas_sales_total']['value']==17108000
    assert m['heat_sales']['value']==1664000
    assert m['heat_cold_sales']['value']==216000
    assert m['water_sales']['value']==43000000
    assert '\n(incl. Brauchwasser)' in m['water_sales']['evidence']
    previous=layout_table_facts(pages(path,[30])[0],2024)
    assert previous[0]['value']==16914000
    assert previous[0]['table_reference']['column']==2


def test_actual_bonn_header_unit_and_employee_count_are_preserved():
    rows=layout_table_facts(pages(ROOT/'Geschaeftsbericht Stadtwerke bonn.pdf',[11])[0],2025)
    m={r['metric']:r for r in rows}
    assert m['revenue']['value']==782181000
    assert m['revenue']['raw_unit']=='T€'
    assert m['employees']['value']==2894
    assert not any('rentabilität' in r['entity'].lower() for r in rows)
    assert 'in T€' in m['revenue']['table_reference']['header']


def test_actual_staggered_columns_keep_charging_year_and_quantity_together():
    p=pages(ROOT/'STAWAG_GB2024_Web_251107.pdf',[19])[0]
    rows=source_facts(p,2024)
    r=next(r for r in rows if r['metric']=='charging_energy')
    assert r['value']==2500 and r['status']=='validated'
    assert r['qualifier']=='less_than'
    assert '2,5 Millionen Kilowattstunden luden Kundinnen\nund Kunden in 2024' in r['evidence']
    assert r['evidence'] in p['text']
