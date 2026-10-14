import json
from pathlib import Path
from stadtwerke.kpi_cards import year_chart_layout,card_facts
from stadtwerke.calculation import available_metrics


def words():return json.loads((Path(__file__).parent/'fixtures/rheinenergie_chart_words.json').read_text())


def test_rheinenergie_sales_are_read_from_the_correct_chart_and_year():
    cards=year_chart_layout(words())
    rows=card_facts({'page':7,'cards':cards},2025)
    assert {r['metric']:r['value'] for r in rows}=={
        'electricity_sales_total':15_135_000,'gas_sales_total':6_040_000,'employees':1697}
    assert all(r['technical_status']=='verified' and r['evidence_kind']=='pdf_year_chart' for r in rows)
    assert 'ohne Auszubildende' in next(r['evidence'] for r in rows if r['metric']=='employees')
    report={'metadata':{'year':2025},'observations':rows}
    assert set(available_metrics(report))=={'electricity_sales_total','gas_sales_total','employees'}


def test_previous_year_is_not_relabelled_as_reporting_year():
    rows=card_facts({'page':7,'cards':year_chart_layout(words())},2024)
    assert {r['metric']:r['value'] for r in rows}=={
        'electricity_sales_total':13_526_000,'gas_sales_total':6_432_000,'employees':2755}


def test_missing_or_duplicate_bar_values_are_not_guessed():
    source=words()
    gas=[w for w in source if w['text']=='6.040' and 270<w['top']<300][0]
    missing=[w for w in source if w is not gas]
    assert not any(c['label']=='Erdgasverkauf' for c in year_chart_layout(missing))
    duplicate=dict(gas,text='9.999',top=gas['top']+12,bottom=gas['bottom']+12)
    assert not any(c['label']=='Erdgasverkauf' for c in year_chart_layout(source+[duplicate]))
