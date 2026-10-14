"""Keep regression tests independent of the user's selected provider and secrets."""
import json
import pytest
from stadtwerke import model_settings
from stadtwerke.config import MODEL


@pytest.fixture(autouse=True)
def isolated_model_settings(tmp_path,monkeypatch):
    import streamlit as st
    st.cache_data.clear()
    path=tmp_path/'model-settings.json'
    path.write_text(json.dumps({'provider':'ollama','model':MODEL,'api_key':''}))
    monkeypatch.setattr(model_settings,'SETTINGS_PATH',path)
    for name in ('STADTWERKE_PROVIDER','STADTWERKE_MODEL','OPENROUTER_API_KEY','KICONNECT_API_KEY'):
        monkeypatch.delenv(name,raising=False)
