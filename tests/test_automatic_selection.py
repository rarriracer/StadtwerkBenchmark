import json
from pathlib import Path
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from stadtwerke.calculation import available_metrics
from stadtwerke.scenarios import analysis_options
from stadtwerke.review import comparison_summary
from stadtwerke.config import ROOT


def test_flensburg_summary_matches_the_actual_selection_and_needs_no_extra_inputs():
    report=json.loads((ROOT/'data/examples/Stadtwerke_Flensburg_2024.json').read_text())
    options=available_metrics(report)
    assert analysis_options(report)==options
    assert comparison_summary(report)['comparable_metrics']==len(options)
    assert not any(key.startswith('scenario_') for key in options)
    with patch('stadtwerke.database.load_report',return_value=report):
        app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=20)
        app.session_state['state']={'report':report}
        app.session_state['workflow_session']='automatic-selection-test-only'
        app.run()
        assert not app.exception,[e.message for e in app.exception]
        choices=[button for button in app.button if (button.key or '').startswith('choose-topic-')]
        assert len([button for button in choices if not button.disabled])==len(options)
        assert any(button.disabled for button in choices)
        assert not app.multiselect
        state_key='automatic-topic-selection-'+report['id']
        first=next(iter(options))
        assert app.session_state[state_key]==[first]
        app.button(key='choose-topic-'+report['id']+'-'+first).click().run()
        assert not app.exception
        assert app.session_state[state_key]==[]
        app.button(key='choose-topic-'+report['id']+'-'+first).click().run()
        assert app.session_state[state_key]==[first]
        assert all(widget.label=='PDF-Seite' for widget in app.number_input)
        assert not any('confirm-' in (box.key or '') for box in app.checkbox)
