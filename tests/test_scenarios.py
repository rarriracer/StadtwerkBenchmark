import csv
import math
from pathlib import Path
import pytest
from stadtwerke.scenarios import available_scenarios,analysis_options,scenario_calculation
from stadtwerke import reporting,workflow,scenarios
from test_enterprise_outlook import observation


def report(*rows):
    return {'id':'scenario-test','metadata':{'year':2024,'company':'Testversorger','location':{'city':'Karlsruhe','federal_state':'Baden-Württemberg'}},'observations':list(rows)}


def reference(b=4,t=4.5,unit='% p.a.'):
    return {'baseline':b,'target':t,'baseline_date':'2024-08-31','target_date':'2026-08-31',
            'geography':'Deutschland','unit':unit,'provider':'Test API','series':'test','fetched_at':'2026-10-13'}


def inputs(**changes):
    return {'amount':20_000_000,'months':6,'confirmed':True,'baseline_date':'2024-08-31',
            'target_date':'2026-08-31','geography':'Deutschland',**changes}


def test_interest_changes_only_explicit_exposure_and_respects_duration():
    item=available_scenarios(report(observation('debt',100_000_000,'EUR','stock')))['scenario_interest']
    ref,c=scenario_calculation(item,reference(),inputs())
    assert c['company_change']==pytest.approx(50_000)
    assert c['expected']==450_000 and c['baseline_company']==400_000
    assert ref['kind']=='scenario' and c['output_unit']=='EUR'


@pytest.mark.parametrize('change',[{'confirmed':False},{'amount':101_000_000},{'amount':math.nan},
                                    {'months':13},{'months':0},{'amount':500_000},{'amount':True},
                                    {'geography':'Karlsruhe'},{'target_date':'2026-09-30'}])
def test_rejects_missing_invalid_or_mismatched_exposures(change):
    item=available_scenarios(report(observation('debt',100_000_000,'EUR','stock')))['scenario_interest']
    with pytest.raises(ValueError):scenario_calculation(item,reference(),inputs(**change))


def test_heat_never_scales_annual_heat_as_if_it_were_partial_period():
    item=available_scenarios(report(observation('heat_sales',1000)))['scenario_heat']
    _,c=scenario_calculation(item,reference(100,120,'K·Tage'),inputs(amount=600,coupling=.5))
    assert c['expected']==660 and c['baseline_company']==600
    assert c['expected']!=1100


def test_water_tariff_changes_revenue_not_physical_water_quantity():
    item=available_scenarios(report(observation('water_sales',1000,'m³')))['scenario_water']
    _,c=scenario_calculation(item,reference(100,110,'Index'),inputs(amount=500,price=2,coupling=.5))
    assert c['expected']==1050 and c['output_unit']=='EUR'
    assert c['assumptions']['amount']==500


def test_unclear_scope_or_profit_alone_cannot_create_scenario():
    assert not available_scenarios(report(observation('ebt',36_600_000,'EUR','annual_revenue')))
    a=observation('debt',20_000_000,'EUR','stock');b=dict(a,scope='own')
    assert not available_scenarios(report(a,b))


def test_charger_scenario_requires_public_integer_count_and_same_geography():
    item=available_scenarios(report(observation('charge_points',100,'Anzahl','stock')))['scenario_chargers']
    with pytest.raises(ValueError):scenario_calculation(item,reference(1000,1200),inputs(amount=80.5))
    _,c=scenario_calculation(item,reference(1000,1200),inputs(amount=80))
    assert c['expected']==96


def test_manual_scenarios_are_excluded_from_automatic_workflow_and_exports(tmp_path,monkeypatch):
    r=report(observation('water_sales',1000,'m³'))
    assert not analysis_options(r)
    options=available_scenarios(r)
    monkeypatch.setattr(scenarios,'scenario_reference',lambda *args:pytest.fail('No manual scenarios may fetch references'))
    monkeypatch.setattr(workflow,'save_result',lambda *args:None)
    result=workflow.calculate({'session_id':'test','report':r,'options':options,
        'selection':{'metrics':['scenario_water'],'target_year':2026,'spread':0,
                     'assumptions':{'scenario_water':inputs(amount=500,price=2,coupling=.5)}}})['result']
    assert not result['topics']
    item=options['scenario_water']
    ref,c=scenario_calculation(item,reference(100,110,'Index'),inputs(amount=500,price=2,coupling=.5))
    result['topics']=[{'metric':'scenario_water',**item,'reference':ref,'calculation':c}]
    monkeypatch.setattr(reporting,'OUTPUTS',tmp_path)
    directory=tmp_path/'test';directory.mkdir();(directory/'scenario_water.pptx').write_bytes(b'old scenario')
    files=reporting.export(result,'test')
    assert 'pptx' not in files
    assert not (directory/'scenario_water.pptx').exists()
    assert 'user_assumption' not in Path(files['json']).read_text()


def test_negative_spot_prices_are_valid_and_do_not_need_a_positive_denominator():
    item=available_scenarios(report(observation('electricity_sales_total',1000)))['scenario_spot']
    _,c=scenario_calculation(item,reference(0,-10,'EUR/MWh'),inputs(amount=500,direction='Beschaffung'))
    assert c['expected']==-5000 and c['company_change']==-5000
    assert c['reference_change_percent'] is None


def test_apparent_scenario_without_confirmed_assumptions_is_removed_from_export():
    from stadtwerke.outlook import company_result
    result={'topics':[{'reference':{'kind':'scenario'},'scenario':'water',
                      'calculation':{'input_origin':'user_assumption','assumptions':{'confirmed':False}}}],'reviews':[]}
    assert company_result(result)['topics']==[]
