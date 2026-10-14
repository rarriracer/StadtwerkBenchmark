"""Verify platform-specific startup branches without launching background servers."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import pytest

spec = importlib.util.spec_from_file_location('stadtwerke_launcher', Path(__file__).parents[1] / 'scripts' / 'start_app.py')
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)


@pytest.mark.parametrize('platform, filename', [('win32', 'ollama.exe'), ('darwin', 'ollama')])
def test_bundled_executable_for_each_platform(tmp_path, monkeypatch, platform, filename):
    binary = tmp_path / '.tools' / 'ollama' / filename
    binary.parent.mkdir(parents=True)
    binary.touch()
    monkeypatch.setattr(launcher.shutil, 'which', lambda _: None)
    assert launcher.ollama_binary(tmp_path, platform, {}) == str(binary)


def test_windows_official_install_with_spaces_and_umlaut(tmp_path, monkeypatch):
    user = tmp_path / 'Jörg Nutzer' / 'AppData' / 'Local'
    binary = user / 'Programs' / 'Ollama' / 'ollama.exe'
    binary.parent.mkdir(parents=True)
    binary.touch()
    monkeypatch.setattr(launcher.shutil, 'which', lambda _: None)
    assert launcher.ollama_binary(tmp_path, 'win32', {'LOCALAPPDATA': str(user)}) == str(binary)
    with pytest.raises(RuntimeError, match='Ollama fehlt'):
        launcher.ollama_binary(tmp_path, 'win32', {})


def test_detached_process_options():
    windows = launcher.process_options('win32')
    assert windows == {'creationflags': 0x208}
    assert 'start_new_session' not in windows
    assert launcher.process_options('darwin') == {'start_new_session': True}


def test_start_uses_invoking_interpreter_and_preserves_spaced_path(tmp_path, monkeypatch):
    root = tmp_path / 'Versorger München'
    root.mkdir()
    calls = []
    monkeypatch.setattr(launcher, 'ROOT', root)
    monkeypatch.setattr(launcher, 'reachable', lambda _: False)
    monkeypatch.setattr(launcher, 'ensure_ollama', lambda _: 'http://localhost:11434')
    monkeypatch.setattr(launcher, 'ensure_model', lambda _: None)
    monkeypatch.setattr(launcher, 'wait_ready', lambda *a: True)
    monkeypatch.setattr(launcher, 'spawn', lambda command, log: calls.append(command) or type('P', (), {'pid': 123})())
    monkeypatch.setattr(launcher.webbrowser, 'open', lambda _: True)
    monkeypatch.setattr(sys, 'argv', ['start_app.py'])
    assert launcher.main() == 0
    assert calls[0][0] == sys.executable
    assert calls[0][4] == str(root / 'app.py')
    assert (root / 'data/runtime/app.pid').read_text() == '123'


def test_reopen_does_not_spawn_duplicate_server(monkeypatch):
    monkeypatch.setattr(launcher, 'reachable', lambda _: True)
    monkeypatch.setattr(launcher, 'ensure_ollama', lambda _: pytest.fail('duplicate model server'))
    monkeypatch.setattr(launcher, 'spawn', lambda *a: pytest.fail('duplicate app server'))
    monkeypatch.setattr(launcher.webbrowser, 'open', lambda _: True)
    monkeypatch.setattr(sys, 'argv', ['start_app.py'])
    assert launcher.main() == 0


def test_missing_model_requires_setup_and_setup_propagates_download_failure(monkeypatch):
    class Response:
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def read(self): return json.dumps({'models': []}).encode()
    monkeypatch.setattr(launcher.urllib.request, 'urlopen', lambda *a, **k: Response())
    monkeypatch.setenv('STADTWERKE_MODEL', 'qwen2.5:3b')
    with pytest.raises(RuntimeError, match='Modell fehlt'):
        launcher.ensure_model('http://localhost:11434')
    monkeypatch.setattr(launcher, 'ollama_binary', lambda: 'ollama.exe')
    def download(command, **kwargs):
        assert command == ['ollama.exe', 'pull', 'qwen2.5:3b']
        assert kwargs['env']['OLLAMA_HOST'] == 'http://localhost:11434'
        raise subprocess.CalledProcessError(1, command)
    monkeypatch.setattr(launcher.subprocess, 'run', download)
    with pytest.raises(subprocess.CalledProcessError):
        launcher.ensure_model('http://localhost:11434', install=True)


def test_local_model_uses_saved_ollama_model(tmp_path,monkeypatch):
    runtime=tmp_path/'data/runtime';runtime.mkdir(parents=True)
    (runtime/'model-settings.json').write_text(json.dumps({'provider':'ollama','model':'qwen3:4b'}))
    monkeypatch.setattr(launcher,'ROOT',tmp_path)
    monkeypatch.delenv('STADTWERKE_MODEL',raising=False)
    class Response:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def read(self):return json.dumps({'models':[{'name':'qwen3:4b'}]}).encode()
    monkeypatch.setattr(launcher.urllib.request,'urlopen',lambda *a,**k:Response())
    launcher.ensure_model('http://localhost:11434')
    assert launcher.model_provider()=='ollama'
