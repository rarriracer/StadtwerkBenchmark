"""Audit the actual Git publication candidates without printing secret values."""
import argparse
import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT=Path(__file__).resolve().parents[1]


def candidate_files(root=ROOT):
    root=Path(root).resolve()
    def run(args):return subprocess.check_output(args,cwd=root,stderr=subprocess.DEVNULL)
    is_repo=subprocess.run(['git','rev-parse','--is-inside-work-tree'],cwd=root,capture_output=True).returncode==0
    if is_repo:
        raw=run(['git','ls-files','--cached','--others','--exclude-standard','-z'])
    else:
        with tempfile.TemporaryDirectory(prefix='stadtwerke-git-check-') as temp:
            git_dir=str(Path(temp)/'git')
            run(['git','init','--quiet','--bare',git_dir])
            raw=run(['git','--git-dir='+git_dir,'--work-tree='+str(root),'-c','core.bare=false','ls-files','--others','--exclude-standard','-z'])
    return sorted({Path(name.decode()) for name in raw.split(b'\0') if name})


def local_keys(root):
    path=root/'data/runtime/model-settings.json'
    if not path.exists():return []
    def walk(value):
        if isinstance(value,dict):
            for key,item in value.items():
                if key=='api_key' and isinstance(item,str) and len(item)>=8:yield item.encode()
                else:yield from walk(item)
        elif isinstance(value,list):
            for item in value:yield from walk(item)
    return list(walk(json.loads(path.read_text())))


def audit(root=ROOT):
    root=Path(root).resolve();files=candidate_files(root);errors=[]
    keys=local_keys(root)
    patterns=[rb'sk-(?:or-v1-|proj-)?[A-Za-z0-9_-]{24,}',rb'AKIA[A-Z0-9]{16}',
              rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----']
    blocked=('data/runtime/','data/raw/','outputs/','.venv/','.tools/','.aws/','.codex/')
    for relative in files:
        path=root/relative;name=relative.as_posix()
        if name.startswith(blocked) or name=='.env' or name=='.streamlit/secrets.toml':
            errors.append(name+': lokale Datei in Git-Auswahl');continue
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            errors.append(name+': externer oder symbolischer Pfad');continue
        if not path.is_file():continue
        data=path.read_bytes()
        if any(key in data for key in keys):errors.append(name+': bekannter lokaler Zugangsschlüssel enthalten')
        if any(re.search(pattern,data) for pattern in patterns):errors.append(name+': mögliches Zugangstoken oder privater Schlüssel')
        if path.suffix.lower() in ('.py','.json','.md','.toml','.yml','.yaml','.cmd','.command') and re.search(rb'(?<![A-Za-z0-9./:-])/(?:Users|home)/[A-Za-z0-9._-]+/',data):
            errors.append(name+': persönlicher absoluter Pfad')
        if len(data)>100*1024*1024:errors.append(name+': Datei größer als 100 MiB')
    manifest=json.loads((root/'data/example-archive.json').read_text())
    if len(manifest['reports'])!=5:errors.append('Beispielarchiv: nicht genau fünf Berichte')
    names={file.as_posix() for file in files}
    for item in manifest['reports']:
        for field,expected in (('pdf',item['id']),('analysis',item['analysis_sha256'])):
            name=item[field];path=root/name
            if name not in names:errors.append(name+': fehlt in Git-Auswahl');continue
            with path.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
            if digest!=expected:errors.append(name+': Prüfsumme stimmt nicht')
        report=json.loads((root/item['analysis']).read_text())
        if Path(report['metadata']['path']).is_absolute():errors.append(item['analysis']+': Beispielpfad ist nicht portabel')
    return files,errors


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--bundle',action='store_true');args=parser.parse_args()
    files,errors=audit()
    if errors:
        for error in errors:print('PRÜFEN:',error)
        return 1
    print(f'OK: {len(files)} Git-Dateien geprüft; fünf Beispiele vollständig; keine bekannten lokalen Schlüssel oder persönlichen Pfade gefunden.')
    if args.bundle:
        target=ROOT/'outputs/Stadtwerke-GitHub.zip';target.parent.mkdir(exist_ok=True)
        temporary=target.with_suffix('.zip.tmp')
        with ZipFile(temporary,'w',ZIP_DEFLATED) as archive:
            for relative in files:archive.write(ROOT/relative,'Stadtwerke/'+relative.as_posix())
        with ZipFile(temporary) as archive:
            if archive.testzip():raise RuntimeError('ZIP-Prüfung fehlgeschlagen')
        temporary.replace(target);print(target)
    return 0


if __name__=='__main__':raise SystemExit(main())
