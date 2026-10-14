import json
from pathlib import Path
from datetime import date
import pytest
from stadtwerke.documents import detect_report_year
from stadtwerke.table_layout import column_year
from stadtwerke.kpi_tables import layout_table_facts
from stadtwerke.calculation import available_metrics,calculate_reference
from stadtwerke.reference_sources import monthly_pair
from stadtwerke.reporting_period import reporting_period

PERIOD={'label':'2024/2025','start':'2024-10-01','end':'2025-09-30'}

@pytest.mark.parametrize('label',['2024/25','2024/2025'])
def test_fiscal_cover_and_columns_override_incidental_calendar_year(label):
    detected=detect_report_year([{'page':1,'text':'Geschäftsbericht\n'+label},
        {'page':34,'text':'Geschäftsjahr 2025. Ausblick Geschäftsjahr 2025/26.'}])
    assert detected['year']==2025 and detected['period_label']=='2024/2025'
    assert column_year(label)==2025
    assert column_year('2024/2026') is None


def test_actual_solingen_table_inherits_sector_and_retains_fiscal_labels():
    pages=json.loads((Path(__file__).parent/'fixtures/solingen_fiscal_tables.json').read_text())
    rows=[r for p in pages for r in layout_table_facts(p,2025)]
    options=available_metrics({'metadata':{'year':2025},'observations':rows})
    assert set(options)=={'electricity_sales_total','gas_sales_total'}
    for metric,value in {'electricity_sales_total':456951,'gas_sales_total':869133,'water_sales':10518000,'net_income':4876000,'balance_total':335864000,'investments':22008000,'revenue':312950000}.items():
        obs=options[metric]['observation'] if metric in options else next(r for r in rows if r['metric']==metric and r['value']==pytest.approx(value))
        assert obs['value']==pytest.approx(value) and obs['status']=='validated'
        assert obs['reporting_period_label']=='2024/2025'
    prior=[r for p in pages for r in layout_table_facts(p,2024)]
    assert next(r for r in prior if r['metric']=='electricity_sales_total')['value']==438194
    assert not any(r['metric'].endswith('_customers') for r in rows)


def test_fiscal_denominator_includes_previous_october_not_following_october():
    rows=[{'date':f'{y}-{m:02d}-01','value':100 if y==2024 else 200 if y==2025 else 300}
          for y in (2024,2025,2026) for m in range(1,13)]
    pair=monthly_pair(rows,2025,2026,date(2026,10,8),reporting_period=PERIOD)
    assert pair['baseline_annual']==2100  # 3 * 100 + 9 * 200
    assert pair['baseline']==1800 and pair['target']==2700
    ref=dict(pair,baseline=pair['baseline_annual'],aligned_baseline=pair['baseline'],kind='flow',unit='MWh')
    calc=calculate_reference({'value':210,'unit':'MWh'},ref)
    assert calc['expected']==270 and calc['historical_company_aligned']==180
    assert calc['company_outlook_series'][-1]['value']==270
    del rows[9] # October 2024
    with pytest.raises(ValueError,match='vollständig'):monthly_pair(rows,2025,2026,date(2026,10,8),reporting_period=PERIOD)


def test_unknown_fiscal_dates_do_not_guess_calendar_baseline():
    with pytest.raises(ValueError,match='Beginn- und Enddaten'):
        monthly_pair([],2025,2026,date(2026,10,8),reporting_period={'label':'2024/2025'})
    detection=detect_report_year([{'page':1,'text':'Geschäftsbericht 2024/2025'}])
    assert 'start' not in reporting_period([{'text':'Andere Firma verweist auf www.stadtwerke-solingen.de'}],detection)
    known=reporting_period([{'text':'Impressum\nwww.stadtwerke-solingen.de'}],detection)
    assert known['start']=='2024-10-01' and known['end']=='2025-09-30'


def test_fiscal_text_table_fallback_also_inherits_sales_sector():
    from stadtwerke.kpi_tables import kpi_table_facts
    page=json.loads((Path(__file__).parent/'fixtures/solingen_fiscal_tables.json').read_text())[0]
    rows=kpi_table_facts(page,2025)
    assert next(r for r in rows if r['metric']=='electricity_sales_total')['value']==456951
    assert next(r for r in rows if r['metric']=='water_sales')['value']==10518000
    assert all(r['reporting_period_label']=='2024/2025' for r in rows)


def test_smard_fetches_the_intermediate_year_needed_by_fiscal_baseline(monkeypatch):
    from datetime import datetime
    from stadtwerke import reference_sources as source
    def timestamp(y,m):return int(datetime(y,m,1,tzinfo=source.BERLIN).timestamp()*1000)
    def fetch(url):
        if url.endswith('index_month.json'):
            payload={'timestamps':[timestamp(y,1) for y in (2024,2025,2026)]}
        else:
            stamp=int(url.rsplit('_',1)[1].split('.')[0])
            y=datetime.fromtimestamp(stamp/1000,source.BERLIN).year
            payload={'series':[[timestamp(y,m),100] for m in range(1,13)]}
        return {'text':json.dumps(payload),'url':url,'sha256':'test','fetched_at':'2026-10-08'}
    monkeypatch.setattr(source,'get_record',fetch)
    rows,_=source.smard_monthly('410',2024,2026)
    pair=source.monthly_pair(rows,2025,2026,date(2026,10,8),reporting_period=PERIOD)
    assert pair['baseline_annual']==1200 and pair['target']==900


def test_actual_solingen_network_totals_and_meter_counts_are_distinct_from_customers():
    page=next(p for p in json.loads((Path(__file__).parent/'fixtures/solingen_fiscal_tables.json').read_text()) if p['page']==62)
    rows=layout_table_facts(page,2025)
    expected={'water_network_length':599,'water_network_connections':32831,'water_network_meters':33101,
        'gas_network_length':492.7,'gas_network_connections':25941,'gas_network_meters':36533,
        'electricity_network_length':1654.4,'electricity_network_connections':35054,'electricity_network_meters':109755}
    assert len(rows)==9
    for metric,value in expected.items():
        row=next(r for r in rows if r['metric']==metric)
        assert row['value']==pytest.approx(value) and row['scope']=='network_area'
        assert row['reporting_period_label']=='2024/2025'
    assert not any(r['metric'].endswith('_customers') for r in rows)
