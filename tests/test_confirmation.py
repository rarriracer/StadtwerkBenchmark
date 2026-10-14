from copy import deepcopy
from pathlib import Path
import pytest
from stadtwerke.models import Candidate
from stadtwerke.extraction import validate
from stadtwerke.review import confirm_observation, topic_coverage
from stadtwerke.calculation import available_metrics


def fixture():
    text='Ende 2024 waren Photovoltaikanlagen mit insgesamt 12,5 MWp installiert.'
    c=Candidate(metric='pv_capacity_dc',raw_value='12,5',raw_unit='MWp',year=2024,
        evidence=text,scope='unknown',basis='stock',portfolio='total',geography='unknown')
    row=validate(c,{'page':1,'text':text},2024)
    report={'id':'confirmation-fixture','metadata':{'year':2024,'company':'Testversorger',
        'page_count':1,'analyzed_pages':[1]},'observations':[row],
        'pages':[{'page':1,'text':text}],'themes':{}}
    return report,row


def test_single_confirmation_keeps_source_checks_and_releases_metric():
    report,row=fixture()
    updated=confirm_observation(report,row)
    assert updated['observations'][-1]['status']=='manual_checked'
    assert updated['observations'][-1]['reviewed_at']
    assert updated['observations'][0]['status']=='superseded'
    assert list(available_metrics(updated))==['pv_capacity_dc']
    assert report['observations'][0]['status']=='needs_review'  # no mutation before saving


@pytest.mark.parametrize('change',[
    {'raw_value':'99'}, {'raw_unit':'GWh'}, {'evidence':'Erfundene Zahl 12,5 MWp Ende 2024.'},
    {'evidence':'Ende 2023 waren Photovoltaikanlagen mit insgesamt 12,5 MWp installiert.'},
    {'evidence':'Ende 2024 waren Photovoltaikanlagen mit insgesamt 12,5 MWp geplant.'},
])
def test_confirmation_cannot_override_invalid_source_year_unit_or_planning(change):
    report,row=fixture()
    row=deepcopy(row);row.update(change)
    if 'evidence' in change and not row['evidence'].startswith('Erfundene'):
        report['pages'][0]['text']=row['evidence']
    with pytest.raises(ValueError): confirm_observation(report,row)
    assert not available_metrics(report)


def test_total_and_subset_remain_separate_after_confirmation():
    report,row=fixture()
    subset=deepcopy(row)
    subset.update(status='manual_checked',value=2,portfolio='defined_subset',scope='reported_portfolio',
        geography='DE',entity='Kommunale Liegenschaften',raw_value='2',page=2)
    report['observations'].append(subset)
    updated=confirm_observation(report,row)
    assert updated['observations'][1]['status']=='manual_checked'
    assert available_metrics(updated)['pv_capacity_dc']['observation']['value']==12.5


def test_coverage_distinguishes_pending_source_and_missing_reference():
    report,row=fixture()
    report['observations'].append(dict(row,metric='gas_sales_total',status='validated',unit='MWh',value=100))
    coverage=topic_coverage(report)
    assert next(r for r in coverage if r['Thema']=='Photovoltaik-Ausbau')['Status']=='Fachliche Bestätigung offen'
    assert next(r for r in coverage if r['Thema']=='Windenergie-Ausbau an Land')['Status']=='Keine Vergleichsbasis'
    assert next(r for r in coverage if r['Thema']=='Gasabsatz / Verbrauchsreferenz')['Status']=='Vergleichsbasis unklar'


def test_ui_confirmation_is_one_click_without_checkbox(monkeypatch,tmp_path):
    from streamlit.testing.v1 import AppTest
    from stadtwerke import database, workflow
    report,row=fixture()
    source=tmp_path/'report.pdf';source.write_bytes(b'fixture')
    report['metadata']['path']=str(source)
    monkeypatch.setattr(database,'DB_PATH',tmp_path/'reports.duckdb')
    database.save_report(report)
    class Response:
        def json(self): return {'models':[]}
    monkeypatch.setattr('httpx.get',lambda *a,**k:Response())
    # A saved report is reused; this test must never invoke the local model.
    def cached_invoke(*a,**kwargs):
        saved=database.load_report(report['id'])
        return {'report':saved,'options':available_metrics(saved)}
    monkeypatch.setattr(workflow,'invoke',cached_invoke)
    at=AppTest.from_file(str(Path(__file__).parents[1]/'app.py'),default_timeout=5)
    at.session_state['state']={'report':report}
    at.session_state['workflow_session']='fixture'
    at.run()
    assert not at.exception
    assert not at.checkbox
    assert any(e.label=='Originaltext und Korrekturen' for e in at.expander)
    next(b for b in at.button if b.label=='Kennzahl bestätigen').click().run()
    # Collect an immediately completed background checkpoint refresh.
    at.run()
    assert not at.exception
    saved=database.load_report(report['id'])
    assert saved['observations'][-1]['status']=='manual_checked'
    assert list(available_metrics(saved))==['pv_capacity_dc']
    assert any('Relevante Themen auswählen' in m.value for m in at.markdown)
