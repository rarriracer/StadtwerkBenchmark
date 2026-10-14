import copy
from datetime import date
import pytest
from stadtwerke.models import Candidate
from stadtwerke.extraction import validate, normalize_number, source_facts
from stadtwerke.calculation import baseline_scenarios, available_metrics
from stadtwerke import references, database, workflow


def candidate(**changes):
    data = dict(metric='pv_capacity_dc', raw_value='12,5', raw_unit='MWp', year=2024,
                evidence='Eigene PV-Anlagen in Deutschland: insgesamt 12,5 MWp am 31.12.2024.',
                scope='own', basis='stock', portfolio='total', geography='DE', entity='Musterstadt')
    return Candidate(**(data | changes))


def test_ratio_and_scenarios():
    result = baseline_scenarios(5, 1000, 1300, .1)
    assert result['ratio_percent'] == .5
    assert result['expected'] == 6.5
    assert result['lower'] == pytest.approx(5.85)
    assert result['upper'] == pytest.approx(7.15)
    assert result['company_change'] == 1.5
    with pytest.raises(ValueError):
        baseline_scenarios(5, 0, 1300)
    with pytest.raises(ValueError):
        baseline_scenarios(float('nan'), 1000, 1300)


def test_german_number_and_evidence():
    assert normalize_number('1.142') == 1142
    assert normalize_number('1.234,56') == 1234.56
    c = candidate()
    page = {'page': 2, 'text': c.evidence}
    assert validate(c, page, 2024)['value'] == 12.5
    assert validate(candidate(evidence='Erfundener Wert 12,5 MWp'), page, 2024)['status'] == 'needs_review'
    assert validate(candidate(raw_unit='GWp'), page, 2024)['status'] == 'needs_review'
    assert validate(candidate(year=2023), page, 2024)['status'] == 'needs_review'
    bad = candidate(evidence=c.evidence.replace('12,5','112,5'))
    assert validate(bad, {'page':2,'text':bad.evidence}, 2024)['status']=='needs_review'


@pytest.mark.parametrize('changes', [dict(basis='planned'), dict(basis='additions'),
                         dict(portfolio='project'), dict(scope='network_area'), dict(geography='mixed')])
def test_unmatched_capacity_not_offered(changes):
    c = candidate(**changes)
    row = validate(c, {'page': 2, 'text': c.evidence}, 2024)
    report = {'metadata': {'year': 2024}, 'observations': [row]}
    assert not available_metrics(report)


def test_conflicting_values_not_silently_selected():
    c = candidate()
    row = validate(c, {'page': 2, 'text': c.evidence}, 2024)
    other = copy.deepcopy(row); other['value'] = 20
    assert not available_metrics({'metadata': {'year': 2024}, 'observations': [row, other]})


def test_completed_month_and_units(monkeypatch):
    record = {'url': 'test://reference', 'sha256': 'test', 'fetched_at': '2026-10-07',
        'payload': {'attributes': {'timestamp_reference': 'period_end'},
        'series': [{'id': 'solar_dc', 'unit': 'GW'}], 'data': [
            {'timestamp': '2024-12-01', 'values': {'solar_dc': 100}},
            {'timestamp': '2026-09-01', 'values': {'solar_dc': 130}},
            {'timestamp': '2026-10-01', 'values': {'solar_dc': 999}}]}}
    monkeypatch.setattr(references, 'capacity_data', lambda: record)
    pair = references.reference_pair('pv_capacity_dc', 2024, 2026, today=date(2026, 10, 7))
    assert pair['target_date'] == '2026-09-30'
    assert pair['baseline_date'] == '2024-12-31'
    assert pair['baseline'] == 100000
    assert pair['target'] == 130000
    assert [r['date'] for r in pair['history']]==['2024-12-31','2026-09-30']


def test_graph_pauses_and_resumes_across_connections(monkeypatch, tmp_path):
    monkeypatch.setattr(workflow, 'RUNTIME', tmp_path)
    monkeypatch.setattr(database, 'DB_PATH', tmp_path / 'test.duckdb')
    c = candidate(); row = validate(c, {'page': 2, 'text': c.evidence}, 2024)
    report = {'id': 'mock-document', 'metadata': {'company': 'Musterstadt', 'year': 2024},
              'pages': [], 'themes': {}, 'observations': [row]}
    database.save_report(report)
    calls = []
    def mock_ingest(state):
        calls.append('ingest')
        return {'report': report}
    monkeypatch.setattr(workflow, 'ingest', mock_ingest)
    monkeypatch.setattr(workflow, 'reference_pair', lambda *a: dict(baseline=100000,
                        target=130000, unit='MWp', target_date='2026-09-30'))
    monkeypatch.setattr(workflow, 'export', lambda *a: {'test': 'mock-export'})
    first = workflow.invoke('test-session', initial={'path': 'mock.pdf', 'year': 2024})
    assert first['__interrupt__'][0].value['question'] == 'Relevante Themen auswählen'
    assert not first.get('result')
    saved = workflow.invoke('test-session')
    assert saved['report']['id'] == 'mock-document'
    final = workflow.invoke('test-session', selection={'metrics': ['pv_capacity_dc'], 'target_year': 2026, 'spread': .1})
    assert final['result']['topics'][0]['calculation']['expected'] == pytest.approx(16.25)
    assert final['files']['test'] == 'mock-export'
    assert calls == ['ingest']


def test_bonn_original_portfolio_keeps_exact_number_and_boundary():
    source = ('Bonner Stadtgebiet. Im Bereich Photovoltaik (PV) wurde der Ausbau vorangetrieben. '
        'Bis Ende des Jahres 2025 waren auf städtischen und SWB-Liegenschaften Anlagen mit rund 2.400 kWp in Betrieb. '
        'Inklusive privater und gewerblicher Objekte sind bis Ende 2025 insgesamt Anlagen mit rund 4.200 kWp umgesetzt worden.')
    location = {'country':'DE','city':'Bonn','source':'test://municipality'}
    rows = source_facts({'page':20,'text':source},2025,location)
    assert len(rows)==2
    good, ambiguous = rows
    assert good['raw_value']=='2.400' and good['value']==2.4
    assert good['status']=='validated' and good['portfolio']=='defined_subset'
    assert good['scope']=='reported_portfolio' and good['entity']=='städtischen und SWB-Liegenschaften'
    assert good['evidence'] in source
    assert ambiguous['status']=='needs_review'
    report = {'metadata':{'year':2025},'observations':rows}
    assert available_metrics(report)['pv_capacity_dc']['observation']['value']==2.4
    different_year = source_facts({'page':20,'text':source},2024,location)
    assert not available_metrics({'metadata':{'year':2024},'observations':different_year})


def test_bounded_portfolio_cannot_have_invented_boundary():
    c = candidate(scope='reported_portfolio',portfolio='defined_subset',entity='Kundenanlagen in Bonn')
    assert validate(c,{'page':2,'text':c.evidence},2024)['status']=='needs_review'


def test_money_cannot_be_released_as_electricity_sales():
    c = candidate(metric='electricity_sales_total',raw_value='362.365',raw_unit='T€',
                  evidence='Stromumsatz 362.365 T€ im Jahr 2024.',basis='annual_sales')
    row = validate(c,{'page':12,'text':c.evidence},2024)
    assert row['status']=='needs_review' and 'Energiemenge' in row['validation_notes']


def test_source_annual_sales_do_not_infer_customer_segment():
    source = ('Trotz des CO2-Preises erfolgte bei Gas im Jahr 2025 keine Preiserhöhung. '
              'Zuwächse im Großkundensegment führten zu einem um 6,5 % auf 1.215 GWh gestiegenen Gasabsatz. '
              'Der Fernwärmeabsatz im Jahr 2025 ist gegenüber dem Vorjahr (424 GWh) um 1,9 % auf 432 GWh gestiegen.')
    rows = source_facts({'page':13,'text':source},2025)
    assert [(r['metric'],r['value']) for r in rows]==[('gas_sales_total',1215000),('heat_sales',432000)]
    assert all(r['status']=='validated' for r in rows)
    assert all(r['evidence'] in source for r in rows)


def test_visible_pdf_page_excludes_adjacent_spread(tmp_path,monkeypatch):
    from stadtwerke import documents
    monkeypatch.setattr(documents,'RUNTIME',tmp_path)
    content = (b'BT /F1 12 Tf -180 180 Td (Foreign 999 MWp) Tj ET\n' +
        b'BT /F1 8 Tf 10 130 Td (Photovoltaik 2.400 kWp report 2025) Tj ET\n' +
        b'BT /F1 8 Tf 10 110 Td (' + b'Visible report text '*12 + b') Tj ET\n')
    # A generous page width accommodates the legitimate test paragraph.
    objects = [b'<< /Type /Catalog /Pages 2 0 R >>',b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
        b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 1200 200] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',
        b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
        b'<< /Length '+str(len(content)).encode()+b' >>\nstream\n'+content+b'endstream']
    pdf=b'%PDF-1.4\n'; offsets=[0]
    for index,obj in enumerate(objects,1):
        offsets.append(len(pdf));pdf+=str(index).encode()+b' 0 obj\n'+obj+b'\nendobj\n'
    xref=len(pdf);pdf+=b'xref\n0 6\n0000000000 65535 f \n'
    for offset in offsets[1:]: pdf+=f'{offset:010d} 00000 n \n'.encode()
    pdf+=f'trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF'.encode()
    path=tmp_path/'spread.pdf';path.write_bytes(pdf)
    _,pages,_=documents.read_pdf(path)
    assert 'Foreign' not in pages[0]['text'] and '2.400' in pages[0]['text']


def test_full_scan_and_model_coverage_invalidates_old_cache(monkeypatch,tmp_path):
    from stadtwerke.models import PageExtraction
    monkeypatch.setattr(workflow,'RUNTIME',tmp_path)
    monkeypatch.setattr(database,'DB_PATH',tmp_path/'test.duckdb')
    pages=[{'page':i,'text':'Photovoltaik: 12 MWp.'} for i in range(1,36)]
    pages.append({'page':36,'text':'Narrative ohne Kennzahl.'})
    monkeypatch.setattr(workflow,'read_pdf',lambda p:('coverage',pages,{'Photovoltaik':list(range(1,36))}))
    database.save_report({'id':'coverage','metadata':{'year':2025},'pages':[], 'observations':[], 'themes':{}})
    calls=[]
    def mock_extract(page,*args):
        calls.append(page['page']);return PageExtraction(),[]
    monkeypatch.setattr(workflow,'release_model',lambda *a:True)
    monkeypatch.setattr(workflow,'extract_page',mock_extract)
    state={'provider':'ollama','path':'mock.pdf','year':2025,'company':'Test'}
    report=workflow.ingest(state)['report']
    assert len(calls)==35 and len(report['metadata']['source_scanned_pages'])==36
    assert report['metadata']['extraction_version']==workflow.EXTRACTION_VERSION
    workflow.ingest(state)
    assert len(calls)==35


@pytest.mark.parametrize('city', ['Bonn','Marburg','Aachen','Berlin','Hamburg','München','Dresden','Kiel'])
def test_local_cohort_uses_verified_location_without_city_specific_rules(city):
    source='Bis Ende des Jahres 2024 waren auf kommunalen Liegenschaften Anlagen mit 1.500 kWp in Betrieb.'
    location={'country':'DE','city':city,'source':'test://verified-location'}
    row=source_facts({'page':2,'text':source},2024,location)[0]
    assert row['status']=='validated' and row['value']==1.5
    assert row['location_reference']['city']==city
    assert source_facts({'page':2,'text':source},2024)[0]['status']=='needs_review'


def test_german_headquarters_does_not_release_foreign_or_group_portfolio():
    from stadtwerke.geography import portfolio_geography
    location={'country':'DE','city':'Musterstadt'}
    assert portfolio_geography('Gesamter Konzernbestand',location=location)[0]=='unknown'
    assert portfolio_geography('Anlagen auf städtischen Liegenschaften in Frankreich', 'städtischen Liegenschaften',location)[0]=='unknown'
    assert portfolio_geography('Anlagen auf städtischen Liegenschaften in Dänemark', 'städtischen Liegenschaften',location)[0]=='unknown'


@pytest.mark.parametrize('metric,text',[
    ('pv_capacity_dc','Unsere eigenen PV-Anlagen in Deutschland haben Ende 2024 eine insgesamt installierte Leistung von 12 Megawatt-Peak.'),
    ('wind_onshore','Unsere Windanlagen an Land in Deutschland haben Ende 2024 insgesamt eine installierte Leistung von 12 MW.'),
    ('wind_offshore','Unsere Windanlagen auf See in Deutschland haben Ende 2024 insgesamt eine installierte Leistung von 12 MW.'),
    ('battery_power','Unsere Batteriespeicher in Deutschland haben Ende 2024 insgesamt eine installierte Leistung von 12 MW.'),
    ('battery_energy','Unsere Batteriespeicher in Deutschland haben Ende 2024 einen insgesamt installierten Bestand von 12 MWh.'),
])
def test_capacity_rules_cover_sectors_without_utility_names(metric,text):
    rows=source_facts({'page':2,'text':text},2024)
    assert len(rows)==1 and rows[0]['metric']==metric
    assert rows[0]['status']=='validated' and rows[0]['value']==12


def test_year_end_values_not_reassigned_to_reporting_year():
    text='Eigene PV-Anlagen in Deutschland: Ende 2024 insgesamt 12 MWp installiert, Ende 2025 insgesamt 15 MWp installiert.'
    rows=source_facts({'page':2,'text':text},2025)
    assert rows[0]['status']=='needs_review' and rows[1]['status']=='validated'


def test_number_unit_must_belong_together():
    c=candidate(raw_value='12',evidence='Eigene PV-Anlagen in Deutschland: insgesamt 12 EUR Kosten und 20 MWp Ende 2024.')
    row=validate(c,{'page':2,'text':c.evidence},2024)
    assert row['status']=='needs_review' and 'unmittelbar' in row['validation_notes']
    assert row['evidence_status']=='not_verified'


def test_original_evidence_and_comparison_release_are_separate():
    c=candidate(geography='unknown')
    row=validate(c,{'page':2,'text':c.evidence},2024)
    assert row['evidence_status']=='verified' and row['status']=='needs_review'


def test_workflow_progress_reflects_actual_nodes(monkeypatch,tmp_path):
    from stadtwerke.models import PageExtraction
    monkeypatch.setattr(workflow,'RUNTIME',tmp_path)
    monkeypatch.setattr(database,'DB_PATH',tmp_path/'test.duckdb')
    source='Eigene PV-Anlagen in Deutschland: Ende 2024 insgesamt 12 MWp installiert.'
    pages=[{'page':1,'text':source}]
    monkeypatch.setattr(workflow,'read_pdf',lambda p:('progress-test',pages,{'Photovoltaik':[1]}))
    monkeypatch.setattr(workflow,'release_model',lambda *a:True)
    monkeypatch.setattr(workflow,'extract_page',lambda *a:(PageExtraction(),[]))
    events=[]
    result=workflow.invoke('progress-test',initial={'provider':'ollama','path':'mock.pdf','year':2024,'company':'Test'},progress=events.append)
    assert result.get('__interrupt__')
    assert {'document','extraction','validation','selection'} <= {r['stage'] for r in events}
    assert all(r['stage'] not in ('reference','outlook') for r in events)


def test_two_paragraph_columns_do_not_mix_numbers(tmp_path,monkeypatch):
    from stadtwerke import documents
    monkeypatch.setattr(documents,'RUNTIME',tmp_path)
    lines=[]
    for i in range(12):
        y=500-i*20
        lines.append(f'BT /F1 8 Tf 20 {y} Td (Left paragraph solar capacity and ownership stated here) Tj ET')
        lines.append(f'BT /F1 8 Tf 420 {y} Td (Right paragraph financing and other explanations here) Tj ET')
    lines[8]='BT /F1 8 Tf 20 420 Td (Own PV in Germany end 2024 installed total 12 MWp.) Tj ET'
    content=('\n'.join(lines)+'\n').encode()
    objects=[b'<< /Type /Catalog /Pages 2 0 R >>',b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
        b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 800 600] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',
        b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
        b'<< /Length '+str(len(content)).encode()+b' >>\nstream\n'+content+b'endstream']
    pdf=b'%PDF-1.4\n';offsets=[0]
    for index,obj in enumerate(objects,1):
        offsets.append(len(pdf));pdf+=str(index).encode()+b' 0 obj\n'+obj+b'\nendobj\n'
    xref=len(pdf);pdf+=b'xref\n0 6\n0000000000 65535 f \n'
    for offset in offsets[1:]: pdf+=f'{offset:010d} 00000 n \n'.encode()
    pdf+=f'trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF'.encode()
    path=tmp_path/'columns.pdf';path.write_bytes(pdf)
    _,pages,_=documents.read_pdf(path)
    page=pages[0]
    assert page['layout']=='two_columns'
    assert page['text'].index('Own PV') < page['text'].index('Right paragraph')
    assert 'installed total 12 MWp.' in page['text']


def test_archive_open_skips_ingestion_and_resumes_at_selection(monkeypatch,tmp_path):
    monkeypatch.setattr(workflow,'RUNTIME',tmp_path)
    monkeypatch.setattr(database,'DB_PATH',tmp_path/'archive.duckdb')
    c=candidate();row=validate(c,{'page':2,'text':c.evidence},2024)
    report={'id':'saved-report','metadata':{'company':'Musterstadt','year':2024},'pages':[],'themes':{},'observations':[row]}
    database.save_report(report)
    monkeypatch.setattr(workflow,'ingest',lambda *a:pytest.fail('Archive must not ingest'))
    monkeypatch.setattr(workflow,'refresh_sources',lambda *a:pytest.fail('Archive must not refresh'))
    monkeypatch.setattr(workflow,'reference_pair',lambda *a:dict(baseline=100000,target=130000,unit='MWp',target_date='2026-09-30'))
    monkeypatch.setattr(workflow,'export',lambda *a:{'test':'mock-export'})
    opened=workflow.open_saved_report('archive-test',report)
    assert opened['report']==report
    assert opened['__interrupt__'][0].value['question']=='Relevante Themen auswählen'
    result=workflow.invoke('archive-test',selection={'metrics':['pv_capacity_dc'],'target_year':2026,'spread':0})
    assert result['result']['topics'][0]['calculation']['expected']==pytest.approx(16.25)
