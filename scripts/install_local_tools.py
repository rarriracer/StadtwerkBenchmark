"""Install official binaries inside this project; no shell-profile changes."""
import concurrent.futures
import hashlib
import json
import tarfile
import platform
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def install(spec):
    repo, name, subdir = spec
    release = json.loads((ROOT / 'downloads' / (repo + '-release.json')).read_text())
    asset = next(a for a in release['assets'] if a['name'] == name)
    target = ROOT / 'downloads' / name
    if not target.exists():
        request = urllib.request.Request(asset['browser_download_url'], headers={'User-Agent':'Stadtwerke-MVP-setup'})
        with urllib.request.urlopen(request, timeout=120) as response, target.open('wb') as out:
            while chunk := response.read(1024 * 1024):
                out.write(chunk)
    actual = hashlib.sha256(target.read_bytes()).hexdigest()
    expected = asset.get('digest', '')
    if expected.startswith('sha256:') and actual != expected[7:]:
        raise RuntimeError('Checksum mismatch: ' + name)
    destination = ROOT / '.tools' / subdir
    destination.mkdir(parents=True, exist_ok=True)
    with tarfile.open(target) as archive:
        archive.extractall(destination, filter='data')
    print(json.dumps({'tool':repo,'version':release['tag_name'],'sha256':actual,'path':str(destination)},ensure_ascii=False),flush=True)

if __name__ == '__main__':
    if sys.platform != 'darwin' or platform.machine() != 'arm64':
        raise SystemExit('Dieser Werkzeug-Installer ist nur fuer Apple Silicon. Unter Windows bitte Windows einrichten.cmd verwenden.')
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(install, [('uv','uv-aarch64-apple-darwin.tar.gz','uv'),('ollama','ollama-darwin.tgz','ollama')]))
