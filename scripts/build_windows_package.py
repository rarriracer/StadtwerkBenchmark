"""Build a portable source bundle; never ship another OS's environment or models."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]


def build():
    files = [ROOT / name for name in (
        'app.py', 'pyproject.toml', 'uv.lock', 'README.md', '.gitignore', '.gitattributes',
        '.github/workflows/tests.yml', 'scripts/check_publish.py',
        'Windows einrichten.cmd', 'Stadtwerke starten.cmd',
        'scripts/start_app.py', 'scripts/build_windows_package.py', 'scripts/audit_report_ingestion.py',
        '.streamlit/config.toml',
        'data/reporting-calendars.json',
        'data/company-comparison-catalog.json',
        'data/research/company-source-audit-2026-10-13.json',
        'data/example-archive.json',
        'scripts/audit_archive.py',
    )]
    for folder, pattern in [('src', '*.py'), ('tests', '*.py'), ('assets', '*.css'), ('docs', '*.md')]:
        files.extend((ROOT / folder).rglob(pattern))
    files.extend((ROOT/'tests'/'fixtures').rglob('*.json'))
    files.extend((ROOT/'assets'/'screenshots').glob('*.jpg'))
    files.extend((ROOT/'data/examples').glob('*.json'))
    files.extend((ROOT/'Geschäftsberichte/Beispiele').glob('*'))
    files.append(ROOT/'Geschäftsberichte/00_Uebersicht.md')
    target = ROOT / 'outputs' / 'Stadtwerke-Windows.zip'
    target.parent.mkdir(exist_ok=True)
    temporary=target.with_suffix('.zip.tmp')
    with ZipFile(temporary, 'w', ZIP_DEFLATED) as archive:
        for path in sorted(files):
            name = 'Stadtwerke/' + path.relative_to(ROOT).as_posix()
            archive.write(path, name)
    with ZipFile(temporary) as archive:
        if archive.testzip():
            raise RuntimeError('ZIP-Pruefung fehlgeschlagen')
    temporary.replace(target)
    print(target)
    return target


if __name__ == '__main__':
    build()
