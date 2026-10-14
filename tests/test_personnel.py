import pytest
from stadtwerke.personnel import personnel_option,personnel_analysis
from stadtwerke.calculation import available_metrics
from stadtwerke import workflow,reporting


def staff(metric,value,**changes):
    return {'metric':metric,'value':value,'raw_value':str(value),'raw_unit':'Anzahl','unit':'Anzahl','year':2024,
            'page':23,'scope':'group','basis':'stock','portfolio':'total','status':'validated',
            'evidence':'Mitarbeiter insgesamt 684 (ohne Auszubildende)' if metric=='employees' else 'Auszubildende 49',
            'entity':metric,'table_reference':{'header':'Im Jahresdurchschnitt 2024 2023','year':2024},**changes}


def report(*rows):return {'id':'personnel-test','metadata':{'year':2024,'company':'Testversorger'},'observations':list(rows)}


def test_personnel_uses_report_values_and_counts_apprentices_in_denominator():
    r=report(staff('employees',684),staff('apprentices',49));option=personnel_option(r)
    ref,calc=personnel_analysis(option,r)
    assert calc['apprentice_share_percent']==pytest.approx(49/733*100)
    assert ref['kind']=='report' and calc['expected'] is None
    assert available_metrics(r)['employees']['reference_kind']=='report'


@pytest.mark.parametrize('changes',[{'page':24},{'scope':'own'},{'table_reference':{'header':'Zum Jahresende 2024'}},{'year':2023}])
def test_personnel_does_not_mix_periods_or_cohorts(changes):
    r=report(staff('employees',684),staff('apprentices',49,**changes))
    ref,calc=personnel_analysis(personnel_option(r),r)
    assert calc['apprentice_share_percent'] is None


def test_ambiguous_headcount_is_not_arbitrarily_selected():
    r=report(staff('employees',684),staff('employees',699,page=7),staff('apprentices',49))
    ref,calc=personnel_analysis(personnel_option(r),r)
    assert ref['personnel']['employees'] is None
    assert calc['apprentice_share_percent'] is None


def test_personnel_workflow_never_fetches_external_reference_and_exports(tmp_path,monkeypatch):
    r=report(staff('employees',684),staff('apprentices',49))
    monkeypatch.setattr(workflow,'reference_pair',lambda *a,**k:pytest.fail('Personnel requires no external API'))
    monkeypatch.setattr(workflow,'save_result',lambda *a:None)
    state={'session_id':'staff','report':r,'options':available_metrics(r),'selection':{'metrics':['employees'],'target_year':2026,'spread':0}}
    result=workflow.calculate(state)['result']
    assert result['topics'][0]['calculation']['apprentice_share_percent']==pytest.approx(6.684856753)
    monkeypatch.setattr(reporting,'OUTPUTS',tmp_path)
    files=reporting.export(result,'staff')
    assert set(files)=={'json','csv','pptx'}
    from pathlib import Path
    assert 'Ausbildungsquote' in Path(files['csv']).read_text()
