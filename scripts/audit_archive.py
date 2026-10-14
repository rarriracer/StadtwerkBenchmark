"""Read-only audit of archived reports against independent regression controls."""
import hashlib
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import pypdfium2 as pdfium
from stadtwerke.config import ROOT
from stadtwerke.database import list_reports, load_report
from stadtwerke.calculation import available_metrics
from stadtwerke.workflow import SOURCE_RULES_VERSION, LAYOUT_VERSION


def matches(row, control):
    return (row.get('status') in ('validated','manual_checked') and row.get('metric')==control['metric']
        and row.get('page')==control['page'] and row.get('unit')==control['unit']
        and isinstance(row.get('value'),(int,float))
        and math.isclose(row['value'],control['value'],rel_tol=1e-9,abs_tol=1e-7)
        and (not control.get('entity') or row.get('entity')==control['entity'])
        and (not control.get('reporting_scope') or row.get('reporting_scope')==control['reporting_scope']))


def main():
    fixtures=ROOT/'tests/fixtures'
    corpus=json.loads((fixtures/'ingestion_pages.json').read_text())
    controls=json.loads((fixtures/'ingestion_expected.json').read_text())
    known={r['sha256']:name for name,r in corpus.items()}
    records=[]
    for rid,meta in list_reports():
        report=load_report(rid);observations=report['observations'];path=Path(meta['path'])
        name=known.get(rid)
        checks=[c for c in controls if c['report']==name]
        if 'Solingen' in meta['company']:
            expected={
                59:{'electricity_sales_total':(456951,'MWh'),'gas_sales_total':(869133,'MWh'),'water_sales':(10518000,'m³')},
                60:{'revenue':(312950000,'EUR'),'net_income':(4876000,'EUR'),'balance_total':(335864000,'EUR'),'investments':(22008000,'EUR')},
                62:{'water_network_length':(599,'km'),'water_network_connections':(32831,'Anzahl'),'water_network_meters':(33101,'Anzahl'),
                    'gas_network_length':(492.7,'km'),'gas_network_connections':(25941,'Anzahl'),'gas_network_meters':(36533,'Anzahl'),
                    'electricity_network_length':(1654.4,'km'),'electricity_network_connections':(35054,'Anzahl'),'electricity_network_meters':(109755,'Anzahl')}}
            checks=[dict(page=p,metric=m,value=v,unit=u) for p,rows in expected.items() for m,(v,u) in rows.items()]
        if rid=='b8606df77f1d9a0ac2af7c3717c30f5bbf9a7d96a348365734bed0c31293b9d3':
            checks=[dict(page=p,metric=m,value=v,unit=u) for p,m,v,u in [
                (6,'electricity_sales_total',347000,'MWh'),(2,'gas_sales_total',552000,'MWh'),(6,'heat_sales',316000,'MWh'),
                (2,'water_sales',5223000,'m³'),(13,'revenue',228492398.74,'EUR'),(12,'debt',52687549.95,'EUR'),
                (13,'interest_expense',3191240.64,'EUR'),(13,'net_income',-95068.72,'EUR'),
                (6,'electricity_customers',91483,'Anzahl'),(6,'gas_customers',21767,'Anzahl'),(2,'employees',360,'Anzahl')]]
        failed=[c for c in checks if not any(matches(r,c) for r in observations)]
        count=None;hash_ok=False
        if path.is_file():
            with path.open('rb') as f: hash_ok=hashlib.file_digest(f,'sha256').hexdigest()==rid
            pdf=pdfium.PdfDocument(path)
            try: count=len(pdf)
            finally:pdf.close()
        pages=[p['page'] for p in report['pages']]
        pages_ok=count is not None and pages==list(range(1,count+1))
        statuses=Counter(r.get('status') for r in observations)
        current=meta.get('source_rules_version')==SOURCE_RULES_VERSION and meta.get('layout_version')==LAYOUT_VERSION
        candidate=bool(checks) and not failed and not statuses['needs_review'] and not meta.get('extraction_errors') and pages_ok and hash_ok and bool(available_metrics(report))
        records.append(dict(id=rid,company=meta['company'],year=meta['year'],stored_pages=len(pages),physical_pages=count,pages_ok=pages_ok,hash_ok=hash_ok,
            statuses=dict(statuses),topics=len(available_metrics(report)),controls=len(checks),passed_controls=len(checks)-len(failed),failed_controls=failed,
            errors=len(meta.get('extraction_errors',[])),current_rules=current,source_rules_version=meta.get('source_rules_version'),layout_version=meta.get('layout_version'),
            provider=meta.get('provider','ollama' if meta.get('model','').startswith('qwen') else 'rules'),model=meta.get('model'),
            candidate=candidate,release_ready=False))
    out=ROOT/'outputs/archive-audit';out.mkdir(parents=True,exist_ok=True)
    (out/'summary.json').write_text(json.dumps({'checked_at':datetime.now(timezone.utc).isoformat(),'records':records},ensure_ascii=False,indent=2))
    lines=['# Prüfung des Berichtsarchivs','',f'Stand: {datetime.now().date().isoformat()}. {len(records)} archivierte Berichte. Die Prüfung liest das Archiv; sie verändert keine Analyse und startet keine Modell- oder Referenzanfragen.','',
        'Geprüft werden PDF-Prüfsumme, Zahl und Reihenfolge der Originalseiten, archivierte Kontrollwerte gegen unabhängig festgelegte Erwartungen, offene Prüfhinweise, technische Fehler und Regelversionen. Diese Kontrolle beweist nicht, dass jede Zahl sämtlicher Berichtsseiten semantisch vollständig erkannt wurde.','',
        '| Bericht | Jahr | Seiten vollständig | Kontrollwerte | Offene Zahlen | Vergleichsthemen | Aktuelle Regeln | Einordnung |',
        '|---|---:|---|---:|---:|---:|---|---|']
    for r in records:
        status='Kandidat; Regeln aktualisieren' if r['candidate'] and not r['current_rules'] else 'Kandidat für Schlussprüfung' if r['candidate'] else 'Weitere Prüfung erforderlich'
        lines.append(f"| {r['company']} | {r['year']} | {r['stored_pages']}/{r['physical_pages'] or '?'} {'✓' if r['pages_ok'] and r['hash_ok'] else 'offen'} | {r['passed_controls']}/{r['controls']} | {r['statuses'].get('needs_review',0)} | {r['topics']} | {'ja' if r['current_rules'] else 'nein'} | {status} |")
    lines += ['', '## Empfohlene Auswahl', '',
        'Flensburg, Karlsruhe, Leipzig und Münster sind Kandidaten ohne offene Zahlenprüfungen und mit unabhängigen Kontrollwerten. Solingen ist ein zusätzlicher Kandidat für ein abweichendes Geschäftsjahr. Vor dem Festsetzen sind ihre gespeicherten Analysen auf die aktuellen Layout- und Quellenregeln zu aktualisieren und die Kontrollen erneut auszuführen.', '',
        'Bremen 2024/2025 ist besonders gut kontrolliert (40 bzw. 36 Kontrollwerte, jeweils vollständige zentrale Kennzahlentabelle), enthält aber noch offene zusätzliche Angaben. München hat 17 geprüfte Kontrollwerte und zusätzliche offene Angaben. Diese Berichte erst nach Klärung der offenen Stellen als endgültige Beispiele übernehmen.', '',
        'Für Bonn, Aachen/STAWAG und Dresden fehlt in diesem Audit ein unabhängig festgelegter vollständiger Kontrollkatalog. Schwerin enthält einen belegten Widerspruch beim Wärmeabsatz. Stade hat keine auswählbaren Vergleichsthemen. Gütersloh liegt als einseitiger Auszug vor. Mainz bietet nur ein Vergleichsthema und enthält offene zusätzliche Angaben.', '',
        '## Was „fertig“ hier bedeutet', '',
        'Kein Bericht erhält derzeit die Freigabe „vollständig perfekt analysiert“. Der nächste überprüfbare Stand ist ein Beispielarchiv mit festgelegtem Kennzahlenumfang, belegten Werten, aktuellen Regeln, geklärten Prüfhinweisen und einem erfolgreichen Referenz- und Exportlauf. Die automatischen Kennzahlenfreigaben allein ersetzen den unabhängigen Kontrollkatalog nicht.', '',
        'Diese Prüfung ruft keine Live-Referenzen ab. Vorhandene frühere Referenzläufe (beispielsweise Solingen) sind separat dokumentiert; sie belegen nicht den aktuellen Ablauf nach den letzten Änderungen. Eine vollständige OpenRouter-Auswertung wurde für diese Auswahl ebenfalls nicht durchgeführt.', '',
        'Für Git empfiehlt sich später ein gezielter, reproduzierbarer Beispieldatensatz mit Prüfmanifest statt der gesamten Laufzeitdatenbank. `data/runtime/` ist bereits ausgeschlossen: API-Schlüssel, Sitzungen und Caches werden dadurch nicht als Beispielarchiv übernommen. Die fünf ausgewählten gespeicherten Analysen werden als portable Beispiele mitgeliefert; es wurde nichts veröffentlicht.', '',
        'Reproduktion: `PYTHONPATH=src .venv/bin/python scripts/audit_archive.py`. Details: `outputs/archive-audit/summary.json`.']
    lines=[line for line in lines if not line.startswith(('Bremen 2024/2025 ist','Für Bonn, Aachen/STAWAG'))]
    manifest_path=ROOT/'data/example-archive.json'
    if manifest_path.exists():
        manifest=json.loads(manifest_path.read_text())
        lines += ['', '## Beispielauswahl in der Anwendung', '',
            'Das Standardarchiv zeigt die fünf ausgewählten Berichte. Andere Analysen wurden aus dem Archiv entfernt; neue Uploads werden weiterhin aufgenommen.', '',
            '| Bericht | Themen | Kategorien |', '|---|---:|---|']
        for r in manifest['reports']:
            lines.append(f"| {r['company']} | {len(r['metrics'])} | {', '.join(r['categories'])} |")
        lines += ['', '„Bericht öffnen · Themen auswählen“ lädt die gespeicherte Analyse direkt in einen Themenwahl-Checkpoint. Dabei werden keine PDF-Seiten neu gelesen, keine Modellanfragen ausgeführt und keine Quellenregeln aktualisiert. Erst die Themenwahl startet den Referenzabruf. Eine Neuauswertung bleibt eine getrennte Aktion.']
    (ROOT/'docs/ARCHIV_PRUEFUNG.md').write_text('\n'.join(lines)+'\n')
    for r in records: print(r['company'],r['year'],f"Kontrollen {r['passed_controls']}/{r['controls']}",f"offen {r['statuses'].get('needs_review',0)}",'Kandidat' if r['candidate'] else 'offen')

if __name__=='__main__':main()
