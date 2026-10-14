"""Seed only packaged public examples, using paths relative to this checkout."""
import hashlib
import json
from pathlib import Path


def seed_examples(db, root):
    root=Path(root).resolve()
    manifest_path=root/'data/example-archive.json'
    if not manifest_path.exists():return
    manifest=json.loads(manifest_path.read_text())
    db.execute('CREATE TABLE IF NOT EXISTS example_imports (id VARCHAR PRIMARY KEY, version VARCHAR)')
    imported={r[0] for r in db.execute('SELECT id FROM example_imports').fetchall()}
    for item in manifest['reports']:
        if item['id'] in imported:continue
        analysis=(root/item['analysis']).resolve();pdf=(root/item['pdf']).resolve()
        if not analysis.is_relative_to(root) or not pdf.is_relative_to(root):
            raise ValueError('Beispielpfad liegt außerhalb des Projekts.')
        raw=analysis.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=item['analysis_sha256']:
            raise ValueError('Prüfsumme der Beispielanalyse stimmt nicht: '+analysis.name)
        with pdf.open('rb') as f:
            if hashlib.file_digest(f,'sha256').hexdigest()!=item['id']:
                raise ValueError('Prüfsumme des Beispiel-PDFs stimmt nicht: '+pdf.name)
        report=json.loads(raw)
        if report['id']!=item['id']:raise ValueError('Falsche Dokumentkennung im Beispielarchiv.')
        report['metadata']['path']=str(pdf)
        report['metadata']['example_report']=True
        # Never overwrite a newer upload or reviewed changes in this database.
        db.execute('INSERT INTO reports VALUES (?, ?, ?, ?, ?) ON CONFLICT DO NOTHING',
            [report['id'],json.dumps(report['metadata']),json.dumps(report['pages']),
             json.dumps(report['observations']),json.dumps(report['themes'])])
        db.execute('INSERT INTO example_imports VALUES (?, ?)',[item['id'],item['analysis_sha256']])
