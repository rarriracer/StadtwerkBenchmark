"""Cross-platform launcher; use the Python environment that invoked this file."""
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
APP_URL = 'http://127.0.0.1:8501'


def reachable(url):
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            return response.status == 200
    except (OSError, ValueError):
        return False


def ollama_binary(root=ROOT, platform=None, environ=None):
    platform = platform or sys.platform
    environ = os.environ if environ is None else environ
    name = 'ollama.exe' if platform == 'win32' else 'ollama'
    local = root / '.tools' / 'ollama' / name
    if local.is_file():
        return str(local)
    installed = shutil.which(name)
    if installed:
        return installed
    if platform == 'win32' and environ.get('LOCALAPPDATA'):
        installed = Path(environ['LOCALAPPDATA']) / 'Programs' / 'Ollama' / name
        if installed.is_file():
            return str(installed)
    raise RuntimeError('Ollama fehlt. Bitte Ollama installieren: https://ollama.com/download')


def process_options(platform=None):
    if (platform or sys.platform) == 'win32':
        # Keep the server alive when the double-click launcher window closes.
        return {'creationflags': 0x00000200 | 0x00000008}  # NEW_PROCESS_GROUP | DETACHED_PROCESS
    return {'start_new_session': True}


def spawn(command, log, env=None):
    with log.open('a', encoding='utf-8') as output:
        return subprocess.Popen(command, cwd=ROOT, env=env, stdout=output,
                                stderr=subprocess.STDOUT, **process_options())


def wait_ready(url, process, seconds=30):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if reachable(url):
            return True
        if process.poll() is not None:
            return False
        time.sleep(.5)
    return reachable(url)


def ensure_ollama(runtime):
    url = os.environ.get('STADTWERKE_OLLAMA_URL', 'http://127.0.0.1:11434').rstrip('/')
    if reachable(url + '/api/tags'):
        return url
    parsed = urlparse(url)
    if parsed.scheme != 'http' or parsed.hostname not in ('127.0.0.1', 'localhost'):
        raise RuntimeError('Der konfigurierte Modellserver ist nicht erreichbar: ' + url)
    binary = ollama_binary()
    env = dict(os.environ, OLLAMA_HOST=parsed.netloc, OLLAMA_NO_CLOUD='1', OLLAMA_NUM_PARALLEL='1',
               OLLAMA_MAX_LOADED_MODELS='1', OLLAMA_CONTEXT_LENGTH='4096',
               OLLAMA_FLASH_ATTENTION='1')
    # Only bundled installations use the existing project-local model store.
    # Official Windows installations keep their normal/user-selected model directory.
    if Path(binary).parent == ROOT / '.tools' / 'ollama':
        env.setdefault('OLLAMA_MODELS', str(ROOT / '.tools' / 'models'))
    process = spawn([binary, 'serve'], runtime / 'ollama.log', env)
    (runtime / 'ollama.pid').write_text(str(process.pid), encoding='utf-8')
    if not wait_ready(url + '/api/tags', process):
        raise RuntimeError('Ollama konnte nicht starten. Details: data/runtime/ollama.log')
    return url


def ensure_model(url, install=False):
    config=ROOT/'data/runtime/model-settings.json'
    saved=json.loads(config.read_text()) if config.exists() else {}
    model = os.environ.get('STADTWERKE_MODEL') or (saved.get('model','qwen2.5:3b') if saved.get('provider')=='ollama' else 'qwen2.5:3b')
    with urllib.request.urlopen(url + '/api/tags', timeout=5) as response:
        tags = json.load(response)
    names = {item.get('name') for item in tags.get('models', [])}
    if model not in names and model + ':latest' not in names:
        if not install:
            raise RuntimeError('Modell fehlt: ' + model + '. Bitte zuerst die Einrichtung ausfuehren.')
        print('Lade lokales Modell ' + model + '. Das kann mehrere Minuten dauern.', flush=True)
        env = dict(os.environ, OLLAMA_HOST=url)
        subprocess.run([ollama_binary(), 'pull', model], env=env, check=True)


def model_provider():
    if os.environ.get('STADTWERKE_PROVIDER'):return os.environ['STADTWERKE_PROVIDER']
    config=ROOT/'data/runtime/model-settings.json'
    return json.loads(config.read_text()).get('provider','openrouter') if config.exists() else 'openrouter'


def main():
    runtime = ROOT / 'data' / 'runtime'
    runtime.mkdir(parents=True, exist_ok=True)
    try:
        # A running app can also be reopened without starting a second server.
        if '--setup' in sys.argv:
            if model_provider()=='ollama':ensure_model(ensure_ollama(runtime), install=True)
            print('Einrichtung abgeschlossen. Jetzt Stadtwerke starten.cmd doppelklicken.')
            return 0
        if not reachable(APP_URL + '/_stcore/health'):
            if model_provider()=='ollama':ensure_model(ensure_ollama(runtime))
            process = spawn([sys.executable, '-m', 'streamlit', 'run', str(ROOT / 'app.py'),
                             '--server.address=127.0.0.1', '--server.port=8501',
                             '--server.headless=true', '--browser.gatherUsageStats=false'], runtime / 'app.log')
            (runtime / 'app.pid').write_text(str(process.pid), encoding='utf-8')
            if not wait_ready(APP_URL + '/_stcore/health', process):
                raise RuntimeError('Die Oberflaeche konnte nicht starten. Details: data/runtime/app.log')
        print('Stadtwerke-Ausblick: ' + APP_URL)
        webbrowser.open(APP_URL)
        return 0
    except (OSError, RuntimeError, ValueError, subprocess.CalledProcessError) as error:
        print('Start fehlgeschlagen: ' + str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
