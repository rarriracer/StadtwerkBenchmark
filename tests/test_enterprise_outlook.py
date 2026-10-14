from pathlib import Path
from stadtwerke.calculation import available_metrics,calculate_reference
from stadtwerke.outlook import company_result
from stadtwerke import reporting,ui


def observation(metric,value=1000,unit='MWh',basis='annual_sales'):
    return {'metric':metric,'value':value,'unit':unit,'basis':basis,'status':'validated','year':2024,
            'scope':'group','portfolio':'total','raw_value':str(value),'raw_unit':unit,'page':1,'evidence':'Originalbeleg'}


def test_context_rows_stay_in_report_but_cannot_be_selected_for_enterprise_outlook():
    rows=[observation('electricity_sales_total'),observation('gas_sales_total'),
          observation('ebt',36600000,'EUR','annual_revenue'),observation('operating_cashflow',1000000,'EUR','annual_revenue'),
          observation('equity',1000000,'EUR','stock'),observation('heat_sales'),observation('water_sales',1000,'m³')]
    report={'metadata':{'year':2024,'location':{'city':'Karlsruhe'}},'observations':rows}
    assert set(available_metrics(report))=={'electricity_sales_total','gas_sales_total'}
    from stadtwerke.review import report_findings
    assert any(row['Berichtsgröße']=='Ergebnis vor Steuern' and row['Referenzvergleich']=='Gespeichert ohne passenden Referenzvergleich' for row in report_findings(report))


def test_legacy_contexts_are_removed_from_display_and_downloads(tmp_path,monkeypatch):
    obs=observation('electricity_sales_total')
    ref={'kind':'flow','unit':'MWh','baseline':10000,'target':6000,'aligned_baseline':5000,'months':6,
         'baseline_date':'2024-06-30','target_date':'2026-06-30','fetched_at':'2026-10-13','provider':'Test API'}
    good={'metric':'electricity_sales_total','label':'Stromabsatz','observation':obs,'reference':ref,'calculation':calculate_reference(obs,ref)}
    bad={'metric':'ebt','label':'Ergebnis','observation':observation('ebt',36600000,'EUR','annual_revenue'),
         'reference':{'kind':'context','baseline':70,'target':107,'unit':'EUR/MWh'},'calculation':{'expected':None}}
    result={'company':'Karlsruhe','topics':[good,bad],'reviews':[]}
    assert company_result(result)['topics']==[good]
    monkeypatch.setattr(reporting,'OUTPUTS',tmp_path)
    directory=tmp_path/'legacy';directory.mkdir();(directory/'ebt.pptx').write_bytes(b'old context deck')
    files=reporting.export(result,'legacy')
    assert not (directory/'ebt.pptx').exists()
    assert 'Ergebnis' not in Path(files['csv']).read_text()
    result['topics']=[bad]
    files=reporting.export(result,'legacy')
    assert 'pptx' not in files and not (directory/'Stadtwerke_Ausblick.pptx').exists()


def test_change_number_and_unit_share_one_svg_text_element(monkeypatch):
    rendered=[];monkeypatch.setattr(ui,'html',rendered.append)
    ui.comparison_bars([1000000,1004588.2],['Vorher','Nachher'],'MWh','Stromabsatz','Gleiche Monate')
    output=rendered[0]
    assert '+4.588,2 MWh</text>' in output
    assert '>MWh</text>' not in output


def test_gas_api_arrow_compares_identical_months_and_keeps_year_basis_separate(monkeypatch):
    ref={'kind':'flow','baseline':844300000,'aligned_baseline':525805000,'target':552606000,
         'unit':'MWh','months':8,'baseline_date':'2024-12-31','target_date':'2026-08-31',
         'series':'slp+rlm','comparison_label':'Gasverbrauch Deutschland'}
    obs=observation('gas_sales_total',727000)
    output=[];captions=[]
    monkeypatch.setattr(ui,'html',output.append)
    monkeypatch.setattr(ui.st,'caption',captions.append)
    ui.outlook_sources(obs,ref,calculate_reference(obs,ref))
    assert '525.805.000,00 → 552.606.000,00 MWh' in output[0]
    assert 'Januar–August 2024 → Januar–August 2026' in output[0]
    assert '844.300.000' not in output[0]
    assert '+5,10 %' in captions[0] and '844.300.000,00 MWh' in captions[0]


def test_reference_periods_support_fiscal_years_without_filling_missing_months():
    from stadtwerke.calculation import reference_comparison
    ref={'kind':'flow','baseline':1000,'aligned_baseline':800,'target':900,'months':10,
         'baseline_date':'2025-09-30','target_date':'2026-10-31',
         'baseline_comparison_dates':[f'2025-{m:02}-01' for m in range(1,10)]+['2024-10-31']}
    result=reference_comparison(ref)
    assert result['baseline_period']=='Oktober 2024; Januar–September 2025'
    assert result['target_period']=='Januar–Oktober 2026'
