import json
from pathlib import Path
import pytest
from langchain_core.runnables import RunnableLambda
from langchain_core.messages import AIMessage
from stadtwerke import extraction
from stadtwerke.calculation import available_metrics


def test_numeric_originals_are_prepared_without_model_copying():
    page={'page':1,'text':'Geschäftsjahr 2024: Stromabsatz 896 GWh. Kreditvolumen 12,5 Mio. Euro. Keine weiteren Angaben.'}
    facts=extraction.numeric_source_candidates(page)
    assert [(f['raw_value'],f['raw_unit']) for f in facts]==[('896','GWh'),('12,5','Mio. Euro')]
    assert all(extraction.evidence_span(page['text'],f['evidence']) is not None for f in facts)


def test_model_cannot_invent_value_quote_or_source_id(monkeypatch):
    def model(*a,**k):
        return AIMessage(content=json.dumps({'classifications':[{'id':999,'metric':'debt','raw_value':'bytes omitted for brevity'}]}))
    monkeypatch.setattr(extraction,'ChatOllama',lambda **k:RunnableLambda(model))
    with pytest.raises(ValueError,match='unbekannten Originalbeleg'):
        extraction.extract_page({'page':1,'text':'Im Jahr 2024 bestanden 12 Mio. Euro Finanzschulden.'},2024)


def test_explicit_financial_header_controls_year_unit_and_consolidation():
    text='31.12.2024 31.12.2023\nPassiva Anhang Euro TEuro\n2. Verbindlichkeiten gegenüber Kreditinstituten 573.271.811,65 478.491\nKONZERNABSCHLUSS'
    rows=extraction.financial_table_facts({'page':135,'text':text},2024)
    assert len(rows)==1 and rows[0]['value']==573271811.65 and rows[0]['unit']=='EUR'
    assert rows[0]['table_reference']['header']==text.splitlines()[0]+'\n'+text.splitlines()[1]
    assert not extraction.financial_table_facts({'page':135,'text':text},2025)
    assert not extraction.financial_table_facts({'page':135,'text':text.replace('Euro TEuro','TEuro')},2024)
    assert not extraction.financial_table_facts({'page':135,'text':text.replace('gegenüber Kreditinstituten','aus Lieferungen und Leistungen')},2024)


def test_actual_stawag_has_verified_bank_debt_in_both_balance_scopes():
    path=Path(__file__).parents[1]/'data/raw/STAWAG_2024.pdf'
    if not path.exists():pytest.skip('Optional original report not available')
    import pdfplumber
    from stadtwerke.documents import visible_text
    with pdfplumber.open(path,pages=[73,135]) as pdf:
        rows=[r for p in pdf.pages for r in extraction.source_facts({'page':p.page_number,'text':visible_text(p)[0]},2024)]
    accepted=[r for r in rows if r['status']=='validated']
    assert [r['value'] for r in accepted]==[139821053.64,573271811.65]
    report={'metadata':{'year':2024},'observations':accepted}
    assert available_metrics(report)['debt']['observation']['scope']=='group'


def test_space_separated_thousands_and_printed_unit_hyphenation_are_preserved():
    page={'page':1,'text':'Im Jahr 2024 wurden 2 100 Giga-\nwattstunden Strom verkauft.'}
    facts=extraction.numeric_source_candidates(page)
    assert len(facts)==1
    assert facts[0]['raw_value']=='2 100' and facts[0]['raw_unit']=='Giga-\nwattstunden'
    assert extraction.normalize_number(facts[0]['raw_value'])==2100
    assert extraction.normalize_unit(facts[0]['raw_unit'])==('MWh',1000)


def test_screenshot_placeholder_can_never_be_a_source_number():
    page={'page':1,'text':'bytes omitted for brevity unknown Keine Zahl angegeben.'}
    assert extraction.numeric_source_candidates(page)==[]
