from pathlib import Path
import json,time,re,collections,pdfplumber,sys,math
from stadtwerke.documents import read_pdf,detect_report_year
from stadtwerke.extraction import source_facts
from stadtwerke.review import report_findings
from stadtwerke.calculation import available_metrics
root=Path('data/research/ingestion-2026-10-07');out=Path('outputs/ingestion-audit');out.mkdir(parents=True,exist_ok=True)
files=[Path(p) for p in sys.argv[1:]] or sorted(root.glob('*.pdf')) or sorted(Path('Geschäftsberichte/Beispiele').glob('*.pdf'))
if not files:raise SystemExit('Keine PDFs gefunden. Die zu prüfenden Dateipfade als Argumente übergeben.')
fixture=Path('tests/fixtures/ingestion_pages.json')
corpus=json.loads(fixture.read_text()) if fixture.exists() else {}
known={r['sha256']:name for name,r in corpus.items()}
controls_path=Path('tests/fixtures/ingestion_expected.json')
expected=json.loads(controls_path.read_text()) if controls_path.exists() else []
for f in files:
 print('READ',f.name,flush=True);start=time.monotonic();rid,pages,themes=read_pdf(str(f));year=detect_report_year(pages)
 assert year, f'Year missing: {f}'
 observations=[r for p in pages for r in source_facts(p,year['year'])]
 losses=[];broken=[]
 with pdfplumber.open(f) as d:
  physical=len(d.pages)
  for p,original in zip(pages,d.pages):
   raw=original.within_bbox(original.bbox).dedupe_chars().extract_text(x_tolerance=2) or ''
   if p['layout']=='ocr':broken.append(p['page']);original.close();continue
   expected_chars=collections.Counter(c for c in raw if c.isalnum());actual_chars=collections.Counter(c for c in p['text'] if c.isalnum())
   if expected_chars-actual_chars:losses.append({'page':p['page'],'missing_characters':sum((expected_chars-actual_chars).values())})
   original.close()
 report={'id':rid,'metadata':{'year':year['year'],'path':str(f.resolve()),'company':f.stem,'page_count':physical,'source_scanned_pages':[p['page'] for p in pages]},'pages':pages,'themes':themes,'observations':observations}
 record={'file':str(f.resolve()),'pages':physical,'read_pages':len(pages),'year':year,'seconds':round(time.monotonic()-start,1),'tables':sum(len(p.get('tables',[])) for p in pages),'rows':sum(len(t['rows']) for p in pages for t in p.get('tables',[])),'visible_text_losses':losses,'ocr_pages':broken,'findings':report_findings(report),'options':list(available_metrics(report)),'report':report}
 controls=[c for c in expected if c['report']==known.get(rid)]
 failed=[c for c in controls if not any(r['metric']==c['metric'] and r['page']==c['page'] and r.get('unit')==c['unit'] and r.get('status')=='validated' and r.get('value') is not None and math.isclose(r['value'],c['value'],rel_tol=1e-9,abs_tol=1e-7) and (not c.get('reporting_scope') or c['reporting_scope']==r.get('reporting_scope')) and (not c.get('entity') or c['entity']==r.get('entity')) for r in observations)]
 record.update(controls=len(controls),failed_controls=failed)
 assert physical==len(pages) and not losses,(f,losses)
 assert not failed,(f,failed)
 (out/(f.stem+'-verified.json')).write_text(json.dumps(record,ensure_ascii=False,indent=2))
 print('RESULT',f.name,{k:record[k] for k in ['pages','read_pages','seconds','tables','rows','visible_text_losses','ocr_pages','options']},'findings',len(record['findings']),flush=True)
