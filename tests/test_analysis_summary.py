from stadtwerke import review


def test_summary_counts_available_metrics_and_distinct_areas(monkeypatch):
    from stadtwerke import calculation
    options={m:{} for m in ('electricity_sales_total','electricity_sales_households','gas_sales_total','gas_sales_slp','heat_sales','water_sales','revenue','debt','interest_expense')}
    monkeypatch.setattr(calculation,'available_metrics',lambda r:options)
    summary=review.comparison_summary({'metadata':{'source_scanned_pages':list(range(1,27))}})
    assert summary=={'scanned_pages':26,'recognized_metrics':0,'comparable_metrics':9,'areas':['Strom','Gas','Wärme','Wasser','Finanzen']}


def test_error_summary_distinguishes_cutoff_from_schema_failure():
    report={'metadata':{'extraction_errors':[{'page':2,'error':'Antwort entspricht nicht dem Kennzahlenschema'}, {'page':15,'error':'Modellausgabe abgeschnitten'}]}}
    rows=review.model_error_summary(report)
    assert rows[0]['Ursache']=='Antwortformat passt nicht zum Kennzahlenschema'
    assert rows[1]['Ursache']=='KI-Antwort wurde abgeschnitten'


def test_material_expense_cannot_be_accepted_as_personnel_expense():
    from stadtwerke.extraction import validate
    from stadtwerke.models import Candidate
    evidence='Die Aufwendungen für Roh-, Hilfs- und Betriebsstoffe im Berichtsjahr betrugen 693,4 Mio. EUR.'
    candidate=Candidate(metric='personnel_expense',raw_value='693,4',raw_unit='Mio. EUR',year=2024,evidence=evidence,scope='group',basis='annual_expense')
    row=validate(candidate,{'page':7,'text':evidence},2024)
    assert row['status']=='needs_review' and row['value'] is None
    assert 'keinen Personalaufwand' in row['validation_notes']
    evidence='Der Personalaufwand im Berichtsjahr betrug 69,4 Mio. EUR.'
    candidate=candidate.model_copy(update={'raw_value':'69,4','evidence':evidence})
    row=validate(candidate,{'page':7,'text':evidence},2024)
    assert row['status']=='validated' and row['value']==69400000
