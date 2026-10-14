from pathlib import Path
import pytest
from stadtwerke.extraction import source_facts, normalize_unit
from stadtwerke.kpi_tables import kpi_table_facts
from stadtwerke.review import report_findings
from stadtwerke.calculation import available_metrics


def test_year_columns_units_and_operating_metrics_are_independent_of_api_eligibility():
    # Format described by the user; numerical customer values are test data.
    text='Kennzahlen\n2023 2024\nBetriebsmengen\nStrom gesamt Millionen Kilowattstunden 600,0 654,6\nGas gesamt Mio. kWh 900,0 950,0\nWasser gesamt Mio. m³ 5,0 5,2\nAnzahl Kunden\nStrom Anzahl 100.000 110.000\nGas Anzahl 30.000 32.000\nWasser Anzahl 20.000 21.000\nUmsatzerlöse Mio. Euro 100,0 120,0'
    rows=kpi_table_facts({'page':1,'text':text},2024)
    by_metric={r['metric']:r for r in rows}
    assert by_metric['electricity_operating_volume']['value']==654600
    assert by_metric['gas_operating_volume']['value']==950000
    assert by_metric['water_operating_volume']['value']==5200000
    assert by_metric['electricity_customers']['value']==110000
    assert by_metric['gas_customers']['value']==32000
    assert by_metric['water_customers']['value']==21000
    assert by_metric['revenue']['value']==120000000
    assert all(r['table_reference']['column']==2 for r in rows)
    assert all(r['evidence'] in text for r in rows)
    report={'metadata':{'year':2024},'observations':rows}
    assert len(report_findings(report))==7
    options=available_metrics(report)
    assert not options
    assert all(r['Referenzvergleich']=='Gespeichert ohne passenden Referenzvergleich' for r in report_findings(report) if r['Berichtsgröße'] in ('Umsatz','Betriebsmenge Wasser'))
    assert all(item['reference_kind']=='context' for item in options.values())
    # No invented customer-count API or sales semantics.


def test_unit_in_section_has_separate_original_proof():
    text='Kennzahlen\n2024 2023\nBetriebsmengen Strom in Millionen Kilowattstunden\ngesamt 654,6 600,0\nAnzahl Kunden Strom\nAnzahl 110.000 100.000'
    rows=kpi_table_facts({'page':1,'text':text},2024)
    assert rows[0]['value']==654600
    assert rows[0]['table_reference']['header']=='2024 2023\nBetriebsmengen Strom in Millionen Kilowattstunden'
    assert rows[0]['evidence']=='gesamt 654,6 600,0'
    assert rows[1]['metric']=='electricity_customers'


def test_explicit_sales_get_reference_but_operating_quantities_do_not():
    rows=source_facts({'page':1,'text':'Kennzahlen\n2024 2023\nStromabsatz gesamt Mio. kWh 654,6 600,0'},2024)
    assert rows[0]['metric']=='electricity_sales_total'
    assert 'electricity_sales_total' in available_metrics({'metadata':{'year':2024},'observations':rows})


def test_unproven_years_columns_and_dimensions_are_not_promoted():
    for text in ['Kennzahlen 2024\nStromabsatz GWh 654,6 600,0',
                 'Kennzahlen\n2024 2024\nStromabsatz GWh 654,6 600,0',
                 'Kennzahlen\n2024 2023\nStromabsatz GWh 654,6',
                 'Kennzahlen\n2024 2023\nStromabsatz Euro 654,6 600,0',
                 'Kennzahlen\n2024 2023\nGeplanter Stromabsatz GWh 654,6 600,0']:
        assert kpi_table_facts({'page':1,'text':text},2024)==[]
    assert normalize_unit('Millionen Kilowattstunden')==('MWh',1000)
    assert normalize_unit('Mio. Euro')==('EUR',1000000)


def test_actual_stawag_financial_segments_do_not_turn_other_rows_into_revenue():
    path=Path(__file__).parents[1]/'data/raw/STAWAG_2024.pdf'
    if not path.exists():pytest.skip('Optional source report')
    import pdfplumber
    from stadtwerke.documents import visible_text
    with pdfplumber.open(path,pages=[4]) as pdf:
        rows=kpi_table_facts({'page':4,'text':visible_text(pdf.pages[0])[0]},2024)
    assert len(rows)==8
    assert rows[0]['value']==1151300000
    assert next(r for r in rows if r['entity']=='Stromversorgung')['value']==514900000
    assert not any('EBIT' in r['entity'] or 'Bilanzsumme' in r['entity'] for r in rows)
    assert all(r['metric']=='revenue' for r in rows)
